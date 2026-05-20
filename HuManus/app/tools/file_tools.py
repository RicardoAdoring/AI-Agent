from app.tools.base import BaseTool, ToolResult
from app.tools.safety import ensure_safe_path


class ReadFileTool(BaseTool):
    name = "read_file"
    description = "Read a UTF-8 text file from the Manus workspace."
    args_schema = {"path": "relative file path inside the workspace"}

    async def run(self, **kwargs) -> ToolResult:
        path_value = str(kwargs.get("path") or "")
        try:
            path = ensure_safe_path(path_value)
            if not path.exists() or not path.is_file():
                raise FileNotFoundError("File does not exist")
            content = path.read_text(encoding="utf-8", errors="ignore")
            return ToolResult(self.name, True, content[:20000], metadata={"path": str(path.as_posix())})
        except Exception as exc:
            return ToolResult(self.name, False, "", error=str(exc))


class WriteFileTool(BaseTool):
    name = "write_file"
    description = "Write UTF-8 text to a file inside the Manus workspace."
    args_schema = {"path": "relative file path inside the workspace", "content": "text content to write"}

    async def run(self, **kwargs) -> ToolResult:
        path_value = str(kwargs.get("path") or "")
        content = str(kwargs.get("content") or "")
        try:
            path = ensure_safe_path(path_value)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return ToolResult(self.name, True, f"Wrote {len(content)} characters to {path.name}", metadata={"path": str(path.as_posix())})
        except Exception as exc:
            return ToolResult(self.name, False, "", error=str(exc))
