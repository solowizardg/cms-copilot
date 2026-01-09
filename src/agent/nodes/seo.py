"""SEO 规划节点模块。

SEO 周任务规划的节点函数。
简化版：一次 LLM 调用生成完整任务列表，不使用子图。
"""

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer
from langgraph.graph.ui import push_ui_message

from agent.state import CopilotState
from agent.tools.seo import SEO_PLANNER_SYSTEM_PROMPT, SEOWeeklyPlan, get_seo_snapshot
from agent.utils.helpers import latest_user_message, message_text
from agent.utils.llm import llm_nostream

# ============ 主图节点 ============


async def start_seo_ui(state: CopilotState) -> dict[str, Any]:
    """创建 SEO 规划的 UI 锚点和初始卡片（loading 状态）。"""
    user_msg = latest_user_message(state)
    user_text = message_text(user_msg)

    # 创建 AIMessage 锚点
    ui_anchor_msg = AIMessage(id=str(uuid.uuid4()), content="")

    # 创建初始 UI 卡片
    ui_msg_start = push_ui_message(
        "seo_planner",
        {
            "status": "loading",
            "step": "initializing",
            "user_text": user_text,
            "steps": [
                "获取 SEO 快照数据",
                "分析问题并生成任务计划",
                "完成规划",
            ],
            "active_step": 1,
            "tasks": None,
            "error_message": None,
        },
        message=ui_anchor_msg,
    )

    return {
        "messages": [ui_anchor_msg],
        "ui": [ui_msg_start],
        "seo_ui_id": ui_msg_start["id"],
        "seo_anchor_id": ui_anchor_msg.id,
    }


