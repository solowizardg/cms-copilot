"""状态定义模块。

定义主图和子图的状态类型。
"""

from typing import Any, Sequence

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.graph.ui import AnyUIMessage, ui_message_reducer
from typing_extensions import Annotated, TypedDict


class CopilotState(TypedDict):
    """主图状态。"""

    # 消息列表
    messages: Annotated[Sequence[BaseMessage], add_messages]
    # UI 消息列表（Generative UI）
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]
    # 意图识别结果
    intent: str | None
    intent_ui_id: str | None
    intent_started_at: float | None
    # 文章工作流
    article_ui_id: str | None
    article_anchor_id: str | None
    # SEO 规划工作流
    seo_ui_id: str | None
    seo_anchor_id: str | None
    # 站点报告工作流
    report_ui_id: str | None
    report_anchor_id: str | None
    report_progress_ui_id: str | None
    report_charts_ui_id: str | None
    report_insights_ui_id: str | None
    # 租户信息
    tenant_id: str | None
    site_id: str | None
    # entry 节点设置的跳转目标
    resume_target: str | None
    # 直接指定意图（跳过意图识别）
    direct_intent: str | None
    # ============ 文章澄清流程（article_clarify）===========
    article_clarify_pending: bool | None
    article_topic: str | None
    article_content_format: str | None
    article_target_audience: str | None
    article_tone: str | None
    article_missing: list[str] | None
    article_clarify_question: str | None
    article_clarify_ui_id: str | None
    article_clarify_anchor_id: str | None


class ShortcutState(TypedDict):
    """Shortcut 子图状态。

    与父图共享 messages/ui 字段，子图会自动继承父图的 checkpointer。
    """

    # 与父图共享的字段
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]
    tenant_id: str | None
    site_id: str | None
    # 子图专属字段
    user_text: str | None  # 用户输入
    options: list[dict[str, Any]] | None  # 可选操作列表
    recommended: str | None  # LLM 推荐的操作 code
    selected: dict[str, Any] | None  # 用户选择的操作
    # MCP 工具调用相关
    mcp_params: dict[str, Any] | None  # LLM 提取的工具参数
    result: str | None  # 执行结果
    error: str | None  # 错误信息
    confirmed: bool | None  # 用户是否确认
    no_tool_selected: bool | None  # LLM 没有选择工具（直接输出回复）
    ui_anchor_id: str | None  # UI 锚点 message id
    ui_id: str | None  # UI 卡片 id


class ReportState(TypedDict):
    """Report 子图状态。

    用于生成站点统计报告的工作流状态。
    """

    # 与父图共享的字段
    messages: Annotated[Sequence[BaseMessage], add_messages]
    ui: Annotated[Sequence[AnyUIMessage], ui_message_reducer]
    tenant_id: str | None
    site_id: str | None
    # 从父图传递的 UI 相关字段
    report_ui_id: str | None  # 父图传递的 UI ID
    report_anchor_id: str | None  # 父图传递的锚点 ID
    report_progress_ui_id: str | None
    report_charts_ui_id: str | None
    report_insights_ui_id: str | None
    # 子图专属字段
    user_text: str | None  # 用户输入
    current_step: str | None  # 当前步骤
    report_type: str | None  # 报告类型：overview/traffic/content/engagement/performance
    report_type_name: str | None  # 报告类型中文名
    period: dict[str, Any] | None  # 报告周期
    # 各维度数据
    traffic_data: dict[str, Any] | None  # 流量趋势数据（图表格式）
    traffic_sources: dict[str, Any] | None  # 流量来源分布（图表格式）
    top_pages: dict[str, Any] | None  # 热门页面（图表格式）
    content_stats: dict[str, Any] | None  # 内容统计
    device_stats: dict[str, Any] | None  # 设备分布（图表格式）
    user_engagement: dict[str, Any] | None  # 用户互动（图表格式）
    performance: dict[str, Any] | None  # 性能指标
    summary: dict[str, Any] | None  # 汇总指标
    report_data: dict[str, Any] | None  # 最终报告数据
    # ============ 洞察层（Report v2）===========
    evidence_pack: dict[str, Any] | None  # 证据包（纯代码生成，可证明事实）
    data_quality: dict[str, Any] | None  # 数据质量提示（阈值/缺失口径/样本不足等）
    insights: dict[str, Any] | None  # 解读（one-liner/evidence/hypotheses）
    actions: list[dict[str, Any]] | None  # 建议动作（仅展示，不触发）
    todos: list[dict[str, Any]] | None  # 可执行 Todo（写入 state，仅展示）
    trace: dict[str, Any] | None  # 洞察轨迹（引用 todo 步骤）
    step_outputs: list[dict[str, Any]] | None  # 洞察逐步产出（对应 todo 步骤）
    # ============ MCP 动态工具调用（Report 新流程）===========
    options: list[dict[str, Any]] | None  # 可选工具列表（UI 展示）
    tool_specs: list[Any] | None  # MCP 工具详细规格（GAToolSpec 列表）
    recommended: str | None  # 推荐工具名
    selected: dict[str, Any] | None  # 用户/LLM 选择的工具
    mcp_params: dict[str, Any] | None  # LLM/用户确认的参数
    tool_result: Any | None  # 工具原始结果（已尽量规整）
    tool_error: str | None  # 工具执行错误
    confirmed: bool | None  # 是否确认执行
    error: str | None  # 错误信息
    # UI 相关（子图内部使用）
    ui_anchor_id: str | None  # UI 锚点 message id
    ui_id: str | None  # UI 卡片 id
