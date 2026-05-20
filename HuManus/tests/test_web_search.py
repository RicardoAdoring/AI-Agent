import pytest

from app.core.config import get_settings
from app.tools.web_tools import WebSearchTool


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "organic_results": [
                {"title": "结果一", "link": "https://example.com/1", "snippet": "摘要一"},
                {"title": "结果二", "url": "https://example.com/2", "description": "摘要二"},
            ]
        }


class FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self.request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def get(self, url, params=None):
        self.request = (url, params)
        return FakeResponse()


@pytest.mark.asyncio
async def test_searchapi_returns_normalized_results(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "manus_search_provider", "searchapi")
    monkeypatch.setattr(settings, "manus_search_api_key", "key")
    monkeypatch.setattr(settings, "manus_search_top_k", 1)
    monkeypatch.setattr("app.tools.web_tools.httpx.AsyncClient", FakeAsyncClient)

    result = await WebSearchTool().run(query="HuManus")

    assert result.success is True
    assert "结果一" in result.content
    assert "结果二" not in result.content
    assert result.metadata["results"][0]["url"] == "https://example.com/1"


@pytest.mark.asyncio
async def test_searchapi_requires_key(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "manus_search_provider", "searchapi")
    monkeypatch.setattr(settings, "manus_search_api_key", "")

    result = await WebSearchTool().run(query="HuManus")

    assert result.success is False
    assert "MANUS_SEARCH_API_KEY" in result.error
