"""Article 节点模块。

处理文章生成工作流。
"""

import json
import os
import uuid
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.config import get_stream_writer
from langgraph.graph.ui import AnyUIMessage, push_ui_message
from pydantic import BaseModel, Field

from agent.config import ARTICLE_CONTENT_STYLE_OPTIONS
from agent.state import CopilotState
from agent.tools.article import call_cloud_article_workflow
from agent.utils.helpers import find_ai_message_by_id, latest_user_message, message_text
from agent.utils.llm import llm_nostream


class ArticleClarifyResult(BaseModel):
    """LLM 输出：文章参数抽取 + 澄清问题。"""

    model_config = {"extra": "forbid"}

    topic: str | None = Field(
        default=None, description="文章主题/标题（中文，尽量具体）"
    )
    content_format: str | None = Field(
        default=None, description="内容格式/栏目（如：新闻中心/博客/产品动态）"
    )
    target_audience: str | None = Field(default=None, description="目标受众（中文）")
    tone: str | None = Field(default=None, description="语气/风格（如：Professional/活泼/严肃）")
    missing: list[str] = Field(
        default_factory=list,
        description="缺失的字段名列表，仅允许：topic/content_format/target_audience/tone",
    )
    question_to_user: str = Field(
        ...,
        description=(
            "当存在缺参时，给用户的澄清问题（中文，多行，包含推荐回复模板）；"
            "当不缺参时，可输出空字符串。"
        ),
    )


async def _llm_extract_and_question(
    user_text: str, collected: dict[str, str | None]
) -> ArticleClarifyResult:
    """依赖大模型从自然语言中抽取参数，并生成缺参澄清问题。"""
    prompt = f"""你是一个 CMS 文章生成助手的“参数补齐器”。

目标：从用户输入中提取文章生成所需的 4 个必要参数：
- topic（主题/标题）
- content_format（内容格式/栏目）
- target_audience（目标受众）
- tone（语气/风格）

你会收到：
1) 用户本轮输入 user_text
2) 历史已收集的参数 collected（可能为空）

要求：
1) 如果 user_text 或 collected 中已经明确提供了某些参数，请填入对应字段。
2) 对于不确定/缺失的参数，请把字段名加入 missing 列表。
3) 当 missing 非空时，输出 question_to_user：
   - 中文
   - 先简短说明需要补齐哪些信息
   - 然后给出推荐回复模板（key: value 形式），让用户一次性填完
4) 当 missing 为空时，question_to_user 输出空字符串。
5) missing 只能包含：topic/content_format/target_audience/tone（不要输出其它值）。

user_text：
{user_text}

collected（历史已收集，若无则为空）：
{json.dumps(collected, ensure_ascii=False)}
"""

    structured = llm_nostream.with_structured_output(ArticleClarifyResult)
    return await structured.ainvoke(
        [
            {"role": "system", "content": "只输出符合 schema 的结构化结果，不要输出多余文字。"},
            {"role": "user", "content": prompt},
        ]
    )


import re  # Added import

# ... (keep existing imports)

