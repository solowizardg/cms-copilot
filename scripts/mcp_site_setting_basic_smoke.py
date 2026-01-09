"""site-setting-basic MCP 冒烟脚本（本地调试用）。

用法（PowerShell）：
  python scripts/mcp_site_setting_basic_smoke.py --site-id 019a144c-... --tenant-id xxx

说明：
- 默认 URL 为 http://127.0.0.1:8000/mcp/site-setting-basic，可通过环境变量 MCP_SITE_SETTING_BASIC_URL 覆盖
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any

# 允许直接在源码仓库中运行：把 src/ 加进 PYTHONPATH
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from agent.tools.mcp import call_mcp  # noqa: E402


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--site-id", required=True)
    p.add_argument("--tenant-id", default="")
    p.add_argument(
        "--url",
        default=os.getenv(
            "MCP_SITE_SETTING_BASIC_URL", "http://127.0.0.1:8000/mcp/site-setting-basic"
        ),
        help="MCP Web endpoint",
    )
    p.add_argument(
        "--sections",
        default="business_information,contact_information",
        help="逗号分隔：business_information/contact_information",
    )
    return p.parse_args()


async def _main() -> dict[str, Any]:
    args = _parse_args()
    os.environ["MCP_SITE_SETTING_BASIC_URL"] = args.url
    sections = [s.strip() for s in (args.sections or "").split(",") if s.strip()]
    print(
        f"[smoke] site_id={args.site_id!r} tenant_id={args.tenant_id!r} url={args.url!r} sections={sections!r}"
    )
    return await call_mcp(
        "get_basic_detail",
        {"sections": sections} if sections else {},
        tenant_id=args.tenant_id,
        site_id=args.site_id,
    )


if __name__ == "__main__":
    try:
        print(asyncio.run(_main()))
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}")
