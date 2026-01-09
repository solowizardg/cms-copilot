# Agent Chat UI 前端对接参数说明（cms-copilot）

本文档面向使用 **agent-chat-ui**（`agentchat.vercel.app`）调用本仓库 LangGraph 的前端同学，说明“前端能传哪些参数/怎么传”。

## 约定

- 本项目通过 `langgraph dev` 启动本地 LangGraph Server（见 `README.md`）。
- 前端调用时传的 **input** 会被合并进图的状态（`CopilotState`）。
- 本项目支持通过 `direct_intent` **跳过意图识别**，直接进入下游流程（统一口径：只接受意图标签，不接受节点名）。

## 前端可传的 input 字段（推荐/支持）

### 1) `messages`（必传）

- **类型**：数组
- **含义**：对话消息列表；最后一条通常是用户输入
- **建议格式**：使用 LangChain 标准消息结构（最常见是 `role/content`）

示例：

```json
{
  "messages": [
    { "role": "user", "content": "如何在后台新建文章？" }
  ]
}
```

### 2) `tenant_id`（可选）

- **类型**：string
- **含义**：租户 ID（部分工具/工作流会用到）

### 3) `site_id`（可选）

- **类型**：string
- **含义**：站点 ID（部分工具/工作流会用到）

### 4) `direct_intent`（可选，但这是“直达/跳过意图识别”的唯一入口参数）

- **类型**：`string | null`
- **含义**：直接指定意图标签，跳过 `router_ui` / `router`，直接进入下游节点
- **允许值（统一意图标签枚举）**：
  - `rag`：RAG 问答
  - `shortcut`：快捷指令（MCP 子图）
  - `article_task`：文章任务（可能会先询问 topic/content_format/target_audience/tone 等必要参数，再进入 workflow UI）
  - `seo_planning`：SEO 规划
  - `site_report`：站点报告

> 注意：`direct_intent` **不再支持**传 `article_ui`/`seo_ui` 这类“节点名”，避免前端有两套规则。

## 明确不建议前端传的字段（内部状态）

这些字段由图/子图内部维护，用于断点恢复或人机交互状态机；前端一般不要手动设置：

- `resume_target`：内部用来决定 entry 后跳到哪个节点（主要用于恢复/续跑）
- `options` / `selected` / `confirmed`：shortcut 子图的人机交互状态
- `intent` / `intent_ui_id` / `intent_started_at`：意图识别与 UI 展示内部字段
- 各类 `*_ui_id` / `*_anchor_id`：UI 卡片锚点/更新用字段

## 调用示例（agent-chat-ui 常用方式）

### 示例 A：默认模式（不传 `direct_intent`，走意图识别）

```json
{
  "messages": [{ "role": "user", "content": "帮我做一个 SEO 周计划" }],
  "tenant_id": "t-xxx",
  "site_id": "s-xxx"
}
```

### 示例 B：直达模式（传 `direct_intent`，跳过意图识别）

```json
{
  "messages": [{ "role": "user", "content": "我想直接问使用说明" }],
  "direct_intent": "rag",
  "tenant_id": "t-xxx",
  "site_id": "s-xxx"
}
```

### 示例 C：同一会话续聊（thread_id）

为了让多轮对话/子图中断恢复（checkpoint）稳定工作，建议前端在同一个会话里固定使用同一个 `thread_id`（agent-chat-ui 通常会提供会话/线程配置入口）。

> 具体 `thread_id` 放在哪个字段里取决于你们接入的 LangGraph Server 调用方式（REST/SDK）。核心要求是：**同一会话的多次请求，`thread_id` 保持一致**，让 checkpointer 能命中同一个线程的状态。

## 常见问题

### 1) 我传了 `direct_intent` 但没有生效？

请检查：

- `direct_intent` 是否是上面的 5 个枚举之一（大小写需一致）
- 是否在同一个会话里复用了旧状态（例如你在恢复线程中，`resume_target` 已经指向 shortcut 流程）

### 2) shortcut 流程需要前端传 `confirmed/options` 吗？

不需要。前端只要按正常聊天把“选择/确认”的文本发回去即可，子图会自己维护状态并通过 interrupt 续跑。

---

## 使用 Generative UI（后端同仓 React 组件）做“文章澄清”（推荐）

如果你使用的是 LangGraph/LangSmith 的 **Generative UI**（`push_ui_message` + 后端同仓的 React 组件），推荐的交互方式是：

- **后端**：用 `push_ui_message("article_clarify", props)` 推送澄清表单组件（并把已收集字段放到 props 里用于预填）。
- **组件内**：通过 `useStreamContext().submit({ messages: [...] })` 继续对话，让图进入下一轮解析/补齐。

这样不会出现默认的 interrupt “需要人工处理”面板，也不需要 resume。


