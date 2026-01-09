"""Article 澄清子图模块。

只负责“文章参数澄清”流程。
一旦澄清完成（article_clarify_pending=False），子图结束，控制权交回主图，
由主图继续执行 article_ui -> article_run（确保 UI 能即时 stream 显示）。
"""

from langgraph.graph import END, START, StateGraph

from agent.nodes.article import (
    article_clarify_parse,
    article_clarify_ui,
)
from agent.state import CopilotState


def build_article_subgraph():
    """构建 Article 澄清子图（不含 workflow UI）。"""
    builder = StateGraph(CopilotState)

    builder.add_node("clarify_parse", article_clarify_parse)
    builder.add_node("clarify_ui", article_clarify_ui)

    builder.add_edge(START, "clarify_parse")

    def _after_parse(state: CopilotState):
        # 如果 pending=True，去显示 UI；否则直接结束子图（去主图跑 workflow）
        return "clarify_ui" if state.get("article_clarify_pending") else END

    builder.add_conditional_edges(
        "clarify_parse",
        _after_parse,
        {"clarify_ui": "clarify_ui", END: END},
    )

    # ui 节点推送后结束本轮，等待用户输入（通过主图重新进入子图或继续）
    builder.add_edge("clarify_ui", END)

    return builder.compile(debug=True)


