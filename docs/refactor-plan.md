# CMS Copilot 生产级项目结构重构方案

## 1. 当前问题

### 1.1 现状分析

```
cms-copilot/
├── src/agent/
│   ├── __init__.py
│   ├── graph.py        # 1200+ 行，所有逻辑混在一起
│   ├── ui.tsx
│   └── react-shim.d.ts
```

**主要问题**：
- `graph.py` 文件过大（1200+ 行），职责不清
- 状态定义、节点函数、子图、工具、配置全部混在一起
- 难以维护、测试和扩展
- 配置硬编码在代码中

### 1.2 代码职责分析

当前 `graph.py` 包含：
1. **状态定义**：`CopilotState`、`ShortcutState`
2. **LLM 实例**：`llm`、`llm_nano`
3. **常量配置**：`MCP_ACTION_CATALOG`、API URLs
4. **辅助函数**：`hitl_confirm`、`_shortcut_push_ui`
5. **节点函数**：
   - 路由：`start_intent_ui`、`route_intent`
   - RAG：`handle_rag`
   - 文章：`start_article_ui`、`handle_article`
   - Shortcut：`shortcut_init`、`shortcut_select`、`shortcut_confirm`、`shortcut_execute`、`shortcut_cancelled`
6. **子图构建**：`build_shortcut_subgraph`
7. **主图构建**：`entry_node`、`build_graph`

---

## 2. 目标结构

参考 LangGraph 官方最佳实践，重构为模块化结构：

```
cms-copilot/
├── src/
│   └── agent/
│       ├── __init__.py           # 导出 graph, build_graph, CopilotState 等
│       ├── graph.py              # 主图构建（只负责组装，~85 行）
│       ├── state.py              # 状态定义（CopilotState, ShortcutState）
│       ├── config.py             # 配置常量（MCP_ACTION_CATALOG, API URLs 等）
│       │
│       ├── nodes/                # 节点函数（按功能分文件）
│       │   ├── __init__.py       # 导出所有节点函数
│       │   ├── entry.py          # entry_node
│       │   ├── router.py         # start_intent_ui, route_intent
│       │   ├── rag.py            # handle_rag
│       │   ├── article.py        # start_article_ui, handle_article
│       │   └── shortcut.py       # shortcut_init/select/confirm/execute/cancelled
│       │
│       ├── subgraphs/            # 子图
│       │   ├── __init__.py       # 导出 build_shortcut_subgraph
│       │   └── shortcut.py       # build_shortcut_subgraph
│       │
│       ├── tools/                # LangChain Tools
│       │   ├── __init__.py       # 导出 tool 函数
│       │   ├── rag.py            # rag_query tool
│       │   └── article.py        # call_cloud_article_workflow, run_article_workflow
│       │
│       ├── utils/                # 工具函数
│       │   ├── __init__.py       # 导出辅助函数
│       │   ├── llm.py            # LLM 实例（llm, llm_nano）
│       │   ├── ui.py             # push_shortcut_ui 辅助函数
│       │   ├── hitl.py           # hitl_confirm HITL 函数
│       │   └── helpers.py        # 其他辅助函数
│       │
│       ├── ui.tsx                # 前端 Generative UI 组件
│       └── react-shim.d.ts       # React 类型声明
│
├── docs/
│   └── refactor-plan.md          # 本文档
│
├── tests/                        # 测试（待添加）
│   ├── unit_tests/
│   │   ├── test_state.py
│   │   └── test_nodes/
│   └── integration_tests/
│       └── test_graph.py
│
├── langgraph.json                # LangGraph 配置
├── pyproject.toml                # Python 项目配置
└── README.md
```

> **说明**：`ui.tsx` 和 `react-shim.d.ts` 保留在 `src/agent/` 内，与 graph 放在一起。
> 这是 LangGraph 官方模板的推荐做法，便于 UI 组件与后端逻辑保持一致。

---

## 3. 模块详细设计

