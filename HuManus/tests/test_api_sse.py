from fastapi.testclient import TestClient

from app.main import app
from app.api import ai


class FakeLoveApp:
    async def chat_stream(self, message, chat_id):
        yield "第一行\n第二行"


class FakeManusApp:
    async def chat_stream(self, message, chat_id):
        yield "data: manus-ok\n\n"
        yield "data: [DONE]\n\n"


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_love_app_sse_escapes_multiline_chunks(monkeypatch):
    monkeypatch.setattr(ai, "love_app", FakeLoveApp())
    client = TestClient(app)

    response = client.get("/api/ai/love_app/chat/sse", params={"message": "hi", "chatId": "test"})

    assert response.status_code == 200
    assert "data: 第一行\ndata: 第二行\n\ndata: [DONE]\n\n" in response.text


def test_manus_sse_contract(monkeypatch):
    monkeypatch.setattr(ai, "manus_app", FakeManusApp())
    client = TestClient(app)

    response = client.get("/api/ai/manus/chat", params={"message": "hi", "chatId": "test"})

    assert response.status_code == 200
    assert response.text.endswith("data: [DONE]\n\n")
