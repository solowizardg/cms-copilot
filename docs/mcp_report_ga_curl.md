# Report MCP（Google Analytics Server）curl 调用指南

本文档用于测试 Report MCP Endpoint：`http://127.0.0.1:8001/mcp`

该服务使用 **MCP streamable_http**（SSE 事件流），因此：

- **所有请求**都必须带 `Accept: application/json, text/event-stream`
- 第一步 `initialize` 会在**响应头**返回 `mcp-session-id`（后续请求要带 `Mcp-Session-Id`）
- 大多数响应体是 `text/event-stream`，内容形如：
  - `event: message`
  - `data: { ...jsonrpc... }`

---

## 0) 约定变量（建议）

在命令行里先准备：

```bash
# MCP endpoint
export MCP_URL="http://127.0.0.1:8001/mcp"

# 必填：站点上下文（按你系统的实际 site uuid 替换）
export SITE_ID="019b6d33-367c-7244-a6ae-af42b7f32090"

# 可选：租户
# export TENANT_ID="your-tenant-id"
```

---

## 1) initialize（建立会话，拿 Mcp-Session-Id）

> 关键：用 `-i` 打印响应头，你需要从响应头里复制 `mcp-session-id: ...`

```bash
curl -i -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "init-1",
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-11-25",
      "capabilities": {},
      "clientInfo": { "name": "cms-copilot", "version": "0.0.0" }
    }
  }'
```

> 备注：你也可以使用旧版 `protocolVersion`（例如 `2024-11-05`），该 server 目前同时兼容多个版本。

你会看到类似响应头（示例）：

```text
mcp-session-id: f7aa62871a9c4366a22ebb5701bca932
content-type: text/event-stream
```

把它保存下来：

```bash
export MCP_SESSION_ID="f7aa62871a9c4366a22ebb5701bca932"
```

> 说明：`initialize` 的响应 body 也是 SSE，你不用等它结束，拿到 session id 即可。

---

## 2) notifications/initialized（会话初始化完成通知）

```bash
curl -i -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
    "params": {}
  }'
```

通常会返回 `202 Accepted`（无 body 或 body 很短）。

---

## 3) tools/list（列出可用工具）

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "tools-list-1",
    "method": "tools/list",
    "params": {}
  }'
```

返回是 SSE，你会看到类似：

```text
event: message
data: {"jsonrpc":"2.0","id":"tools-list-1","result":{"tools":[ ... ]}}
```

你需要关注每个 tool 的：

- `name`：工具名（后续 `tools/call` 要用）
- `inputSchema`：入参（snake_case）

---

## 4) tools/call（调用工具：通用模板）

通用模板如下（把 `<TOOL_NAME>` 和 `arguments` 替换掉）：

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-1",
    "method": "tools/call",
    "params": {
      "name": "<TOOL_NAME>",
      "arguments": { }
    }
  }'
```

### 4.1 响应解析（重要）

大多数工具返回结构是：

- JSON-RPC 外层：`data: {"jsonrpc":"2.0","id":"...","result":{...}}`
- 真实内容通常在：`result.content[0].text`
- 且 `text` **经常是 JSON 字符串**（你需要再 JSON.parse 一次；用肉眼看也行）

示例（缩写）：

```json
{
  "jsonrpc": "2.0",
  "id": "call-1",
  "result": {
    "content": [
      { "type": "text", "text": "{\\n  \\\"rows\\\": [...]\\n}" }
    ]
  }
}
```

---

## 5) 常用工具示例（按当前 server：Google Analytics）

> 下面工具名以 `tools/list` 实际返回为准（GA MCP Server 通常会包含这些）。

### 5.1 获取账号/属性列表：get_account_summaries

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-account-summaries-1",
    "method": "tools/call",
    "params": {
      "name": "get_account_summaries",
      "arguments": {}
    }
  }'
```

你会在内容里看到类似：

- `account`: `"accounts/xxxx"`
- `property_summaries[].property`: `"properties/339898497"`

### 5.2 获取属性详情：get_property_details

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-property-details-1",
    "method": "tools/call",
    "params": {
      "name": "get_property_details",
      "arguments": {
        "property_id": "properties/339898497"
      }
    }
  }'
```

