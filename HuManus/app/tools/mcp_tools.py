from app.mcp.client import McpClient
from app.tools.base import BaseTool, ToolResult


class McpToolProxy(BaseTool):
    name = "mcp_tool_proxy"
    description = "Call an enabled MCP tool. Use tool_name as either '<server>:<tool>' or '<tool>'."
    args_schema = {"tool_name": "MCP tool name, optionally prefixed with server:", "args": "MCP tool arguments object"}

    async def run(self, **kwargs) -> ToolResult:
        tool_name = str(kwargs.get("tool_name") or "").strip()
        args = kwargs.get("args") if isinstance(kwargs.get("args"), dict) else {}
        if not tool_name:
            return ToolResult(self.name, False, "", error="tool_name is required")
        result = await McpClient().call_tool(tool_name, args)
        return ToolResult(
            self.name,
            bool(result.get("success")),
            str(result.get("content") or result.get("structured_content") or ""),
            error=result.get("error"),
            metadata={key: value for key, value in result.items() if key not in {"content", "error"}},
        )
