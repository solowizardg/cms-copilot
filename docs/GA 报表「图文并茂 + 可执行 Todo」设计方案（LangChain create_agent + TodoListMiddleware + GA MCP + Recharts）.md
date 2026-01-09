# GA 报表「图文并茂 + 可执行 Todo」设计方案（LangChain `create_agent` + `TodoListMiddleware` + GA MCP + Recharts）

> 目标：用户从“查询报表”开始，报表输出过程中**边出图边解释**，流程最后给出**可操作项**（如“发新闻/发案例/触发 SEO/优化落地页”），并把这些操作项写入**Todo 清单**，方便用户执行与复盘。

------

## 1. 背景与目标

### 1.1 你现在的问题

- 你已经能用 GA MCP 取数并在 LangGraph 聊天 UI 里画 Recharts 图表。
- 但用户看完图仍然“不知道这意味着什么 / 下一步做什么”。

### 1.2 本方案要达成的产品结果

1. **看得懂**：每张图旁边立刻输出“1 句话结论 + 证据点 + 假设（带置信度）”。
2. **有动作**：每张图后生成 1~3 个可执行动作，并写入 Todo list（`write_todos`）。`TodoListMiddleware`会给 agent 自动注入 `write_todos` 工具和系统提示。[LangChain 文档+1](https://docs.langchain.com/oss/python/langchain/middleware/built-in?utm_source=chatgpt.com)
3. **有结果**：每个动作都带“验收指标 + 复盘窗口（例如 7 天）”，可以一键复跑同一套报表对比。

------

## 2. 技术选型与关键约束

### 2.1 Agent 与规划能力

- 使用 LangChain **`create_agent`**：官方定位是“production-ready agent”，在循环里调用工具直到满足停止条件。[LangChain 文档+1](https://docs.langchain.com/oss/python/langchain/agents?utm_source=chatgpt.com)
- 用 **`TodoListMiddleware`**：提供 `write_todos` 工具与引导提示，使建议能落成结构化任务清单。[LangChain 文档+1](https://docs.langchain.com/oss/python/langchain/middleware/built-in?utm_source=chatgpt.com)
- 建议搭配 **Structured Output**：`create_agent` 支持结构化输出，结构化结果会落在 agent state 的 `structured_response`。[LangChain 文档](https://docs.langchain.com/oss/python/langchain/structured-output?utm_source=chatgpt.com)

### 2.2 GA MCP 接入

- 使用 `langchain-mcp-adapters` 的 **`MultiServerMCPClient`** 加载 GA MCP tools。[GitHub+1](https://github.com/langchain-ai/langchain-mcp-adapters?utm_source=chatgpt.com)
- 默认 **stateless**：每次 tool 调用创建新 session、执行、清理；如果以后需要 stateful，可用 `client.session()` 管理生命周期。[LangChain 文档](https://docs.langchain.com/oss/python/langchain/mcp?utm_source=chatgpt.com)

### 2.3 流式“图文并茂”输出

- LangGraph 支持在节点/工具内部用 `get_stream_writer()` 发**自定义流数据**，并在 `.stream/.astream` 里设置 `stream_mode="custom"`（可与 `["updates","custom"]` 联用）。[LangChain 文档+2LangChain 文档+2](https://docs.langchain.com/oss/python/langgraph/streaming?utm_source=chatgpt.com)

> 工程注意：社区与 issue 里有反馈“async tools 的 custom events 捕获问题/事件元数据继承问题”，建议把 UI 事件发射放在**graph 节点（或同步路径）**里，不要依赖 async tool 内部直接写 UI。[GitHub+1](https://github.com/langchain-ai/langgraph/issues/6447?utm_source=chatgpt.com)

### 2.4 Recharts 数据形态

- Recharts X 轴/线条都依赖 `dataKey` 指向 `data` 数组对象的字段，例如 `XAxis dataKey="date"`、`Line dataKey="sessions"`。[Recharts+1](https://recharts.github.io/en-US/api/XAxis/?utm_source=chatgpt.com)

------

## 3. MVP 范围（先做能卖的最小闭环）

> 不要先做“任意 GA 问答 + 任意建议”。先锁 3 张图 + 3 类动作，最容易让客户感到价值。

### 3.1 固定三张图（每次查询都输出）

1. **趋势图**：最近 7/28 天 `sessions/users/key_events` 走势
2. **渠道贡献图**：按 channel group（或 source/medium）拆变化贡献度
3. **落地页 TopN**：Top landing pages 的 sessions、key_events 或转化相关指标

GA Data API 的 `runReport` 是简单报表查询的首选方法；漏斗类（可选）用 `runFunnelReport`。[Google for Developers+1](https://developers.google.com/analytics/devguides/reporting/data/v1?utm_source=chatgpt.com)

### 3.2 固定三类动作（按证据触发）

- 内容类：**发新闻/发案例/FAQ 扩写**（直接触发你的 article workflow）
- SEO 类：**触发 SEO 体检/索引与标题描述检查**（你的 SEO 子图）
- 站点改造类：**打开站点设计器定位到页面/组件**（落地页 CTA/表单/首屏文案优化）

------

## 4. 总体架构

### 4.1 分层原则（最重要）

1. **取数层（GA MCP tools）**：只管数据查询
2. **分析层（确定性代码）**：生成“证据包 EvidencePack”（环比、贡献度、TopN、异常点）
3. **解释与动作层（LLM Agent）**：只读 EvidencePack，输出 Explain + Actions，并写入 Todo

这样能最大幅度减少“模型看错口径/胡归因”。

### 4.2 组件图（建议）

- `GAReportOrchestrator`（LangGraph 主图）
  - `FetchReportsNode`（调用 GA MCP）
  - `AnalyzeNode`（纯代码：EvidencePack）
  - `EmitChartNode`（把数据变成 Recharts-friendly，并发 UI 事件）
  - `InsightsAgentNode`（`create_agent` + `TodoListMiddleware` + structured output）
  - `EmitExplainActionsNode`（发解释卡 + 动作卡 UI 事件）
  - `EmitSummaryNode`（总览卡）

------

## 5. 流式 UI 事件协议（前端 Recharts 友好）

### 5.1 事件通道

- 后端：`writer({ ... })` 发 `custom` 事件
- 前端：订阅 `custom` stream，按顺序 append 到卡片列表

LangGraph 自定义流方式与 `stream_mode="custom"` 的要求见官方文档。[LangChain 文档+2LangChain 文档+2](https://docs.langchain.com/oss/python/langgraph/streaming?utm_source=chatgpt.com)

### 5.2 统一事件模型

```
{
  "type": "ui.card",
  "card": {
    "kind": "chart" | "explain" | "actions" | "summary",
    "id": "uuid",
    "groupId": "request-uuid",
    "title": "...",
    "payload": {}
  }
}
```

### 5.3 ChartCard（Recharts-ready）

```
{
  "kind": "chart",
  "title": "最近28天 Sessions 趋势",
  "payload": {
    "chartType": "line",
    "xKey": "date",
    "series": [
      {"key": "sessions", "label": "Sessions"},
      {"key": "key_events", "label": "Key events"}
    ],
    "data": [
      {"date": "2026-01-01", "sessions": 1200, "key_events": 21}
    ]
  }
}
```

> 前端渲染依据：`XAxis dataKey`、`Line dataKey` 的定义见 Recharts API。[Recharts+1](https://recharts.github.io/en-US/api/XAxis/?utm_source=chatgpt.com)

### 5.4 ExplainCard（可读解释）

```
{
  "kind": "explain",
  "title": "解读：自然流量导致总体下滑",
  "payload": {
    "oneLiner": "最近7天 Sessions 环比下降 18%，主要由自然搜索下降导致。",
    "evidence": [
      "自然搜索 sessions -2400（贡献度 62%）",
      "Top1 落地页 /product-a sessions -900",
      "移动端 key events rate 下降 1.2pp"
    ],
    "hypotheses": [
      {"text": "核心页面收录/排名波动", "confidence": "high"},
      {"text": "移动端体验影响参与度", "confidence": "medium"}
    ]
  }
}
```

### 5.5 ActionsCard（可执行动作 + 验收指标）

```
{
  "kind": "actions",
  "title": "下一步可操作项",
  "payload": {
    "actions": [
      {
        "id": "act-1",
        "title": "发一篇新闻：围绕 Product A 新应用场景",
        "why": "该落地页流量下降明显，需要新内容覆盖长尾",
        "effort": "low",
        "impact": "medium",
        "cta": {
          "type": "trigger_workflow",
          "workflow": "article.news",
          "params": {"topic_hint": "Product A 应用场景/案例", "category": "企业新闻"}
        },
        "successMetric": {"metric": "organic_sessions", "windowDays": 7, "target": "+10%"}
      }
    ]
  }
}
```

------

## 6. 后端详细设计（指导 Cursor 改代码）

### 6.1 推荐目录结构

```
src/
  graphs/
    ga_insights_flow.py
  ga/
    mcp_client.py
    query_plans.py
    analyzers.py
    chart_builders.py
  agents/
    insights_agent.py
    prompts/
      insights_system.md
      action_catalog.md
  schemas/
    ui_cards.py
    evidence.py
```

### 6.2 GA MCP 客户端封装（`ga/mcp_client.py`）

- 用 `MultiServerMCPClient` 加载 tools，进程级缓存工具列表
- 明确 stateless 特性，避免你在一次对话里假设它“记住了上一步”[LangChain 文档+1](https://docs.langchain.com/oss/python/langchain/mcp?utm_source=chatgpt.com)

关键输出：

- `get_ga_tools() -> list[Tool]`
- `run_report(plan) -> RawReport`

### 6.3 查询剧本（`ga/query_plans.py`）

固定 3 套计划（趋势/渠道/落地页），每套产出 `ChartSpec[]`。

- `runReport` 是简单查询首选。[Google for Developers](https://developers.google.com/analytics/devguides/reporting/data/v1?utm_source=chatgpt.com)
- 后续要做漏斗再补 `runFunnelReport`。[Google for Developers](https://developers.google.com/analytics/devguides/reporting/data/v1/rest/v1alpha/properties/runFunnelReport?utm_source=chatgpt.com)

> 建议：把“时间范围、对比窗口、维度/指标、过滤器”都写死为模板参数，别让模型自由拼查询。

### 6.4 分析器（`ga/analyzers.py`）——生成 EvidencePack（纯代码）

输入：RawReport
 输出：EvidencePack（结构化事实）

最少字段：

- `metric_current`, `metric_prev`, `delta_abs`, `delta_pct`
- `contributors`: Top 渠道贡献度、Top 落地页贡献度
- `anomalies`: 基于阈值/简单统计的异常点
- `kpi`: 与 key events 相关的变化（如有）

### 6.5 图表构建（`ga/chart_builders.py`）——生成 Recharts-friendly data

输出必须符合：

- `data: list[dict]`
- `xKey`、`series[i].key` 都是 dict 的字段名
   Recharts 的 `XAxis dataKey` 与 `Line dataKey` 依赖该结构。[Recharts+1](https://recharts.github.io/en-US/api/XAxis/?utm_source=chatgpt.com)

### 6.6 Insights Agent（`agents/insights_agent.py`）

用 LangChain `create_agent` + `TodoListMiddleware`：

- `create_agent` 是官方推荐的 agent 构建方式。[LangChain 文档+1](https://docs.langchain.com/oss/python/langchain/agents?utm_source=chatgpt.com)
- `TodoListMiddleware` 自动提供 `write_todos` 工具与提示。[LangChain 文档+1](https://docs.langchain.com/oss/python/langchain/middleware/built-in?utm_source=chatgpt.com)
- 用 structured output，让输出稳定落在 `structured_response`。[LangChain 文档](https://docs.langchain.com/oss/python/langchain/structured-output?utm_source=chatgpt.com)

**Agent 的输入**：EvidencePack + ActionCatalog（你允许推荐/触发的动作清单）
 **Agent 的输出（结构化）**：ExplainCard + ActionsCard +（可选）SummaryHighlights
 同时 agent 会调用 `write_todos` 写 todo。

> 你可以再加一个 `LLMToolSelectorMiddleware`（工具过滤）降低“工具太多选错”的概率（该 middleware 用 structured output 选择工具）。[LangChain 文档](https://docs.langchain.com/oss/python/langchain/middleware/built-in?utm_source=chatgpt.com)

### 6.7 LangGraph 主图（`graphs/ga_insights_flow.py`）

**核心模式：每张图一个“段落”**：先发图，再发解释，再发动作，最后总览。

伪流程：

1. 解析用户意图 → 选择 query plan（趋势/渠道/落地页）
2. 对每个 ChartSpec：
   - 调 GA MCP 取数（runReport）
   - analyzer 产出 EvidencePack
   - chart_builder 产出 ChartCard（Recharts payload）
   - `writer(ui.card: chart)` 立即发图[LangChain 文档](https://docs.langchain.com/oss/python/langgraph/streaming?utm_source=chatgpt.com)
   - 调 insights_agent 生成 explain/actions（structured）
   - `writer(ui.card: explain)`、`writer(ui.card: actions)` 立即发出[LangChain 文档](https://docs.langchain.com/oss/python/langgraph/streaming?utm_source=chatgpt.com)
3. 汇总：发 SummaryCard（Top 3 结论 + Top 3 动作 + 复盘指标）

调用 `.astream(..., stream_mode=["updates","custom"])`，便于 UI 与调试同时进行。[LangChain 文档+1](https://docs.langchain.com/oss/python/langchain/streaming?utm_source=chatgpt.com)

------

## 7. 前端详细设计（React + Recharts）

### 7.1 渲染模型：卡片流

- 状态：`cards: UICard[]`
- 收到 `ui.card` 事件：`setCards(prev => [...prev, card])`

### 7.2 ChartCard 组件（核心）

- `payload.data` 直接传 `<LineChart data={data}>`
- `<XAxis dataKey={xKey} />`、`<Line dataKey={series[i].key} />`
   Recharts API 对这些 props 有明确说明。[Recharts+1](https://recharts.github.io/en-US/api/XAxis/?utm_source=chatgpt.com)

### 7.3 ActionsCard 组件（关键闭环）

- 每个 action 显示：title/why/effort/impact/successMetric
- CTA 点击：
  - `trigger_workflow(article.news, params)` → 调你的平台 API（Laravel/平台服务层）触发文章工作流
  - `open_designer(pageId, componentId)` → 打开设计器定位
  - `trigger_seo_audit(pageId)` → 触发 SEO 子图

------

## 8. Action Catalog（动作目录）设计

建议配置化（YAML/DB 均可），并在 agent prompt 里声明：

- **只能推荐目录内动作**（防止模型编造不存在的按钮）
- 每个动作必须输出 successMetric（7 天复盘）

示例（YAML）：

```
- id: article.news
  label: 发新闻
  params_schema:
    topic_hint: string
    category: string
- id: seo.audit
  label: SEO体检
  params_schema:
    page_id: string
- id: designer.open
  label: 打开设计器
  params_schema:
    page_id: string
    anchor: string
```

------

## 9. 可靠性、成本与风控

### 9.1 限流与合并查询

- `runReport` 是首选；有批量需求可以用 `batchRunReports`（减少往返）。[Google for Developers](https://developers.google.com/analytics/devguides/reporting/data/v1?utm_source=chatgpt.com)
- 缓存策略：同一请求内的中间报表结果缓存；同一站点短时间重复查询可做 1~5 分钟缓存（按你业务决定）。

### 9.2 结果可信度提示

ExplainCard 必须带：

- “证据点来源于哪张图/哪个维度”
- hypotheses 置信度（high/medium/low）
- 如缺 key event/样本不足：优先建议“补埋点/定义关键事件/延长窗口”

### 9.3 安全

- GA 凭据只放后端，不下发前端
- Actions 的 `cta.params` 需要后端校验（避免前端篡改触发越权操作）

------

## 10. 测试计划（最少要做这些）

### 10.1 单元测试（必须）

- `analyzers.py`：环比、贡献度分解、TopN 逻辑
- `chart_builders.py`：输出是否满足 Recharts dataKey 需求

### 10.2 集成测试（建议）

- 用 mock GA MCP 返回固定 report，跑一遍 graph，断言输出的 `ui.card` 序列：
  - chart → explain → actions → chart → explain → actions → summary

### 10.3 回归测试（建议）

- 固定 3 个典型用户问题（流量下降/转化下降/渠道对比）做 snapshot（卡片 payload 不应乱变）

------

## 11. 交付清单（你让 Cursor 按这个改就行）

1. 新增 schemas：`UICard`, `ChartPayload`, `ExplainPayload`, `ActionsPayload`, `EvidencePack`
2. 新增 `ActionCatalog` 配置与校验
3. 新增 `ga/query_plans.py`（三套剧本）
4. 新增 `ga/analyzers.py`（证据包）
5. 新增 `ga/chart_builders.py`（Recharts-ready）
6. 新增 `agents/insights_agent.py`：`create_agent + TodoListMiddleware + structured output`[LangChain 文档+2LangChain 文档+2](https://docs.langchain.com/oss/python/langchain/agents?utm_source=chatgpt.com)
7. 改 `graphs/ga_insights_flow.py`：按“段落”流式发 `ui.card`，`stream_mode=["updates","custom"]`[LangChain 文档+1](https://docs.langchain.com/oss/python/langchain/streaming?utm_source=chatgpt.com)
8. 前端新增 3 个卡片组件（Chart/Explain/Actions）+ 卡片流容器（Recharts 渲染按 `dataKey`）