from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.core.config import get_settings
from app.llm.factory import get_chat_model, get_ollama_chat_model
from app.memory.file_chat_memory import FileChatMemory


SYSTEM_PROMPT = """你是 AI 恋爱大师，擅长提供真诚、尊重、理性且可执行的情感沟通建议。
你应该帮助用户理解关系中的沟通问题，避免操控、骚扰、PUA 或越界行为。
如果用户表达自伤、伤害他人或严重心理危机风险，应建议尽快联系可信任的人或专业机构。"""


class LoveApp:
    def __init__(self, memory: FileChatMemory | None = None) -> None:
        self.memory = memory or FileChatMemory()

    def chat(self, message: str, chat_id: str) -> str:
        safe_chat_id = self.memory.sanitize_chat_id(chat_id)
        history = self.memory.load_messages(safe_chat_id)
        messages = self._build_messages(history, message)
        self.memory.append_message(safe_chat_id, "user", message)

        try:
            model = get_chat_model(streaming=False)
            response = model.invoke(messages)
        except Exception:
            if not get_settings().enable_ollama_fallback:
                raise
            model = get_ollama_chat_model()
            response = model.invoke(messages)

        answer = self._content_to_text(response.content)
        self.memory.append_message(safe_chat_id, "assistant", answer)
        return answer

    async def chat_stream(self, message: str, chat_id: str) -> AsyncIterator[str]:
        safe_chat_id = self.memory.sanitize_chat_id(chat_id)
        history = self.memory.load_messages(safe_chat_id)
        messages = self._build_messages(history, message)
        self.memory.append_message(safe_chat_id, "user", message)

        chunks: list[str] = []
        try:
            model = get_chat_model(streaming=True)
            async for chunk in model.astream(messages):
                text = self._content_to_text(chunk.content)
                if not text:
                    continue
                chunks.append(text)
                yield text
        except Exception:
            if chunks or not get_settings().enable_ollama_fallback:
                raise
            model = get_ollama_chat_model()
            async for chunk in model.astream(messages):
                text = self._content_to_text(chunk.content)
                if not text:
                    continue
                chunks.append(text)
                yield text

        self.memory.append_message(safe_chat_id, "assistant", "".join(chunks))

    def _build_messages(self, history: list[dict], message: str) -> list:
        messages = [SystemMessage(content=SYSTEM_PROMPT)]
        for item in history:
            role = item.get("role")
            content = item.get("content", "")
            if not content:
                continue
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
        messages.append(HumanMessage(content=message))
        return messages

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