async def article_clarify_parse(state: CopilotState) -> dict[str, Any]:
    """文章澄清：解析用户补充内容（依赖大模型），更新已收集字段与缺失项。

    这个节点不负责推 UI；只负责把状态更新好，让后续 UI 节点渲染时能“自动带入”已填写内容。
    """
    # Generative UI 推荐使用 submit 继续对话：直接从最新用户消息解析
    user_msg = latest_user_message(state)
    user_text = message_text(user_msg)

    # 兼容前端用 submit 发送 JSON（更稳定）：先做一次合并，再交给 LLM 做最终抽取/补齐
    submit_payload: dict[str, Any] | None = None
    if isinstance(user_text, str):
        s = user_text.strip()
        # 1. 尝试直接解析 JSON（兼容旧版纯 JSON 发送）
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    submit_payload = obj
            except Exception:
                pass
        
        # 2. 尝试解析 "隐写" 在 HTML 注释里的 JSON（新版 UI：文本+隐藏JSON）
        #    例如: "... <!-- {"topic": "..."} -->"
        if not submit_payload:
            match = re.search(r"<!--\s*(\{.*?\})\s*-->", s, re.DOTALL)
            if match:
                try:
                    obj = json.loads(match.group(1))
                    if isinstance(obj, dict):
                        submit_payload = obj
                except Exception:
                    pass

    # 合并历史已收集的参数（支持多轮补齐）
    collected = {
        "topic": (state.get("article_topic") or "").strip(),
        "content_format": (state.get("article_content_format") or "").strip(),
        "target_audience": (state.get("article_target_audience") or "").strip(),
        "tone": (state.get("article_tone") or "").strip(),
    }

    # 如果 submit 传了结构化字段，先覆盖到 collected（空字符串不覆盖）
    if submit_payload:
        for k in ("topic", "content_format", "target_audience", "tone"):
            v = submit_payload.get(k)
            if isinstance(v, str) and v.strip():
                collected[k] = v.strip()

    # 依赖 LLM 抽取/判断缺参/生成澄清问题
    # 把 user_text 也传给 LLM：如果是 JSON，就传格式化后的 JSON，模型更容易理解
    user_text_for_llm = (
        json.dumps(submit_payload, ensure_ascii=False) if submit_payload else user_text
    )
    result = await _llm_extract_and_question(
        user_text=user_text_for_llm, collected=collected
    )

    # 合并 LLM 提取结果
    merged = {
        "topic": (result.topic or collected.get("topic") or "").strip(),
        "content_format": (result.content_format or collected.get("content_format") or "").strip(),
        "target_audience": (result.target_audience or collected.get("target_audience") or "").strip(),
        "tone": (result.tone or collected.get("tone") or "").strip(),
    }
    # 关键：不要完全相信模型的 missing（它可能“误判缺失”）。
    # 以合并后的真实字段值是否为空为准，确保用户已填写时能进入下一步。
    required_keys = ["topic", "content_format", "target_audience", "tone"]
    missing = [k for k in required_keys if not merged.get(k)]
    is_complete = len(missing) == 0

    if not is_complete:
        # 如果这是第一次进入澄清流程，则初始化 UI anchor / ui_id，便于后续 UI 节点 merge 更新
        ui_id = state.get("article_clarify_ui_id")
        anchor_id = state.get("article_clarify_anchor_id")
        out_messages: list[Any] = []
        if not ui_id:
            ui_id = str(uuid.uuid4())
        if not anchor_id:
            anchor_msg = AIMessage(id=str(uuid.uuid4()), content="")
            out_messages.append(anchor_msg)
            anchor_id = anchor_msg.id

        return {
            "messages": out_messages,
            "article_clarify_pending": True,
            "article_topic": merged.get("topic") or None,
            "article_content_format": merged.get("content_format") or None,
            "article_target_audience": merged.get("target_audience") or None,
            "article_tone": merged.get("tone") or None,
            "article_missing": missing,
            "article_clarify_question": (
                result.question_to_user
                or "请补充缺失信息：target_audience、tone（Content style）。"
            ),
            "article_clarify_ui_id": ui_id,
            "article_clarify_anchor_id": anchor_id,
        }

    return {
        "article_clarify_pending": False,
        "article_topic": merged["topic"],
        "article_content_format": merged["content_format"],
        "article_target_audience": merged["target_audience"],
        "article_tone": merged["tone"],
        "article_missing": [],
        "article_clarify_question": "",
    }


