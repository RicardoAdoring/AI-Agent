# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

This workspace contains both the original upstream project and the Python rewrite:

- `HuManus/` — active Python/FastAPI rewrite. Prefer making new backend changes here.
- `old/yu-ai-agent/` — cloned original Java/Spring AI project kept as a reference for behavior, endpoint compatibility, tools, and frontend integration.
- `old/yu-ai-agent/yu-ai-agent-frontend/` — original Vue 3 + Vite frontend. It is used for UI compatibility testing against the Python backend.
- `logger/` — implementation logs and Manus runtime HTML logs.
- `preview.html` — original rewrite task brief.
- `mcp.json` — local MCP stub config; default is an empty server list.

## Common commands

### Python backend: `HuManus`

Set up and install dependencies:

```bash
cd HuManus
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
```

Run the backend on the frontend-compatible port:

```bash
cd HuManus
.venv/Scripts/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8123
```

Compile-check the backend:

```bash
cd HuManus
.venv/Scripts/python -m compileall app
```

There is no project test suite under `HuManus/` yet. Use targeted smoke checks:

```bash
curl http://127.0.0.1:8123/health

curl -G "http://127.0.0.1:8123/api/ai/love_app/chat" \
  --data-urlencode "message=请只回复ok" \
  --data-urlencode "chatId=smoke_love"

curl -X POST http://127.0.0.1:8123/api/ai/rag/index

curl -G "http://127.0.0.1:8123/api/ai/rag/retrieve" \
  --data-urlencode "message=HuManus 第二阶段实现了什么"

curl http://127.0.0.1:8123/api/ai/manus/tools

curl http://127.0.0.1:8123/api/ai/manus/mcp/status

curl -N -G "http://127.0.0.1:8123/api/ai/manus/chat" \
  --data-urlencode "message=请只回复manus-ok，不需要使用工具，直接 final" \
  --data-urlencode "chatId=smoke_manus"
```

### Vue frontend: original UI compatibility target

Install, run, and build:

```bash
cd old/yu-ai-agent/yu-ai-agent-frontend
npm install
npm run dev -- --host 0.0.0.0
npm run build
```

The frontend expects the backend at `http://localhost:8123/api` and uses these SSE endpoints:

- `GET /api/ai/love_app/chat/sse`
- `GET /api/ai/manus/chat`

The frontend listens to default `EventSource.onmessage`; backend SSE intended for the frontend should emit default `data:` events and finish with `data: [DONE]`.

### Original Java project reference

The Java project in `old/yu-ai-agent/` is a reference copy of `https://github.com/liyupi/yu-ai-agent`. Use it to compare endpoint behavior, agent concepts, and tool responsibilities. Do not port Java code line-by-line into `HuManus/`.

## Python backend architecture

`HuManus/app/main.py` creates the FastAPI app, enables CORS, registers the AI router, and exposes `/health`.

`HuManus/app/api/ai.py` is the single HTTP route module. It wires module-level service instances:

- `LoveApp` for love-app chat and SSE compatibility endpoints.
- `RagApp` for local RAG indexing, retrieval, and RAG answers.
- `ManusApp` for YuManus Agent SSE.
- `McpClient` for MCP status.

### Configuration and model access

`HuManus/app/core/config.py` defines `Settings` via `pydantic-settings` and loads `.env` from the `HuManus/` working directory. It groups config for:

- app host/port
- primary OpenAI-compatible chat model
- Ollama fallback model
- DashScope settings
- chat memory
- RAG
- Manus tools/Agent
- MCP stub

`HuManus/app/llm/factory.py` centralizes chat model creation. Primary provider defaults to DeepSeek via OpenAI-compatible settings (`LLM_BASE_URL=https://api.deepseek.com`, `LLM_MODEL=deepseek-v4-flash`), with explicit Ollama fallback used by `LoveApp`, `RagApp`, and `YuManusAgent` when enabled.

### LoveApp chat

`HuManus/app/services/love_app.py` implements the AI love-advice app. It:

- builds a fixed system prompt
- loads/saves JSON chat memory through `FileChatMemory`
- supports sync and streaming responses
- falls back to Ollama if primary chat model fails before streaming output begins

`HuManus/app/memory/file_chat_memory.py` stores one JSON file per sanitized `chatId` in `data/chat_memory/`.

### RAG

RAG is local-file based:

- `HuManus/app/rag/loaders.py` loads `.txt`, `.md`, `.json` from `data/knowledge/` and splits documents.
- `HuManus/app/rag/embeddings.py` tries configured embeddings and can fall back to hash embeddings for development flow validation.
- `HuManus/app/rag/vector_store.py` persists a JSON vector index in `data/rag/index.json` and performs cosine similarity search.
- `HuManus/app/services/rag_app.py` coordinates rebuild, retrieve, and answer generation.

RAG currently supports only local text-like files. DeepSeek is configured for chat; RAG embedding defaults to hash embeddings for flow validation, not semantic retrieval quality.

### Tools and YuManus Agent

`HuManus/app/tools/registry.py` defines the default safe tools exposed to the Agent:

- `read_file`
- `write_file`
- `web_search`
- `web_scrape`
- `resource_download`
- `generate_pdf`
- `terminate`

`HuManus/app/tools/safety.py` enforces path and URL safety. File operations stay inside configured Manus directories. Private, loopback, link-local, and multicast URLs are blocked unless explicitly enabled. Arbitrary terminal execution is intentionally not registered; `terminal_tools.py` is a disabled stub.

`HuManus/app/agents/yumanus.py` implements the current YuManus Agent. It prompts the model to return strict JSON with one action per step, executes at most `MANUS_MAX_STEPS`, and records observations for follow-up steps. `HuManus/app/services/manus_app.py` adapts the Agent to frontend-compatible SSE and appends the generated HTML log path before `[DONE]`.

Agent run logs are written by `HuManus/app/services/html_step_logger.py` to `logger/manus-runs/` relative to the backend process working directory.

### MCP stub

`HuManus/app/mcp/config.py` reads `mcp.json`. `HuManus/app/mcp/client.py` returns status and empty tools when disabled. `MCP_ENABLED=false` by default; the stub does not start external commands or implement MCP transport.

## Compatibility notes

- Keep port `8123` for backend/frontend compatibility unless updating the frontend API base as well.
- Keep `/api/ai/love_app/chat/sse` and `/api/ai/manus/chat` compatible with default SSE `onmessage` handling.
- The original Java controller effective prefix is `/api/ai`; Python routes already include `/api/ai` directly.
- `old/` is reference material; the active Python implementation lives in `HuManus/`.

## Logs and generated data

Development phase logs are in root `logger/` (`step-*.html`). Manus runtime logs are in `logger/manus-runs/` when the backend is started from `HuManus/`. Generated chat memory, RAG indexes, downloads, outputs, and runtime logs are ignored by `HuManus/.gitignore` where applicable.
