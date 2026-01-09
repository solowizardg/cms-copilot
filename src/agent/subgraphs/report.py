"""Report 子图模块（ReAct：AI 规划多步 MCP 工具调用）。"""

from langgraph.graph import END, START, StateGraph

from agent.nodes.report import (
    report_build_evidence,
    report_execute_tool,
    report_generate_insights,
    report_init,
    report_render_charts,
    report_finalize,
)
from agent.state import ReportState


def build_report_subgraph_v1():
    """构建 Report 子图（v1：仅取数+图表）。

    旧逻辑保留做 fallback / 对比。
    """
    builder = StateGraph(ReportState)

    builder.add_node("init", report_init)
    builder.add_node("execute", report_execute_tool)
    builder.add_node("finalize", report_finalize)

    builder.add_edge(START, "init")
    builder.add_edge("init", "execute")
    builder.add_edge("execute", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()


def build_report_subgraph():
    """构建 Report 子图（v2：取数 -> EvidencePack -> 洞察/Todo -> 渲染）。

    流程：init -> execute -> analyze -> render_charts -> insights -> finalize -> END
    """
    builder = StateGraph(ReportState)

    builder.add_node("init", report_init)
    builder.add_node("execute", report_execute_tool)
    builder.add_node("analyze", report_build_evidence)
    builder.add_node("insights", report_generate_insights)
    builder.add_node("render", report_render_charts)
    builder.add_node("finalize", report_finalize)

    builder.add_edge(START, "init")
    builder.add_edge("init", "execute")
    # execute 失败（如 planning_failed）时直接 finalize，避免后续节点继续跑导致空数据/覆盖
    def _after_execute(state: ReportState):
        return "finalize" if state.get("tool_error") else "analyze"

    builder.add_conditional_edges(
        "execute",
        _after_execute,
        {"analyze": "analyze", "finalize": "finalize"},
    )
    builder.add_edge("analyze", "render")
    builder.add_edge("render", "insights")
    builder.add_edge("insights", "finalize")
    builder.add_edge("finalize", END)

    return builder.compile()


