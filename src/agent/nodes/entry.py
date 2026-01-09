"""Entry 节点模块。

入口节点：检查是否需要恢复 shortcut 流程。
"""

from typing import Any

from agent.state import CopilotState


async def entry_node(state: CopilotState) -> dict[str, Any]:
    """入口节点：检查是否是恢复消息或直接指定意图。

    返回 resume_target 标记，后续条件边根据此值决定跳转。
    """
    options = state.get("options")
    confirmed = state.get("confirmed")
    direct_intent = state.get("direct_intent")
    resume_target = state.get("resume_target")
    article_clarify_pending = state.get("article_clarify_pending")

    # 主图可达的下游节点白名单（主要用于“恢复/续跑”时校验）
    allowed_targets = {
        "router_ui",
        "rag",
        "article_clarify",  # 子图（参数澄清）
        "article_ui",  # 主图（工作流UI）
        "article_run",  # 主图（执行逻辑）
        "seo_ui",
        "report_ui",
        "shortcut",
    }

    # 统一口径：前端/调用方仅传“意图标签”（而不是节点名）
    allowed_intents = {"rag", "shortcut", "article_task", "seo_planning", "site_report"}

    # 如果 options 存在且 confirmed 还是 None，说明在等待确认
    if options is not None and confirmed is None:
        print("[DEBUG] entry_node: resuming shortcut flow")
        return {"resume_target": "shortcut"}

    # 如果处在“文章参数澄清”流程中：跳回 article_clarify 子图继续
    if article_clarify_pending:
        print("[DEBUG] entry_node: resuming article clarify flow")
        return {"resume_target": "article_clarify"}

    # 如果 state 已经有 resume_target（通常来自 checkpointer 的恢复/续跑），仅在可恢复节点时尊重
    if (
        isinstance(resume_target, str)
        and resume_target in allowed_targets
        and resume_target in {"shortcut", "article_clarify", "article_ui", "article_run"}
    ):
        print(f"[DEBUG] entry_node: resume_target preset -> {resume_target}")
        return {"resume_target": resume_target}

    # 检查是否直接指定了意图（跳过意图识别）
    if isinstance(direct_intent, str) and direct_intent:
        if direct_intent not in allowed_intents:
            print(
                f"[DEBUG] entry_node: invalid direct_intent '{direct_intent}', fallback to router_ui"
            )
            return {"resume_target": "router_ui"}

        # 意图标签 -> 下游节点（统一规则，仅这一处）
        intent_to_target = {
            "seo_planning": "seo_ui",
            "article_task": "article_clarify",  # 文章任务先去澄清参数
            "shortcut": "shortcut",
            "site_report": "report_ui",
            "rag": "rag",
        }
        target = intent_to_target.get(direct_intent, "router_ui")
        print(f"[DEBUG] entry_node: direct intent '{direct_intent}' -> {target}")
        # 注意：这里仍写入 intent，方便后续可观测/埋点；但流程会直接走 target，跳过 router
        return {"resume_target": target, "intent": direct_intent}

    print("[DEBUG] entry_node: starting intent recognition")
    return {"resume_target": "router_ui"}
