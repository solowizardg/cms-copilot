"""Article 工具模块。"""

import inspect

from langchain_core.tools import tool
from langgraph_sdk import get_client

from agent.config import (
    ARTICLE_WORKFLOW_URL,
    ARTICLE_WORKFLOW_API_KEY,
    ARTICLE_ASSISTANT_ID,
)


async def call_cloud_article_workflow(
    input_data: dict, on_item=None, headers: dict | None = None
):
    """使用 langgraph_sdk 调用部署在 LangGraph Cloud 上的文章 workflow。"""
    if not ARTICLE_WORKFLOW_API_KEY:
        raise RuntimeError(
            "缺少 LangGraph Cloud API key，请设置环境变量 "
            "LANGGRAPH_CLOUD_API_KEY 或 LANGSMITH_API_KEY"
        )

    client = get_client(
        url=ARTICLE_WORKFLOW_URL, api_key=ARTICLE_WORKFLOW_API_KEY, headers=headers
    )
    print(f"[DEBUG] call_cloud_article_workflow: input_data = {input_data}")
    print(f"[DEBUG] call_cloud_article_workflow: headers = {headers}")
    thread = await client.threads.create()
    thread_id = thread["thread_id"]

    stream_results: list[dict] = []
    async for chunk in client.runs.stream(
        thread_id,
        ARTICLE_ASSISTANT_ID,
        input=input_data,
        stream_mode="updates",
    ):
        item = {
            "event": getattr(chunk, "event", None),
            "data": getattr(chunk, "data", None),
        }
        stream_results.append(item)
        if on_item is not None:
            maybe = on_item(item)
            if inspect.isawaitable(maybe):
                await maybe

    return stream_results


@tool
async def run_article_workflow(topic: str, site_id: str, locale: str = "zh-CN"):
    """为站点生成文章草稿。

    通过 langgraph_sdk 调用 Cloud 部署的 workflow。
    """
    input_data: dict = {
        "chat_type": "chat",
        "user_id": 1,
        "app_id": "64",
        "model_id": "93",
        "language": "中文",
        "human_prompt": topic,
        "topic": topic,
        "content_format": "新闻中心",
        "target_audience": "读者和投资者",
        "tone": "Professional",
    }

    return await call_cloud_article_workflow(input_data)
