"""Report 洞察（plan→execute）。

说明：
- 该模块只负责对 EvidencePack 做洞察：先生成分析计划（plan），再用确定性代码执行（execute）
  产出 step_outputs，最后基于 step_outputs 生成 insights/actions。
- 不使用 ReAct 循环，避免死循环与 recursion_limit 问题。
"""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agent.utils.llm import llm_nostream


_PLANNER = None
_SUMMARIZER = None


class HypothesisModel(BaseModel):
    text: str = Field(..., description="待验证假设")
    confidence: Literal["high", "medium", "low"] = Field(..., description="置信度")
    next_step: str = Field(..., description="如何验证该假设")


class SuccessMetricModel(BaseModel):
    metric: str
    window_days: int = 7
    target: str | None = None


class ActionModel(BaseModel):
    id: str
    title: str
    why: str | None = None
    effort: Literal["low", "medium", "high"] = "medium"
    impact: Literal["low", "medium", "high"] = "medium"
    success_metric: SuccessMetricModel | None = None


class InsightsModel(BaseModel):
    one_liner: str
    evidence: list[str] = Field(default_factory=list)
    hypotheses: list[HypothesisModel] = Field(default_factory=list)


class TraceModel(BaseModel):
    todo_summary: str = Field(..., description="一句话说明本次按哪些 Todo 步骤完成分析")
    used_todos: list[str] = Field(default_factory=list, description="引用的 Todo content（顺序可对应步骤）")


class StepOutputModel(BaseModel):
    step: str = Field(..., description="对应的分析步骤标题")
    result: str = Field(..., description="该步骤的具体产出（含关键数字/结论）")
    evidence_ref: str | None = Field(
        default=None, description="证据来源引用（例如 summary / charts.device_stats 等）"
    )

class PlanStepModel(BaseModel):
    title: str = Field(..., description="分析步骤标题（中文，短句）")
    evidence_refs: list[str] = Field(
        default_factory=list,
        description="本步骤允许引用的 EvidencePack 字段路径（如 summary / charts.device_stats / data_quality）",
    )
    output_expectation: str = Field(
        ..., description="该步骤应该产出的内容类型（例如：占比、Top3、趋势概述、数据质量提示等）"
    )


class AnalysisPlanModel(BaseModel):
    steps: list[PlanStepModel] = Field(..., description="分析步骤列表（1~4 条）")


class InsightsOutputModel(BaseModel):
    insights: InsightsModel
    actions: list[ActionModel] = Field(default_factory=list)
    # trace/step_outputs 由执行器生成，这里仅保留最终洞察与建议动作


def _get_planner():
    """生成分析计划（plan）。"""
    global _PLANNER
    if _PLANNER is None:
        _PLANNER = llm_nostream.with_structured_output(AnalysisPlanModel)
    return _PLANNER


def _get_summarizer():
    """基于 step_outputs 生成洞察/建议（summarize）。"""
    global _SUMMARIZER
    if _SUMMARIZER is None:
        _SUMMARIZER = llm_nostream.with_structured_output(InsightsOutputModel)
    return _SUMMARIZER

def _fmt_int(v: Any) -> str:
    try:
        return f"{int(v):,}"
    except Exception:
        return str(v)


def _fmt_pct(v: float) -> str:
    try:
        return f"{v*100:.1f}%"
    except Exception:
        return str(v)


def _extract_pie_distribution(chart: dict[str, Any]) -> tuple[int, list[tuple[str, int, float]]]:
    """从 pie chart data 提取总数与占比。"""
    data = chart.get("data") or []
    items: list[tuple[str, int]] = []
    total = 0
    for r in data:
        if not isinstance(r, dict):
            continue
        name = str(r.get("name") or r.get("label") or "")
        val = r.get("value")
        try:
            iv = int(val)
        except Exception:
            continue
        if not name:
            name = "—"
        items.append((name, iv))
        total += iv
    dist: list[tuple[str, int, float]] = []
    if total > 0:
        for name, iv in sorted(items, key=lambda x: x[1], reverse=True)[:5]:
            dist.append((name, iv, iv / total))
    return total, dist


