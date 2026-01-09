import pytest

from agent import graph
from langchain_core.messages import HumanMessage
import os

pytestmark = pytest.mark.anyio


@pytest.mark.skipif(
    bool(os.getenv("LANGSMITH_API_KEY")) is False,
    reason="未配置 LANGSMITH_API_KEY，跳过 LangSmith 相关用例（避免 401）。",
)
async def test_agent_simple_passthrough() -> None:
    inputs = {
        "messages": [HumanMessage(content="如何在后台新建文章？")],
        # 关键：前端指定意图标签（统一口径），跳过意图识别
        "direct_intent": "rag",
    }
    res = await graph.ainvoke(inputs)
    assert res is not None
    assert "messages" in res
    # RAG 会落一条最终 AIMessage（mock）
    assert len(res["messages"]) >= 2


async def test_article_clarify_before_ui_when_missing_params() -> None:
    """不触发 interrupt：直接单测 parse 节点，验证缺参会进入澄清态。"""
    import agent.nodes.article as article_mod

    async def _fake_llm(user_text: str, collected: dict):  # type: ignore[no-untyped-def]
        return article_mod.ArticleClarifyResult(
            topic=None,
            content_format=None,
            target_audience=None,
            tone=None,
            missing=["topic", "content_format", "target_audience", "tone"],
            question_to_user="为了帮你生成文章，请补充：主题/内容格式/目标受众/语气。",
        )

    from pytest import MonkeyPatch

    mp = MonkeyPatch()
    mp.setattr(article_mod, "_llm_extract_and_question", _fake_llm)

    state = {
        "messages": [HumanMessage(content="生成一篇新闻")],
        "ui": [],
        "tenant_id": None,
        "site_id": None,
        "article_topic": None,
        "article_content_format": None,
        "article_target_audience": None,
        "article_tone": None,
        "article_clarify_input": None,
    }
    out = await article_mod.article_clarify_parse(state)  # type: ignore[arg-type]
    mp.undo()

    assert out["article_clarify_pending"] is True
    assert "article_missing" in out
    assert "article_clarify_question" in out
