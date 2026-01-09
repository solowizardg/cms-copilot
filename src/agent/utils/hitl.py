"""Human-in-the-loop 辅助函数模块。

提供 HITL 确认请求等功能。
"""

from typing import Any

try:
    # 这部分依赖 langchain 的 HITL middleware（不同版本兼容性差）
    from langchain.agents.middleware.human_in_the_loop import (  # type: ignore
        ActionRequest,
        DecisionType,
        HITLRequest,
        ReviewConfig,
    )
except Exception:  # pragma: no cover
    ActionRequest = None  # type: ignore[assignment]
    ReviewConfig = None  # type: ignore[assignment]
    HITLRequest = dict  # type: ignore[assignment]
    DecisionType = str  # type: ignore[assignment]

from langgraph.types import interrupt


def hitl_confirm(
    action_name: str,
    args: dict[str, Any],
    description: str,
    allowed_decisions: list[DecisionType] | None = None,
) -> bool:
    """发起 HITL 确认请求，返回是否批准。

    Args:
        action_name: 操作名称
        args: 操作参数
        description: 操作描述
        allowed_decisions: 允许的决策类型，默认为 ["approve", "reject"]

    Returns:
        bool: 用户是否批准
    """
    if ActionRequest is None or ReviewConfig is None:
        raise ImportError(
            "HITL 依赖未安装或版本不兼容：无法导入 "
            "`langchain.agents.middleware.human_in_the_loop`。"
        )

    if allowed_decisions is None:
        allowed_decisions = ["approve", "reject"]

    request: HITLRequest = {
        "action_requests": [
            ActionRequest(name=action_name, args=args, description=description)
        ],
        "review_configs": [
            ReviewConfig(
                action_name=action_name, allowed_decisions=list(allowed_decisions)
            )
        ],
    }

    response = interrupt(request)

    # 解析响应
    if isinstance(response, dict):
        decisions = response.get("decisions", [])
        if decisions and isinstance(decisions, list):
            return decisions[0].get("type") == "approve"
        # 兼容简单格式
        return response.get("type") in ["accept", "approve", "confirm"]

    # 文本格式兼容
    text = str(response).strip().lower() if response else ""
    return any(
        k in text
        for k in [
            "确认",
            "确定",
            "执行",
            "ok",
            "yes",
            "好",
            "同意",
            "accept",
            "approve",
        ]
    )
