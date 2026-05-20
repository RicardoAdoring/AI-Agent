from app.core.config import get_settings
from app.mcp.config import load_mcp_config


class McpClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def status(self) -> dict:
        servers = load_mcp_config(self.settings.mcp_config_path)
        return {
            "enabled": self.settings.mcp_enabled,
            "config_path": str(self.settings.mcp_config_path.as_posix()),
            "servers": [server.__dict__ for server in servers],
            "tools": [] if not self.settings.mcp_enabled else self.list_tools(),
        }

    def list_tools(self) -> list[dict]:
        if not self.settings.mcp_enabled:
            return []
        return []

    async def call_tool(self, name: str, args: dict) -> dict:
        if not self.settings.mcp_enabled:
            return {"success": False, "error": "MCP is disabled"}
        return {"success": False, "error": "MCP transport is not implemented in this MVP"}
