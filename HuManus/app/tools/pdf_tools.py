from xml.sax.saxutils import escape

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.core.config import get_settings
from app.tools.base import BaseTool, ToolResult
from app.tools.safety import safe_output_path


class PdfGenerationTool(BaseTool):
    name = "generate_pdf"
    description = "Generate a PDF file from plain text content in the Manus output directory."
    args_schema = {"title": "PDF title", "content": "plain text content", "file_name": "output PDF file name"}

    async def run(self, **kwargs) -> ToolResult:
        settings = get_settings()
        title = str(kwargs.get("title") or "HuManus Report")
        content = str(kwargs.get("content") or "")
        file_name = str(kwargs.get("file_name") or "report.pdf")
        if not file_name.lower().endswith(".pdf"):
            file_name += ".pdf"
        try:
            path = safe_output_path(file_name, settings.manus_output_dir)
            doc = SimpleDocTemplate(str(path))
            styles = getSampleStyleSheet()
            story = [Paragraph(escape(title), styles["Title"]), Spacer(1, 12)]
            for paragraph in content.split("\n"):
                if paragraph.strip():
                    story.append(Paragraph(escape(paragraph.strip()), styles["Normal"]))
                    story.append(Spacer(1, 8))
            doc.build(story)
            return ToolResult(self.name, True, f"Generated PDF: {path.name}", metadata={"path": str(path.as_posix()), "bytes": path.stat().st_size})
        except Exception as exc:
            return ToolResult(self.name, False, "", error=str(exc))
