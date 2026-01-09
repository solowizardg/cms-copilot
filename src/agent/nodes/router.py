"""路由节点模块。

意图识别和路由分发。
"""

import time
import uuid
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph.ui import push_ui_message

from agent.state import CopilotState
from agent.utils.helpers import latest_ai_message, latest_user_message, message_text
from agent.utils.llm import llm_nano_nostream


async def start_intent_ui(state: CopilotState) -> dict[str, Any]:
    """先把"正在识别意图"的卡片显示出来。"""
    user_msg = latest_user_message(state)
    user_text = message_text(user_msg)

    started_at = time.monotonic()

    # 关键：先写入锚点 AIMessage（生成 message_id），前端才能立刻挂载/渲染 UI
    ui_anchor_msg = AIMessage(id=str(uuid.uuid4()), content="")
    ui_msg_start = push_ui_message(
        "intent_router",
        {
            "status": "thinking",
            "user_text": user_text,
            "steps": [
                "解析用户输入",
                "调用意图分类模型（gpt-4.1-nano）",
                "映射到下游路由（rag / article / shortcut / report）",
            ],
            "active_step": 1,
        },
        message=ui_anchor_msg,
    )

    return {
        "messages": [ui_anchor_msg],
        "ui": [ui_msg_start],
        "intent_ui_id": ui_msg_start["id"],
        "intent_started_at": started_at,
    }


async def route_intent(state: CopilotState) -> dict[str, Any]:
    """使用 LLM 对最后一条用户消息做意图分类。"""
    user_msg = latest_user_message(state)
    user_text = message_text(user_msg)

    # UI 绑定到 start_intent_ui 写入的锚点 AIMessage
    ui_anchor_msg = latest_ai_message(state)
    intent_ui_id = state.get("intent_ui_id")
    started_at = state.get("intent_started_at")
    if ui_anchor_msg is None or not intent_ui_id:
        # 兜底：如果没有先经过 start_intent_ui，也能正常渲染
        ui_anchor_msg = ui_anchor_msg or AIMessage(id=str(uuid.uuid4()), content="")
        ui_msg_start = push_ui_message(
            "intent_router",
            {
                "status": "thinking",
                "user_text": user_text,
                "steps": [
                    "解析用户输入",
                    "调用意图分类模型（gpt-4.1-nano）",
                    "映射到下游路由（rag / article / shortcut / report）",
                ],
                "active_step": 1,
            },
            message=ui_anchor_msg,
        )
        intent_ui_id = ui_msg_start["id"]
        started_at = started_at or time.monotonic()

    prompt = (
        "你是一个 CMS Copilot 的意图分类器。\n"
        "请根据用户的中文输入，将其归类为以下五类之一：\n"
        "1. article_task: 用户在要求写文章、生成内容、新闻稿、营销文案等。\n"
        "2. shortcut: 用户在说某个后台操作快捷指令，例如修改公司名称、修改站点 Logo等。\n"
        "3. seo_planning: 用户在询问 SEO 规划、SEO 任务、SEO 周计划、网站优化建议等。\n"
        "4. site_report: 用户在询问站点报告、访问量统计、流量分析、数据报表、站点数据、用户统计等。\n"
        "5. rag: 用户在询问使用说明、配置方法、后台操作指引、如何做某件事等。\n"
        "只输出一个标签：article_task、shortcut、seo_planning、site_report 或 rag，不要输出其它任何文字。\n"
        f"用户输入：{user_text}\n"
        "输出："
    )

    intent_label = "rag"
    raw_model_output = ""

    try:
        resp = await llm_nano_nostream.ainvoke(prompt)
        raw_model_output = getattr(resp, "content", str(resp)).strip()
        label = raw_model_output.lower()

        if "article_task" in label or label == "article":
            intent_label = "article_task"
        elif "shortcut" in label:
            intent_label = "shortcut"
        elif "seo_planning" in label or "seo" in label:
            intent_label = "seo_planning"
        elif "site_report" in label or "report" in label:
            intent_label = "site_report"
        elif "rag" in label:
            intent_label = "rag"
        else:
            # LLM 输出异常时的兜底规则
            if "文章" in user_text or "写" in user_text:
                intent_label = "article_task"
            elif "草稿" in user_text or "新建" in user_text:
                intent_label = "shortcut"
            elif (
                "seo" in user_text.lower() or "优化" in user_text or "任务" in user_text
            ):
                intent_label = "seo_planning"
            elif (
                "报告" in user_text
                or "统计" in user_text
                or "访问量" in user_text
                or "流量" in user_text
                or "数据" in user_text
            ):
                intent_label = "site_report"
            else:
                intent_label = "rag"
    except Exception:
        # LLM 调用失败时回退到简单规则
        if "文章" in user_text or "写" in user_text:
            intent_label = "article_task"
        elif "草稿" in user_text or "新建" in user_text:
            intent_label = "shortcut"
        elif "seo" in user_text.lower() or "优化" in user_text or "任务" in user_text:
            intent_label = "seo_planning"
        elif (
            "报告" in user_text
            or "统计" in user_text
            or "访问量" in user_text
            or "流量" in user_text
            or "数据" in user_text
        ):
            intent_label = "site_report"
        else:
            intent_label = "rag"

    # 将 intent 标签映射到实际的下游路由节点
    if intent_label == "article_task":
        route_to = "article"
    elif intent_label == "shortcut":
        route_to = "shortcut"
    elif intent_label == "seo_planning":
        route_to = "seo"
    elif intent_label == "site_report":
        route_to = "report"
    else:
        route_to = "rag"

    elapsed_s: float | None = None
    if started_at is not None:
        elapsed_s = max(0.0, time.monotonic() - started_at)

    ui_msg_done = push_ui_message(
        "intent_router",
        {
            "status": "done",
            "user_text": user_text,
            "intent": intent_label,
            "route": route_to,
            "raw": raw_model_output,
            "elapsed_s": elapsed_s,
            "steps": [
                "解析用户输入",
                "调用意图分类模型（gpt-4.1-nano）",
                "映射到下游路由（rag / article / shortcut）",
                f"完成：intent={intent_label} → route={route_to}",
            ],
            "active_step": 4,
        },
        id=intent_ui_id,
        message=ui_anchor_msg,
        merge=True,
    )

    return {
        "intent": intent_label,
        "ui": [ui_msg_done],
    }
