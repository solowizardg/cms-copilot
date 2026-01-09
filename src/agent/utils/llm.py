"""LLM 实例模块。

提供预配置的 LLM 实例。
"""

from __future__ import annotations

from typing import Any, Optional

try:
    from langchain_openai import ChatOpenAI  # type: ignore
except Exception:  # pragma: no cover
    ChatOpenAI = None  # type: ignore[assignment]

from agent.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_NANO_MODEL

def _require_chat_openai() -> Any:
    if ChatOpenAI is None:
        raise ImportError(
            "LLM 依赖未安装或版本不兼容：无法导入 `langchain_openai.ChatOpenAI`。"
        )
    return ChatOpenAI


def _make_llm(model: str, *, disable_streaming: bool = False) -> Any:
    Chat = _require_chat_openai()
    return Chat(
        model=model,
        temperature=0,
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        disable_streaming=disable_streaming,
    )


# 注意：不要在 import 时就强制初始化 LLM（会导致依赖/环境问题直接炸 import）
_llm: Optional[Any] = None
_llm_nostream: Optional[Any] = None
_llm_nano: Optional[Any] = None
_llm_nano_nostream: Optional[Any] = None


def get_llm() -> Any:
    global _llm
    if _llm is None:
        _llm = _make_llm(LLM_MODEL, disable_streaming=False)
    return _llm


def get_llm_nostream() -> Any:
    global _llm_nostream
    if _llm_nostream is None:
        _llm_nostream = _make_llm(LLM_MODEL, disable_streaming=True)
    return _llm_nostream


def get_llm_nano() -> Any:
    global _llm_nano
    if _llm_nano is None:
        _llm_nano = _make_llm(LLM_NANO_MODEL, disable_streaming=False)
    return _llm_nano


def get_llm_nano_nostream() -> Any:
    global _llm_nano_nostream
    if _llm_nano_nostream is None:
        _llm_nano_nostream = _make_llm(LLM_NANO_MODEL, disable_streaming=True)
    return _llm_nano_nostream


# 向后兼容：保留原变量名（按需惰性初始化）
class _LazyLLM:
    def __init__(self, getter):
        self._getter = getter

    def __getattr__(self, item):
        return getattr(self._getter(), item)

    def __call__(self, *args, **kwargs):
        return self._getter()(*args, **kwargs)


llm = _LazyLLM(get_llm)
llm_nostream = _LazyLLM(get_llm_nostream)
llm_nano = _LazyLLM(get_llm_nano)
llm_nano_nostream = _LazyLLM(get_llm_nano_nostream)
