import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.schema import AgentRunResult, AgentState, AgentStep
from app.core.config import get_settings
from app.llm.factory import get_chat_model, get_ollama_chat_model
from app.services.html_step_logger import HtmlStepLogger
from app.tools.registry import get_tool_map, list_tools_for_prompt

SYSTEM_PROMPT = """你是 HuManus 全流程智能体。你必须以严格 JSON 回复下一步动作。
可用工具由 tools 列表给出。每一步只能选择一个 action。
禁止要求或执行任意终端命令；文件操作只能在工作区内；不要编造工具结果。
如果任务已经完成，action 使用 final 或 terminate。
输出 JSON 格式：{"thought":"思考","action":"工具名或final","action_input":{},"final_answer":"最终答案或空字符串"}。"""


class YuManusAgent:
    def __init__(self, chat_id: str = "manus-default", max_steps: int | None = None) -> None:
        settings = get_settings()
        self.chat_id = chat_id
        self.max_steps = max_steps or settings.manus_max_steps
        self.state = AgentState.IDLE
        self.tools = get_tool_map()
        self.steps: list[AgentStep] = []
        self.observations: list[str] = []
        self.logger = HtmlStepLogger(chat_id, "HuManus YuManus Agent Run")

    async def run(self, task: str) -> AgentRunResult:
        self.state = AgentState.RUNNING
        self.logger.start(task)
        answer = ""
        reason = "max_steps"
        try:
            for index in range(1, self.max_steps + 1):
                step = await self._run_step(index, task)
                self.steps.append(step)
                self.logger.log_step(step)
                if step.action in {"final", "terminate"}:
                    answer = step.observation or step.thought or "任务已完成。"
                    reason = "finished"
                    self.state = AgentState.FINISHED
                    break
            if not answer:
                answer = "已达到最大步骤限制，任务自动结束。"
                self.state = AgentState.FINISHED
        except Exception as exc:
            self.state = AgentState.ERROR
            answer = f"Agent 执行失败：{exc}"
            reason = "error"
        self.logger.finish(answer, reason)
        return AgentRunResult(answer=answer, steps=self.steps, log_path=str(self.logger.path.as_posix()), finished_reason=reason)

    async def _run_step(self, index: int, task: str) -> AgentStep:
        decision = self._decide(task)
        step = AgentStep(
            index=index,
            thought=str(decision.get("thought") or ""),
            action=str(decision.get("action") or "final"),
            action_input=decision.get("action_input") if isinstance(decision.get("action_input"), dict) else {},
        )
        if step.action == "final":
            step.observation = str(decision.get("final_answer") or step.thought or "任务已完成。")
            step.status = "finished"
            return step
        if step.action not in self.tools:
            step.observation = f"未知工具：{step.action}。任务结束。"
            step.action = "final"
            step.status = "finished"
            return step
        result = await self.tools[step.action].run(**step.action_input)
        step.observation = result.content if result.success else result.error or "工具执行失败"
        step.status = "success" if result.success else "error"
        if step.action == "terminate" or result.metadata.get("terminated"):
            step.action = "terminate"
            step.status = "finished"
        self.observations.append(f"Step {index} {step.action}: {step.observation}")
        return step

    def _decide(self, task: str) -> dict[str, Any]:
        prompt = {
            "task": task,
            "tools": list_tools_for_prompt(),
            "previous_observations": self.observations[-8:],
            "instruction": "Return strict JSON only. Choose one tool, final, or terminate.",
        }
        messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=json.dumps(prompt, ensure_ascii=False))]
        try:
            model = get_chat_model(streaming=False)
            response = model.invoke(messages)
        except Exception:
            if not get_settings().enable_ollama_fallback:
                raise
            model = get_ollama_chat_model()
            response = model.invoke(messages)
        return self._parse_decision(self._content_to_text(response.content))

    def _parse_decision(self, text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        return {"thought": cleaned, "action": "final", "action_input": {}, "final_answer": cleaned}

    def _content_to_text(self, content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or ""))
            return "".join(parts)
        return str(content)
