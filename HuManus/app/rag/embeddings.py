import hashlib
import math

from langchain_core.embeddings import Embeddings

from app.core.config import get_settings


class HashEmbeddings(Embeddings):
    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = [token for token in text.lower().split() if token]
        if not tokens:
            tokens = [text]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


def get_embedding_model() -> Embeddings:
    settings = get_settings()
    provider = settings.rag_embedding_provider.lower().strip()

    try:
        if provider in {"openai", "openai_compatible", "custom"}:
            return _openai_compatible_embeddings()
        if provider == "dashscope":
            return _dashscope_embeddings()
        if provider == "ollama":
            return get_ollama_embedding_model()
        if provider == "hash":
            if settings.rag_allow_hash_embedding:
                return get_hash_embedding_model()
            raise RuntimeError("Hash embeddings are disabled")
    except Exception:
        if not settings.rag_allow_hash_embedding:
            raise

    if settings.rag_allow_hash_embedding:
        return get_hash_embedding_model()

    raise RuntimeError(f"Unsupported RAG_EMBEDDING_PROVIDER: {settings.rag_embedding_provider}")


def _openai_compatible_embeddings() -> Embeddings:
    settings = get_settings()
    api_key = settings.rag_embedding_api_key or settings.llm_api_key
    base_url = settings.rag_embedding_base_url or settings.llm_base_url
    if not api_key:
        raise RuntimeError("RAG_EMBEDDING_API_KEY or LLM_API_KEY is required for OpenAI-compatible embeddings")
    from langchain_openai import OpenAIEmbeddings

    kwargs = {
        "model": settings.rag_embedding_model,
        "api_key": api_key,
        "base_url": base_url,
    }
    if settings.rag_embedding_dimensions > 0:
        kwargs["dimensions"] = settings.rag_embedding_dimensions
    return OpenAIEmbeddings(**kwargs)


def _dashscope_embeddings() -> Embeddings:
    settings = get_settings()
    if not settings.rag_embedding_api_key and not settings.dashscope_api_key:
        raise RuntimeError("RAG_EMBEDDING_API_KEY or DASHSCOPE_API_KEY is required for DashScope embeddings")
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=settings.rag_embedding_model,
        api_key=settings.rag_embedding_api_key or settings.dashscope_api_key,
        base_url=settings.rag_embedding_base_url or settings.dashscope_base_url,
    )


def get_ollama_embedding_model() -> Embeddings:
    settings = get_settings()
    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(
        model=settings.ollama_embedding_model,
        base_url=settings.ollama_base_url,
    )


def get_hash_embedding_model() -> Embeddings:
    return HashEmbeddings()
