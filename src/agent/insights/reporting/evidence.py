"""Report 洞察：EvidencePack 构建（纯代码，避免胡归因）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EvidencePack:
    """给 LLM 的证据包：只包含可证明事实与必要上下文。"""

    property_id: str | None
    window_days: int | None
    summary: dict[str, Any]
    charts: dict[str, Any]
    notes: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_id": self.property_id,
            "window_days": self.window_days,
            "summary": self.summary,
            "charts": self.charts,
            "data_quality": {"notes": self.notes, "warnings": self.warnings},
        }


def build_evidence_pack(
    *,
    tool_result: dict[str, Any] | None,
    user_text: str | None,
    default_window_days: int | None = None,
) -> EvidencePack:
    """从 report_execute_tool 的输出构造 EvidencePack。

    约束：
    - 不做因果归因，只做“可直接从数据读出的事实”与“数据质量提示”。
    - 当前实现先提供稳定骨架，后续再逐步丰富（例如：环比、TopN、异常点）。
    """

    tool_result = tool_result or {}
    summary = tool_result.get("summary") if isinstance(tool_result, dict) else {}
    charts = tool_result.get("charts") if isinstance(tool_result, dict) else {}
    raws = tool_result.get("raws") if isinstance(tool_result, dict) else None

    # 估计 window_days（优先从 raws[0].args.date_ranges 推断，否则 fallback）
    window_days: int | None = default_window_days
    property_id: str | None = None
    try:
        if isinstance(raws, list) and raws:
            first = raws[0] or {}
            args = (first.get("args") or {}) if isinstance(first, dict) else {}
            property_id = args.get("property_id")
            date_ranges = args.get("date_ranges") or []
            if isinstance(date_ranges, list) and date_ranges:
                dr0 = date_ranges[0] or {}
                start = str((dr0.get("start_date") or "")).strip()
                # 仅处理类似 "7daysAgo" 这种
                if start.endswith("daysAgo"):
                    n = start.replace("daysAgo", "")
                    if n.isdigit():
                        window_days = int(n)
    except Exception:
        pass

    notes: list[str] = []
    warnings: list[str] = []

    if not summary:
        warnings.append("未能从 GA 返回结果计算 summary（可能是指标缺失或返回结构变化）。")

    if not charts:
        warnings.append("未生成任何图表数据（可能是维度未映射到前端支持的 chart key）。")

    notes.append("注意：所有内容基于AI生成，仅供参考!")

    return EvidencePack(
        property_id=property_id,
        window_days=window_days,
        summary=summary if isinstance(summary, dict) else {},
        charts=charts if isinstance(charts, dict) else {},
        notes=notes,
        warnings=warnings,
    )

