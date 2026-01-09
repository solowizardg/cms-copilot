"""SEO 工具模块。

提供 SEO 快照数据读取等功能。
"""

from typing import Literal

from langchain_core.tools import tool
from pydantic import BaseModel, Field

# ============ Pydantic 模型定义 ============


class SEOTaskEvidence(BaseModel):
    """任务证据项"""

    model_config = {"extra": "forbid"}

    evidence_path: str = Field(
        ...,
        description="快照中的字段路径，如 crawl_indexing.sitemaps[0].lastmod_coverage_ratio",
    )
    value_summary: str = Field(..., max_length=120, description="当前值的摘要说明")


class SEOTaskParams(BaseModel):
    """工作流参数"""

    model_config = {"extra": "forbid"}

    url: str | None = Field(default=None, description="目标页面 URL")
    urls: list[str] | None = Field(default=None, description="目标页面 URL 列表")
    issue_type: str | None = Field(default=None, description="问题类型标识")
    query: str | None = Field(default=None, description="搜索查询词")
    topic: str | None = Field(default=None, description="内容主题")
    target_metric: str | None = Field(default=None, description="目标指标名称")


class SEOTask(BaseModel):
    """SEO 周任务项"""

    model_config = {"extra": "forbid"}

    date: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="任务日期，格式 YYYY-MM-DD"
    )
    day_of_week: Literal["Mon", "Tue", "Wed", "Thu", "Fri"] = Field(
        ..., description="星期几（仅工作日）"
    )
    category: Literal[
        "Indexing", "OnPage", "Performance", "Content", "StructuredData"
    ] = Field(..., description="任务类别")
    issue_type: str = Field(..., description="问题类型标识，如 ONPAGE_MISSING_TITLE")
    title: str = Field(..., max_length=26, description="任务标题，中文，不超过26字")
    description: str = Field(..., max_length=120, description="任务描述，中文1~2句")
    impact: int = Field(..., ge=1, le=5, description="影响程度，1-5分")
    difficulty: int = Field(..., ge=1, le=5, description="执行难度，1-5分")
    severity: Literal["critical", "warning", "notice"] = Field(
        ..., description="严重程度"
    )
    requires_manual_confirmation: bool = Field(
        ...,
        description="是否需要人工确认（会改站点配置/页面内容/发布的任务需要为 true）",
    )
    workflow_id: str = Field(..., description="关联的工作流 ID")
    params: SEOTaskParams = Field(
        default_factory=SEOTaskParams, description="工作流参数"
    )
    evidence: list[SEOTaskEvidence] = Field(
        ..., min_length=1, max_length=4, description="任务证据列表"
    )
    fix_action: Literal["article", "link", "none"] = Field(
        default="none",
        description="修复动作类型：article=调用文章生成流程，link=跳转链接，none=暂无",
    )
    fix_prompt: str | None = Field(
        default=None,
        max_length=200,
        description="完整的内容生成需求描述（用于 article 类型），如：针对'耳机 风噪 抑制'关键词，创建专题博客内容。",
    )


class SEOWeeklyPlan(BaseModel):
    """SEO 周任务计划"""

    model_config = {"extra": "forbid"}

    site_id: str = Field(..., description="站点 ID")
    week_start: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="周起始日期，格式 YYYY-MM-DD"
    )
    week_end: str = Field(
        ..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="周结束日期，格式 YYYY-MM-DD"
    )
    tasks: list[SEOTask] = Field(
        ...,
        min_length=3,
        max_length=5,
        description="任务列表，3~5条（工作日，每天最多1条）",
    )


# Mock SEO 快照数据
MOCK_SEO_SNAPSHOT = {
    "semrush": {
        "keyword_gap": {
            "updated_at": "2025-12-23T18:50:00Z",
            "you": "demo-shop.example.com",
            "competitors": [
                "competitor-a.example.com",
                "competitor-b.example.com",
                "competitor-c.example.com",
            ],
            "keyword_types": ["missing", "untapped"],
            "missing": [
                {
                    "keyword": "蓝牙耳机 续航 测试",
                    "volume": 2900,
                    "kd": 44,
                    "intent": "informational",
                    "top_competitor": "competitor-a.example.com",
                    "top_competitor_url": "https://competitor-a.example.com/blog/battery-test-guide",
                    "note": "竞争对手有排名，你站点无排名",
                },
                {
                    "keyword": "耳机 风噪 抑制",
                    "volume": 1600,
                    "kd": 37,
                    "intent": "informational",
                    "top_competitor": "competitor-b.example.com",
                    "top_competitor_url": "https://competitor-b.example.com/noise/wind-noise",
                    "note": "竞争对手有排名，你站点无排名",
                },
            ],
            "untapped": [
                {
                    "keyword": "65w 氮化镓 充电器 选购",
                    "volume": 2400,
                    "kd": 39,
                    "intent": "commercial",
                    "top_competitor": "competitor-c.example.com",
                    "top_competitor_url": "https://competitor-c.example.com/blog/gan-65w-buying-guide",
                    "note": "至少一个竞争对手有排名，你站点无排名",
                }
            ],
        }
    },
    "keyword_coverage": {
        "updated_at": "2025-12-23T19:10:00Z",
        "matching_method": "title_or_h1_or_primary_keyword_tag",
        "by_keyword": [
            {
                "keyword": "蓝牙耳机 续航",
                "status": "covered",
                "mapped_url": "https://demo-shop.example.com/products/earbuds-x1",
                "confidence": 0.84,
                "evidence_path": "semrush.on_page_seo_checker.targets[0].target_keyword",
            },
            {
                "keyword": "蓝牙耳机 续航 测试",
                "status": "no_content_page",
                "mapped_url": None,
                "confidence": 0.92,
                "suggested_content_type": "blog_post",
                "suggested_slug": "/blog/earbuds-battery-test",
                "evidence_path": "semrush.keyword_gap.missing[0]",
            },
            {
                "keyword": "耳机 风噪 抑制",
                "status": "no_content_page",
                "mapped_url": None,
                "confidence": 0.90,
                "suggested_content_type": "blog_post",
                "suggested_slug": "/blog/wind-noise-reduction",
                "evidence_path": "semrush.keyword_gap.missing[1]",
            },
            {
                "keyword": "65w 氮化镓 充电器 选购",
                "status": "weak_coverage",
                "mapped_url": "https://demo-shop.example.com/products/gan-charger-65w",
                "confidence": 0.62,
                "reason": "只有产品页，缺少选购指南类内容承接长尾词",
                "evidence_path": "semrush.keyword_gap.untapped[0]",
            },
        ],
        "summary": {"covered": 1, "weak_coverage": 1, "no_content_page": 2},
    },
    "issues": {
        "summary": [
            {
                "issue_type": "CONTENT_KEYWORD_NO_PAGE",
                "category": "Content",
                "severity": "notice",
                "count": 2,
                "top_examples": [
                    {
                        "url": "(new) https://demo-shop.example.com/blog/earbuds-battery-test",
                        "evidence_path": "keyword_coverage.by_keyword[1]",
                    },
                    {
                        "url": "(new) https://demo-shop.example.com/blog/wind-noise-reduction",
                        "evidence_path": "keyword_coverage.by_keyword[2]",
                    },
                ],
            }
        ]
    },
}


