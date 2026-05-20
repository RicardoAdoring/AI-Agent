from pathlib import Path

import httpx

from app.core.config import get_settings
from app.tools.base import BaseTool, ToolResult
from app.tools.safety import ensure_safe_url, safe_output_path


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web when a search provider is configured."
    args_schema = {"query": "search query"}

    async def run(self, **kwargs) -> ToolResult:
        settings = get_settings()
        query = str(kwargs.get("query") or "").strip()
        if not query:
            return ToolResult(self.name, False, "", error="query is required")
        if settings.manus_search_provider == "placeholder":
            return ToolResult(
                self.name,
                False,
                "",
                error="Web search provider is not configured. Set MANUS_SEARCH_PROVIDER and MANUS_SEARCH_API_KEY.",
                metadata={"query": query},
            )
        return ToolResult(self.name, False, "", error=f"Unsupported search provider: {settings.manus_search_provider}")


class WebScrapeTool(BaseTool):
    name = "web_scrape"
    description = "Fetch a public HTTP/HTTPS page and return trimmed text. Private network URLs are blocked by default."
    args_schema = {"url": "public http or https URL"}

    async def run(self, **kwargs) -> ToolResult:
        settings = get_settings()
        url = str(kwargs.get("url") or "").strip()
        try:
            safe_url = ensure_safe_url(url)
            async with httpx.AsyncClient(timeout=settings.manus_http_timeout_seconds, follow_redirects=True) as client:
                response = await client.get(safe_url)
                response.raise_for_status()
            text = " ".join(response.text.split())[:20000]
            return ToolResult(self.name, True, text, metadata={"url": safe_url, "status_code": response.status_code})
        except Exception as exc:
            return ToolResult(self.name, False, "", error=str(exc), metadata={"url": url})


class ResourceDownloadTool(BaseTool):
    name = "resource_download"
    description = "Download a public HTTP/HTTPS resource into the Manus downloads directory with size limits."
    args_schema = {"url": "public resource URL", "file_name": "safe output file name"}

    async def run(self, **kwargs) -> ToolResult:
        settings = get_settings()
        url = str(kwargs.get("url") or "").strip()
        file_name = str(kwargs.get("file_name") or Path(url).name or "download.bin")
        try:
            safe_url = ensure_safe_url(url)
            output_path = safe_output_path(file_name, settings.manus_download_dir)
            total = 0
            async with httpx.AsyncClient(timeout=settings.manus_http_timeout_seconds, follow_redirects=True) as client:
                async with client.stream("GET", safe_url) as response:
                    response.raise_for_status()
                    with output_path.open("wb") as file:
                        async for chunk in response.aiter_bytes():
                            total += len(chunk)
                            if total > settings.manus_max_download_bytes:
                                raise ValueError("Download exceeds max allowed size")
                            file.write(chunk)
            return ToolResult(self.name, True, f"Downloaded {total} bytes", metadata={"path": str(output_path.as_posix()), "url": safe_url, "bytes": total})
        except Exception as exc:
            return ToolResult(self.name, False, "", error=str(exc), metadata={"url": url})
