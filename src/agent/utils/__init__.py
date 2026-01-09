"""工具函数模块。"""

from agent.utils.helpers import (
    find_ai_message_by_id,
    is_cancel,
    is_confirm,
    latest_ai_message,
    latest_user_message,
    message_text,
    parse_shortcut_selection,
)
from agent.utils.ui import push_shortcut_ui

# 可选依赖：HITL / LLM 在不同环境下可能不可用；避免 import 时直接炸
try:  # pragma: no cover
    from agent.utils.hitl import hitl_confirm  # type: ignore
except Exception:  # pragma: no cover
    hitl_confirm = None  # type: ignore[assignment]

try:  # pragma: no cover
    from agent.utils.llm import llm, llm_nano  # type: ignore
except Exception:  # pragma: no cover
    llm = None  # type: ignore[assignment]
    llm_nano = None  # type: ignore[assignment]

__all__ = [
    "llm",
    "llm_nano",
    "hitl_confirm",
    "push_shortcut_ui",
    "message_text",
    "latest_user_message",
    "latest_ai_message",
    "find_ai_message_by_id",
    "parse_shortcut_selection",
    "is_confirm",
    "is_cancel",
]
