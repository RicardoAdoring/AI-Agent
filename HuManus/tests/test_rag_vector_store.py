import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.core.config import get_settings
from app.rag.vector_store import LocalVectorStore


class TinyEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        return [1.0, 0.0] if "alpha" in text else [0.0, 1.0]


def test_vector_store_build_and_search(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rag_embedding_provider", "custom")
    monkeypatch.setattr(settings, "rag_embedding_model", "tiny")
    monkeypatch.setattr(settings, "rag_score_threshold", 0.0)
    store = LocalVectorStore(index_dir=tmp_path)

    store.build([Document(page_content="alpha content", metadata={"source": "a.md"})], TinyEmbeddings())
    results = store.similarity_search("alpha", TinyEmbeddings())

    assert results[0].text == "alpha content"
    assert results[0].score == pytest.approx(1.0)


def test_vector_store_rejects_stale_index_config(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "rag_embedding_provider", "custom")
    monkeypatch.setattr(settings, "rag_embedding_model", "tiny")
    monkeypatch.setattr(settings, "rag_require_index_config_match", True)
    store = LocalVectorStore(index_dir=tmp_path)
    store.build([Document(page_content="alpha content", metadata={"source": "a.md"})], TinyEmbeddings())

    monkeypatch.setattr(settings, "rag_embedding_model", "other")

    with pytest.raises(RuntimeError, match="RAG index configuration mismatch"):
        store.similarity_search("alpha", TinyEmbeddings())
