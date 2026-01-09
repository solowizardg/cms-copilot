"""Shortcut 节点模块。

MCP 快捷操作相关节点 — 使用 langchain-mcp-adapters 连接 MCP Server。
"""

import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.graph.ui import AnyUIMessage, push_ui_message
from langgraph.types import interrupt

from agent.state import ShortcutState
from agent.tools.mcp import call_mcp_tool, get_mcp_tools
from agent.utils.helpers import message_text
from agent.utils.hitl import hitl_confirm
from agent.utils.llm import llm_nostream

# ============================================================
# LLM Tool Calling 核心逻辑
# ============================================================

TOOL_CALLING_SYSTEM_PROMPT = """你是一个智能助手，负责帮用户操作网站后台的基础设置。

请根据用户的自然语言请求：
1. 选择最合适的工具
2. 从用户输入中提取相关参数
3. 如果用户没有提供某个字段，就不要填该字段（留空/不传）

注意：
- 如果用户想"查看/获取/读取"信息，选择获取类工具
- 如果用户想"保存/更新/修改"信息，选择保存类工具
- 尽可能从用户输入中提取具体的字段值"""


async def _llm_tool_calling_with_mcp(
    user_text: str,
    tenant_id: str | None,
    site_id: str | None,
) -> tuple[str | None, dict[str, Any], list[Any], float, str | None]:
    """使用 LLM tool calling（基于 MCP 工具）决定调用哪个工具及参数。

    Returns:
        (tool_name, arguments, mcp_tools, confidence, llm_response)
        - llm_response: 当 LLM 没有选择工具时，返回 LLM 的文本回复
    """
    # 获取 MCP 工具（LangChain Tool 格式）
    mcp_tools = await get_mcp_tools(tenant_id=tenant_id, site_id=site_id)

    if not mcp_tools:
        return None, {}, [], 0.0, None

    print(f"[shortcut] Got {len(mcp_tools)} tools from MCP Server")
    for tool in mcp_tools:
        desc = tool.description[:50] if tool.description else ""
        print(f"  - {tool.name}: {desc}...")

    # 绑定工具到 LLM
    llm_with_tools = llm_nostream.bind_tools(mcp_tools)

    messages = [
        SystemMessage(content=TOOL_CALLING_SYSTEM_PROMPT),
        HumanMessage(content=user_text),
    ]

    try:
        response = await llm_with_tools.ainvoke(messages)
        tool_calls = getattr(response, "tool_calls", []) or []

        if not tool_calls:
            # LLM 没有选择工具，返回 LLM 的文本回复
            llm_content = getattr(response, "content", "") or ""
            print(
                f"[shortcut] LLM did not select any tool, response: {llm_content[:100]}..."
            )
            return None, {}, mcp_tools, 0.0, llm_content

        # 取第一个 tool call
        first_call = tool_calls[0]
        tool_name = first_call.get("name", "")
        tool_args = first_call.get("args", {})

        print(f"[shortcut] LLM selected tool: {tool_name} with args: {tool_args}")

        return tool_name, tool_args, mcp_tools, 1.0, None

    except Exception as e:
        print(f"[shortcut] LLM tool calling error: {e}")
        return None, {}, mcp_tools, 0.0, None


# ============================================================
# UI 辅助函数
# ============================================================


def _shortcut_push_ui(
    state: ShortcutState,
    props: dict[str, Any],
    merge: bool = False,
) -> AnyUIMessage:
    """推送/更新 shortcut 的 UI 卡片。"""
    writer = get_stream_writer()
    anchor_id = state.get("ui_anchor_id")
    ui_id = state.get("ui_id") if merge else None

    anchor_msg = None
    if anchor_id:
        for m in state.get("messages", []):
            if isinstance(m, AIMessage) and getattr(m, "id", None) == anchor_id:
                anchor_msg = m
                break
    if anchor_msg is None:
        anchor_msg = AIMessage(id=str(uuid.uuid4()), content="")

    ui_msg = push_ui_message(
        "mcp_workflow",
        props,
        id=ui_id,
        message=anchor_msg,
        merge=merge,
    )
    if writer is not None:
        writer(ui_msg)
    return ui_msg


