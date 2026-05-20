import json
from dataclasses import dataclass, field
from pathlib import Path


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
    servers = data.get("servers", [])
    result = []
    for item in servers:
        if not isinstance(item, dict):
            continue
        result.append(
            McpServerConfig(
                name=str(item.get("name") or "unnamed"),
                command=str(item.get("command") or ""),
                args=list(item.get("args") or []),
                env=dict(item.get("env") or {}),
                enabled=bool(item.get("enabled", False)),
            )
        )
    return result