def execute_plan(
    *,
    evidence_pack: dict[str, Any],
    plan: AnalysisPlanModel,
) -> list[dict[str, Any]]:
    """确定性执行：根据 plan 从 EvidencePack 生成 step_outputs。"""
    out: list[dict[str, Any]] = []
    summary = (evidence_pack or {}).get("summary") or {}
    charts = (evidence_pack or {}).get("charts") or {}
    dq = (evidence_pack or {}).get("data_quality") or {}

    for step in plan.steps:
        title = step.title
        title_l = title.lower()
        result_lines: list[str] = []
        evidence_ref: str | None = None

        # 核心指标
        if ("核心" in title) or ("指标" in title) or ("summary" in " ".join(step.evidence_refs).lower()):
            tv = summary.get("total_visits")
            tu = summary.get("total_unique_visitors")
            tpv = summary.get("total_page_views")
            pps = summary.get("pages_per_session")
            if tv is not None:
                result_lines.append(f"总访问量 sessions：{_fmt_int(tv)}")
            if tu is not None:
                result_lines.append(f"独立访客 activeUsers：{_fmt_int(tu)}")
            if tpv is not None:
                result_lines.append(f"页面浏览 pageViews：{_fmt_int(tpv)}")
            if pps is not None:
                result_lines.append(f"每会话浏览页数 pages/session：{pps}")
            evidence_ref = "summary"

        # 设备分布
        if ("设备" in title) or ("device" in title_l) or ("charts.device" in " ".join(step.evidence_refs).lower()):
            chart = charts.get("device_stats") or {}
            total, dist = _extract_pie_distribution(chart) if isinstance(chart, dict) else (0, [])
            if total and dist:
                parts = [f"{name} {_fmt_int(val)}（{_fmt_pct(p)}）" for name, val, p in dist]
                result_lines.append(f"设备总量：{_fmt_int(total)}；Top： " + "，".join(parts))
            evidence_ref = "charts.device_stats"

        # 渠道/来源
        if ("来源" in title) or ("渠道" in title) or ("traffic" in title_l) or ("charts.traffic" in " ".join(step.evidence_refs).lower()):
            chart = charts.get("traffic_sources") or {}
            total, dist = _extract_pie_distribution(chart) if isinstance(chart, dict) else (0, [])
            if total and dist:
                parts = [f"{name} {_fmt_int(val)}（{_fmt_pct(p)}）" for name, val, p in dist]
                result_lines.append(f"来源总量：{_fmt_int(total)}；Top： " + "，".join(parts))
            evidence_ref = "charts.traffic_sources"

        # 趋势（简单描述）
        if ("趋势" in title) or ("trend" in title_l) or ("charts.daily" in " ".join(step.evidence_refs).lower()):
            chart = charts.get("daily_visits") or {}
            data = (chart.get("data") or []) if isinstance(chart, dict) else []
            if isinstance(data, list) and data:
                first = data[0]
                last = data[-1]
                xk = chart.get("x_key") or "date"
                y_keys = chart.get("y_keys") or []
                if isinstance(first, dict) and isinstance(last, dict) and y_keys:
                    y0 = y_keys[0]
                    try:
                        v0 = float(first.get(y0))
                        v1 = float(last.get(y0))
                        delta = v1 - v0
                        result_lines.append(
                            f"{y0} 从 {first.get(xk)} 的 {int(v0)} 变化到 {last.get(xk)} 的 {int(v1)}（Δ {int(delta)}）"
                        )
                    except Exception:
                        pass
            evidence_ref = "charts.daily_visits"

        # 数据质量
        if ("质量" in title) or ("口径" in title) or ("data_quality" in " ".join(step.evidence_refs).lower()):
            notes = dq.get("notes") or []
            warns = dq.get("warnings") or []
            if warns:
                result_lines.append("Warnings：" + "；".join([str(w) for w in warns[:3]]))
            if notes:
                result_lines.append("Notes：" + "；".join([str(n) for n in notes[:3]]))
            evidence_ref = "data_quality"

        if not result_lines:
            # 没匹配到规则时给出最小可追踪输出
            result_lines.append(f"（该步骤暂未实现确定性执行规则：{step.output_expectation}）")
            evidence_ref = step.evidence_refs[0] if step.evidence_refs else None

        out.append(
            {
                "step": title,
                "result": "\n".join(result_lines),
                "evidence_ref": evidence_ref,
            }
        )

    return out


async def generate_report_insights(
    *,
    evidence_pack: dict[str, Any],
    user_text: str | None = None,
) -> dict[str, Any]:
    """plan→execute：生成 plan，执行得到 step_outputs，再总结为 insights/actions。"""
    charts_keys = sorted(list(((evidence_pack or {}).get("charts") or {}).keys()))
    planner = _get_planner()
    summarizer = _get_summarizer()

    plan_prompt = (
        "你是站点 GA 报表分析规划器。\n"
        "请根据 EvidencePack 中可用字段，生成 1~4 条分析步骤计划（steps）。\n"
        "每条步骤要说明：标题、可引用的 evidence_refs、期望产出。\n"
        "禁止编造不存在的字段。\n"
        f"可用 charts keys：{charts_keys}\n"
        f"用户问题（可选）：{user_text or ''}\n"
        "EvidencePack（JSON）：\n"
        + json.dumps(evidence_pack, ensure_ascii=False)
    )
    plan: AnalysisPlanModel = await planner.ainvoke(
        [HumanMessage(content=plan_prompt)], config={"callbacks": []}
    )

    step_outputs = execute_plan(evidence_pack=evidence_pack, plan=plan)

    summary_prompt = (
        "你是站点 GA 报表洞察助手。\n"
        "只能基于 step_outputs（逐步产出）给出最终洞察与建议动作，禁止引入 step_outputs 之外的新事实。\n"
        "请输出：insights（one_liner/evidence/hypotheses）与 actions（1~3条）。\n"
        "step_outputs（JSON）：\n"
        + json.dumps(step_outputs, ensure_ascii=False)
    )
    final: InsightsOutputModel = await summarizer.ainvoke(
        [HumanMessage(content=summary_prompt)], config={"callbacks": []}
    )

    todos = [{"content": s.title, "status": "completed"} for s in plan.steps]
    trace = {
        "todo_summary": "本次洞察按计划步骤逐项分析并产出结论。",
        "used_todos": [s.title for s in plan.steps],
    }

    return {
        "plan": plan.model_dump(),
        "insights": final.insights.model_dump(),
        "actions": [a.model_dump() for a in final.actions],
        "trace": trace,
        "step_outputs": step_outputs,
        "todos": todos,
    }