async def article_clarify_ui(state: CopilotState) -> dict[str, Any]:
    """文章澄清：专门负责渲染/推送澄清 UI（含预填 + Content style 下拉）。

    每次用户补充信息后，都会先经过 `article_clarify_parse` 更新 state，
    如果仍缺参，就会回到这里再次展示 UI，并自动带入已填写的答案。
    """
    ui_id = state.get("article_clarify_ui_id")
    anchor_id = state.get("article_clarify_anchor_id")
    anchor_msg = find_ai_message_by_id(state, anchor_id)
    if ui_id is None or anchor_msg is None:
        # 理论上 parse 节点已经初始化过；这里兜底防御
        ui_id = ui_id or str(uuid.uuid4())
        anchor_msg = anchor_msg or AIMessage(id=str(uuid.uuid4()), content="")

    missing = state.get("article_missing") or []
    question = state.get("article_clarify_question") or ""

    ui_props = {
        "status": "need_info",
        "missing": missing,
        "question": question,
        "topic": state.get("article_topic") or "",
        "content_format": state.get("article_content_format") or "",
        "target_audience": state.get("article_target_audience") or "",
        # Content style：这里复用 tone 字段承载（后续 workflow 也用 tone）
        "tone": state.get("article_tone") or "",
        "tone_options": ARTICLE_CONTENT_STYLE_OPTIONS,
    }

    # 推送 UI（merge 更新）
    try:
        ui_msg = push_ui_message(
            "article_clarify",
            ui_props,
            id=ui_id,
            message=anchor_msg,
            merge=True,
        )
        writer = get_stream_writer()
        if writer is not None:
            writer(ui_msg)
    except Exception:
        ui_msg = None

    # 不使用 interrupt：让自定义 UI 组件通过 useStreamContext().submit() 继续对话
    # 这样不会出现默认的 “需要人工处理 / resume” 面板。
    return {
        "article_clarify_pending": True,
    }


async def start_article_ui(state: CopilotState) -> dict[str, Any]:
    """先把文章 workflow 的进度卡片显示出来。"""
    user_msg = latest_user_message(state)
    _ = message_text(user_msg)  # 暂时不展示 topic

    ui_anchor_msg = AIMessage(id=str(uuid.uuid4()), content="")

    # 关键：必须先 stream anchor 消息，否则前端收到 UI 消息时找不到 anchor 会报错
    writer = None
    try:
        writer = get_stream_writer()
        if writer is not None:
            writer({"messages": [ui_anchor_msg]})
    except Exception as e:
        writer = None

    ui_msg_start = push_ui_message(
        "article_workflow",
        {
            "status": "running",
            "run_id": None,
            "thread_id": None,
            "current_node": None,
            "flow_node_list": [],
            "error_message": None,
        },
        message=ui_anchor_msg,
    )

    # 只通过 writer() 发送 UI，不要同时放到返回值的 ui 字段（避免冲突）
    if writer is not None:
        writer(ui_msg_start)

    # 注意：不返回 ui 字段，只通过 writer() 实时 stream
    # 但需要保存 ui_id 和 anchor_id 供后续节点更新 UI
    return {
        "messages": [ui_anchor_msg],
        "article_ui_id": ui_msg_start["id"],
        "article_anchor_id": ui_anchor_msg.id,
    }