def _parse_shortcut_selection(
    text: str, options: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """解析用户对 MCP/后台操作的选择。"""
    t = (text or "").strip().lower()
    if not t:
        return None
    if t.isdigit():
        idx = int(t) - 1
        if 0 <= idx < len(options):
            return options[idx]
    for opt in options:
        name = str(opt.get("name") or "").lower()
        if t == name:
            return opt
    return None


def _mcp_tools_to_options(mcp_tools: list[Any]) -> list[dict[str, Any]]:
    """将 MCP tools（LangChain Tool）转换为 UI options 格式。"""
    options = []
    for tool in mcp_tools:
        options.append(
            {
                "code": tool.name,
                "name": tool.name,
                "desc": tool.description or "",
            }
        )
    return options


# ============================================================
# Shortcut 子图节点
# ============================================================


async def shortcut_init(state: ShortcutState) -> dict[str, Any]:
    """初始化：获取 MCP 工具列表、LLM Tool Calling 分析、推送初始 UI。"""
    writer = get_stream_writer()

    user_text = state.get("user_text") or ""
    if not user_text:
        for m in reversed(state.get("messages", [])):
            if not isinstance(m, AIMessage):
                user_text = message_text(m)
                break

    tenant_id = state.get("tenant_id")
    site_id = state.get("site_id")

    # 创建 AIMessage 锚点
    anchor = AIMessage(id=str(uuid.uuid4()), content="")

    if writer is not None:
        writer({"messages": [anchor]})

    # 创建初始 UI 卡片
    ui_msg = push_ui_message(
        "mcp_workflow",
        {
            "status": "loading",
            "title": "正在连接 MCP Server...",
            "message": "获取可用工具列表",
        },
        message=anchor,
    )
    if writer is not None:
        writer(ui_msg)

    # ============ LLM Tool Calling（使用 MCP 工具） ============
    try:
        (
            tool_name,
            tool_args,
            mcp_tools,
            confidence,
            llm_response,
        ) = await _llm_tool_calling_with_mcp(user_text, tenant_id, site_id)
    except Exception as e:
        print(f"[shortcut] Failed to connect MCP Server: {e}")
        ui_msg_error = push_ui_message(
            "mcp_workflow",
            {
                "status": "error",
                "title": "无法连接 MCP Server",
                "message": str(e),
            },
            id=ui_msg["id"],
            message=anchor,
            merge=True,
        )
        if writer is not None:
            writer(ui_msg_error)
        return {
            "messages": [anchor],
            "ui": [ui_msg_error],
            "user_text": user_text,
            "options": [],
            "error": str(e),
            "ui_anchor_id": anchor.id,
            "ui_id": ui_msg["id"],
        }

    if not mcp_tools:
        ui_msg_error = push_ui_message(
            "mcp_workflow",
            {
                "status": "error",
                "title": "无可用工具",
                "message": "MCP Server 未返回任何工具",
            },
            id=ui_msg["id"],
            message=anchor,
            merge=True,
        )
        if writer is not None:
            writer(ui_msg_error)
        return {
            "messages": [anchor],
            "ui": [ui_msg_error],
            "user_text": user_text,
            "options": [],
            "error": "MCP Server 未返回任何工具",
            "ui_anchor_id": anchor.id,
            "ui_id": ui_msg["id"],
        }

    # 转换为 UI options
    options = _mcp_tools_to_options(mcp_tools)

    # 根据 tool_name 找到对应的 option
    auto_selected: dict[str, Any] | None = None
    if tool_name and confidence >= 0.7:
        for opt in options:
            if opt["code"] == tool_name:
                auto_selected = opt
                break

    # ============ LLM 没有选择工具，直接输出回复并结束 ============
    if not tool_name and llm_response:
        ui_msg_done = push_ui_message(
            "mcp_workflow",
            {
                "status": "done",
                "title": "处理完成",
                "message": llm_response,
            },
            id=ui_msg["id"],
            message=anchor,
            merge=True,
        )
        if writer is not None:
            writer(ui_msg_done)

        response_msg = AIMessage(content=llm_response)
        return {
            "messages": [anchor, response_msg],
            "ui": [ui_msg_done],
            "user_text": user_text,
            "options": options,
            "selected": None,
            "no_tool_selected": True,  # 标记：LLM 没有选择工具
            "result": llm_response,
            "ui_anchor_id": anchor.id,
            "ui_id": ui_msg["id"],
        }

    # 如果 LLM 没有选出工具，fallback 到全部选项让用户选
    final_options = [auto_selected] if auto_selected else options
    recommended = tool_name if auto_selected else None

    # 更新 UI
    if auto_selected:
        ui_msg_updated = push_ui_message(
            "mcp_workflow",
            {
                "status": "ready",
                "title": "后台操作",
                "options": [auto_selected],
                "recommended": recommended,
                "message": f"AI 已自动选择：{auto_selected.get('name')}",
                "tool_args": tool_args,
            },
            id=ui_msg["id"],
            message=anchor,
            merge=True,
        )
    else:
        ui_msg_updated = push_ui_message(
            "mcp_workflow",
            {
                "status": "ready",
                "title": "后台操作",
                "options": options,
                "recommended": recommended,
                "message": f"请选择要执行的操作（共 {len(options)} 个）",
            },
            id=ui_msg["id"],
            message=anchor,
            merge=True,
        )

    if writer is not None:
        writer(ui_msg_updated)

    return {
        "messages": [anchor],
        "ui": [ui_msg_updated],
        "user_text": user_text,
        "options": final_options,
        "recommended": recommended,
        "selected": auto_selected,
        "mcp_params": tool_args,
        "ui_anchor_id": anchor.id,
        "ui_id": ui_msg["id"],
    }


async def shortcut_select(state: ShortcutState) -> dict[str, Any]:
    """等待用户选择操作（使用 interrupt）— 只有 LLM 无法确定时才进入。"""
    options = state.get("options") or []
    recommended = state.get("recommended")

    ui_msg = _shortcut_push_ui(
        state,
        {
            "status": "select",
            "title": "请选择要执行的后台操作",
            "options": options,
            "recommended": recommended,
            "message": "AI 无法确定您的意图，请选择操作（输入序号或名称）",
        },
        merge=True,
    )

    user_choice = interrupt(
        {
            "type": "mcp_select",
            "options": options,
            "message": "请输入序号选择操作",
        }
    )

    choice_text = str(user_choice) if user_choice else ""
    selected = _parse_shortcut_selection(choice_text, options)

    if not selected:
        return {"error": f"无效选择: {choice_text}", "selected": None}

    # 用户手动选择后，需要重新提取参数
    user_text = state.get("user_text") or ""
    tenant_id = state.get("tenant_id")
    site_id = state.get("site_id")

    try:
        _, tool_args, _, _, _ = await _llm_tool_calling_with_mcp(
            user_text, tenant_id, site_id
        )
    except Exception:
        tool_args = {}

    return {"selected": selected, "mcp_params": tool_args, "ui": [ui_msg]}


async def shortcut_confirm(state: ShortcutState) -> dict[str, Any]:
    """等待用户确认（使用 HITLRequest 格式）。"""
    selected = state.get("selected")
    options = state.get("options") or []
    mcp_params = state.get("mcp_params") or {}

    if not selected and len(options) == 1:
        selected = options[0]

    if not selected:
        return {"error": "未选择操作", "confirmed": False}

    is_confirmed = hitl_confirm(
        action_name=selected.get("code", "execute"),
        args={
            "name": selected.get("name"),
            "params": mcp_params,
        },
        description=f"即将执行「{selected.get('name')}」操作，请确认或取消。",
    )

    return {"confirmed": is_confirmed, "selected": selected}


async def shortcut_execute(state: ShortcutState) -> dict[str, Any]:
    """执行 MCP 操作。"""
    selected = state.get("selected") or {}
    tool_name = selected.get("code")
    tenant_id = state.get("tenant_id")
    site_id = state.get("site_id")
    mcp_params = state.get("mcp_params") or {}

    _shortcut_push_ui(
        state,
        {
            "status": "running",
            "title": f"正在执行：{selected.get('name') or tool_name}",
            "selected": selected,
            "message": "正在调用 MCP 服务…",
            "params": mcp_params,
        },
        merge=True,
    )

    # 调用 MCP 工具
    try:
        result = await call_mcp_tool(
            tool_name=tool_name,
            tool_input=mcp_params,
            tenant_id=tenant_id,
            site_id=site_id,
        )

        # 解析结果
        if isinstance(result, dict):
            if result.get("success"):
                result_text = result.get("message", "操作成功")
                data = result.get("data")
                ui_msg = _shortcut_push_ui(
                    state,
                    {
                        "status": "done",
                        "title": "执行完成",
                        "selected": selected,
                        "result": result_text,
                        "data": data,
                    },
                    merge=True,
                )
                result_msg = AIMessage(content=result_text)
                return {"result": result_text, "ui": [ui_msg], "messages": [result_msg]}
            else:
                error_msg = result.get("error", "未知错误")
                ui_msg = _shortcut_push_ui(
                    state,
                    {
                        "status": "error",
                        "title": "执行失败",
                        "selected": selected,
                        "message": error_msg,
                    },
                    merge=True,
                )
                return {"error": error_msg, "ui": [ui_msg]}
        else:
            # 非 dict 结果，视为成功
            result_text = str(result) if result else "操作成功"
            ui_msg = _shortcut_push_ui(
                state,
                {
                    "status": "done",
                    "title": "执行完成",
                    "selected": selected,
                    "result": result_text,
                },
                merge=True,
            )
            result_msg = AIMessage(content=result_text)
            return {"ui": [ui_msg]}

    except Exception as exc:
        ui_msg = _shortcut_push_ui(
            state,
            {
                "status": "error",
                "title": "执行失败",
                "selected": selected,
                "message": str(exc),
            },
            merge=True,
        )
        return {"error": str(exc), "ui": [ui_msg]}


async def shortcut_cancelled(state: ShortcutState) -> dict[str, Any]:
    """用户取消操作。"""
    ui_msg = _shortcut_push_ui(
        state,
        {
            "status": "cancelled",
            "title": "已取消",
            "message": "后台操作已取消。",
        },
        merge=True,
    )
    return {"ui": [ui_msg]}
