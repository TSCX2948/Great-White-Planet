"""gwp.ui.windows：独立窗口。

* :class:`DocumentWindow`  —— 打开 Markdown 时的独立编辑窗口
* :class:`GlobalChatWindow` —— 菜单栏右上角入口打开的 AI 日常对话窗口
"""

from gwp.ui.windows.document_window import DocumentWindow
from gwp.ui.windows.global_chat_window import (
    DAILY_SESSION_KEY,
    DAILY_SESSION_TITLE,
    GlobalChatWindow,
)

__all__ = [
    "DAILY_SESSION_KEY",
    "DAILY_SESSION_TITLE",
    "DocumentWindow",
    "GlobalChatWindow",
]
