"""Shortcut 子图模块。

构建 MCP 快捷操作子图。
"""

from langgraph.graph import END, START, StateGraph

from agent.nodes.shortcut import (
    shortcut_cancelled,
    shortcut_confirm,
    shortcut_execute,
    shortcut_init,
    shortcut_select,
)
from agent.state import ShortcutState


def build_shortcut_subgraph():
    """构建 Shortcut 子图，使用条件边声明所有可能的跳转路径。"""
    builder = StateGraph(ShortcutState)

    builder.add_node("init", shortcut_init)
    builder.add_node("select", shortcut_select)
    builder.add_node("confirm", shortcut_confirm)
    builder.add_node("execute", shortcut_execute)
    builder.add_node("cancelled", shortcut_cancelled)

    builder.add_edge(START, "init")

    # init 后的条件边
    def _after_init(state: ShortcutState):
        options = state.get("options") or []
        selected = state.get("selected")
        no_tool_selected = state.get("no_tool_selected")
        error = state.get("error")

        print(
            f"[DEBUG] _after_init: options={len(options)}, selected={selected is not None}, no_tool={no_tool_selected}, error={error}"
        )

        # 如果 LLM 没有选择工具（已输出回复），或者有错误，直接结束
        if no_tool_selected or error:
            return "end"

        # 如果 init 阶段已经自动消歧义并选中动作，则跳过 select 直接进入 confirm
        if selected is not None or len(options) == 1:
            return "confirm"
        return "select"

    builder.add_conditional_edges(
        "init",
        _after_init,
        {"select": "select", "confirm": "confirm", "end": END},
    )

    builder.add_edge("select", "confirm")

    # confirm 后的条件边
    def _after_confirm(state: ShortcutState):
        confirmed = state.get("confirmed")
        print(f"[DEBUG] _after_confirm: confirmed = {confirmed}")
        if confirmed:
            return "execute"
        return "cancelled"

    builder.add_conditional_edges(
        "confirm",
        _after_confirm,
        {"execute": "execute", "cancelled": "cancelled"},
    )

    builder.add_edge("execute", END)
    builder.add_edge("cancelled", END)

    # 子图不配置 checkpointer，父图会传递
    return builder.compile()
