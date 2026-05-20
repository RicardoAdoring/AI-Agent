# HuManus

`HuManus` 是根据 `yu-ai-agent` 功能思想重构的 Python / FastAPI 版本。当前已完成基础聊天、SSE、多轮记忆、本地 RAG、安全工具层、YuManus Agent、MCP stub 和 HTML 日志体系。

## 已实现阶段

1. Phase 1：FastAPI MVP、基础聊天、SSE、模型接入、JSON 多轮记忆。
2. Phase 2：本地 RAG 知识库，支持 `.txt`、`.md`、`.json`。
3. Phase 3：安全工具层，支持文件、网页抓取、资源下载、PDF 生成、terminate。
4. Phase 4：YuManus Agent，支持有限步数 ReAct 风格工具循环和 SSE 输出。
5. Phase 5：MCP stub/config，默认禁用，不启动外部命令。
6. Phase 6：文档、验证和 HTML 日志收尾。

## 目录

```text
HuManus/
├── app/
│   ├── main.py
│   ├── api/ai.py
│   ├── agents/
│   ├── core/config.py
│   ├── llm/
│   ├── mcp/
│   ├── memory/file_chat_memory.py
│   ├── rag/
│   ├── services/
│   └── tools/
├── data/
│   ├── chat_memory/
│   ├── knowledge/
│   ├── rag/
│   └── manus/
├── requirements.txt
└── .env.example
```

## 启动

```bash
cd HuManus
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8123
```

## 模型配置

主模型使用 DeepSeek OpenAI-compatible 服务：

```env
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
ENABLE_OLLAMA_FALLBACK=true
```

备用模型使用 Ollama：

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:4b
```

## 基础聊天接口

```bash
curl http://localhost:8123/health

curl -G "http://localhost:8123/api/ai/love_app/chat" \
  --data-urlencode "message=你好" \
  --data-urlencode "chatId=test001"

curl -N -G "http://localhost:8123/api/ai/love_app/chat/sse" \
  --data-urlencode "message=帮我分析一下怎么和喜欢的人聊天" \
  --data-urlencode "chatId=test_sse"
```

## RAG 知识库

将知识文件放到：

```text
data/knowledge/
```

构建索引：

```bash
curl -X POST http://localhost:8123/api/ai/rag/index
```

检索调试：

```bash
curl -G "http://localhost:8123/api/ai/rag/retrieve" \
  --data-urlencode "message=你的问题"
```

RAG 问答：

```bash
curl -G "http://localhost:8123/api/ai/rag/chat" \
  --data-urlencode "message=根据知识库回答你的问题" \
  --data-urlencode "chatId=rag_test"
```

## YuManus Agent

查看工具：

```bash
curl http://localhost:8123/api/ai/manus/tools
```

运行 Agent：

```bash
curl -N -G "http://localhost:8123/api/ai/manus/chat" \
  --data-urlencode "message=生成一份简短任务计划，并保存到 plan.txt" \
  --data-urlencode "chatId=manus_test"
```

每次运行会生成 HTML 日志：

```text
logger/manus-runs/{chatId}-{timestamp}.html
```

## 安全工具层

默认注册工具：

- `read_file`
- `write_file`
- `web_search`
- `web_scrape`
- `resource_download`
- `generate_pdf`
- `terminate`

安全边界：

- 任意终端命令执行已禁用。
- 文件读写限制在 `MANUS_WORKSPACE_DIR` 等配置目录内。
- 默认阻止 private / loopback / link-local / multicast URL。
- 下载有大小限制。
- Web search 未配置 provider 时返回明确错误，不伪造搜索结果。

## MCP stub

MCP 默认关闭：

```env
MCP_ENABLED=false
MCP_CONFIG_PATH=./mcp.json
```

状态接口：

```bash
curl http://localhost:8123/api/ai/manus/mcp/status
```

当前 MCP 仅提供配置读取和 stub，不启动任意外部命令。

## 阶段日志

开发阶段日志保存于工作区根目录的 `logger/`：

- `step-1-humanus-mvp-log.html`
- `step-3-tools-log.html`
- `step-4-agent-log.html`
- `step-5-mcp-log.html`
- `step-6-final-validation-log.html`

## 当前限制

- RAG 当前仅支持 `.txt`、`.md`、`.json`。
- DeepSeek 当前配置用于聊天模型；RAG embedding 默认使用 hash embedding，仅适合流程验证。
- MCP transport 未实现。
- Web search 需要后续配置真实 provider。
- 终端命令工具不会开放，除非后续加入明确沙箱和审批机制。
