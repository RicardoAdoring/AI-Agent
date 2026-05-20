from collections.abc import AsyncIterator

from app.agents.langgraph_manus import LangGraphManusAgent
from app.agents.yumanus import YuManusAgent
from app.core.config import get_settings


def sse_data(text: str) -> str:
    lines = str(text).splitlines() or [""]
    return "".join(f"data: {line}\n" for line in lines) + "\n"


class ManusApp:
    async def chat(self, message: str, chat_id: str = "manus-default") -> dict:
        agent = self._agent(chat_id)
        result = await agent.run(message)
        return result.to_dict()

    async def chat_stream(self, message: str, chat_id: str = "manus-default") -> AsyncIterator[str]:
        agent = self._agent(chat_id)
        result = await agent.run(message)
        for step in result.steps:
            text = step.observation or step.thought
            if text:
                yield sse_data(text)
        yield sse_data(f"日志文件：{result.log_path}")
        yield sse_data("[DONE]")

    def _agent(self, chat_id: str):
        if get_settings().agent_backend.lower().strip() == "legacy":
            return YuManusAgent(chat_id=chat_id)
        return LangGraphManusAgent(chat_id=chat_id)