### 3.1 `state.py` - 状态定义

```python
# src/agent/state.py
from typing import Any, Optional, Sequence
from typing_extensions import Annotated, TypedDict
from langgraph.graph.message import add_messages
from langgraph.graph.ui import AnyUIMessage, ui_message_reducer
from langchain_core.messages import BaseMessage


class CopilotState(TypedDict):
    """主图状态"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]
    intent: Optional[str]
    intent_ui_id: Optional[str]
    intent_started_at: Optional[float]
    article_ui_id: Optional[str]
    article_anchor_id: Optional[str]
    tenant_id: Optional[str]
    site_id: Optional[str]
    # shortcut 相关（子图共享）
    user_text: Optional[str]
    options: Optional[list[dict[str, Any]]]
    recommended: Optional[str]
    selected: Optional[dict[str, Any]]
    company_name: Optional[str]
    logo_url: Optional[str]
    result: Optional[str]
    error: Optional[str]
    confirmed: Optional[bool]
    ui_anchor_id: Optional[str]
    ui_id: Optional[str]
    resume_target: Optional[str]


class ShortcutState(TypedDict):
    """Shortcut 子图状态"""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]
    tenant_id: Optional[str]
    site_id: Optional[str]
    user_text: Optional[str]
    options: Optional[list[dict[str, Any]]]
    recommended: Optional[str]
    selected: Optional[dict[str, Any]]
    company_name: Optional[str]
    logo_url: Optional[str]
    result: Optional[str]
    error: Optional[str]
    confirmed: Optional[bool]
    ui_anchor_id: Optional[str]
    ui_id: Optional[str]
```

### 3.2 `config.py` - 配置管理

```python
# src/agent/config.py
import os

# API 配置
LANGGRAPH_CLOUD_BASE_URL = os.getenv(
    "ARTICLE_WORKFLOW_URL",
    "https://ai-dev-content-xxx.us.langgraph.app",
)
LANGGRAPH_CLOUD_API_KEY = os.getenv("LANGGRAPH_CLOUD_API_KEY") or os.getenv("LANGSMITH_API_KEY")
CLOUD_ASSISTANT_ID = os.getenv("ARTICLE_ASSISTANT_ID", "multiple_graph")

# LLM 配置
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://117.50.168.6/")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
LLM_NANO_MODEL = os.getenv("LLM_NANO_MODEL", "gpt-4.1-nano")

# MCP 操作目录
MCP_ACTION_CATALOG: list[dict] = [
    {"code": "update_company_name", "name": "修改站点公司名称", "desc": "更新站点显示的公司名称"},
    {"code": "update_logo", "name": "修改站点 Logo", "desc": "更新站点的 Logo 图片"},
]
```

### 3.3 `utils/llm.py` - LLM 实例

```python
# src/agent/utils/llm.py
from langchain_openai import ChatOpenAI
from ..config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LLM_NANO_MODEL

llm = ChatOpenAI(
    model=LLM_MODEL,
    temperature=0,
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
)

llm_nano = ChatOpenAI(
    model=LLM_NANO_MODEL,
    temperature=0,
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
)
```

### 3.4 `utils/hitl.py` - HITL 辅助函数

```python
# src/agent/utils/hitl.py
from typing import Any
from langgraph.types import interrupt
from langchain.agents.middleware.human_in_the_loop import (
    HITLRequest, ActionRequest, ReviewConfig, DecisionType
)


def hitl_confirm(
    action_name: str,
    args: dict[str, Any],
    description: str,
    allowed_decisions: list[DecisionType] = ["approve", "reject"],
) -> bool:
    """发起 HITL 确认请求，返回是否批准。"""
    request: HITLRequest = {
        "action_requests": [
            ActionRequest(name=action_name, args=args, description=description)
        ],
        "review_configs": [
            ReviewConfig(action_name=action_name, allowed_decisions=list(allowed_decisions))
        ],
    }
    
    response = interrupt(request)
    
    if isinstance(response, dict):
        decisions = response.get("decisions", [])
        if decisions and isinstance(decisions, list):
            return decisions[0].get("type") == "approve"
        return response.get("type") in ["accept", "approve", "confirm"]
    
    text = str(response).strip().lower() if response else ""
    return any(k in text for k in ["确认", "确定", "执行", "ok", "yes", "好", "同意", "accept", "approve"])
```

