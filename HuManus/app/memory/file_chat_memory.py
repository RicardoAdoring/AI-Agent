import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings


class FileChatMemory:
    def __init__(self, memory_dir: Path | None = None, max_messages: int | None = None) -> None:
        settings = get_settings()
        self.memory_dir = memory_dir or settings.chat_memory_dir
        self.max_messages = max_messages or settings.max_history_messages
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def load_messages(self, chat_id: str) -> list[dict[str, Any]]:
        path = self._path_for(chat_id)
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def append_message(self, chat_id: str, role: str, content: str) -> None:
        messages = self.load_messages(chat_id)
        messages.append(
            {
                "role": role,
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        self.save_messages(chat_id, messages)

    def save_messages(self, chat_id: str, messages: list[dict[str, Any]]) -> None:
        trimmed = self.trim_messages(messages)
        path = self._path_for(chat_id)
        path.write_text(json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8")

    def trim_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.max_messages <= 0:
            return messages
        return messages[-self.max_messages :]

    def sanitize_chat_id(self, chat_id: str | None) -> str:
        if not chat_id:
            return "default"
        clean = re.sub(r"[^a-zA-Z0-9_-]", "_", chat_id.strip())
        return clean[:100] or "default"

    def _path_for(self, chat_id: str) -> Path:
        safe_chat_id = self.sanitize_chat_id(chat_id)
        return self.memory_dir / f"{safe_chat_id}.json"
