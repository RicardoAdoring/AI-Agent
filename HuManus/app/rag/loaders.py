from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import get_settings

SUPPORTED_SUFFIXES = {".txt", ".md", ".json"}


def load_knowledge_documents() -> list[Document]:
    settings = get_settings()
    knowledge_dir = settings.rag_knowledge_dir
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    documents: list[Document] = []
    root = knowledge_dir.resolve()
    for path in sorted(knowledge_dir.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        if path.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        resolved = path.resolve()
        if root not in resolved.parents and resolved != root:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not text:
            continue
        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": str(path.as_posix()),
                    "file_name": path.name,
                    "file_extension": path.suffix.lower(),
                },
            )
        )
    return documents


def split_documents(documents: list[Document]) -> list[Document]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ".", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    for index, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = index
    return chunks
