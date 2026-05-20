from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any

from app.core.config import get_settings


class HtmlStepLogger:
    def __init__(self, chat_id: str, title: str = "HuManus Agent Run") -> None:
        settings = get_settings()
        run_dir = settings.manus_log_dir / "manus-runs"
        run_dir.mkdir(parents=True, exist_ok=True)
        safe_chat_id = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in chat_id)[:80] or "default"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.path = run_dir / f"{safe_chat_id}-{timestamp}.html"
        self.title = title
        self._write_header()

    def start(self, user_task: str) -> None:
        self.append_section("任务开始", {"user_task": user_task})

    def log_step(self, step: Any) -> None:
        payload = step.to_dict() if hasattr(step, "to_dict") else dict(step)
        self.append_section(f"Step {payload.get('index', '')}", payload)

    def finish(self, answer: str, reason: str) -> None:
        self.append_section("任务结束", {"answer": answer, "reason": reason})
        with self.path.open("a", encoding="utf-8") as file:
            file.write("</div></body></html>\n")

    def append_section(self, heading: str, payload: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(f"<h2>{escape(str(heading))}</h2>\n<table>\n")
            for key, value in payload.items():
                file.write("<tr>")
                file.write(f"<th>{escape(str(key))}</th>")
                file.write(f"<td><pre>{escape(str(value))}</pre></td>")
                file.write("</tr>\n")
            file.write("</table>\n")

    def _write_header(self) -> None:
        content = f"""<!DOCTYPE html>
<html lang=\"zh-CN\"><head><meta charset=\"UTF-8\" />
<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
<title>{escape(self.title)}</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',Arial,sans-serif;line-height:1.7;background:#f6f8fb;color:#1f2937;padding:28px}}.container{{max-width:1080px;margin:0 auto;background:#fff;border-radius:16px;padding:32px;box-shadow:0 10px 30px rgba(15,23,42,.08)}}h1{{margin-top:0}}h2{{border-left:5px solid #2563eb;padding-left:12px;margin-top:28px}}table{{width:100%;border-collapse:collapse;margin:12px 0}}td,th{{border:1px solid #e5e7eb;padding:10px;text-align:left;vertical-align:top}}th{{width:180px;background:#f3f4f6}}pre{{white-space:pre-wrap;margin:0;font-family:Consolas,monospace}}</style>
</head><body><div class=\"container\"><h1>{escape(self.title)}</h1><p>创建时间：{datetime.now().isoformat()}</p>
"""
        self.path.write_text(content, encoding="utf-8")