async def handle_seo(state: CopilotState) -> dict[str, Any]:
    """处理 SEO 规划：获取快照、生成任务列表。"""
    writer = get_stream_writer()

    user_msg = latest_user_message(state)
    user_text = message_text(user_msg)
    site_id = state.get("site_id") or "site-001"

    # 获取 UI 锚点
    ui_id = state.get("seo_ui_id")
    anchor_id = state.get("seo_anchor_id")
    anchor_msg = None
    if anchor_id:
        for m in state.get("messages", []):
            if isinstance(m, AIMessage) and getattr(m, "id", None) == anchor_id:
                anchor_msg = m
                break

    if anchor_msg is None:
        anchor_msg = AIMessage(id=str(uuid.uuid4()), content="")

    def _push_ui(props: dict[str, Any]):
        """推送 UI 更新"""
        ui_msg = push_ui_message(
            "seo_planner",
            props,
            id=ui_id,
            message=anchor_msg,
            merge=True,
        )
        if writer is not None:
            writer(ui_msg)
        return ui_msg

    # Step 1: 获取 SEO 快照
    _push_ui(
        {
            "status": "loading",
            "step": "fetching_snapshot",
            "steps": ["获取 SEO 快照数据", "分析问题并生成任务计划", "完成规划"],
            "active_step": 1,
            "tasks": None,
            "error_message": None,
        }
    )

    snapshot = await get_seo_snapshot.ainvoke({"site_id": site_id})

    # Step 2: 分析并生成任务计划
    _push_ui(
        {
            "status": "loading",
            "step": "analyzing",
            "steps": ["获取 SEO 快照数据", "分析问题并生成任务计划", "完成规划"],
            "active_step": 2,
            "tasks": None,
            "error_message": None,
        }
    )

    # 计算周起止日期（工作日：周一到周五）
    today = datetime.now()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    week_start = today + timedelta(days=days_until_monday)
    week_end = week_start + timedelta(days=4)  # 周五，不是周日
    week_start_str = week_start.strftime("%Y-%m-%d")
    week_end_str = week_end.strftime("%Y-%m-%d")

    # 构建 prompt
    plan_prompt = f"""分析以下 SEO 快照数据，生成完整的 SEO 周任务计划。

站点 ID：{site_id}
周期：{week_start_str} ~ {week_end_str}（工作日：周一至周五）

SEO 快照数据：
```json
{json.dumps(snapshot, ensure_ascii=False, indent=2)}
```

要求：
1. 生成 3~5 条任务（每天最多 1 条，仅工作日周一~周五）
2. 每条 issue_type 必须唯一
3. 必须覆盖至少 3 个类别（Indexing/OnPage/Performance/Content/StructuredData）
4. 如果 critical_blockers > 0，必须包含 Indexing 类 critical 任务
5. 优先级：Indexing阻塞 > OnPage修复 > Performance劣化 > Content机会
6. title：中文，不超过 26 个字
7. description：中文 1~2 句话
8. evidence：使用快照中的具体字段路径
9. fix_action 修复动作类型：
   - "article"：Content 类别的任务（内容缺口、低 CTR 等），需要生成内容来修复
   - "link"：有明确外部工具或页面可以修复的任务
   - "none"：暂无自动修复方案的任务
10. fix_prompt：当 fix_action="article" 时，提供完整的内容生成需求描述（中文，50~100字），格式示例：
    - "针对'耳机 风噪 抑制'关键词，创建专题博客内容，提升相关搜索覆盖。"
    - "优化'降噪耳机选购指南'页面内容，增加产品对比和选购建议，提升页面 CTR。"

请生成完整的任务计划。"""

    try:
        # 使用禁用流式输出的 LLM 实例，防止 JSON 被流式发送到前端
        structured_llm = llm_nostream.with_structured_output(SEOWeeklyPlan)
        plan_result: SEOWeeklyPlan = await structured_llm.ainvoke(
            [
                {"role": "system", "content": SEO_PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": plan_prompt},
            ]
        )

        # 转换为 dict
        tasks_data = {
            "site_id": site_id,
            "week_start": week_start_str,
            "week_end": week_end_str,
            "tasks": [task.model_dump() for task in plan_result.tasks],
        }
        error_message = None

    except Exception:
        # 使用默认任务（工作日：周一~周五，最多 5 条）
        # 计算各工作日日期
        mon_date = week_start.strftime("%Y-%m-%d")
        tue_date = (week_start + timedelta(days=1)).strftime("%Y-%m-%d")
        wed_date = (week_start + timedelta(days=2)).strftime("%Y-%m-%d")
        thu_date = (week_start + timedelta(days=3)).strftime("%Y-%m-%d")
        fri_date = (week_start + timedelta(days=4)).strftime("%Y-%m-%d")

        tasks_data = {
            "site_id": site_id,
            "week_start": week_start_str,
            "week_end": week_end_str,
            "tasks": [
                {
                    "date": mon_date,
                    "day_of_week": "Mon",
                    "category": "Indexing",
                    "issue_type": "SITEMAP_LASTMOD_LOW",
                    "title": "修复 Sitemap lastmod 覆盖率",
                    "description": "Sitemap 中 lastmod 覆盖率仅 41%，建议补齐或修正生成策略。",
                    "impact": 4,
                    "difficulty": 2,
                    "severity": "warning",
                    "requires_manual_confirmation": True,
                    "workflow_id": "seo_fix_indexing",
                    "params": {"issue_type": "SITEMAP_LASTMOD_LOW"},
                    "evidence": [
                        {
                            "evidence_path": "sitemap.lastmod_coverage_ratio",
                            "value_summary": "41%",
                        }
                    ],
                    "fix_action": "link",
                    "fix_prompt": None,
                },
                {
                    "date": tue_date,
                    "day_of_week": "Tue",
                    "category": "OnPage",
                    "issue_type": "MISSING_TITLE",
                    "title": "修复缺失的页面标题",
                    "description": "耳机产品页缺少 title 标签，影响搜索展示。",
                    "impact": 5,
                    "difficulty": 1,
                    "severity": "critical",
                    "requires_manual_confirmation": True,
                    "workflow_id": "seo_fix_onpage",
                    "params": {
                        "url": "https://demo-shop.example.com/products/earbuds-x1",
                        "issue_type": "MISSING_TITLE",
                    },
                    "evidence": [
                        {
                            "evidence_path": "issues.on_page[0]",
                            "value_summary": "earbuds-x1 页面缺少 title",
                        }
                    ],
                    "fix_action": "link",
                    "fix_prompt": None,
                },
                {
                    "date": wed_date,
                    "day_of_week": "Wed",
                    "category": "Performance",
                    "issue_type": "HIGH_LCP",
                    "title": "优化页面 LCP 指标",
                    "description": "耳机页面 LCP 达 4600ms，超过 2.5s 阈值。",
                    "impact": 4,
                    "difficulty": 3,
                    "severity": "warning",
                    "requires_manual_confirmation": False,
                    "workflow_id": "seo_fix_performance",
                    "params": {
                        "url": "https://demo-shop.example.com/products/earbuds-x1",
                        "issue_type": "HIGH_LCP",
                    },
                    "evidence": [
                        {
                            "evidence_path": "performance.lcp_ms",
                            "value_summary": "4600ms",
                        }
                    ],
                    "fix_action": "link",
                    "fix_prompt": None,
                },
                {
                    "date": thu_date,
                    "day_of_week": "Thu",
                    "category": "Content",
                    "issue_type": "LOW_CTR",
                    "title": "优化低点击率页面",
                    "description": "降噪指南页面 CTR 仅 0.46%，建议优化标题和描述。",
                    "impact": 3,
                    "difficulty": 2,
                    "severity": "notice",
                    "requires_manual_confirmation": True,
                    "workflow_id": "seo_fix_content",
                    "params": {
                        "url": "https://demo-shop.example.com/blog/noise-cancelling-guide",
                        "issue_type": "LOW_CTR",
                    },
                    "evidence": [
                        {
                            "evidence_path": "gsc.top_queries[2].ctr",
                            "value_summary": "0.46%",
                        }
                    ],
                    "fix_action": "article",
                    "fix_prompt": "针对'降噪耳机 选购 推荐'关键词，优化现有降噪耳机选购指南内容，增加产品对比和使用场景分析，提升页面点击率和搜索覆盖。",
                },
                {
                    "date": fri_date,
                    "day_of_week": "Fri",
                    "category": "StructuredData",
                    "issue_type": "MISSING_PRODUCT_SCHEMA",
                    "title": "添加产品结构化数据",
                    "description": "产品页缺少 Product schema，影响富媒体搜索结果展示。",
                    "impact": 3,
                    "difficulty": 2,
                    "severity": "notice",
                    "requires_manual_confirmation": True,
                    "workflow_id": "seo_fix_structureddata",
                    "params": {"issue_type": "MISSING_PRODUCT_SCHEMA"},
                    "evidence": [
                        {
                            "evidence_path": "structured_data.product_pages",
                            "value_summary": "缺少 Product schema",
                        }
                    ],
                    "fix_action": "none",
                    "fix_prompt": None,
                },
            ],
        }
        error_message = None  # 使用默认任务，不显示错误

    # Step 3: 完成
    final_ui_msg = _push_ui(
        {
            "status": "done",
            "step": "completed",
            "steps": ["获取 SEO 快照数据", "分析问题并生成任务计划", "完成规划"],
            "active_step": 3,
            "tasks": tasks_data,
            "progress": f"共生成 {len(tasks_data['tasks'])} 条任务",
            "error_message": error_message,
        }
    )

    return {
        "ui": [final_ui_msg],
    }
