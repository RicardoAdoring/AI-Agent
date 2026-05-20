# HuManus 项目说明

HuManus 是 yu-ai-agent 的 Python 改造版本。

第一阶段实现了 FastAPI 后端、基础聊天、SSE 流式输出、OpenAI-compatible 主模型、Ollama 备用模型和 JSON 文件多轮记忆。

第二阶段实现本地 RAG 知识库，支持读取 data/knowledge 下的 txt、md、json 文件，构建本地向量索引，并通过 /api/ai/rag/chat 提供知识库增强问答。
