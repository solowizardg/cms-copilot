"""MCP Client 模块 — 使用 langchain-mcp-adapters。

基于官方 langchain-mcp-adapters 库连接 MCP Server：
- 自动处理 initialize → notifications/initialized → tools/list
- 自动将 MCP 的 JSON Schema 转换为 LangChain Tool
- 返回的 tools 可直接用于 llm.bind_tools()
"""

from __future__ import annotations

import inspect
import os
from typing import Any

from langchain_mcp_adapters.client import MultiServerMCPClient

from agent.config import MCP_SITE_SETTING_BASIC_URL


def _mcp_debug_enabled() -> bool:
    """检查是否启用 MCP 调试日志。"""
    return os.getenv("MCP_DEBUG", "0") in {
        "1",
        "true",
        "True",
        "yes",
        "YES",
        "on",
        "ON",
    }


def _default_site_id(site_id: str | None) -> str:
    """获取默认 site_id。"""
    return str(
        site_id or os.getenv("CMS_SITE_ID") or "019b6d33-367c-7244-a6ae-af42b7f32090"
    )


def _default_tenant_id(tenant_id: str | None) -> str:
    """获取默认 tenant_id。"""
    return str(tenant_id or os.getenv("CMS_TENANT_ID") or "")


def _create_mcp_client(
    tenant_id: str | None = None,
    site_id: str | None = None,
) -> MultiServerMCPClient:
    """创建 MCP Client 实例。

    Args:
        tenant_id: 租户 ID
        site_id: 站点 ID（UUID）

    Returns:
        MultiServerMCPClient 实例
    """
    t_id = _default_tenant_id(tenant_id)
    s_id = _default_site_id(site_id)

    headers = {"X-Site-Id": s_id}
    if t_id:
        headers["X-Tenant-Id"] = t_id

    if _mcp_debug_enabled():
        print(
            f"[MCP] Creating client for {MCP_SITE_SETTING_BASIC_URL} with headers={headers}"
        )

    return MultiServerMCPClient(
        {
            "site-setting-basic": {
                "url": MCP_SITE_SETTING_BASIC_URL,
                "transport": "streamable_http",
                "headers": headers,
            }
        }
    )


async def get_mcp_tools(
    tenant_id: str | None = None,
    site_id: str | None = None,
) -> list[Any]:
    """获取 MCP Server 提供的工具列表（LangChain Tool 格式）。

    Returns:
        LangChain Tool 列表，可直接用于 llm.bind_tools()
    """
    client = _create_mcp_client(tenant_id=tenant_id, site_id=site_id)
    tools = client.get_tools()
    if inspect.isawaitable(tools):
        tools = await tools

    if _mcp_debug_enabled():
        print(f"[MCP] Got {len(tools)} tools from MCP Server:")
        for tool in tools:
            desc = tool.description[:50] if tool.description else ""
            print(f"  - {tool.name}: {desc}...")

    return tools


async def call_mcp_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    tenant_id: str | None = None,
    site_id: str | None = None,
) -> Any:
    """调用 MCP 工具。

    Args:
        tool_name: 工具名称（如 get_basic_detail、save_basic_detail）
        tool_input: 工具输入参数
        tenant_id: 租户 ID
        site_id: 站点 ID

    Returns:
        工具执行结果
    """
    if _mcp_debug_enabled():
        print(f"[MCP][call] tool={tool_name!r} input={tool_input!r}")

    client = _create_mcp_client(tenant_id=tenant_id, site_id=site_id)
    tools = client.get_tools()
    if inspect.isawaitable(tools):
        tools = await tools

    # 找到对应的工具
    target_tool = None
    for tool in tools:
        if tool.name == tool_name:
            target_tool = tool
            break

    if not target_tool:
        return {"success": False, "error": f"未找到工具: {tool_name}"}

    # 调用工具
    result = await target_tool.ainvoke(tool_input)

    if _mcp_debug_enabled():
        print(f"[MCP][result] {result!r}")

    return result


# ============ 兼容旧接口（逐步废弃） ============


async def list_mcp_tools(
    tenant_id: str | None = None,
    site_id: str | None = None,
) -> list[dict[str, Any]]:
    """获取 MCP 工具列表（返回原始 dict 格式，兼容旧代码）。

    注意：推荐使用 get_mcp_tools() 获取 LangChain Tool 格式。
    """
    tools = await get_mcp_tools(tenant_id=tenant_id, site_id=site_id)
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "inputSchema": tool.args_schema.schema()
            if hasattr(tool, "args_schema") and tool.args_schema
            else {},
        }
        for tool in tools
    ]


async def call_mcp(
    method: str,
    params: dict[str, Any],
    tenant_id: str | None = None,
    site_id: str | None = None,
) -> dict[str, Any]:
    """调用 MCP 服务（兼容旧接口）。

    注意：推荐使用 call_mcp_tool()。
    """
    result = await call_mcp_tool(
        tool_name=method,
        tool_input=params,
        tenant_id=tenant_id,
        site_id=site_id,
    )
    # 尝试解析结果
    if isinstance(result, dict):
        return result
    if isinstance(result, str):
        # MCP 返回的可能是 JSON 字符串
        import json

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"success": True, "message": result}

    return {"success": True, "data": result}
