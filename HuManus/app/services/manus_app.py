from collections.abc import AsyncIterator

from app.agents.yumanus import YuManusAgent


class ManusApp:
    async def chat(self, message: str, chat_id: str = "manus-default") -> dict:
        agent = YuManusAgent(chat_id=chat_id)
        result = await agent.run(message)
        return result.to_dict()

    async def chat_stream(self, message: str, chat_id: str = "manus-default") -> AsyncIterator[str]:
        agent = YuManusAgent(chat_id=chat_id)
        result = await agent.run(message)
        for step in result.steps:
            text = step.observation or step.thought
            if text:
                yield f"data: {text}\n\n"
        yield f"data: 日志文件：{result.log_path}\n\n"
        yield "data: [DONE]\n\n"
