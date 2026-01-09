"""RAG 工具模块。"""

from langchain_core.tools import tool


@tool
def rag_query(question: str, tenant_id: str, site_id: str):
    """查询站点知识库，返回操作指引或说明（当前为 mock 实现）。"""
    return {
        "answer": f"【Mock RAG】站点 {site_id}（租户 {tenant_id}）的知识库回复：\n"
        f"针对问题「{question}」，请参考后台配置文档完成相应操作。",
        "citations": [
            {
                "title": "CMS 使用说明（Mock）",
                "url": "https://example.com/docs/cms/mock",
            }
        ],
    }