### 5.3 绑定的 Google Ads 链接：list_google_ads_links

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-ads-links-1",
    "method": "tools/call",
    "params": {
      "name": "list_google_ads_links",
      "arguments": {
        "property_id": "properties/339898497"
      }
    }
  }'
```

### 5.4 自定义维度/指标：get_custom_dimensions_and_metrics

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-custom-dims-1",
    "method": "tools/call",
    "params": {
      "name": "get_custom_dimensions_and_metrics",
      "arguments": {
        "property_id": "properties/339898497"
      }
    }
  }'
```

### 5.5 跑报表（历史区间）：run_report

GA Data API `run_report` 需要：

- `property_id`
- `date_ranges`（数组，元素包含 `start_date`/`end_date`）
- `dimensions`（数组）
- `metrics`（数组）

#### 示例 A：最近 7 天每日 active users

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-run-report-1",
    "method": "tools/call",
    "params": {
      "name": "run_report",
      "arguments": {
        "property_id": "properties/339898497",
        "date_ranges": [
          { "start_date": "7daysAgo", "end_date": "yesterday" }
        ],
        "dimensions": ["date"],
        "metrics": ["activeUsers"],
        "limit": 10000
      }
    }
  }'
```

#### 示例 B：设备分布（sessions by deviceCategory）

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-run-report-2",
    "method": "tools/call",
    "params": {
      "name": "run_report",
      "arguments": {
        "property_id": "properties/339898497",
        "date_ranges": [
          { "start_date": "7daysAgo", "end_date": "yesterday" }
        ],
        "dimensions": ["deviceCategory"],
        "metrics": ["sessions"],
        "limit": 100
      }
    }
  }'
```

#### 示例 C：流量来源（sessions by sessionDefaultChannelGroup）

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-run-report-3",
    "method": "tools/call",
    "params": {
      "name": "run_report",
      "arguments": {
        "property_id": "properties/339898497",
        "date_ranges": [
          { "start_date": "7daysAgo", "end_date": "yesterday" }
        ],
        "dimensions": ["sessionDefaultChannelGroup"],
        "metrics": ["sessions"],
        "limit": 100
      }
    }
  }'
```

#### 示例 D：热门页面（pagePath + pageTitle by screenPageViews）

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-run-report-4",
    "method": "tools/call",
    "params": {
      "name": "run_report",
      "arguments": {
        "property_id": "properties/339898497",
        "date_ranges": [
          { "start_date": "7daysAgo", "end_date": "yesterday" }
        ],
        "dimensions": ["pagePath", "pageTitle"],
        "metrics": ["screenPageViews"],
        "limit": 200
      }
    }
  }'
```

### 5.6 跑实时报表：run_realtime_report

Realtime 需要：

- `property_id`
- `dimensions`（realtime dimensions）
- `metrics`（realtime metrics）

示例：当前在线用户按国家（示例维度/指标以 GA Realtime Schema 为准）

```bash
curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "X-Site-Id: $SITE_ID" \
  -H "Mcp-Session-Id: $MCP_SESSION_ID" \
  -d '{
    "jsonrpc": "2.0",
    "id": "call-realtime-1",
    "method": "tools/call",
    "params": {
      "name": "run_realtime_report",
      "arguments": {
        "property_id": "properties/339898497",
        "dimensions": ["country"],
        "metrics": ["activeUsers"],
        "limit": 50
      }
    }
  }'
```

---

## 6) 常见错误

### 6.1 406 Not Acceptable

如果你看到：

```json
{"error":{"message":"Not Acceptable: Client must accept both application/json and text/event-stream"}}
```

说明你缺了这个头：

```text
Accept: application/json, text/event-stream
```

### 6.2 session 相关错误

如果 `tools/list` / `tools/call` 失败，优先确认：

- 你已经 `initialize` 并拿到了 `mcp-session-id`
- 后续请求带了 `Mcp-Session-Id: ...`
- 已发送 `notifications/initialized`


