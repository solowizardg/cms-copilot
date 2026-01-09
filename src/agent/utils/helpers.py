"""通用辅助函数模块。"""

from typing import Any

from langchain_core.messages import AIMessage, BaseMessage

from agent.state import CopilotState


def message_text(msg: Any) -> str:
    """尽量从 message 的 content 中提取纯文本。

    兼容：
    - LangChain BaseMessage
    - LangGraph/SDK 可能传入的 dict 消息（如 {"type":"human","content":"..."}）
    """
    if isinstance(msg, dict):
        raw_content = msg.get("content", "")
    else:
        raw_content = getattr(msg, "content", msg)
    if isinstance(raw_content, list):
        text_parts: list[str] = []
        for part in raw_content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
            else:
                text_parts.append(str(part))
        return "".join(text_parts)
    if isinstance(raw_content, str):
        return raw_content
    return str(raw_content)


def latest_user_message(state: CopilotState) -> BaseMessage:
    """拿到最近一条"非 AIMessage"的消息，作为用户输入。"""
    for m in reversed(state["messages"]):
        if not isinstance(m, AIMessage):
            return m
    return state["messages"][-1]


def latest_ai_message(state: CopilotState) -> AIMessage | None:
    """拿到最近一条 AIMessage。"""
    for m in reversed(state["messages"]):
        if isinstance(m, AIMessage):
            return m
    return None


def find_ai_message_by_id(
    state: CopilotState, message_id: str | None
) -> AIMessage | None:
    """根据 ID 查找 AIMessage。"""
    if not message_id:
        return None
    for m in state["messages"]:
        if isinstance(m, AIMessage) and getattr(m, "id", None) == message_id:
            return m
    return None


def parse_shortcut_selection(
    text: str, options: list[dict[str, Any]]
) -> dict[str, Any] | None:
    """解析用户对 MCP/后台操作的选择：支持输入序号(1/2/3) 或 code。"""
    t = (text or "").strip().lower()
    if not t:
        return None
    # 序号选择
    if t.isdigit():
        idx = int(t) - 1
        if 0 <= idx < len(options):
            return options[idx]
    # code / name 模糊匹配
    for opt in options:
        code = str(opt.get("code") or "").lower()
        name = str(opt.get("name") or "").lower()
        if t == code or t == name:
            return opt
    return None


def is_confirm(text: str) -> bool:
    """判断是否为确认指令。"""
    t = (text or "").strip().lower()
    return t in {"确认", "确定", "yes", "y", "ok", "好的", "执行", "开始", "confirm"}


def is_cancel(text: str) -> bool:
    """判断是否为取消指令。"""
    t = (text or "").strip().lower()
    return t in {"取消", "算了", "不做了", "no", "n", "cancel", "停止", "退出"}
