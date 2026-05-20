from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import get_settings
from app.llm.factory import get_chat_model, get_ollama_chat_model
from app.rag.embeddings import HashEmbeddings, get_embedding_model, get_hash_embedding_model
from app.rag.loaders import load_knowledge_documents, split_documents
from app.rag.vector_store import LocalVectorStore

RAG_SYSTEM_PROMPT = """你是 HuManus 的知识库问答助手。
请优先依据给定的知识库上下文回答问题；如果上下文不足，请明确说明无法从知识库确认。
回答应简洁、准确，并尽量用中文。"""


class RagApp:
    def __init__(self, vector_store: LocalVectorStore | None = None) -> None:
        self.vector_store = vector_store or LocalVectorStore()

    def rebuild_index(self) -> dict[str, Any]:
        settings = get_settings()
        if not settings.rag_enabled:
            raise RuntimeError("RAG is disabled")

        documents = load_knowledge_documents()
        chunks = split_documents(documents)
        embeddings = self._working_embeddings()
        summary = self.vector_store.build(chunks, embeddings)
        summary["knowledge_dir"] = str(settings.rag_knowledge_dir.as_posix())
        summary["hash_embedding_fallback"] = isinstance(embeddings, HashEmbeddings)
        return summary

    def retrieve(self, message: str) -> list[dict[str, Any]]:
        self._ensure_index()
        embeddings = self._working_embeddings(query=message)
        chunks = self.vector_store.similarity_search(message, embeddings)
        return [chunk.to_dict() for chunk in chunks]

    def chat(self, message: str, chat_id: str | None = None) -> dict[str, Any]:
        chunks = self.retrieve(message)
        context = self._format_context(chunks)
        prompt = (
            f"知识库上下文：\n{context}\n\n"
            f"用户问题：{message}\n\n"
            "请基于知识库上下文回答，并在答案末尾简要列出参考来源。"
        )
        messages = [SystemMessage(content=RAG_SYSTEM_PROMPT), HumanMessage(content=prompt)]

        try:
            model = get_chat_model(streaming=False)
            response = model.invoke(messages)
        except Exception:
            if not get_settings().enable_ollama_fallback:
                raise
            model = get_ollama_chat_model()
            response = model.invoke(messages)

        return {
            "answer": self._content_to_text(response.content),
            "sources": self._sources_from_chunks(chunks),
            "chatId": chat_id or "default",
        }

    def status(self) -> dict[str, Any]:
        self.vector_store.load()
        return self.vector_store.summary() if self.vector_store.documents else {"status": "empty"}

    def _working_embeddings(self, query: str | None = None) -> Embeddings:
        settings = get_settings()
        embeddings = get_embedding_model()
        try:
            if query is None:
                embeddings.embed_query("HuManus RAG embedding check")
            else:
                embeddings.embed_query(query)
            return embeddings
        except Exception:
            if not settings.rag_allow_hash_embedding:
                raise
            return get_hash_embedding_model()

    def _ensure_index(self) -> None:
        settings = get_settings()
        if not settings.rag_enabled:
            raise RuntimeError("RAG is disabled")
        if self.vector_store.exists:
            self.vector_store.load()
            return
        if settings.rag_auto_build:
            self.rebuild_index()
            return
        raise RuntimeError("RAG index does not exist. Call POST /api/ai/rag/index first.")

    def _format_context(self, chunks: list[dict[str, Any]]) -> str:
        if not chunks:
            return "没有检索到相关知识库内容。"
        parts = []
        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk.get("metadata", {})
            source = metadata.get("source", "unknown")
            score = chunk.get("score", 0)
            text = chunk.get("text", "")
            parts.append(f"[来源 {index}: {source}, 相似度 {score:.3f}]\n{text}")
        return "\n\n".join(parts)

    def _sources_from_chunks(self, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        sources = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            sources.append(
                {
                    "source": metadata.get("source"),
                    "file_name": metadata.get("file_name"),
                    "chunk_index": metadata.get("chunk_index"),
                    "score": chunk.get("score"),
                }
            )
        return sources

    def _content_to_text(self, content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(str(item.get("text") or item.get("content") or ""))
            return "".join(parts)
        return str(content)
