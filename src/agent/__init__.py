"""CMS Copilot Agent 模块。

提供主图和相关组件的导出。
"""

from __future__ import annotations

from typing import Any

from agent.state import CopilotState, ShortcutState

__all__ = [
    "graph",
    "build_graph",
    "CopilotState",
    "ShortcutState",
]


def __getattr__(name: str) -> Any:
    """懒加载导出，避免循环导入。

    常见场景：`import agent.nodes.article` 会先执行 `agent/__init__.py`。
    如果这里立即 import `agent.graph`，而 `agent.graph` 又 import `agent.nodes.*`，
    会形成循环导入链条。改为按需导入可规避该问题。
    """

    if name in {"graph", "build_graph"}:
        from agent.graph import build_graph, graph  # 本文件加载方式下用绝对导入更稳

        return graph if name == "graph" else build_graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
