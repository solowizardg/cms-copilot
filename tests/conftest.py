import pytest
import sys
from pathlib import Path


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# 让 tests 可以直接 import src 下的模块（兼容 `from agent import graph`）
SRC_DIR = (Path(__file__).resolve().parents[1] / "src").as_posix()
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)


# 兼容某些环境下 langchain/langchain_core 版本不匹配导致的属性缺失
try:  # pragma: no cover
    import langchain  # type: ignore

    if not hasattr(langchain, "debug"):
        langchain.debug = False  # type: ignore[attr-defined]
    if not hasattr(langchain, "verbose"):
        langchain.verbose = False  # type: ignore[attr-defined]
except Exception:
    pass