### 3.5 `nodes/router.py` - 路由节点

```python
# src/agent/nodes/router.py
import uuid
from typing import Any
from langgraph.graph.ui import push_ui_message
from langgraph.config import get_stream_writer
from langchain_core.messages import AIMessage

from ..state import CopilotState
from ..utils.llm import llm_nano


async def start_intent_ui(state: CopilotState) -> dict[str, Any]:
    """初始化意图识别 UI。"""
    # ... 实现
    pass


async def route_intent(state: CopilotState) -> dict[str, Any]:
    """意图识别节点。"""
    # ... 实现
    pass
```

### 3.6 `nodes/shortcut.py` - Shortcut 节点

```python
# src/agent/nodes/shortcut.py
from typing import Any
from ..state import ShortcutState
from ..utils.hitl import hitl_confirm
from ..utils.llm import llm_nano
from ..config import MCP_ACTION_CATALOG


async def shortcut_init(state: ShortcutState) -> dict[str, Any]:
    """初始化 shortcut 流程。"""
    pass


async def shortcut_select(state: ShortcutState) -> dict[str, Any]:
    """等待用户选择操作。"""
    pass


async def shortcut_confirm(state: ShortcutState) -> dict[str, Any]:
    """等待用户确认。"""
    pass


async def shortcut_execute(state: ShortcutState) -> dict[str, Any]:
    """执行操作。"""
    pass


async def shortcut_cancelled(state: ShortcutState) -> dict[str, Any]:
    """取消操作。"""
    pass
```

### 3.7 `subgraphs/shortcut.py` - Shortcut 子图

```python
# src/agent/subgraphs/shortcut.py
from langgraph.graph import END, START, StateGraph
from ..state import ShortcutState
from ..nodes.shortcut import (
    shortcut_init, shortcut_select, shortcut_confirm,
    shortcut_execute, shortcut_cancelled
)


def build_shortcut_subgraph():
    """构建 Shortcut 子图。"""
    builder = StateGraph(ShortcutState)
    
    builder.add_node("init", shortcut_init)
    builder.add_node("select", shortcut_select)
    builder.add_node("confirm", shortcut_confirm)
    builder.add_node("execute", shortcut_execute)
    builder.add_node("cancelled", shortcut_cancelled)
    
    builder.add_edge(START, "init")
    
    def _after_init(state: ShortcutState):
        options = state.get("options") or []
        return "confirm" if len(options) == 1 else "select"
    
    builder.add_conditional_edges("init", _after_init, {"select": "select", "confirm": "confirm"})
    builder.add_edge("select", "confirm")
    
    def _after_confirm(state: ShortcutState):
        return "execute" if state.get("confirmed") else "cancelled"
    
    builder.add_conditional_edges("confirm", _after_confirm, {"execute": "execute", "cancelled": "cancelled"})
    builder.add_edge("execute", END)
    builder.add_edge("cancelled", END)
    
    return builder.compile()
```

### 3.8 `graph.py` - 主图（精简版）

