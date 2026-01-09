## cms-copilot

基于 **LangGraph** 的内容/站点运营 Copilot：把“意图识别 → 任务分流 → 工具调用（含 MCP）→ 结果输出”串成一张可在 **LangGraph Studio** 可视化调试的工作流图。

### 你能用它做什么

- **RAG 问答**：默认分支，直接检索增强问答并返回结果
- **文章任务**：进入文章相关 UI/节点，执行文章生成/处理类任务
- **SEO 规划**：进入 SEO 相关 UI/节点，输出 SEO 规划类结果
- **站点报告**：进入 report 子图，生成站点报告
- **快捷指令**：进入 shortcut 子图，用更“命令式”的方式完成常用动作
- **MCP 工具接入**：通过 MCP Server 动态拉取 tools，并可直接作为 LangChain tools 绑定到模型

### 关键入口

- **主图**：`src/agent/graph.py`（意图分流 + 子图/节点组装）
- **Studio UI**：`src/ui/ui.tsx`（在 Studio 中呈现的交互 UI）
- **LangGraph 配置**：`langgraph.json`（graphs/ui/env 等）
- **MCP 客户端封装**：`src/agent/tools/mcp.py`（`MultiServerMCPClient`，动态 tools/list）

## 快速开始

### 1) 准备环境

- **Python**：>= 3.12.10
- **推荐工具**：`uv`（仓库包含 `uv.lock`）

### 2) 安装依赖

#### 方式 A：使用 uv（推荐）

```bash
uv sync --group dev
```

#### 方式 B：pip 可编辑安装

```bash
pip install -e . "langgraph-cli[inmem]"
```

### 3) 配置环境变量（强烈建议）

项目会从 `.env` 读取环境变量（见 `langgraph.json` 的 `"env": ".env"`）。请在项目根目录新建一个本地 `.env`（不要提交到仓库），至少配置下面这些（按你环境调整）：

```text
# LLM（建议覆盖默认值）
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=gpt-4.1-mini
LLM_NANO_MODEL=gpt-4.1-nano

# LangGraph Cloud（如需调用云端图/assistant 才配置）
LANGGRAPH_CLOUD_API_KEY=
ARTICLE_WORKFLOW_URL=
ARTICLE_ASSISTANT_ID=multiple_graph

# MCP Server（站点基础设置示例）
MCP_SITE_SETTING_BASIC_URL=
CMS_SITE_ID=
CMS_TENANT_ID=
MCP_DEBUG=0
```

说明：

- **不要依赖仓库内的默认 key/base_url**。请在本地或 CI 环境显式设置，避免误用或泄露。
- MCP 侧会自动在请求头注入 `X-Site-Id`（以及可选的 `X-Tenant-Id`），详见 `src/agent/tools/mcp.py`。

### 4) 启动本地 LangGraph Server（含 Studio）

```bash
langgraph dev
```

启动后即可在 LangGraph Studio 中打开并调试图（支持热更新、回放、编辑历史状态等）。

如果启动报错，可以尝试，关闭自动reload
```bash
langgraph dev --no-reload
```

## 目录结构（简版）

```text
src/
  agent/
    graph.py              # 主图组装（节点/边/子图）
    config.py             # 配置与环境变量入口
    nodes/                # 具体业务节点（entry/router/rag/article/seo/report/shortcut）
    subgraphs/            # 子图（report/shortcut）
    tools/                # 工具层（含 MCP 封装）
    utils/                # 通用工具（LLM/UI/HITL 等）
  ui/
    ui.tsx                # Studio UI
docs/
tests/
langgraph.json
```

## 前端项目
`https://agentchat.vercel.app/`
LangSmith Api Key填写.env中的LANGCHAIN_API_KEY即可

前端对接参数说明见：`docs/agent-chat-ui-params.md`

## 开发与测试

### 运行单测

```bash
pytest -q
```

### 代码质量（可选）

```bash
ruff check .
```

## 常见问题

### git status 提示 node_modules 路径不存在

这通常是历史产物或本地环境残留导致的告警，不影响 Python 侧运行；建议清理/重装前端依赖或删除异常的 node_modules 引用后再观察。

### 我想加一个新的意图/任务分支

- 在 `src/agent/nodes/` 新增节点（或在 `src/agent/subgraphs/` 新增子图）
- 在 `src/agent/graph.py`：
  - `builder.add_node(...)`
  - 在 router 的条件边里增加 intent → node 映射
  - 连接到 `END` 或下一步节点

## License

MIT（见 `LICENSE`）

