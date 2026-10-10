"""gwp.ai：可插拔 AI 层。

对外只需要认识 :class:`AIManager`（选择/兜底）、:class:`Summarizer`（生成 summary）、
:class:`ChatSession`（聊天记录）与 :class:`AIWorker`（后台线程）。

这里使用惰性导入：``AIWorker`` 依赖 PyQt6，但 AI 的核心逻辑不依赖，
因此纯命令行场景（例如批量生成总结）不需要加载 Qt。
"""

from __future__ import annotations

import importlib
from typing import Any

_EXPORTS = {
    "AIManager": ("gwp.ai.manager", "AIManager"),
    "ChatSession": ("gwp.ai.chat_session", "ChatSession"),
    "ChatStore": ("gwp.ai.chat_session", "ChatStore"),
    "session_key": ("gwp.ai.chat_session", "session_key"),
    "Summarizer": ("gwp.ai.summarizer", "Summarizer"),
    "SummaryMaterial": ("gwp.ai.summarizer", "SummaryMaterial"),
    "SummaryResult": ("gwp.ai.summarizer", "SummaryResult"),
    "ProgressEvent": ("gwp.ai.summarizer", "ProgressEvent"),
    "AIWorker": ("gwp.ai.worker", "AIWorker"),
    "SimpleWorker": ("gwp.ai.worker", "SimpleWorker"),
    "AIError": ("gwp.ai.types", "AIError"),
    "AIConfigError": ("gwp.ai.types", "AIConfigError"),
    "AINetworkError": ("gwp.ai.types", "AINetworkError"),
    "AIAuthError": ("gwp.ai.types", "AIAuthError"),
    "AIRateLimitError": ("gwp.ai.types", "AIRateLimitError"),
    "AIUnavailableError": ("gwp.ai.types", "AIUnavailableError"),
    "AiQuestion": ("gwp.ai.types", "AiQuestion"),
    "ChatCancelled": ("gwp.ai.types", "ChatCancelled"),
    "ChatMessage": ("gwp.ai.types", "ChatMessage"),
    "ChatOptions": ("gwp.ai.types", "ChatOptions"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:  # PEP 562
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    module = importlib.import_module(module_name)
    value = getattr(module, attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
