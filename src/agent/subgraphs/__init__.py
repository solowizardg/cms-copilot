"""子图模块。"""

from agent.subgraphs.article import build_article_subgraph
from agent.subgraphs.report import build_report_subgraph
from agent.subgraphs.shortcut import build_shortcut_subgraph

__all__ = ["build_article_subgraph", "build_shortcut_subgraph", "build_report_subgraph"]
