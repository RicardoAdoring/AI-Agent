import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import get_settings


@dataclass
class McpServerConfig:
    name: str
    command: str = ""
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    enabled: bool = False


def load_mcp_config(path: Path | str) -> list[McpServerConfig]:
    config_path = Path(path)
    if not config_path.exists():
        return []
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if isinstance(data.get("mcpServers"), dict):
        return _load_claude_style_servers(data["mcpServers"])
    servers = data.get("servers", [])
    result = []
    for item in servers:
        if not isinstance(item, dict):
            continue
        result.append(
            McpServerConfig(
                name=str(item.get("name") or "unnamed"),
                command=str(item.get("command") or ""),
                args=[str(arg) for arg in item.get("args") or []],
                env=_resolve_env(dict(item.get("env") or {})),
                enabled=bool(item.get("enabled", False)),
            )
        )
    return result


def _load_claude_style_servers(items: dict) -> list[McpServerConfig]:
    result = []
    for name, item in items.items():
        if not isinstance(item, dict):
            continue
        result.append(
            McpServerConfig(
                name=str(name),
                command=str(item.get("command") or ""),
                args=[str(arg) for arg in item.get("args") or []],
                env=_resolve_env(dict(item.get("env") or {})),
                enabled=bool(item.get("enabled", True)),
            )
        )
    return result


def _resolve_env(values: dict[str, str]) -> dict[str, str]:
    settings = get_settings()
    resolved = {}
    for key, value in values.items():
        text = str(value)
        if text in {"${AMAP_MAPS_API_KEY}", "$AMAP_MAPS_API_KEY", "your-amap-api-key", "你的 API Key"}:
            text = settings.amap_maps_api_key or os.getenv("AMAP_MAPS_API_KEY", "")
        elif text.startswith("${") and text.endswith("}"):
            text = os.getenv(text[2:-1], "")
        resolved[str(key)] = text
    return resolved
