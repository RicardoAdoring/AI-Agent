from app.tools.base import BaseTool, ToolResult


class TerminalCommandTool(BaseTool):
    name = "terminal_command"
    description = "Disabled terminal command tool. Arbitrary command execution is not available in the Python MVP."
    args_schema = {"command": "command string"}

    async def run(self, **kwargs) -> ToolResult:
        return ToolResult(
            self.name,
            False,
            "",
            error="Terminal command execution is disabled in HuManus Python MVP for safety.",
        )