async def handle_article(state: CopilotState) -> CopilotState:
    """处理文章生成工作流。"""
    user_msg = latest_user_message(state)
    topic = (state.get("article_topic") or "").strip() or message_text(user_msg)

    site_id = state.get("site_id") or "mock-site"

    ui_msg_id = state.get("article_ui_id")
    ui_anchor_msg = find_ai_message_by_id(state, state.get("article_anchor_id"))
    writer = get_stream_writer()

    if ui_anchor_msg is None or not ui_msg_id:
        ui_anchor_msg = AIMessage(id=str(uuid.uuid4()), content="")
        ui_msg_start = push_ui_message(
            "article_workflow",
            {
                "status": "running",
                "run_id": None,
                "thread_id": None,
                "current_node": None,
                "flow_node_list": [],
                "error_message": None,
            },
            message=ui_anchor_msg,
        )
        ui_msg_id = ui_msg_start["id"]
        state["messages"].append(ui_anchor_msg)
        state["ui"] = list(state.get("ui") or []) + [ui_msg_start]

    flow_node_list: list[dict] = []
    current_node: str | None = None
    run_id: str | None = None
    thread_id: str | None = None
    error_message: str | None = None
    last_ui_msg: AnyUIMessage | None = None

    def _find_flow_progress(obj):
        if isinstance(obj, dict):
            fp = obj.get("flow_progress")
            if isinstance(fp, dict):
                return fp
            for v in obj.values():
                found = _find_flow_progress(v)
                if found is not None:
                    return found
        elif isinstance(obj, list):
            for v in obj:
                found = _find_flow_progress(v)
                if found is not None:
                    return found
        return None

    def _finalize_flow_nodes_for_done(nodes: list[dict]) -> list[dict]:
        finalized: list[dict] = []
        for n in nodes:
            if not isinstance(n, dict):
                continue
            node_status = (n.get("node_status") or "").upper()
            if node_status in {"FAILED", "ERROR"}:
                new_status = node_status
            else:
                new_status = "SUCCESS"
            nn = dict(n)
            nn["node_status"] = new_status
            finalized.append(nn)

        if not any(
            (x.get("node_code") == "__completed__")
            for x in finalized
            if isinstance(x, dict)
        ):
            finalized.append(
                {
                    "node_code": "__completed__",
                    "node_name": "Workflow completed",
                    "node_status": "SUCCESS",
                    "node_message": "文章工作流已执行完成。",
                }
            )
        return finalized

    def _merge_ui(status: str):
        nonlocal last_ui_msg, current_node, flow_node_list
        payload_flow_nodes = flow_node_list
        payload_current_node = current_node
        if status == "done":
            payload_flow_nodes = _finalize_flow_nodes_for_done(flow_node_list)
            payload_current_node = "__completed__"
            flow_node_list = payload_flow_nodes
            current_node = payload_current_node

        ui_msg = push_ui_message(
            "article_workflow",
            {
                "status": status,
                "run_id": run_id,
                "thread_id": thread_id,
                "current_node": payload_current_node,
                "flow_node_list": payload_flow_nodes,
                "error_message": error_message,
            },
            id=ui_msg_id,
            message=ui_anchor_msg,
            merge=True,
        )
        last_ui_msg = ui_msg
        if writer is not None:
            writer(ui_msg)

    try:
        workflow_headers = {
            "X-Site-Id": str(
                state.get("site_id")
                or os.getenv("CMS_SITE_ID")
                or "019a104d-98e9-7298-8be1-af1926bbc085"
            ),
            "X-Tenant-Id": str(
                state.get("tenant_id") or os.getenv("CMS_TENANT_ID") or "1234567890"
            ),
            "X-Site-Host": str(
                os.getenv("CMS_SITE_HOST", "https://site-dev.cedemo.cn/api")
            ),
        }

        input_data: dict = {
            "chat_type": "chat",
            "user_id": 1,
            "app_id": "57",
            "model_id": "76",
            "language": "中文",
            "human_prompt": topic,
            "topic": topic,
            "content_format": state.get("article_content_format") or "新闻中心",
            "target_audience": state.get("article_target_audience") or "读者和投资者",
            "tone": state.get("article_tone") or "Professional",
        }

        async def _on_item(item: dict):
            nonlocal run_id, thread_id, current_node, flow_node_list, error_message
            event = item.get("event")
            data = item.get("data") or {}

            if event == "metadata":
                run_id = data.get("run_id") or run_id
                _merge_ui("running")
                return

            if event == "updates":
                fp = _find_flow_progress(data)
                if isinstance(fp, dict):
                    maybe_list = fp.get("flow_node_list")
                    if isinstance(maybe_list, list):
                        flow_node_list = maybe_list
                    cn = fp.get("current_node")
                    if isinstance(cn, str):
                        current_node = cn
                if isinstance(data, dict):
                    for v in data.values():
                        if isinstance(v, dict):
                            thread_id = v.get("thread_id") or thread_id
                            run_id = v.get("run_id") or run_id
                _merge_ui("running")
                return

            if event == "error":
                msg = (
                    data.get("message")
                    or data.get("error")
                    or json.dumps(data, ensure_ascii=False)
                )
                error_message = str(msg)
                _merge_ui("error")

        _ = await call_cloud_article_workflow(
            input_data, on_item=_on_item, headers=workflow_headers
        )

    except Exception as exc:
        error_message = str(exc)
        _merge_ui("error")
        return state

    if error_message:
        return state

    _merge_ui("done")
    if last_ui_msg is not None:
        state["ui"] = list(state.get("ui") or []) + [last_ui_msg]
    return state
