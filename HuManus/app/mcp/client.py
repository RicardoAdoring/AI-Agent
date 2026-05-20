import asyncio
import json
from typing import Any

from app.core.config import get_settings
from app.mcp.config import McpServerConfig, load_mcp_config


class McpClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def status(self) -> dict:
        servers = load_mcp_config(self.settings.mcp_config_path)
        return {
            "enabled": self.settings.mcp_enabled,
            "config_path": str(self.settings.mcp_config_path.as_posix()),
            "servers": [self._server_status(server) for server in servers],
            "tools": [] if not self.settings.mcp_enabled else self.list_tools(),
        }

    def list_tools(self) -> list[dict]:
        if not self.settings.mcp_enabled:
            return []
        return asyncio.run(self.list_tools_async())

    async def list_tools_async(self) -> list[dict]:
        if not self.settings.mcp_enabled:
            return []
        tools = []
        for server in self._enabled_servers():
            try:
                async with self._session(server) as session:
                    result = await asyncio.wait_for(session.list_tools(), timeout=self.settings.mcp_tool_call_timeout_seconds)
                    for tool in result.tools:
                        tools.append(
                            {
                                "server": server.name,
                                "name": tool.name,
                                "description": tool.description or "",
                                "input_schema": tool.inputSchema,
                            }
                        )
            except Exception as exc:
                tools.append({"server": server.name, "error": str(exc)})
        return tools

    async def call_tool(self, name: str, args: dict) -> dict:
        if not self.settings.mcp_enabled:
            return {"success": False, "error": "MCP is disabled"}
        server_name, tool_name = self._split_tool_name(name)
        for server in self._enabled_servers():
            if server_name and server.name != server_name:
                continue
            try:
                async with self._session(server) as session:
                    tools = await asyncio.wait_for(session.list_tools(), timeout=self.settings.mcp_tool_call_timeout_seconds)
                    if tool_name not in {tool.name for tool in tools.tools}:
                        continue
                    result = await asyncio.wait_for(session.call_tool(tool_name, arguments=args), timeout=self.settings.mcp_tool_call_timeout_seconds)
                    return {
                        "success": not bool(getattr(result, "isError", False)),
                        "server": server.name,
                        "tool": tool_name,
                        "content": self._content_to_text(getattr(result, "content", [])),
                        "structured_content": getattr(result, "structuredContent", None),
                    }
            except Exception as exc:
                return {"success": False, "server": server.name, "tool": tool_name, "error": str(exc)}
        return {"success": False, "error": f"MCP tool not found: {name}"}

    def _enabled_servers(self) -> list[McpServerConfig]:
        return [server for server in load_mcp_config(self.settings.mcp_config_path) if server.enabled and server.command]

    def _server_status(self, server: McpServerConfig) -> dict:
        return {
            "name": server.name,
            "command": server.command,
            "args": server.args,
            "enabled": server.enabled,
            "env_keys": sorted(server.env.keys()),
        }

    def _split_tool_name(self, name: str) -> tuple[str | None, str]:
        if ":" in name:
            server, tool = name.split(":", 1)
            return server.strip() or None, tool.strip()
        return None, name.strip()

    def _content_to_text(self, content: list[Any]) -> str:
        parts = []
        for item in content:
            text = getattr(item, "text", None)
            if text is not None:
                parts.append(str(text))
            else:
                parts.append(json.dumps(item, ensure_ascii=False, default=str))
        return "\n".join(parts)

    def _session(self, server: McpServerConfig):
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        params = StdioServerParameters(command=server.command, args=server.args, env=server.env)

        class SessionContext:
            async def __aenter__(self_inner):
                self_inner.stdio = stdio_client(params)
                self_inner.read, self_inner.write = await self_inner.stdio.__aenter__()
                self_inner.session = ClientSession(self_inner.read, self_inner.write)
                self_inner.client = await self_inner.session.__aenter__()
                await self_inner.client.initialize()
                return self_inner.client

            async def __aexit__(self_inner, exc_type, exc, tb):
                await self_inner.session.__aexit__(exc_type, exc, tb)
                await self_inner.stdio.__aexit__(exc_type, exc, tb)

        return SessionContext()
