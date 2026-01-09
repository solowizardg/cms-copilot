## GA MCP 工具说明（给产品/业务同学）

本文描述当前系统通过 **GA MCP**（`http://127.0.0.1:8001/mcp`）可调用的工具能力、适用场景与输入输出口径。站点报告（Report）相关能力均通过 MCP 工具完成调用与取数。

### 一句话总结
- **报表类**：`run_report`（历史窗口报表）、`run_realtime_report`（近 30 分钟实时）——用于图表与洞察。
- **配置/元信息类**：`get_account_summaries`、`get_property_details`、`get_custom_dimensions_and_metrics`、`list_property_annotations`、`list_google_ads_links`——用于站点/属性信息、口径解释、调试与联动配置检查。

---

## MCP 调用方式（从产品视角理解）

### 调用链路
- Copilot 后端通过 MCP 客户端加载工具列表（tools），再按需调用其中某个工具。
- 每次工具调用都带上租户/站点上下文（HTTP Header：`X-Site-Id`、`X-Tenant-Id`），用于权限与数据隔离。

### 返回数据形态
- MCP 工具返回通常会被后端规整为 JSON 友好的结构（例如 report 的 rows/dimensions/metrics），便于渲染与后续洞察分析。

---

## 1) run_report（历史窗口报表）

### 作用
用于查询指定 GA4 属性在**某个时间范围**内的统计数据（最常用的离线报表查询）。

### 典型用途
- 7/28 天趋势（按 date）
- 渠道/来源分布（按 `sessionDefaultChannelGroup`、`sourceMedium` 等）
- 设备分布（按 `deviceCategory`）
- 热门页面（按 `pagePath` / `pageTitle`）

### 可用参数（以 MCP tool 描述为准）
说明：当前 GA MCP 未暴露可机器读取的参数 schema（所以在产品侧看不到“枚举列表”），但 **tool description** 给出了可用字段与约束。`run_report` 支持的参数如下（字段名用 snake_case）：  

- **property_id**：GA4 属性 ID。格式：数字或 `properties/<number>`
- **date_ranges**：日期范围列表（GA Data API `DateRange`）
- **dimensions**：维度列表（GA Data API dimensions）
- **metrics**：指标列表（GA Data API metrics）
- **dimension_filter（可选）**：维度过滤（GA Data API `FilterExpression`）
- **metric_filter（可选）**：指标过滤（GA Data API `FilterExpression`）
- **order_bys（可选）**：排序（GA Data API `OrderBy` 列表）
- **limit（可选）**：返回行数上限（`<= 250,000`；分页用）
- **offset（可选）**：分页起始行（从 0 开始）
- **currency_code（可选）**：货币代码（ISO4217，比如 `USD`）
- **return_property_quota（可选）**：是否返回 quota 信息

### 我们“能统计什么 metrics / dimensions”？
这里的 metrics/dimensions **不是后端写死的枚举**，而是：
- **标准口径**：GA4 Data API 文档表格里的标准维度/指标（所有属性都可用）  
  - metrics 列表：`https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema#metrics`  
  - dimensions 列表：`https://developers.google.com/analytics/devguides/reporting/data/v1/api-schema#dimensions`
- **自定义口径**：你们 GA4 属性里配置的 custom dimensions/metrics  
  - 用 `get_custom_dimensions_and_metrics` 获取 `apiName`，然后直接放进 `dimensions/metrics` 列表

为了便于产品理解，下面列“常用且对 CMS/站点运营最有用的一小部分”（不是全量）：
- **常用 metrics**：`sessions`、`activeUsers`、`screenPageViews`、`engagedSessions`、`engagementRate`、`averageSessionDuration`、`bounceRate`、`eventCount`、`keyEvents`（若 GA4 配置了关键事件）
- **常用 dimensions**：`date`、`sessionDefaultChannelGroup`、`sourceMedium`、`deviceCategory`、`country`、`pagePath`、`pageTitle`、`landingPage`、`eventName`

### 输出（概念说明）
返回一个表格型结果：
- **dimension_headers / metric_headers**：维度/指标列名
- **rows**：每行包含一组维度值与对应指标值