```python
# src/agent/graph.py
"""主图构建 - 只负责组装各模块。"""
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from .state import CopilotState
from .nodes.entry import entry_node
from .nodes.router import start_intent_ui, route_intent
from .nodes.rag import handle_rag
from .nodes.article import start_article_ui, handle_article
from .subgraphs.shortcut import build_shortcut_subgraph


def build_graph():
    """构建主图。"""
    builder = StateGraph(CopilotState)
    
    # 添加节点
    builder.add_node("entry", entry_node)
    builder.add_node("router_ui", start_intent_ui)
    builder.add_node("router", route_intent)
    builder.add_node("rag", handle_rag)
    builder.add_node("article_ui", start_article_ui)
    builder.add_node("article", handle_article)
    builder.add_node("shortcut", build_shortcut_subgraph())
    
    # 定义边
    builder.add_edge(START, "entry")
    
    def _entry_route(state: CopilotState):
        return state.get("resume_target") or "router_ui"
    
    builder.add_conditional_edges("entry", _entry_route, {"router_ui": "router_ui", "shortcut": "shortcut"})
    builder.add_edge("router_ui", "router")
    
    def _route(state: CopilotState):
        intent = state.get("intent") or "rag"
        if intent == "article_task":
            return "article_task"
        if intent == "shortcut":
            return "shortcut"
        return "rag"
    
    builder.add_conditional_edges("router", _route, {"rag": "rag", "article_task": "article_ui", "shortcut": "shortcut"})
    builder.add_edge("rag", END)
    builder.add_edge("article_ui", "article")
    builder.add_edge("article", END)
    builder.add_edge("shortcut", END)
    
    return builder.compile(checkpointer=MemorySaver())


# 导出
graph = build_graph()
```

---

## 4. 迁移步骤

### Phase 1: 基础模块拆分
1. [x] 创建 `state.py`，迁移状态定义
2. [x] 创建 `config.py`，迁移配置常量
3. [x] 创建 `utils/llm.py`，迁移 LLM 实例
4. [x] 创建 `utils/hitl.py`，迁移 HITL 辅助函数
5. [x] 创建 `utils/ui.py`，迁移 UI 辅助函数
6. [x] 创建 `utils/helpers.py`，迁移辅助函数

### Phase 2: 节点拆分
7. [x] 创建 `nodes/entry.py`
8. [x] 创建 `nodes/router.py`
9. [x] 创建 `nodes/rag.py`
10. [x] 创建 `nodes/article.py`
11. [x] 创建 `nodes/shortcut.py`

### Phase 3: 子图拆分
12. [x] 创建 `subgraphs/shortcut.py`

### Phase 4: 主图精简
13. [x] 重构 `graph.py`，只保留图构建逻辑
14. [x] 更新 `__init__.py` 导出
15. [x] 更新 `langgraph.json` 使用模块路径 `agent.graph:build_graph`

### Phase 5: 前端 UI 组件（可选迁移）
> **当前状态**：`ui.tsx` 和 `react-shim.d.ts` 保留在 `src/agent/` 目录内。
> 这符合 LangGraph 的推荐做法——UI 组件与 graph 放在同一 agent 目录下，便于维护。

16. [ ] **可选**：移动 `ui.tsx` 和 `react-shim.d.ts` 到独立的 `src/ui/` 目录
17. [ ] **可选**：如果移动，更新 `langgraph.json` 的 `ui` 路径

### Phase 6: 测试
18. [ ] 为每个模块添加单元测试
19. [ ] 运行集成测试验证

---

## 5. 注意事项

### 5.1 循环导入
- 使用延迟导入或依赖注入避免循环导入
- 状态定义放在独立文件，其他模块只导入状态

### 5.2 配置管理
- 敏感信息（API Key）必须通过环境变量
- 考虑使用 `pydantic-settings` 进行配置验证

### 5.3 langgraph.json 配置
```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "agent": "agent.graph:build_graph"
  },
  "ui": {
    "agent": "./src/agent/ui.tsx"
  },
  "env": ".env",
  "image_distro": "wolfi"
}
```

> **重要**：使用模块路径 `agent.graph:build_graph` 而非文件路径，避免相对导入错误。
> 需要先运行 `uv pip install -e .` 将项目安装为可编辑包。

### 5.4 测试策略
- 单元测试：测试单个节点函数
- 集成测试：测试完整图流程
- 使用 mock 隔离外部依赖（LLM、API）

---

## 6. 重构收益

