from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "HuManus"
    app_host: str = "0.0.0.0"
    app_port: int = 8123

    llm_provider: str = Field(default="openai_compatible")
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-flash"
    enable_ollama_fallback: bool = True

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"

    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    dashscope_model: str = "qwen-plus"

    chat_memory_dir: Path = Path("./data/chat_memory")
    max_history_messages: int = 20

    rag_enabled: bool = True
    rag_knowledge_dir: Path = Path("./data/knowledge")
    rag_index_dir: Path = Path("./data/rag")
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 120
    rag_top_k: int = 4
    rag_embedding_provider: str = "hash"
    rag_embedding_model: str = "hash-embedding"
    rag_embedding_api_key: str = ""
    rag_embedding_base_url: str = ""
    rag_embedding_dimensions: int = 0
    ollama_embedding_model: str = "nomic-embed-text"
    rag_allow_hash_embedding: bool = True
    rag_auto_build: bool = True
    rag_score_threshold: float = -1.0
    rag_require_index_config_match: bool = True

    manus_enabled: bool = True
    manus_max_steps: int = 20
    manus_workspace_dir: Path = Path("./data/manus/workspace")
    manus_output_dir: Path = Path("./data/manus/output")
    manus_download_dir: Path = Path("./data/manus/downloads")
    manus_log_dir: Path = Path("./logger")
    manus_allow_private_urls: bool = False
    manus_http_timeout_seconds: float = 15.0
    manus_max_download_bytes: int = 10 * 1024 * 1024
    manus_search_provider: str = "placeholder"
    manus_search_api_key: str = ""
    manus_search_base_url: str = "https://www.searchapi.io/api/v1/search"
    manus_search_engine: str = "baidu"
    manus_search_top_k: int = 5

    mcp_enabled: bool = False
    mcp_config_path: Path = Path("./mcp.json")
    mcp_tool_call_timeout_seconds: float = 30.0
    amap_maps_api_key: str = ""

    agent_backend: str = "langgraph"
    agent_checkpoint_path: Path = Path("./data/manus/checkpoints.sqlite")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
