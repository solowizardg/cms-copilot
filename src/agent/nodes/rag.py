"""RAG 节点模块。

处理知识库查询请求。
"""

import asyncio

from langchain_core.messages import AIMessage, AIMessageChunk
from langgraph.config import get_stream_writer

from agent.state import CopilotState
from agent.tools.rag import rag_query


async def handle_rag(state: CopilotState) -> CopilotState:
    """处理 RAG 知识库查询。"""
    last = state["messages"][-1]

    # 提取用户问题
    raw_content = getattr(last, "content", last)
    if isinstance(raw_content, list):
        text_parts = []
        for part in raw_content:
            if isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part.get("text", ""))
            else:
                text_parts.append(str(part))
        question = "".join(text_parts)
    elif isinstance(raw_content, str):
        question = raw_content
    else:
        question = str(raw_content)

    tenant_id = state.get("tenant_id") or "mock-tenant"
    site_id = state.get("site_id") or "mock-site"

    rag_result = rag_query.invoke(
        {
            "question": question,
            "tenant_id": tenant_id,
            "site_id": site_id,
        }
    )

    base_answer = (
        rag_result.get("answer") if isinstance(rag_result, dict) else str(rag_result)
    )

    # 生成更长的 mock 文本（约 200+ 字），并用于模拟流式输出
    answer_text = (
        f"{base_answer}\n\n"
        + "下面是一个更详细的操作示例（模拟知识库答案，约 200 字）：\n"
        + f"1) 进入后台【内容管理】→【文章/新闻】列表，确认当前站点为 {site_id}。\n"
        + "2) 点击【新建】选择栏目与模板，填写标题与摘要；正文建议先用段落+小标题的结构。\n"
        + "3) 在【SEO】中补全 URL、关键词、描述，并检查是否启用站点地图/自动推送。\n"
        + "4) 预览页面确认图片与排版，再提交审核；审核通过后发布，并到【日志/统计】观察收录与点击。\n"
        + "如果你告诉我你卡在哪一步（例如权限、模板、发布失败或收录问题），我可以给出更针对性的排查路径。"
    )

    # 模拟流式输出
    writer = get_stream_writer()
    if writer is not None:
        chunk_size = 26
        for i in range(0, len(answer_text), chunk_size):
            piece = answer_text[i : i + chunk_size]
            writer({"messages": [AIMessageChunk(content=piece)]})
            await asyncio.sleep(0)

    # 落最终完整消息
    state["messages"].append(AIMessage(content=answer_text))
    return state
