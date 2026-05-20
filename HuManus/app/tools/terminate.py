from app.tools.base import BaseTool, ToolResult


class TerminateTool(BaseTool):
    name = "terminate"
    description = "Finish the current Manus task with a final answer."
    args_schema = {"answer": "final answer", "reason": "optional finish reason"}

    async def run(self, **kwargs) -> ToolResult:
        answer = str(kwargs.get("answer") or "任务已完成。")
        reason = str(kwargs.get("reason") or "finished")
        return ToolResult(self.name, True, answer, metadata={"terminated": True, "reason": reason})