@tool
async def get_seo_snapshot(site_id: str | None = None) -> dict:
    """获取站点的 SEO 快照数据。

    返回包含索引状态、页面 SEO、性能指标、内容分析和结构化数据的完整快照。

    Args:
        site_id: 可选的站点 ID，不提供则返回默认 mock 数据。

    Returns:
        SEO 快照数据字典，包含 crawl_indexing、on_page、performance、content、structured_data 等字段。
    """
    import asyncio
    import random

    # 模拟数据读取延迟 1~2 秒
    await asyncio.sleep(random.uniform(1.0, 2.0))

    # TODO: 实际实现时，这里应该调用真实的 SEO 数据服务
    # 目前返回 mock 数据
    snapshot = MOCK_SEO_SNAPSHOT.copy()

    if site_id:
        snapshot["site_id"] = site_id
    return snapshot


# SEO 周任务规划的系统提示词
SEO_PLANNER_SYSTEM_PROMPT = """你是“CMS Copilot 的 SEO 周任务规划器”。你的工作是：根据输入的 SEO 快照数据（seo_snapshot_v1），生成未来 7 天的 SEO 任务列表（仅生成列表，不执行任何动作）。

【输入说明】
- 数据来源仅包含：
  1) Google PageSpeed Insights（基于 Lighthouse 的实验室数据与分类得分）
  2) Semrush（Site Audit + On Page SEO Checker）
- 不包含 Search Console 数据，因此内容类任务必须基于 Semrush 的关键词/页面机会与 On Page 建议来生成。

【输出要求】
- 只输出严格 JSON（不要 Markdown、不要解释文字、不要多余字段）。
- 输出必须符合下面给出的 JSON Schema。
- 每条任务要可点击跳转到 Copilot 工作流：用 workflow_id + params 表达。
- 每条任务必须包含 evidence（证据），证据使用快照中的字段路径（evidence_path）并给出当前值的摘要。
- 任务标题 title：中文，<= 26 个字；description：中文 1~2 句。
- 风险标记：任何“会改站点配置/页面内容/发布”的任务，requires_manual_confirmation=true；纯检查/分析类可为 false。

【排期与配额】
- 输出覆盖 7 天：从 week_start 到 week_end（包含起止日期），每天 0~2 条任务。
- 总任务数：6~10 条。
- 必须至少覆盖 3 个类别：Indexing、OnPage、Performance、Content、StructuredData 中任意 3 类。
- 优先级排序规则（从高到低）：
  1) Indexing 基础设施/抓取阻塞（4xx/robots/sitemap/大量重定向链/死链等，主要来自 Semrush Site Audit）
  2) OnPage 的高影响低难度（缺 Title/Desc/H1、重复 meta、canonical 异常等）
  3) Performance 的关键指标劣化（LCP/INP/CLS 或 Lighthouse performance 分数很低）
  4) Content 机会（Semrush 关键词机会、On Page SEO Checker 的语义/内容长度/可读性建议等）
- 去重：同一 url 同一 issue_type 本周最多出现一次。

【重要SEO常识（用于推理）】
- PSI 返回 Lighthouse 分类分数（Performance/SEO 等）以及关键性能诊断；本任务用其判断“性能类”任务优先级。
- Semrush Site Audit 的 Errors/Warnings/Notices 代表严重程度层级；优先处理 Errors，再处理 Warnings。
- On Page SEO Checker 提供结构化的优化行动清单；适合生成“页面级可执行任务”。

【开始工作】
读入用户提供的 seo_snapshot_v1 JSON，按上述规则输出周任务 JSON。
"""
