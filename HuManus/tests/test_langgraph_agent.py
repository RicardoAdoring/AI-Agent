import pytest

from app.agents.langgraph_manus import LangGraphManusAgent
from app.core.config import get_settings


class FakeResponse:
    content = '{"thought":"done","action":"final","action_input":{},"final_answer":"agent-ok"}'


class FakeModel:
    def invoke(self, messages):
        return FakeResponse()


@pytest.mark.asyncio
async def test_langgraph_agent_returns_final_answer(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "agent_checkpoint_path", tmp_path / "checkpoints.sqlite")
    monkeypatch.setattr("app.agents.langgraph_manus.get_chat_model", lambda streaming=False: FakeModel())

    result = await LangGraphManusAgent(chat_id="test-agent", max_steps=3).run("say ok")

    assert result.answer == "agent-ok"
    assert result.finished_reason == "finished"
    assert result.steps[0].action == "final"
