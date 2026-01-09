"""UI 辅助函数模块。

提供 UI 消息推送等功能。
"""

import uuid
from typing import Any

from langgraph.graph.ui import AnyUIMessage, push_ui_message

from agent.state import ShortcutState


def push_shortcut_ui(
    state: ShortcutState,
    props: dict[str, Any],
    merge: bool = False,
) -> AnyUIMessage:
    """推送 Shortcut UI 消息。

    Args:
        state: 当前状态
        props: UI 属性
        merge: 是否合并到现有 UI

    Returns:
        AnyUIMessage: UI 消息对象
    """
    ui_id = state.get("ui_id") or str(uuid.uuid4())
    anchor_id = state.get("ui_anchor_id")

    return push_ui_message(
        name="mcp_workflow",
        props=props,
        id=ui_id,
        message_id=anchor_id,
        merge=merge,
    )
