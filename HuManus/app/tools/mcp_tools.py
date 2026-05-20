from app.mcp.client import McpClient
from app.tools.base import BaseTool, ToolResult


class McpToolProxy(BaseTool):
    name = "mcp_tool_proxy"
    description = "MCP tool proxy stub. Real MCP transport is not enabled in the MVP."
    args_schema = {"tool_name": "MCP tool name", "args": "MCP tool arguments object"}

    async def run(self, **kwargs) -> ToolResult:
        tool_name = str(kwargs.get("tool_name") or "")
        args = kwargs.get("args") if isinstance(kwargs.get("args"), dict) else {}
        result = await McpClient().call_tool(tool_name, args)
        return ToolResult(self.name, bool(result.get("success")), str(result), error=result.get("error"))
