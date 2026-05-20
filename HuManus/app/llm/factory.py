from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import get_settings


def get_chat_model(streaming: bool = False) -> BaseChatModel:
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()

    if provider == "ollama":
        return get_ollama_chat_model()

    if provider in {"openai", "openai_compatible", "custom"}:
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is required when LLM_PROVIDER=openai_compatible")

        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0.7,
            streaming=streaming,
        )

    if provider == "dashscope":
        if not settings.dashscope_api_key:
            raise RuntimeError("DASHSCOPE_API_KEY is required when LLM_PROVIDER=dashscope")

        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.dashscope_model,
            api_key=settings.dashscope_api_key,
            base_url=settings.dashscope_base_url,
            temperature=0.7,
            streaming=streaming,
        )

    raise RuntimeError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")


def get_ollama_chat_model() -> BaseChatModel:
    settings = get_settings()
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.7,
    )
