from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse

from app.services.love_app import LoveApp
from app.services.manus_app import ManusApp
from app.mcp.client import McpClient
from app.services.rag_app import RagApp
from app.tools.registry import list_tools_for_prompt

router = APIRouter(prefix="/api/ai", tags=["ai"])
love_app = LoveApp()
rag_app = RagApp()
manus_app = ManusApp()


def resolve_chat_id(
    chatId: str | None = None,
    chat_id: str | None = None,
    session_id: str | None = None,
) -> str:
    return chatId or chat_id or session_id or "default"


@router.get("/love_app/chat", response_class=PlainTextResponse)
@router.get("/love_app/chat/sync", response_class=PlainTextResponse)
def chat_with_love_app_sync(
    message: str = Query(..., min_length=1),
    chatId: str | None = None,
    chat_id: str | None = None,
    session_id: str | None = None,
) -> str:
    try:
        return love_app.chat(message, resolve_chat_id(chatId, chat_id, session_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/love_app/chat/sse")
async def chat_with_love_app_sse(
    message: str = Query(..., min_length=1),
    chatId: str | None = None,
    chat_id: str | None = None,
    session_id: str | None = None,
) -> StreamingResponse:
    chat_id_value = resolve_chat_id(chatId, chat_id, session_id)

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for chunk in love_app.chat_stream(message, chat_id_value):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {str(exc)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/love_app/chat/server_sent_event")
async def chat_with_love_app_server_sent_event(
    message: str = Query(..., min_length=1),
    chatId: str | None = None,
    chat_id: str | None = None,
    session_id: str | None = None,
) -> StreamingResponse:
    return await chat_with_love_app_sse(message, chatId, chat_id, session_id)


@router.get("/love_app/chat/sse_emitter")
async def chat_with_love_app_sse_emitter(
    message: str = Query(..., min_length=1),
    chatId: str | None = None,
    chat_id: str | None = None,
    session_id: str | None = None,
) -> StreamingResponse:
    return await chat_with_love_app_sse(message, chatId, chat_id, session_id)


@router.post("/rag/index")
def rebuild_rag_index() -> dict:
    try:
        return rag_app.rebuild_index()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/rag/retrieve")
def retrieve_from_rag(message: str = Query(..., min_length=1)) -> dict:
    try:
        return {"results": rag_app.retrieve(message)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/rag/chat")
def chat_with_rag(
    message: str = Query(..., min_length=1),
    chatId: str | None = None,
    chat_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    try:
        return rag_app.chat(message, resolve_chat_id(chatId, chat_id, session_id))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/manus/tools")
def list_manus_tools() -> dict:
    return {"tools": list_tools_for_prompt()}


@router.get("/manus/mcp/status")
def manus_mcp_status() -> dict:
    return McpClient().status()


@router.get("/manus/chat")
async def chat_with_manus(
    message: str = Query(..., min_length=1),
    chatId: str | None = None,
    chat_id: str | None = None,
    session_id: str | None = None,
) -> StreamingResponse:
    chat_id_value = resolve_chat_id(chatId, chat_id, session_id)

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for event in manus_app.chat_stream(message, chat_id_value):
                yield event
        except Exception as exc:
            yield f"event: error\ndata: {str(exc)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
