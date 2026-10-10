"""轻量事件总线：让数据层与界面层解耦。

界面控件只订阅事件名，不直接依赖数据管理器；数据层只发事件，不认识界面。
新增功能时不需要改动已有模块，符合“模块化、易扩展”的要求。
"""

from __future__ import annotations

import logging
import threading
from collections import defaultdict
from typing import Any, Callable

log = logging.getLogger(__name__)

#: 事件名常量（新增事件在此登记，避免拼写错误）
SUBJECTS_CHANGED = "subjects_changed"          # 科目列表增删改
BOOKS_CHANGED = "books_changed"                # 书目列表增删改
BOOK_CONTENT_CHANGED = "book_content_changed"  # 书目内文件变化
SUMMARY_UPDATED = "summary_updated"            # summary 重新生成
SUMMARY_BACKUP_RESTORED = "summary_backup_restored"
AI_PROVIDER_CHANGED = "ai_provider_changed"
AI_FALLBACK = "ai_fallback"                    # 主 AI 不可用，已切换兜底
CONFIG_CHANGED = "config_changed"
STATUS_MESSAGE = "status_message"              # 状态栏提示
TASK_PROGRESS = "task_progress"                # 长任务进度


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[..., Any]]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event: str, handler: Callable[..., Any]) -> Callable[[], None]:
        """订阅事件，返回一个取消订阅的函数。"""
        with self._lock:
            self._subscribers[event].append(handler)

        def unsubscribe() -> None:
            self.unsubscribe(event, handler)

        return unsubscribe

    def unsubscribe(self, event: str, handler: Callable[..., Any]) -> None:
        with self._lock:
            handlers = self._subscribers.get(event)
            if handlers and handler in handlers:
                handlers.remove(handler)

    def emit(self, event: str, **payload: Any) -> None:
        """同步派发。异常被吞掉并记日志，避免一个订阅者搞崩整个流程。"""
        with self._lock:
            handlers = list(self._subscribers.get(event, ()))
        for handler in handlers:
            try:
                handler(**payload)
            except Exception:  # noqa: BLE001 - 订阅者异常不应影响发布者
                log.exception("事件 %s 的订阅者执行失败: %r", event, handler)

    def clear(self) -> None:
        with self._lock:
            self._subscribers.clear()


#: 全局总线
bus = EventBus()