---

## 2) run_realtime_report（实时数据报表）

### 作用
用于查询 GA4 属性**最近约 30 分钟**的实时数据（不带 date_ranges）。

### 典型用途
- 当前在线用户（active users now）
- 实时来源/国家/页面等分布（视 MCP 实现支持的维度/指标）

### 可用参数（以 MCP tool 描述为准）
- **property_id**：GA4 属性 ID
- **dimensions**：Realtime 维度列表（必须是 realtime schema 支持的维度）
- **metrics**：Realtime 指标列表（必须是 realtime schema 支持的指标；Realtime 不支持 custom metrics）
- **dimension_filter（可选）**：维度过滤（`FilterExpression`）
- **metric_filter（可选）**：指标过滤（`FilterExpression`）
- **order_bys（可选）**：排序（`OrderBy`）
- **limit（可选）**：行数上限（`<= 250,000`；分页用）
- **offset（可选）**：分页起始行（从 0 开始）
- **return_property_quota（可选）**：是否返回 realtime quota 信息

### Realtime 的可用 metrics / dimensions
Realtime 口径与 run_report 不同，以 GA4 Realtime schema 为准：
- dimensions：`https://developers.google.com/analytics/devguides/reporting/data/v1/realtime-api-schema#dimensions`
- metrics：`https://developers.google.com/analytics/devguides/reporting/data/v1/realtime-api-schema#metrics`

### 输出
同样是表格型 rows，只是数据窗口为实时。

---

## 3) get_account_summaries（账号摘要）
### 可用参数
- 无（直接返回当前凭据可访问的账号/属性摘要）


### 作用
获取当前凭据可访问的 GA 账号概览，以及账号下的属性/资源摘要。

### 典型用途
- 站点接入时确认“当前账号下有哪些 GA4 属性可选”
- 排查“为什么取不到某个 property”的权限问题

---

## 4) get_property_details（属性详情）
### 可用参数
- **property_id**：GA4 属性 ID（数字或 `properties/<number>`）


### 作用
获取某个 GA4 属性（property）的基础信息（例如显示名、时区等，具体字段取决于 MCP 服务端实现）。

### 典型用途
- 在 UI 上展示“当前报表来自哪个 GA4 属性/时区口径”
- 排查时区导致的日期边界差异（例如 yesterday 的定义）

---

## 5) get_custom_dimensions_and_metrics（自定义维度/指标）
### 可用参数
- **property_id**：GA4 属性 ID（数字或 `properties/<number>`）


### 作用
列出该 GA4 属性下配置的 **custom dimensions / custom metrics**（自定义口径）。

### 典型用途
- 解释“某个业务指标为何查不到”：需要先在 GA4 配置自定义维度/指标
- 生成报表时给出“可用口径清单”（避免模型/用户用不存在的维度/指标）

---

## 6) list_property_annotations（属性注释列表）
### 可用参数
- **property_id**：GA4 属性 ID（数字或 `properties/<number>`）


### 作用
列出 GA4 属性下的注释/事件标记（例如某天上线/投放/改版的注释，具体取决于 MCP 实现）。

### 典型用途
- 报表解读时补充背景：“某天有改版/投放”可作为解释线索

---

## 7) list_google_ads_links（Google Ads 关联列表）
### 可用参数
- **property_id**：GA4 属性 ID（数字或 `properties/<number>`）


### 作用
列出 GA4 属性与 Google Ads 的关联关系（link）。

### 典型用途
- 验证广告投放链路是否正确打通（是否已关联）
- 解释 paid traffic/广告相关维度指标是否可用

---

## 访问与限制（产品需要知道的边界）
- **工具数量由 MCP 服务端决定**：系统只能调用 MCP 暴露出来的工具。当前工具集较精简（以报表查询与元信息为主）。
- **权限/隔离由站点上下文控制**：通过 `X-Site-Id` / `X-Tenant-Id` 做隔离；若无权限，工具会返回错误。
- **报表口径受 GA4 配置影响**：如未配置自定义维度/关键事件等，相关指标可能缺失或为 0。

