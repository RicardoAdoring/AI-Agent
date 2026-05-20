import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.core.config import get_settings

INDEX_FILE_NAME = "index.json"


@dataclass
class RetrievedChunk:
    text: str
    score: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "score": self.score,
            "metadata": self.metadata,
        }


class LocalVectorStore:
    def __init__(self, index_dir: Path | None = None) -> None:
        settings = get_settings()
        self.index_dir = index_dir or settings.rag_index_dir
        self.index_path = self.index_dir / INDEX_FILE_NAME
        self.documents: list[dict[str, Any]] = []
        self.metadata: dict[str, Any] = {}

    @property
    def exists(self) -> bool:
        return self.index_path.exists()

    def build(self, documents: list[Document], embeddings: Embeddings) -> dict[str, Any]:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        texts = [document.page_content for document in documents]
        vectors = embeddings.embed_documents(texts) if texts else []
        self.documents = []
        for document, vector in zip(documents, vectors, strict=True):
            self.documents.append(
                {
                    "text": document.page_content,
                    "vector": vector,
                    "metadata": document.metadata,
                }
            )
        self.metadata = self._current_metadata(vectors[0] if vectors else [])
        self.save()
        return self.summary()

    def load(self) -> None:
        if not self.index_path.exists():
            self.documents = []
            self.metadata = {}
            return
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.documents = data.get("documents", [])
        self.metadata = {key: value for key, value in data.items() if key != "documents"}

    def save(self) -> None:
        payload = {
            **self._current_metadata(self.documents[0].get("vector", []) if self.documents else []),
            "documents": self.documents,
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def similarity_search(self, query: str, embeddings: Embeddings, top_k: int | None = None) -> list[RetrievedChunk]:
        settings = get_settings()
        if not self.documents:
            self.load()
        if not self.documents:
            return []
        self._assert_index_matches_current_config()

        query_vector = np.array(embeddings.embed_query(query), dtype=float)
        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            return []

        results: list[RetrievedChunk] = []
        for item in self.documents:
            vector = np.array(item.get("vector", []), dtype=float)
            vector_norm = np.linalg.norm(vector)
            if vector_norm == 0 or vector.shape != query_vector.shape:
                continue
            score = float(np.dot(query_vector, vector) / (query_norm * vector_norm))
            if settings.rag_score_threshold >= 0 and score < settings.rag_score_threshold:
                continue
            results.append(
                RetrievedChunk(
                    text=item.get("text", ""),
                    score=score,
                    metadata=item.get("metadata", {}),
                )
            )

        limit = top_k or settings.rag_top_k
        return sorted(results, key=lambda chunk: chunk.score, reverse=True)[:limit]

    def summary(self) -> dict[str, Any]:
        settings = get_settings()
        sources = {item.get("metadata", {}).get("source") for item in self.documents}
        metadata = self._current_metadata(self.documents[0].get("vector", []) if self.documents else [])
        return {
            "status": "ok",
            "files": len([source for source in sources if source]),
            "chunks": len(self.documents),
            "embedding_provider": metadata["embedding_provider"],
            "embedding_model": metadata["embedding_model"],
            "embedding_dimensions": metadata["embedding_dimensions"],
            "hash_embedding_fallback_allowed": settings.rag_allow_hash_embedding,
            "index_dir": str(self.index_dir.as_posix()),
        }

    def _current_metadata(self, sample_vector: list[float]) -> dict[str, Any]:
        settings = get_settings()
        return {
            "version": 2,
            "chunk_size": settings.rag_chunk_size,
            "chunk_overlap": settings.rag_chunk_overlap,
            "embedding_provider": settings.rag_embedding_provider,
            "embedding_model": settings.rag_embedding_model if settings.rag_embedding_provider != "ollama" else settings.ollama_embedding_model,
            "embedding_dimensions": len(sample_vector),
        }

    def _assert_index_matches_current_config(self) -> None:
        settings = get_settings()
        if not settings.rag_require_index_config_match:
            return
        expected = self._current_metadata(self.documents[0].get("vector", []) if self.documents else [])
        mismatches = []
        for key in ("embedding_provider", "embedding_model", "chunk_size", "chunk_overlap"):
            if self.metadata.get(key) != expected.get(key):
                mismatches.append(f"{key}: index={self.metadata.get(key)!r}, current={expected.get(key)!r}")
        if mismatches:
            raise RuntimeError("RAG index configuration mismatch. Rebuild index. " + "; ".join(mismatches))
