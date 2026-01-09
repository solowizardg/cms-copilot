# CMS Copilot Shortcut 流程重构规划

## 1. 当前问题分析

### 1.1 现有实现的缺陷

当前 `handle_shortcut` 函数存在以下问题：

1. **单一大函数**：所有状态转换逻辑都堆积在一个 200+ 行的函数中，难以维护
2. **纯 state 驱动**：使用 `shortcut_ctx.phase` 手动管理状态机，需要额外的 entry 节点判断
3. **未使用 interrupt**：之前尝试使用 interrupt 遇到前端渲染问题（`shadowRoot` null）
4. **重复进入主图**：每次用户输入都要重新从 START → entry → 判断 phase → shortcut，效率低

### 1.2 前端报错原因分析

`Cannot read properties of null (reading 'shadowRoot')` 错误的根本原因：
- interrupt 暂停执行后，UI 消息的 `message_id` 对应的 AIMessage 还未被前端正确渲染
- LangGraph Studio 的 Generative UI 渲染机制与 interrupt 的配合需要特殊处理

## 2. 改进方案：Subgraph + Interrupt

### 2.1 核心思路

将 shortcut 流程封装为**独立子图（Subgraph）**，使用 **interrupt** 实现人机交互：

```
┌─────────────────────────────────────────────────────────────────┐
│                        Main Graph                               │
│                                                                 │
│  START → router_ui → router ─┬→ rag → END                      │
│                              ├→ article_ui → article → END     │
│                              └→ shortcut_subgraph ────────────→│
│                                       ↓                         │
│                         ┌─────────────────────────┐             │
│                         │   Shortcut Subgraph     │             │
│                         │                         │             │
│                         │  init → select ──────┐  │             │
│                         │           ↓          │  │             │
│                         │      [interrupt]     │  │             │
│                         │           ↓          │  │             │
│                         │      confirm ──────┐ │  │             │
│                         │           ↓        │ │  │             │
│                         │      [interrupt]   │ │  │             │
│                         │           ↓        │ │  │             │
│                         │      execute → END │ │  │             │
│                         │           ↓        │ │  │             │
│                         │      cancelled ←───┘ │  │             │
│                         └─────────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

> **为什么不需要 entry 节点？**
> 
> 当前方案中，entry 节点的唯一作用是检测 `shortcut_ctx.phase`，决定是否跳过意图识别。
> 
> 使用 interrupt 后，resume 会**直接从子图的暂停点继续执行**，而不是重新从 START 进入主图。
> 因此 entry 节点完全可以移除，简化主图结构。

### 2.2 子图节点设计

#### ShortcutState（子图状态）

```python
class ShortcutState(TypedDict):
    # 继承自父图
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]
    
    # 子图专属
    user_text: str                          # 用户输入
    options: list[dict[str, Any]]           # 可选操作列表
    recommended: Optional[str]              # LLM 推荐的操作 code
    selected: Optional[dict[str, Any]]      # 用户选择的操作
    company_name: Optional[str]             # 提取的公司名称
    logo_url: Optional[str]                 # 提取的 Logo URL
    result: Optional[str]                   # 执行结果
    error: Optional[str]                    # 错误信息
    ui_anchor_id: Optional[str]             # UI 锚点 message id
    ui_id: Optional[str]                    # UI 卡片 id
