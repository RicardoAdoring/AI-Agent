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
        self.save()
        return self.summary()

    def load(self) -> None:
        if not self.index_path.exists():
            self.documents = []
            return
        data = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.documents = data.get("documents", [])

    def save(self) -> None:
        settings = get_settings()
        payload = {
            "version": 1,
            "chunk_size": settings.rag_chunk_size,
            "chunk_overlap": settings.rag_chunk_overlap,
            "embedding_provider": settings.rag_embedding_provider,
            "embedding_model": settings.rag_embedding_model,
            "documents": self.documents,
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def similarity_search(self, query: str, embeddings: Embeddings, top_k: int | None = None) -> list[RetrievedChunk]:
        settings = get_settings()
        if not self.documents:
            self.load()
        if not self.documents:
            return []

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
        return {
            "status": "ok",
            "files": len([source for source in sources if source]),
            "chunks": len(self.documents),
            "embedding_provider": settings.rag_embedding_provider,
            "embedding_model": settings.rag_embedding_model,
            "index_dir": str(self.index_dir.as_posix()),
        }
