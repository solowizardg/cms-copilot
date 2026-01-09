# MCP 网站设置（基础信息）接口文档

## 概述

本文档描述 **MCP 网站设置（基础信息）** 的调用方式，供 LangGraph / Agent 通过 MCP（Model Context Protocol）读取与保存站点基础信息：

- **Business Information（业务信息）**
- **Contact Information（联系信息）**

对应 MCP Web 路由：`/mcp/site-setting-basic`。

---

## MCP 请求流程（Web 模式）

与现有低代码 MCP 一致，必须走标准会话流程：

1. `initialize`（建立会话，获取 `Mcp-Session-Id`）
2. `notifications/initialized`
3. （可选）`tools/list`
4. `tools/call`（调用具体工具）

---

## 请求头（必带）

所有请求必须包含：

```http
Content-Type: application/json
Accept: application/json
Mcp-Session-Id: {session_id}
X-Site-Id: {site_uuid}
```

可选：

```http
X-Tenant-Id: {tenant_id}
```

说明：
- `X-Site-Id` 是站点 UUID（字符串）。后端 `mcpauth` 中间件会读取该 header，用于识别站点上下文。

---

## 响应解析规则（重要）

MCP 返回为 JSON-RPC 包装格式，**真实业务数据在**：

- `result.content[0].text`

并且 `text` 是一个 **JSON 字符串**，需要再次解析：

```js
const rpc = await res.json();
const text = rpc.result.content?.[0]?.text ?? "{}";
const payload = JSON.parse(text);
```

业务 payload 通常形如：

```json
{
  "success": true,
  "message": "xxx",
  "data": { }
}
```

---

## 工具列表

### 1) 获取基础信息：`get_basic_detail`

#### 工具信息
- **name**：`get_basic_detail`
- **用途**：获取网站基础信息（业务信息/联系信息）。当用户想查看、获取、读取网站设置时调用。

#### 参数
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| sections | array | 否 | 要获取的分组，枚举值：`business_information`、`contact_information`；不传则返回全部 |

#### 请求示例（curl）

```bash
curl -X POST "http://localhost:8000/mcp/site-setting-basic" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Mcp-Session-Id: session_12345" \
  -H "X-Site-Id: 019a144c-112e-733a-a7ce-b493dae58453" \
  -d '{
    "jsonrpc": "2.0",
    "id": "setting-basic-001",
    "method": "tools/call",
    "params": {
      "name": "get_basic_detail",
      "arguments": {
        "sections": ["business_information", "contact_information"]
      }
    }
  }'
```

#### 成功响应（业务 payload）

```json
{
  "success": true,
  "message": "获取基础信息成功",
  "data": {
    "sections": [
      {
        "group_name": "business_information",
        "i18n_key": "...",
        "children": []
      },
      {
        "group_name": "contact_information",
        "i18n_key": "...",
        "children": []
      }
    ]
  }
}
```

---

### 2) 保存基础信息：`save_basic_detail`

#### 工具信息
- **name**：`save_basic_detail`
- **用途**：保存网站基础信息。当用户想保存、更新、修改网站设置时调用。

#### 参数
| 参数名 | 类型 | 必填 | 说明 |
|---|---|---|---|
| section | string | 是 | 要保存的分组类型，枚举：`business_information`、`contact_information` |
| system_basic_inspect | object | 是 | 要保存的字段（根据 section 不同，可填字段不同） |

---

#### section = `business_information` 字段

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| industry | string | 否 | 行业，枚举：`manufacturing`, `electronics`, `textiles`, `machinery`, `chemicals`, `food`, `other` |
| main_products | string | 否 | 主营产品 |
| main_business_introduction | string | 否 | 主营业务介绍/公司简介 |
| sales_market | object | 否 | 销售市场 |
| sales_market.country | string | 否 | 国家代码，如 `US`、`CN` |
| sales_market.state | string | 否 | 州/省代码，如 `CA`、`GD` |

---

#### section = `contact_information` 字段

> 注意：系统内该分组实际落在 `company_information`（MCP 对外使用 `contact_information` 命名）。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| company_name | string | 否 | 公司名称 |
| country | object | 否 | 公司所在国家/省州 |
| country.country | string | 否 | 国家代码 |
| country.state | string | 否 | 州/省代码 |
| address | array | 否 | 地址列表 |
| customer_service_hotline | array | 否 | 客服热线列表 |
| customer_service_email | array | 否 | 客服邮箱列表 |

**address 数组元素：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | integer | 否 | 地址ID（更新时传） |
| genre | string | 是 | 地址类型，枚举：`headquarters`, `branch`, `factory`, `warehouse` |
| name | string | 是 | 详细地址 |

**customer_service_hotline 数组元素：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | integer | 否 | ID（更新时传） |
| genre | string | 是 | 类型，枚举：`support`, `sales`, `complaint` |
| country | string | 是 | 国家代码 |
| prefix | string | 是 | 电话国家码，如 `+86`、`+1` |
| phone | string | 是 | 电话号码 |

**customer_service_email 数组元素：**

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| id | integer | 否 | ID（更新时传） |
| genre | string | 是 | 类型，枚举：`support`, `sales`, `complaint` |
| email | string | 是 | 邮箱地址（email 格式） |

#### 请求示例：保存 Business Information

```bash
curl -X POST "http://localhost:8000/mcp/site-setting-basic" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Mcp-Session-Id: session_12345" \
  -H "X-Site-Id: 019a144c-112e-733a-a7ce-b493dae58453" \
  -d '{
    "jsonrpc": "2.0",
    "id": "setting-basic-002",
    "method": "tools/call",
    "params": {
      "name": "save_basic_detail",
      "arguments": {
        "section": "business_information",
        "system_basic_inspect": {
          "industry": "manufacturing",
          "main_products": "xxx",
          "main_business_introduction": "yyy",
          "sales_market": { "state": "CA", "country": "US" }
        }
      }
    }
  }'
```

#### 请求示例：保存 Contact Information

```bash
curl -X POST "http://localhost:8000/mcp/site-setting-basic" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "Mcp-Session-Id: session_12345" \
  -H "X-Site-Id: 019a144c-112e-733a-a7ce-b493dae58453" \
  -d '{
    "jsonrpc": "2.0",
    "id": "setting-basic-003",
    "method": "tools/call",
    "params": {
      "name": "save_basic_detail",
      "arguments": {
        "section": "contact_information",
        "system_basic_inspect": {
          "company_name": "ACME Inc.",
          "country": { "state": "CA", "country": "US" },
          "address": [
            { "genre": "headquarters", "name": "1 Infinite Loop" }
          ],
          "customer_service_hotline": [
            { "genre": "sales", "country": "US", "prefix": "+1", "phone": "123-456-7890" }
          ],
          "customer_service_email": [
            { "genre": "support", "email": "support@example.com" }
          ]
        }
      }
    }
  }'
```

#### 成功响应（业务 payload）

```json
{
  "success": true,
  "message": "保存成功",
  "data": {
    "save": [],
    "detail": []
  }
}
```

---

## 常见错误

### 1) 缺少站点 ID

当未提供 `X-Site-Id` 时，工具会返回：

```json
{
  "success": false,
  "error": "站点 ID 不能为空（请通过请求头 X-Site-Id 传入）"
}
```

### 2) 参数校验失败

会返回：

```json
{
  "success": false,
  "error": "第一条错误信息",
  "errors": { }
}
```


