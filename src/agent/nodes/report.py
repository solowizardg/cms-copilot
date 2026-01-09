"""站点 Report 节点模块（ReAct：AI 规划 → 连续调用 GA MCP tools → 图表展示）。

目标：
- 用户提问 → 意图识别进入 report
- AI 基于需求规划要调用哪些 GA MCP tools（可能多次 run_report）
- 执行 tool calling 获取数据
- 聚合为前端 SiteReportCard 期望的 charts 结构并展示
"""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langgraph.graph.ui import UIMessage, push_ui_message

from agent.state import CopilotState, ReportState
from agent.tools.ga_mcp import list_ga_tool_specs, normalize_ga_tool_result, with_ga_tools
from agent.utils.helpers import latest_user_message, message_text
from agent.utils.llm import llm_nostream
from agent.insights.reporting.evidence import build_evidence_pack
from agent.insights.report_insights_agent import generate_report_insights

from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition


DEFAULT_GA_PROPERTY_ID = os.getenv("CMS_GA_PROPERTY_ID", "properties/337059212")
DEFAULT_DAYS = int(os.getenv("CMS_GA_DEFAULT_DAYS", "7"))


def _default_run_report_args(property_id: str, days: int = 7) -> dict[str, Any]:
    """生成默认的 run_report 参数（时间趋势）。"""
    return {
        "property_id": property_id,
        "date_ranges": [{"start_date": f"{days}daysAgo", "end_date": "yesterday"}],
        "dimensions": ["date"],
        "metrics": ["activeUsers", "sessions", "screenPageViews"],
        "limit": 10000,
    }


def _extract_property_id(text: str) -> str | None:
    m = re.search(r"(properties/\d+)", text or "", flags=re.IGNORECASE)
    return m.group(1) if m else None


def _get_anchor_msg_by_id(state: ReportState, anchor_id: str | None) -> AIMessage:
    if anchor_id:
        for m in state.get("messages", []):
            if isinstance(m, AIMessage) and getattr(m, "id", None) == anchor_id:
                return m
    return AIMessage(id=str(uuid.uuid4()), content="")


def _get_anchor_msg(state: ReportState) -> AIMessage:
    anchor_id = state.get("report_anchor_id") or state.get("ui_anchor_id")
    return _get_anchor_msg_by_id(state, anchor_id)


def _get_ui_id(state: ReportState) -> str | None:
    return state.get("report_ui_id") or state.get("ui_id")

def _get_progress_ui_id(state: ReportState) -> str | None:
    return state.get("report_progress_ui_id") or _get_ui_id(state)


def _get_charts_ui_id(state: ReportState) -> str | None:
    return state.get("report_charts_ui_id") or _get_ui_id(state)


def _get_insights_ui_id(state: ReportState) -> str | None:
    return state.get("report_insights_ui_id") or _get_ui_id(state)


def _make_ui_message(
    name: str,
    ui_id: str | None,
    anchor_msg: AIMessage,
    props: dict[str, Any],
    *,
    merge: bool = True,
) -> UIMessage:
    """通过 push_ui_message 发送 UI stream，并写入 state.ui。"""
    stable_id = ui_id or f"{name}:{getattr(anchor_msg, 'id', '')}"
    return push_ui_message(
        name=name,
        props=props,
        id=stable_id,
        message=anchor_msg,
        merge=merge,
    )