```

#### 节点划分

| 节点名 | 职责 | 是否 interrupt |
|--------|------|----------------|
| `shortcut_init` | 1. 创建 AIMessage 锚点<br>2. LLM 分析用户意图选择 options<br>3. 提取参数（company_name/logo_url）<br>4. 推送初始 UI 卡片 | ❌ |
| `shortcut_select` | 1. 如果只有 1 个选项，自动选择并跳过<br>2. 否则 interrupt 等待用户选择序号 | ✅ `interrupt(options)` |
| `shortcut_confirm` | 1. 更新 UI 显示确认信息<br>2. interrupt 等待用户确认/取消 | ✅ `interrupt(selected)` |
| `shortcut_execute` | 1. 执行 MCP 操作（mock）<br>2. 更新 UI 为完成状态<br>3. 返回结果 | ❌ |
| `shortcut_cancelled` | 1. 更新 UI 为取消状态 | ❌ |

### 2.3 边与条件路由

```python
def build_shortcut_subgraph():
    builder = StateGraph(ShortcutState)
    
    builder.add_node("init", shortcut_init)
    builder.add_node("select", shortcut_select)
    builder.add_node("confirm", shortcut_confirm)
    builder.add_node("execute", shortcut_execute)
    builder.add_node("cancelled", shortcut_cancelled)
    
    builder.add_edge(START, "init")
    
    # init 后根据 options 数量决定是否跳过选择
    builder.add_conditional_edges(
        "init",
        lambda s: "select" if len(s.get("options", [])) > 1 else "confirm",
        {"select": "select", "confirm": "confirm"}
    )
    
    # select 后进入 confirm
    builder.add_edge("select", "confirm")
    
    # confirm 后根据用户输入决定执行或取消
    builder.add_conditional_edges(
        "confirm",
        lambda s: "execute" if s.get("_confirmed") else "cancelled",
        {"execute": "execute", "cancelled": "cancelled"}
    )
    
    builder.add_edge("execute", END)
    builder.add_edge("cancelled", END)
    
    return builder.compile()
```

### 2.4 interrupt 使用方式

#### 选择阶段

```python
async def shortcut_select(state: ShortcutState):
    """等待用户选择操作（使用 interrupt）"""
    options = state["options"]
    
    # 更新 UI 显示选择列表
    _push_ui(state, status="select", message="请选择要执行的操作")
    
    # interrupt 暂停，等待用户输入
    user_choice = interrupt({
        "type": "mcp_select",
        "options": options,
        "message": "请输入序号（如 1）选择操作",
    })
    
    # 解析用户选择
    selected = _parse_selection(user_choice, options)
    if not selected:
        # 选择无效，可以再次 interrupt 或返回错误
        return {"error": "无效选择"}
    
    return {"selected": selected}
```

#### 确认阶段

```python
async def shortcut_confirm(state: ShortcutState):
    """等待用户确认（使用 interrupt）"""
    selected = state["selected"]
    
    # 更新 UI 显示确认信息
    _push_ui(state, status="confirm", message=f"确认执行「{selected['name']}」？")
    
    # interrupt 暂停，等待用户确认
    decision = interrupt({
        "type": "mcp_confirm",
        "selected": selected,
        "message": "请回复「确认」执行，或「取消」放弃",
    })
    
    # 解析用户决定
    is_confirmed = _is_confirm_text(decision)
    return {"_confirmed": is_confirmed}
```

### 2.5 前端适配

#### 解决 shadowRoot null 问题

关键点：**确保 AIMessage 锚点在 interrupt 之前已写入 state 并被前端渲染**

```python
async def shortcut_init(state: ShortcutState):
    """初始化：创建锚点并推送 UI（在任何 interrupt 之前）"""
    writer = get_stream_writer()
    
    # 1. 创建 AIMessage 锚点
    anchor = AIMessage(id=str(uuid.uuid4()), content="")
    
    # 2. 立即通过 writer 推送，让前端渲染
    if writer:
        writer({"messages": [anchor]})
    
    # 3. 创建初始 UI 卡片
    ui_msg = push_ui_message(
        "mcp_workflow",
        {"status": "loading", "title": "正在分析..."},
        message=anchor,
    )
    if writer:
        writer(ui_msg)
    
    # 4. 执行 LLM 分析等操作...
    options, recommended = await _select_mcp_actions_with_llm(state["user_text"])
    
    # 5. 更新 UI
    ui_msg_updated = push_ui_message(
        "mcp_workflow",
        {"status": "ready", "options": options},
        id=ui_msg["id"],
        message=anchor,
        merge=True,
    )
    
    return {
        "messages": [anchor],
        "ui": [ui_msg_updated],
        "options": options,
        "recommended": recommended,
        "ui_anchor_id": anchor.id,
        "ui_id": ui_msg["id"],
    }
```

#### 前端 resume 交互

前端按钮点击后，通过 LangGraph SDK 恢复执行：

```typescript
// 前端代码（MCPWorkflowCard 组件）
const handleConfirm = async () => {
  // 使用 LangGraph SDK 恢复执行
  await client.runs.wait(threadId, assistantId, {
    input: new Command({ resume: "确认" }),
  });
};

