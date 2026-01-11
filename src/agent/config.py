"""配置常量模块。

集中管理所有配置项，支持环境变量覆盖。
"""

import os

# ============ LangGraph Cloud 配置 ============

ARTICLE_WORKFLOW_URL = os.getenv(
    "ARTICLE_WORKFLOW_URL",
)

ARTICLE_WORKFLOW_API_KEY = os.getenv("ARTICLE_WORKFLOW_API_KEY") or os.getenv(
    "LANGCHAIN_API_KEY",
)

ARTICLE_ASSISTANT_ID = os.getenv("ARTICLE_ASSISTANT_ID", "multiple_graph")


# ============ LLM 配置 ============

LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini")
LLM_NANO_MODEL = os.getenv("LLM_NANO_MODEL", "gpt-4.1-nano")


# ============ MCP 配置 ============
# 注：MCP 工具列表现在通过 tools/list 从 MCP Server 动态获取，不再硬编码
MCP_SITE_SETTING_BASIC_URL = os.getenv(
    "MCP_SITE_SETTING_BASIC_URL"
)


# ============ Article（前端澄清 UI）配置 ============
def _csv_list(v: str) -> list[str]:
    return [x.strip() for x in (v or "").split(",") if x.strip()]


# Content style（用于前端澄清 UI 的下拉选项，可按需修改）
# 也可用环境变量覆盖：ARTICLE_CONTENT_STYLE_OPTIONS="Professional,活泼,严谨"
ARTICLE_CONTENT_STYLE_OPTIONS: list[str] = _csv_list(
    os.getenv(
        "ARTICLE_CONTENT_STYLE_OPTIONS",
        "Professional,严谨正式,活泼亲和,营销转化,科技理性,温暖故事感",
    )
)