def _build_report_snapshot(
    *,
    site_id: str | None,
    tool_result: dict[str, Any] | None,
    data_quality: dict[str, Any] | None,
    insights: dict[str, Any] | None,
    actions: Any,
    todos: Any,
) -> dict[str, Any]:
    """构造可安全覆盖的 report 快照（避免发送 None 清空字段）。"""
    tool_result = tool_result or {}
    report: dict[str, Any] = {
        "site_id": site_id,
        "report_type": "overview",
        "report_type_name": "网站数据报告",
        "summary": tool_result.get("summary") or {},
        "charts": tool_result.get("charts") or {},
    }
    if data_quality:
        report["data_quality"] = data_quality
    if insights:
        report["insights"] = insights
    if isinstance(actions, list) and actions:
        report["actions"] = actions
    if isinstance(todos, list) and todos:
        report["todos"] = todos
    return report


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """从模型输出中提取 JSON object（兼容 ```json ...``` 包裹）。"""
    t = (text or "").strip()
    if not t:
        return None
    # 直接尝试
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    # 尝试截取第一个 { 到最后一个 }
    l = t.find("{")
    r = t.rfind("}")
    if 0 <= l < r:
        try:
            obj = json.loads(t[l : r + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def _try_build_summary_from_report(result: dict[str, Any]) -> dict[str, Any] | None:
    """从 GA report rows 推导 summary（用于前端摘要区）。"""
    try:
        metric_headers = result.get("metric_headers") or []
        metric_names = [h.get("name") for h in metric_headers if h.get("name")]
        rows = result.get("rows") or []
        totals: dict[str, float] = {mn: 0.0 for mn in metric_names}
        for r in rows:
            met_vals = r.get("metric_values") or []
            for i, mn in enumerate(metric_names):
                if i < len(met_vals):
                    v = (met_vals[i] or {}).get("value")
                    try:
                        totals[mn] += float(v)
                    except Exception:
                        pass
        total_visits = int(totals.get("sessions", 0))
        total_unique = int(totals.get("activeUsers", 0))
        total_pv = int(totals.get("screenPageViews", 0))
        return {
            "total_visits": total_visits,
            "total_unique_visitors": total_unique,
            "total_page_views": total_pv,
            "avg_session_duration": 0,
            "bounce_rate": 0.0,
            "pages_per_session": round(total_pv / total_visits, 2) if total_visits > 0 else 0,
        }
    except Exception:
        return None


def _normalize_ga_tool_args(tool_name: str, args: Any, *, property_id: str) -> dict[str, Any]:
    """把 LLM 生成的参数归一化，并补齐 GA MCP 工具的必填字段。

    关键点：
    - GA MCP run_report 必填：property_id / date_ranges / dimensions / metrics
    - GA MCP run_realtime_report 必填：property_id / dimensions / metrics
    - LLM 可能输出驼峰字段名（dateRanges、orderBys 等），这里做一次兼容转换
    """
    if not isinstance(args, dict):
        args = {}

    # 常见驼峰/变体转 snake_case
    alias_map = {
        "propertyId": "property_id",
        "dateRanges": "date_ranges",
        "dateRange": "date_ranges",
        "dimension": "dimensions",
        "dims": "dimensions",
        "metric": "metrics",
        "orderBys": "order_bys",
        "currencyCode": "currency_code",
        "returnPropertyQuota": "return_property_quota",
    }
    normalized: dict[str, Any] = {}
    for k, v in args.items():
        kk = alias_map.get(k, k)
        normalized[kk] = v

    # 统一 property_id
    normalized.setdefault("property_id", property_id)

    if tool_name == "run_report":
        # 默认 date_ranges
        normalized.setdefault(
            "date_ranges",
            [{"start_date": f"{DEFAULT_DAYS}daysAgo", "end_date": "yesterday"}],
        )
        # 默认 dimensions/metrics
        normalized.setdefault("dimensions", ["date"])
        normalized.setdefault("metrics", ["activeUsers", "sessions", "screenPageViews"])
    elif tool_name == "run_realtime_report":
        normalized.setdefault("dimensions", ["country"])
        normalized.setdefault("metrics", ["activeUsers"])

    # 确保 list 类型
    if "dimensions" in normalized and not isinstance(normalized["dimensions"], list):
        normalized["dimensions"] = [normalized["dimensions"]]
    if "metrics" in normalized and not isinstance(normalized["metrics"], list):
        normalized["metrics"] = [normalized["metrics"]]
    if "date_ranges" in normalized and not isinstance(normalized["date_ranges"], list):
        normalized["date_ranges"] = [normalized["date_ranges"]]

    return normalized


def _humanize_ga_value(dim_name: str, value: str) -> str:
    """把 GA 技术名称转换为人类可读的中文描述。"""
    if not value:
        return value
    
    # sessionDefaultChannelGroup 翻译
    if dim_name == "sessionDefaultChannelGroup":
        mapping = {
            "Organic Search": "自然搜索",
            "Direct": "直接访问",
            "Paid Search": "付费搜索",
            "Organic Social": "社交媒体",
            "Referral": "外部链接",
            "Email": "邮件",
            "Paid Social": "付费社交",
            "Display": "展示广告",
            "Organic Shopping": "自然购物",
            "Paid Shopping": "付费购物",
            "Organic Video": "视频",
            "(Other)": "其他",
            "(not set)": "未设置",
        }
        return mapping.get(value, value)
    
    # deviceCategory 翻译
    if dim_name == "deviceCategory":
        mapping = {
            "desktop": "桌面端",
            "mobile": "移动端",
            "tablet": "平板",
        }
        return mapping.get(value.lower(), value)
    
    # 其他维度（如有需要可继续扩展）
    return value


def _build_chart_from_ga_report(result: dict[str, Any]) -> dict[str, Any] | None:
    """通用 GA report -> chart（line/bar/pie），并翻译技术名称为人类可读。"""
    rows = result.get("rows") or []
    dim_headers = result.get("dimension_headers") or []
    metric_headers = result.get("metric_headers") or []

    dim_names = [h.get("name") for h in dim_headers if h.get("name")]
    metric_names = [h.get("name") for h in metric_headers if h.get("name")]
    if not metric_names:
        return None

    data: list[dict[str, Any]] = []
    for r in rows:
        row: dict[str, Any] = {}
        dim_vals = r.get("dimension_values") or []
        met_vals = r.get("metric_values") or []
        for i, dn in enumerate(dim_names):
            if i < len(dim_vals):
                raw_val = (dim_vals[i] or {}).get("value")
                # 翻译维度值为人类可读
                row[dn] = _humanize_ga_value(dn, raw_val)
        for i, mn in enumerate(metric_names):
            if i < len(met_vals):
                v = (met_vals[i] or {}).get("value")
                try:
                    row[mn] = float(v) if "." in str(v) else int(v)
                except Exception:
                    row[mn] = v
        data.append(row)

    # 维度为 date：折线
    x_key = dim_names[0] if dim_names else "x"
    if "date" in (x_key or "").lower():
        return {
            "chart_type": "line",
            "title": "趋势",
            "data": data,
            "x_key": x_key,
            "y_keys": metric_names,
            "y_labels": metric_names,
            "colors": ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444"],
        }

    # 单指标分布：仅在“分布类维度”下使用饼图；页面/内容类维度用柱状图更符合预期
    PIE_FRIENDLY_DIMS = {
        "deviceCategory",
        "sessionDefaultChannelGroup",
        "country",
        "city",
        "region",
        "browser",
        "operatingSystem",
        "platform",
        "language",
    }
    if len(metric_names) == 1 and len(data) <= 12 and (x_key in PIE_FRIENDLY_DIMS):
        pie_data = [{"name": r.get(x_key), "value": r.get(metric_names[0], 0)} for r in data]
        return {
            "chart_type": "pie",
            "title": f"{x_key} 分布",
            "data": pie_data,
            "value_key": "value",
            "label_key": "name",
        }

    # 否则：柱状图
    y_key = metric_names[0]
    return {
        "chart_type": "bar",
        "title": f"{x_key} - {y_key}",
        "data": data,
        "x_key": x_key,
        "y_key": y_key,
        "color": "#6366f1",
        "show_change": False,
    }


def _chart_key_for_report(result: dict[str, Any], chart: dict[str, Any] | None) -> str | None:
    """根据 GA 的维度决定塞到前端哪个 chart key。
    
    只支持以下维度映射：
    - date → daily_visits
    - sessionDefaultChannelGroup → traffic_sources
    - deviceCategory → device_stats
    
    其他维度（如 country、eventName 等）会返回 None（不渲染），避免错误映射。
    """
    if not chart:
        return None
    dim_headers = result.get("dimension_headers") or []
    dim_names = [h.get("name") for h in dim_headers if h.get("name")]
    first = (dim_names[0] if dim_names else "") or ""
    
    # 白名单：只映射前端支持的三种维度
    if first == "date":
        return "daily_visits"
    if first == "sessionDefaultChannelGroup":
        return "traffic_sources"
    if first == "deviceCategory":
        return "device_stats"

    # 热门页面/内容类维度
    if first in {
        "pagePath",
        "pageTitle",
        "landingPage",
        "pageLocation",
        "screenName",
        "hostName",
        "pageReferrer",
    } or ("page" in first.lower()) or ("screen" in first.lower()):
        return "top_pages"

    # 事件/互动类维度
    if first == "eventName" or ("event" in first.lower()):
        return "user_engagement"
    
    # 其他维度（包括 country、eventName、page* 等）不渲染
    return None


# ============ 主图节点 ============


async def start_report_ui(state: CopilotState) -> dict[str, Any]:
    """创建报告 UI 锚点和初始卡片。"""
    user_msg = latest_user_message(state)
    user_text = message_text(user_msg)

    anchor = AIMessage(id=str(uuid.uuid4()), content="")
    # 只创建锚点与 UI id；实际 UI 首次渲染放到 report_init（避免主图/子图各 push 一次导致双卡）
    progress_ui_id = f"report_progress:{anchor.id}"
    charts_ui_id = f"report_charts:{anchor.id}"
    insights_ui_id = f"report_insights:{anchor.id}"

    ui_msg = _make_ui_message(
        "report_progress",
        progress_ui_id,
        anchor,
        {
            "status": "loading",
            "step": "initializing",
            "user_text": user_text,
            "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
            "active_step": 1,
            "report": None,
            "error_message": None,
        },
        merge=False,
    )
    return {
        "messages": [anchor],
        "ui": [ui_msg],
        "report_progress_ui_id": progress_ui_id,
        "report_charts_ui_id": charts_ui_id,
        "report_insights_ui_id": insights_ui_id,
        "report_anchor_id": anchor.id,
        "user_text": user_text,
    }


# ============ 子图节点 ============


async def report_init(state: ReportState) -> dict[str, Any]:
    """初始化：拉取 tools 列表，给 UI & ReAct 规划提供上下文。"""
    ui_id = _get_progress_ui_id(state)
    anchor_msg = _get_anchor_msg(state)

    user_msg = latest_user_message(state)
    user_text = message_text(user_msg) if user_msg else ""

    ui_1 = _make_ui_message(
        "report_progress",
        ui_id,
        anchor_msg,
        {
            "status": "loading",
            "step": "listing_tools",
            "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
            "active_step": 1,
            "message": "正在从 GA MCP 获取工具列表…",
        },
    )

    tenant_id = state.get("tenant_id")
    site_id = state.get("site_id")
    
    # 从 GA MCP 获取工具列表（含详细描述和参数 schema）
    specs = await list_ga_tool_specs(site_id=site_id, tenant_id=tenant_id)
    options = [
        {"code": s.name, "name": s.name, "desc": s.description, "schema": s.input_schema}
        for s in specs
    ]

    property_id = _extract_property_id(user_text) or DEFAULT_GA_PROPERTY_ID

    ui_2 = _make_ui_message(
        "report_progress",
        ui_id,
        anchor_msg,
        {
            "status": "loading",
            "step": "planning",
            "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
            "active_step": 1,
            "message": f"已获取 {len(specs)} 个 GA MCP 工具，AI 正在规划调用…",
        },
    )

    return {"ui": [ui_1, ui_2], "user_text": user_text, "options": options, "tool_specs": specs}


async def report_execute_tool(state: ReportState) -> dict[str, Any]:
    """Planning + Execution：先基于 MCP 工具列表规划，再批量执行。"""
    ui_id = _get_progress_ui_id(state)
    anchor_msg = _get_anchor_msg(state)

    tenant_id = state.get("tenant_id")
    site_id = state.get("site_id")
    user_text = state.get("user_text") or ""
    options = state.get("options") or []
    tool_specs = state.get("tool_specs") or []

    property_id = _extract_property_id(user_text) or DEFAULT_GA_PROPERTY_ID

    ui_fetch = _make_ui_message(
        "report_progress",
        ui_id,
        anchor_msg,
        {
            "status": "loading",
            "step": "fetching_data",
            "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
            "active_step": 2,
            "message": "AI 正在基于 MCP 工具列表规划数据获取方案…",
        },
    )

    # 构建工具详情（给 LLM 参考）
    tool_details = []
    for spec in tool_specs[:10]:  # 最多展示 10 个工具
        desc = spec.description[:200] if spec.description else "无描述"
        schema_info = ""
        if spec.input_schema and isinstance(spec.input_schema, dict):
            required = spec.input_schema.get("required") or []
            schema_info = f" (必填参数: {', '.join(required)})" if required else ""
        tool_details.append(f"- {spec.name}: {desc}{schema_info}")
    
    tool_info = "\n".join(tool_details) if tool_details else "无工具可用"

    # Planning + Execution 模式：先让 AI 规划出需要哪些数据
    planning_prompt = f"""你是 GA 数据分析助手。用户问题：{user_text}

## 第一步：查看可用的 MCP 工具
以下是从 GA MCP 获取的工具列表：

{tool_info}

## 第二步：规划数据获取方案
现在你要**规划出一份数据获取方案**（不是立即调用工具，而是先列出方案）：

如果用户要"网站报告/趋势/流量分析"，请返回 JSON 格式的方案：
{{
  "plan": [
    {{"desc": "时间趋势", "tool": "run_report", "args": {{"property_id": "{property_id}", "date_ranges": [{{"start_date": "7daysAgo", "end_date": "yesterday"}}], "dimensions": ["date"], "metrics": ["activeUsers","sessions","screenPageViews"]}}}},
    {{"desc": "流量来源", "tool": "run_report", "args": {{"property_id": "{property_id}", "date_ranges": [{{"start_date": "7daysAgo", "end_date": "yesterday"}}], "dimensions": ["sessionDefaultChannelGroup"], "metrics": ["sessions"]}}}},
    {{"desc": "设备分布", "tool": "run_report", "args": {{"property_id": "{property_id}", "date_ranges": [{{"start_date": "7daysAgo", "end_date": "yesterday"}}], "dimensions": ["deviceCategory"], "metrics": ["sessions"]}}}}
  ]
}}

**重要限制**：
1. 只使用上面列出的 MCP 工具（优先 run_report）
2. 必须严格按工具的 inputSchema 生成参数（snake_case），尤其是 date_ranges / dimensions / metrics / order_bys
3. 如果用户提到“热门页面/Top pages/页面访问量”，优先使用 dimensions=["pagePath"] 或 ["pageTitle"]，并用 order_bys 按 screenPageViews/sessions 降序
4. date_ranges 格式必须是 [{{"start_date": "7daysAgo", "end_date": "yesterday"}}]
5. property_id 必须是 "{property_id}"
6. 输出必须是严格 JSON（不要多余文字）

输出方案："""

    async def _run(tools_by_name: dict[str, Any]):
        """Planning + Execution 模式：先规划方案，再批量执行，避免 ReAct 重复同样参数。"""

        plan_items: list[dict[str, Any]] | None = None
        plan_descs: list[str] = []

        # Step 1: LLM 规划（内部 JSON）
        try:
            # 禁用回调/流事件，避免把 LLM 的 JSON 规划输出到聊天框
            plan_resp = await llm_nostream.ainvoke(planning_prompt, config={"callbacks": []})
            plan_text = getattr(plan_resp, "content", str(plan_resp)) or ""
            plan_json = _extract_json_object(plan_text) or {}
            maybe_items = plan_json.get("plan") if isinstance(plan_json, dict) else None
            if isinstance(maybe_items, list) and maybe_items:
                plan_items = maybe_items
        except Exception:
            plan_items = None

        # fallback：规划失败则使用默认计划（保证执行稳定）
        if not isinstance(plan_items, list) or not plan_items:
            only_device = ("设备" in user_text) and ("趋势" not in user_text) and ("流量" not in user_text)
            plan_items = (
                [
                    {
                        "desc": "设备分布",
                        "tool": "run_report",
                        "args": {
                            "property_id": property_id,
                            "date_ranges": [{"start_date": "7daysAgo", "end_date": "yesterday"}],
                            "dimensions": ["deviceCategory"],
                            "metrics": ["sessions"],
                        },
                    }
                ]
                if only_device
                else [
                    {"desc": "时间趋势", "tool": "run_report", "args": _default_run_report_args(property_id, 7)},
                    {
                        "desc": "流量来源",
                        "tool": "run_report",
                        "args": {
                            "property_id": property_id,
                            "date_ranges": [{"start_date": "7daysAgo", "end_date": "yesterday"}],
                            "dimensions": ["sessionDefaultChannelGroup"],
                            "metrics": ["sessions"],
                        },
                    },
                    {
                        "desc": "设备分布",
                        "tool": "run_report",
                        "args": {
                            "property_id": property_id,
                            "date_ranges": [{"start_date": "7daysAgo", "end_date": "yesterday"}],
                            "dimensions": ["deviceCategory"],
                            "metrics": ["sessions"],
                        },
                    },
                ]
            )

        # 步骤 2：去重（基于 dimensions，避免重复调用）
        seen_dims: set[str] = set()
        unique_plan: list[dict[str, Any]] = []
        for item in plan_items:
            dims = item.get("args", {}).get("dimensions") or []
            # 标准化：统一小写，排序
            dims_normalized = [str(d).lower().strip() for d in dims]
            dims_key = ",".join(sorted(dims_normalized)) if dims_normalized else "__no_dims__"
            if dims_key not in seen_dims and len(unique_plan) < 6:
                seen_dims.add(dims_key)
                unique_plan.append(item)

        # 步骤 3：依次执行 plan 中的工具调用
        charts: dict[str, Any] = {}
        summary: dict[str, Any] | None = None
        raws: list[Any] = []

        for item in unique_plan:
            tool_name = item.get("tool")
            args = item.get("args") or {}
            desc = item.get("desc") or tool_name
            if desc:
                plan_descs.append(str(desc))

            if tool_name in {"run_report", "run_realtime_report"}:
                args = _normalize_ga_tool_args(str(tool_name), args, property_id=property_id)

            tool_obj = tools_by_name.get(tool_name)
            if tool_obj is None:
                norm = {"error": f"unknown tool: {tool_name}"}
            else:
                try:
                    out = await tool_obj.ainvoke(args)
                    norm = normalize_ga_tool_result(out)
                except Exception as e:
                    norm = {"error": str(e)}

            raws.append({"desc": desc, "tool": tool_name, "args": args, "result": norm})
            if summary is None:
                summary = _try_build_summary_from_report(norm)
            if isinstance(norm, dict) and ("rows" in norm or "dimension_headers" in norm):
                chart = _build_chart_from_ga_report(norm)
                key = _chart_key_for_report(norm, chart)
                if key and chart:
                    # 如果 key 已存在，跳过（避免覆盖）
                    if key not in charts:
                        charts[key] = chart
                

        return (
            f"已完成 {len(unique_plan)} 次数据获取（{', '.join(str(p.get('desc','')) for p in unique_plan)}）",
            charts,
            summary or {},
            raws,
            plan_descs,
        )

    try:
        final_text, charts, summary, raws, plan_descs = await with_ga_tools(
            site_id=site_id, tenant_id=tenant_id, fn=_run
        )
        ui_plan = _make_ui_message(
            "report_progress",
            ui_id,
            anchor_msg,
            {
                "status": "loading",
                "step": "plan_ready",
                "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
                "active_step": 2,
                "message": "本次将获取以下数据：\n- " + "\n- ".join([d for d in plan_descs if d]),
            },
        )
        return {
            "ui": [ui_fetch, ui_plan],
            "tool_result": {"final": final_text, "charts": charts, "summary": summary, "raws": raws},
            "tool_error": None,
        }
    except Exception as e:
        # 保留 tool_error（例如 MCP 调用异常），但不把“规划失败”当致命错误
        return {"ui": [ui_fetch], "tool_result": None, "tool_error": str(e)}


async def report_build_evidence(state: ReportState) -> dict[str, Any]:
    """纯代码生成 EvidencePack 与数据质量提示。"""
    evidence = build_evidence_pack(
        tool_result=state.get("tool_result") if isinstance(state.get("tool_result"), dict) else None,
        user_text=state.get("user_text"),
        default_window_days=DEFAULT_DAYS,
    )
    return {
        "evidence_pack": evidence.to_dict(),
        "data_quality": evidence.to_dict().get("data_quality"),
    }


async def report_render_charts(state: ReportState) -> dict[str, Any]:
    """在 analyze 后立即把图表/summary 推到前端（同一张 site_report 卡 merge 更新）。"""
    ui_id = _get_charts_ui_id(state)
    anchor_msg = _get_anchor_msg(state)

    tool_result = state.get("tool_result") if isinstance(state.get("tool_result"), dict) else None
    # 图表卡只承载图表相关数据，避免在多个 UI 卡之间重复嵌套同一份内容
    report_snapshot: dict[str, Any] = {
        "site_id": state.get("site_id"),
        "report_type": "overview",
        "report_type_name": "网站数据报告",
        "summary": (tool_result or {}).get("summary") or {},
        "charts": (tool_result or {}).get("charts") or {},
    }

    ui_msg = _make_ui_message(
        "report_charts",
        ui_id,
        anchor_msg,
        {
            "status": "loading",
            "step": "charts_ready",
            "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
            "active_step": 3,
            "message": "图表已生成，正在生成洞察与 Todo…",
            "report": report_snapshot,
        },
    )
    # 同步更新进度卡，避免只更新 charts 卡导致进度停滞
    progress_ui = _make_ui_message(
        "report_progress",
        _get_progress_ui_id(state),
        anchor_msg,
        {
            "status": "loading",
            "step": "charts_ready",
            "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
            "active_step": 3,
            "message": "图表已生成，正在生成洞察与 Todo…",
        },
    )
    return {"ui": [ui_msg, progress_ui]}


async def report_generate_insights(state: ReportState) -> dict[str, Any]:
    """调用洞察 agent：生成 insights/actions，并通过 TodoListMiddleware 写入 todos。"""
    ui_id = _get_insights_ui_id(state)
    anchor_msg = _get_anchor_msg(state)

    def _map_todos_for_ui(todos: Any) -> list[dict[str, Any]] | None:
        if not isinstance(todos, list) or not todos:
            return None
        mapped: list[dict[str, Any]] = []
        for i, t in enumerate(todos):
            if not isinstance(t, dict):
                continue
            content = str(t.get("content") or "").strip()
            status = str(t.get("status") or "").strip()
            if not content:
                continue
            mapped.append(
                {
                    "id": f"todo-{i+1}",
                    "title": content,
                    "description": f"状态：{status}" if status else None,
                }
            )
        return mapped or None

    ui_msg = _make_ui_message(
        "report_insights",
        ui_id,
        anchor_msg,
        {
            "status": "loading",
            "step": "generating_insights",
            "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
            "active_step": 4,
            "message": "正在生成解读与可执行 Todo…",
        },
    )
    # 同步更新进度卡（洞察阶段）
    progress_thinking = _make_ui_message(
        "report_progress",
        _get_progress_ui_id(state),
        anchor_msg,
        {
            "status": "loading",
            "step": "generating_insights",
            "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
            "active_step": 4,
            "message": "正在生成洞察…",
        },
    )

    evidence_pack = state.get("evidence_pack") or {}
    try:
        out = await generate_report_insights(evidence_pack=evidence_pack, user_text=state.get("user_text"))
        ui_todos = _map_todos_for_ui(out.get("todos"))

        # 洞察卡只承载洞察相关数据（不重复塞 charts/summary）
        report_snapshot: dict[str, Any] = {
            "site_id": state.get("site_id"),
            "report_type": "overview",
            "report_type_name": "网站数据报告",
        }
        if state.get("data_quality"):
            report_snapshot["data_quality"] = state.get("data_quality")
        if isinstance(ui_todos, list) and ui_todos:
            report_snapshot["todos"] = ui_todos
        if isinstance(out.get("insights"), dict):
            report_snapshot["insights"] = out.get("insights")
        if isinstance(out.get("actions"), list) and out.get("actions"):
            report_snapshot["actions"] = out.get("actions")

        if isinstance(out.get("trace"), dict):
            report_snapshot["trace"] = out.get("trace")
        if isinstance(out.get("step_outputs"), list) and out.get("step_outputs"):
            report_snapshot["step_outputs"] = out.get("step_outputs")
        # 不在 UI 中额外渲染错误块；错误仍可通过进度卡/洞察卡状态体现
        ui_ready = _make_ui_message(
            "report_insights",
            ui_id,
            anchor_msg,
            {
                "status": "loading",
                "step": "insights_ready",
                "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
                "active_step": 4,
                "message": "洞察已生成，正在汇总报告…",
                "report": report_snapshot,
            },
        )
        progress_ready = _make_ui_message(
            "report_progress",
            _get_progress_ui_id(state),
            anchor_msg,
            {
                "status": "loading",
                "step": "insights_ready",
                "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
                "active_step": 4,
                "message": "洞察已生成，正在汇总报告…",
            },
        )
        return {
            "ui": [ui_msg, progress_thinking, ui_ready, progress_ready],
            "insights": out.get("insights"),
            "actions": out.get("actions"),
            "todos": ui_todos,
            "trace": out.get("trace"),
            "step_outputs": out.get("step_outputs"),
        }
    except Exception as e:
        # 洞察失败不影响报表基础数据展示
        return {
            "ui": [ui_msg, progress_thinking],
            "insights": None,
            "actions": None,
            "todos": None,
            "error": f"generate_insights_failed: {e}",
        }


async def report_finalize(state: ReportState) -> dict[str, Any]:
    """最终渲染：置为 done，并输出完整 report_data。"""
    ui_id = _get_progress_ui_id(state)
    anchor_msg = _get_anchor_msg(state)

    tool_error = state.get("tool_error")
    if tool_error:
        ui_err = _make_ui_message(
            "report_progress",
            ui_id,
            anchor_msg,
            {
                "status": "error",
                "step": "failed",
                "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
                "active_step": 5,
                "error_message": tool_error,
            },
        )
        return {"ui": [ui_err], "error": tool_error}

    ui_done = _make_ui_message(
        "report_progress",
        ui_id,
        anchor_msg,
        {
            "status": "done",
            "step": "completed",
            "steps": ["AI 规划调用", "获取数据", "展示图表", "生成洞察", "完成"],
            "active_step": 5,
            "message": "报告已生成。",
        },
    )
    # 同步把 charts/insights 两张卡也置为 done，避免它们一直停留在 loading
    tool_result = state.get("tool_result") if isinstance(state.get("tool_result"), dict) else None
    charts_report: dict[str, Any] = {
        "site_id": state.get("site_id"),
        "report_type": "overview",
        "report_type_name": "网站数据报告",
        "summary": (tool_result or {}).get("summary") or {},
        "charts": (tool_result or {}).get("charts") or {},
    }
    charts_done = _make_ui_message(
        "report_charts",
        _get_charts_ui_id(state),
        anchor_msg,
        {
            "status": "done",
            "step": "completed",
            "message": "图表数据已生成。",
            "report": charts_report,
        },
    )

    insights_report: dict[str, Any] = {
        "site_id": state.get("site_id"),
        "report_type": "overview",
        "report_type_name": "网站数据报告",
    }
    if state.get("data_quality"):
        insights_report["data_quality"] = state.get("data_quality")
    if state.get("insights"):
        insights_report["insights"] = state.get("insights")
    if state.get("actions"):
        insights_report["actions"] = state.get("actions")
    if state.get("todos"):
        insights_report["todos"] = state.get("todos")
    if state.get("trace"):
        insights_report["trace"] = state.get("trace")
    if state.get("step_outputs"):
        insights_report["step_outputs"] = state.get("step_outputs")
    insights_done = _make_ui_message(
        "report_insights",
        _get_insights_ui_id(state),
        anchor_msg,
        {
            "status": "done",
            "step": "completed",
            "message": "洞察已生成。",
            "report": insights_report,
        },
    )

    return {"ui": [ui_done, charts_done, insights_done]}


