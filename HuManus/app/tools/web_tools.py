from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.tools.base import BaseTool, ToolResult
from app.tools.safety import ensure_safe_url, safe_output_path


class WebSearchTool(BaseTool):
    name = "web_search"
    description = "Search the web with a configured provider and return ranked results with source URLs."
    args_schema = {"query": "search query"}

    async def run(self, **kwargs) -> ToolResult:
        settings = get_settings()
        query = str(kwargs.get("query") or "").strip()
        if not query:
            return ToolResult(self.name, False, "", error="query is required")

        provider = settings.manus_search_provider.lower().strip()
        if provider == "placeholder":
            return ToolResult(
                self.name,
                False,
                "",
                error="Web search provider is not configured. Set MANUS_SEARCH_PROVIDER and MANUS_SEARCH_API_KEY.",
                metadata={"query": query},
            )
        if provider == "searchapi":
            return await self._searchapi(query)
        return ToolResult(self.name, False, "", error=f"Unsupported search provider: {settings.manus_search_provider}")

    async def _searchapi(self, query: str) -> ToolResult:
        settings = get_settings()
        if not settings.manus_search_api_key:
            return ToolResult(self.name, False, "", error="MANUS_SEARCH_API_KEY is required for searchapi", metadata={"query": query})

        params = {
            "q": query,
            "api_key": settings.manus_search_api_key,
            "engine": settings.manus_search_engine,
        }
        try:
            async with httpx.AsyncClient(timeout=settings.manus_http_timeout_seconds) as client:
                response = await client.get(str(settings.manus_search_base_url), params=params)
                response.raise_for_status()
            payload = response.json()
            results = self._normalize_searchapi_results(payload)
            limit = max(1, settings.manus_search_top_k)
            results = results[:limit]
            if not results:
                return ToolResult(self.name, True, "No search results found.", metadata={"query": query, "results": []})
            content = "\n".join(
                f"{item['rank']}. {item['title']}\nURL: {item['url']}\n摘要: {item['snippet']}"
                for item in results
            )
            return ToolResult(self.name, True, content[:12000], metadata={"query": query, "provider": "searchapi", "results": results})
        except Exception as exc:
            return ToolResult(self.name, False, "", error=str(exc), metadata={"query": query, "provider": "searchapi"})

    def _normalize_searchapi_results(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        raw_results = payload.get("organic_results") or payload.get("results") or []
        results = []
        for index, item in enumerate(raw_results, start=1):
            if not isinstance(item, dict):
                continue
            url = str(item.get("link") or item.get("url") or "").strip()
            title = str(item.get("title") or "Untitled").strip()
            snippet = str(item.get("snippet") or item.get("description") or "").strip()
            if not url:
                continue
            results.append({"rank": index, "title": title, "url": url, "snippet": snippet})
        return results


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