const handleCancel = async () => {
  await client.runs.wait(threadId, assistantId, {
    input: new Command({ resume: "取消" }),
  });
};
```

或者使用 LangGraph Studio 注入的全局函数：

```typescript
const handleConfirm = () => {
  window.__LANGGRAPH_RESUME__?.("确认");
};
```

## 3. 主图集成

### 3.1 子图作为节点

```python
def build_graph():
    builder = StateGraph(CopilotState)
    
    # ... 其他节点 ...
    
    # 将子图作为节点添加
    shortcut_subgraph = build_shortcut_subgraph()
    builder.add_node("shortcut", shortcut_subgraph)
    
    # ... 其他边 ...
    
    return builder.compile(checkpointer=MemorySaver())  # 必须配置 checkpointer！
```

### 3.2 Checkpointer 配置

**interrupt 必须配合 checkpointer 使用**，否则无法暂停和恢复：

```python
from langgraph.checkpoint.memory import MemorySaver

# 开发/测试环境
checkpointer = MemorySaver()

# 生产环境（推荐）
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)

graph = build_graph().compile(checkpointer=checkpointer)
```

### 3.3 移除 entry 节点

使用子图 + interrupt 后，**完全移除 entry 节点**：

```python
def build_graph():
    builder = StateGraph(CopilotState)
    
    # 直接从 START 进入 router_ui，无需 entry
    builder.add_edge(START, "router_ui")
    builder.add_edge("router_ui", "router")
    
    # router 根据 intent 分流
    builder.add_conditional_edges("router", _route, {...})
    
    # 移除 shortcut_ctx 状态字段（子图内部管理）
```

**为什么可以移除？**
- interrupt 暂停后，resume 直接从子图内部继续
- 不会重新从 START 进入主图
- 无需在主图检测"是否处于 shortcut 中间状态"

## 4. 实施步骤

### Phase 1：基础重构（不使用 interrupt）

1. 创建 `ShortcutState` 类型定义
2. 拆分 `handle_shortcut` 为多个节点函数
3. 构建子图 `build_shortcut_subgraph()`
4. 在主图中集成子图
5. 测试基本流程

### Phase 2：引入 interrupt

1. 配置 checkpointer（MemorySaver 用于开发）
2. 在 `shortcut_select` 节点添加 interrupt
3. 在 `shortcut_confirm` 节点添加 interrupt
4. 测试 interrupt 暂停和恢复

### Phase 3：前端适配

1. 更新 `MCPWorkflowCard` 组件
2. 实现按钮点击调用 `Command(resume=...)` 恢复执行
3. 处理 `__interrupt__` 响应
4. 测试端到端流程

### Phase 4：优化与完善

1. 添加超时处理
2. 添加错误恢复机制
3. 优化 UI 状态展示
4. 编写单元测试和集成测试

## 5. 风险与注意事项

### 5.1 interrupt 使用注意

1. **不要在节点中重新排序 interrupt 调用**：LangGraph 按索引匹配 resume 值
2. **不要条件性跳过 interrupt**：会导致索引错位
3. **确保 checkpointer 配置正确**：否则 interrupt 不会生效

### 5.2 子图与 UI 渲染

1. 子图中的 UI 消息需要正确传递 `message_id`
2. 子图的 state 更新会合并到父图
3. 子图节点重新执行时，interrupt 之前的代码会再次运行

### 5.3 兼容性考虑

1. LangGraph Studio 的 `__LANGGRAPH_RESUME__` 函数可能不存在
2. 需要提供降级方案（文字输入确认/取消）
3. 不同前端宿主可能有不同的 resume 机制

## 6. 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/agent/graph.py` | 重构 | 拆分 shortcut 为子图 |
| `src/agent/shortcut.py` | 新增 | 子图定义和节点实现 |
| `src/agent/ui.tsx` | 修改 | 适配 resume 机制 |
| `langgraph.json` | 修改 | 配置 checkpointer |
| `tests/unit_tests/test_shortcut.py` | 新增 | 子图单元测试 |

## 7. 预期效果

1. **代码可读性提升**：每个节点职责单一，易于理解和维护
2. **图结构清晰**：子图封装 shortcut 流程，主图简洁
3. **用户体验提升**：interrupt 实现真正的"暂停等待"，按钮交互更自然
4. **可扩展性增强**：添加新的 MCP 操作只需修改子图