| 方面 | 重构前 | 重构后 |
|------|--------|--------|
| 代码行数（graph.py） | 1200+ 行 | **85 行** ✅ |
| 模块数量 | 1 个巨型文件 | **14 个模块** |
| 可维护性 | 低 | **高** |
| 可测试性 | 低 | **高** |
| 模块复用 | 无 | **支持** |
| 团队协作 | 困难 | **容易** |
| 扩展新功能 | 困难 | **容易** |

### 重构后的模块清单

| 模块 | 文件 | 职责 |
|------|------|------|
| 状态 | `state.py` | CopilotState, ShortcutState |
| 配置 | `config.py` | API URLs, MCP_ACTION_CATALOG |
| LLM | `utils/llm.py` | llm, llm_nano 实例 |
| HITL | `utils/hitl.py` | hitl_confirm 函数 |
| UI 推送 | `utils/ui.py` | push_shortcut_ui 函数 |
| 辅助 | `utils/helpers.py` | 消息解析、状态查找等 |
| 入口节点 | `nodes/entry.py` | entry_node |
| 路由节点 | `nodes/router.py` | start_intent_ui, route_intent |
| RAG 节点 | `nodes/rag.py` | handle_rag |
| 文章节点 | `nodes/article.py` | start_article_ui, handle_article |
| Shortcut 节点 | `nodes/shortcut.py` | shortcut_init/select/confirm/execute/cancelled |
| Shortcut 子图 | `subgraphs/shortcut.py` | build_shortcut_subgraph |
| RAG 工具 | `tools/rag.py` | rag_query |
| 文章工具 | `tools/article.py` | call_cloud_article_workflow |
| 主图 | `graph.py` | build_graph（组装逻辑）|

---

## 7. 前端 UI 组件说明

### 7.1 文件结构

```
src/agent/
├── ui.tsx              # Generative UI 组件
└── react-shim.d.ts     # React 类型声明（TypeScript 兼容）
```

### 7.2 UI 组件清单

| 组件名 | 用途 | 触发 `push_ui_message` 的 name |
|--------|------|-------------------------------|
| `IntentRouterCard` | 显示意图识别状态 | `intent_router` |
| `ArticleWorkflowCard` | 显示文章生成工作流进度 | `article_workflow` |
| `MCPWorkflowCard` | 显示 MCP/Shortcut 工作流 | `mcp_workflow` |

### 7.3 react-shim.d.ts 作用

该文件为 TypeScript 提供最小化的 React 类型声明，确保在没有安装 `@types/react` 的环境中 IDE 不会报错。

```typescript
// 关键声明
declare module "react" {
  export type ReactNode = any;
  export type FC<P = {}> = (props: P) => any;
  // ...
}
```

### 7.4 是否需要迁移？

**当前决策**：保留在 `src/agent/` 目录内。

**原因**：
1. LangGraph 官方模板将 UI 与 graph 放在同一目录
2. `langgraph.json` 的 `ui` 配置支持当前路径
3. UI 组件与后端状态紧密耦合，放在一起便于维护

**如需迁移到 `src/ui/`**：
1. 创建 `src/ui/` 目录
2. 移动 `ui.tsx` 和 `react-shim.d.ts`
3. 更新 `langgraph.json`：
   ```json
   "ui": {
     "agent": "./src/ui/ui.tsx"
   }
   ```
4. 更新 `ui.tsx` 中的 `/// <reference path="./react-shim.d.ts" />`

---

## 8. 参考资料

- [LangGraph Best Practices](https://www.swarnendu.de/blog/langgraph-best-practices/)
- [LangGraph GitHub Templates](https://github.com/langchain-ai/langgraphjs-starter-template)
- [Building Production-Ready LangGraph Applications](https://medium.com/@vishwajeetv2003/building-production-ready-applications-with-langgraph)
- [LangGraph Generative UI](https://langchain-ai.github.io/langgraph/agents/generative-ui/)
