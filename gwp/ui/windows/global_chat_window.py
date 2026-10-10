"""AI 日常对话窗口（菜单栏右上角入口）。

和文档视图里的「AI 双栏」区别：

* **不绑定任何文件**：适合问概念、梳理思路、写点东西、随便聊聊；
* 输入区更宽裕，窗口独立，可以一边看资料一边问；
* 使用 ``prompts.daily_chat_system`` 这套提示词（不会假装读过你的资料）。

聊天记录与文档对话共用 :mod:`gwp.ai.chat_session` 的存储，键为
``__global__/daily``，因此同样受"关闭软件清空聊天记录"的设置控制。
"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gwp.bootstrap import AppContext
from gwp.services import themes
from gwp.ui import common
from gwp.ui.widgets.chat_panel import ChatPanel

#: 日常对话会话的固定键（不会与文档会话冲突）
DAILY_SESSION_KEY = "__global__/daily"
DAILY_SESSION_TITLE = "AI 日常对话"


class GlobalChatWindow(QMainWindow):
    """不绑定文件的 AI 对话窗口。"""

    status_message = pyqtSignal(str)

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle(f"AI 日常对话 — {context.config.get('app.name', 'Great White Planet')}")
        self.resize(880, 720)
        self.setMinimumSize(560, 420)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # 顶部说明条
        bar = QHBoxLayout()
        bar.setSpacing(8)
        hint = QLabel(
            "日常对话：不读取任何文件。想讨论某份资料的内容，请打开它并用文档里的「AI 双栏」。"
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        bar.addWidget(hint, 1)
        self.btn_new = QPushButton("新对话")
        self.btn_new.setToolTip("清空当前对话，重新开始")
        self.btn_new.clicked.connect(self.new_conversation)
        bar.addWidget(self.btn_new)
        layout.addLayout(bar)

        # 复用文档视图里的聊天面板（document_path=None 即日常模式）
        self.chat = ChatPanel(context)
        self.chat.status_message.connect(self.status_message.emit)
        layout.addWidget(self.chat, 1)

        self.setCentralWidget(central)
        self.setWindowIcon(common.app_icon(config=context.config))
        self.apply_theme()

        # 未绑定文件时这两个按钮没有意义，面板里已经隐藏；
        # 这里把「发送」设为默认按钮，回车即可发送（Ctrl+Enter 也保留）。
        self.chat.btn_send.setDefault(True)
        shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        shortcut.activated.connect(self.new_conversation)

        self.chat.bind_document(None, DAILY_SESSION_KEY, title=DAILY_SESSION_TITLE)

    # ------------------------------------------------------------------

    def apply_theme(self) -> None:
        self.setStyleSheet(
            themes.app_qss(
                theme=self.context.theme,
                accent=str(self.context.config.get("ui.accent", "") or ""),
                font_family=str(self.context.config.get("ui.font_family", "") or ""),
                font_size=int(self.context.config.get("ui.font_size", 10) or 10),
            )
        )
        self.setWindowIcon(common.app_icon(config=self.context.config))

    def focus_input(self) -> None:
        """把焦点放到输入框（从菜单栏点开时直接可以打字）。"""
        self.chat.input.setFocus()

    def new_conversation(self) -> None:
        if self.chat.is_busy():
            common.warn(self, "AI 正在回答，请先点「停止」或稍候。")
            return
        session = self.chat.session
        if session is not None and not session.is_empty:
            if not common.confirm(self, "清空当前对话并重新开始？", "新对话"):
                return
            session.clear()
            self.context.chats.delete(DAILY_SESSION_KEY)
        self.chat._render()
        self.status_message.emit("已开始新的对话")
        self.focus_input()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt 接口
        if self.chat.is_busy():
            if not common.confirm(self, "AI 正在回答，确定要关闭吗？", "关闭"):
                event.ignore()
                return
            self.chat.wait_for_idle()
        self.chat.save_session()
        event.accept()


__all__ = ["DAILY_SESSION_KEY", "DAILY_SESSION_TITLE", "GlobalChatWindow"]
