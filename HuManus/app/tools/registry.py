from app.tools.base import BaseTool
from app.tools.file_tools import ReadFileTool, WriteFileTool
from app.tools.pdf_tools import PdfGenerationTool
from app.tools.terminate import TerminateTool
from app.tools.web_tools import ResourceDownloadTool, WebScrapeTool, WebSearchTool


def get_default_tools() -> list[BaseTool]:
    return [
        ReadFileTool(),
        WriteFileTool(),
        WebSearchTool(),
        WebScrapeTool(),
        ResourceDownloadTool(),
        PdfGenerationTool(),
        TerminateTool(),
    ]


def get_tool_map() -> dict[str, BaseTool]:
    return {tool.name: tool for tool in get_default_tools()}


def list_tools_for_prompt() -> list[dict]:
    return [tool.prompt_spec() for tool in get_default_tools()]
