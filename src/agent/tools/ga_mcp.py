"""GA MCP 工具封装（仅用于 Report）。

约束：
- Report 只能使用 GA MCP：`http://127.0.0.1:8001/mcp`
- Shortcut 只能使用 site-setting-basic（见 `src/agent/tools/mcp.py`）
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

GA_MCP_URL = "http://127.0.0.1:8001/mcp"


def _default_site_id(site_id: str | None) -> str:
    return str(
        site_id or os.getenv("CMS_SITE_ID") or "019b6d33-367c-7244-a6ae-af42b7f32090"
    )


def _default_tenant_id(tenant_id: str | None) -> str:
    return str(tenant_id or os.getenv("CMS_TENANT_ID") or "")


def _ensure_langchain_globals() -> None:
    """兼容旧版 langchain 缺少 debug/verbose 导致 tool.ainvoke 报错。"""
    try:
        import langchain  # type: ignore

        if not hasattr(langchain, "debug"):
            langchain.debug = False  # type: ignore[attr-defined]
        if not hasattr(langchain, "verbose"):
            langchain.verbose = False  # type: ignore[attr-defined]
    except Exception:
        return None


def _ga_headers(site_id: str | None, tenant_id: str | None) -> dict[str, str]:
    headers: dict[str, str] = {
        "Accept": "application/json, text/event-stream",
        "X-Site-Id": _default_site_id(site_id),
    }
    t_id = _default_tenant_id(tenant_id)
    if t_id:
        headers["X-Tenant-Id"] = t_id
    return headers


@dataclass(frozen=True)
class GAToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]


async def list_ga_tool_specs(
    *, site_id: str | None = None, tenant_id: str | None = None
) -> list[GAToolSpec]:
    """列出 GA MCP tools（用于 UI 展示）。"""
    _ensure_langchain_globals()
    client = MultiServerMCPClient(
        {
            "ga-report": {
                "url": GA_MCP_URL,
                "transport": "streamable_http",
                "headers": _ga_headers(site_id, tenant_id),
            }
        }
    )
    async with client.session("ga-report") as session:
        tools = await load_mcp_tools(session)
        specs: list[GAToolSpec] = []
        for t in tools:
            try:
                schema = (
                    t.args_schema.schema()  # type: ignore[union-attr]
                    if getattr(t, "args_schema", None)
                    else {}
                )
            except Exception:
                schema = {}
            specs.append(
                GAToolSpec(
                    name=t.name,
                    description=t.description or "",
                    input_schema=schema,
                )
            )
        return specs


async def call_ga_tool(
    *,
    tool_name: str,
    tool_input: dict[str, Any],
    site_id: str | None = None,
    tenant_id: str | None = None,
) -> Any:
    """调用 GA MCP 工具（每次调用建立一次会话，确保正确释放资源）。"""
    _ensure_langchain_globals()
    client = MultiServerMCPClient(
        {
            "ga-report": {
                "url": GA_MCP_URL,
                "transport": "streamable_http",
                "headers": _ga_headers(site_id, tenant_id),
            }
        }
    )
    async with client.session("ga-report") as session:
        tools = await load_mcp_tools(session)
        target = next((t for t in tools if t.name == tool_name), None)
        if target is None:
            raise RuntimeError(f"GA MCP 未找到工具: {tool_name}")
        return await target.ainvoke(tool_input)


async def with_ga_tools(
    *,
    site_id: str | None = None,
    tenant_id: str | None = None,
    fn,
) -> Any:
    """在同一个 MCP session 内加载 tools 并执行回调。

    适用于 ReAct：一次用户请求内连续调用多个工具，避免重复建连。
    """
    _ensure_langchain_globals()
    client = MultiServerMCPClient(
        {
            "ga-report": {
                "url": GA_MCP_URL,
                "transport": "streamable_http",
                "headers": _ga_headers(site_id, tenant_id),
            }
        }
    )
    async with client.session("ga-report") as session:
        tools = await load_mcp_tools(session)
        tools_by_name = {t.name: t for t in tools}
        return await fn(tools_by_name)


def normalize_ga_tool_result(res: Any) -> Any:
    """尽量把 tool 返回结果规整为可 JSON 序列化的对象。"""
    def _strip_keys(obj: Any) -> Any:
        """递归清理 key/value 两端空格（兼容部分返回中字段名带空格的情况）。"""
        if isinstance(obj, dict):
            out: dict[str, Any] = {}
            for k, v in obj.items():
                kk = k.strip() if isinstance(k, str) else str(k)
                vv = _strip_keys(v)
                # 对 GA schema 常见的 name/value 字段做额外 strip
                if kk in {"name", "value"} and isinstance(vv, str):
                    vv = vv.strip()
                out[kk] = vv
            return out
        if isinstance(obj, list):
            return [_strip_keys(x) for x in obj]
        if isinstance(obj, str):
            return obj.strip()
        return obj

    def _try_parse_json_text(text: str) -> Any:
        t = (text or "").strip()
        if not t:
            return t
        # 直接 JSON
        try:
            return json.loads(t)
        except Exception:
            pass
        # 尝试截取第一个 { 到最后一个 } 的片段
        l = t.find("{")
        r = t.rfind("}")
        if 0 <= l < r:
            try:
                return json.loads(t[l : r + 1])
            except Exception:
                return t
        return t

    # MCP/LC 常见：返回 list[{"type":"text","text":"{...}"}] 或 list[{"id":..,"type":"text","text":"{...}"}]
    if isinstance(res, list) and res:
        first = res[0]
        if isinstance(first, dict) and "text" in first and isinstance(first.get("text"), str):
            parsed = _try_parse_json_text(first.get("text") or "")
            return _strip_keys(parsed)
        # 如果是 list[str]，尝试解析第一段
        if isinstance(first, str):
            parsed = _try_parse_json_text(first)
            return _strip_keys(parsed)
        return _strip_keys(res)

    if isinstance(res, dict):
        return _strip_keys(res)

    if isinstance(res, str):
        parsed = _try_parse_json_text(res)
        return _strip_keys(parsed)

    if isinstance(res, (int, float, bool)) or res is None:
        return res

    return str(res)


