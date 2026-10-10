"""可折叠的单词卡控件。

需求原话：

> 单词卡可折叠 …… 单词卡折叠后只显示英语 单击后展开

所以这是一个**明确的交互契约**，不是一个可有可无的开关：

* **折叠态**：只显示英文（+ 右侧一个小箭头），一眼扫过去就是一列生词；
* **展开态**：显示音标、词性、中文释义、例句、搭配、记忆提示、自己的笔记；
* **单击整个头部**就切换（不用专门去找那个小箭头 —— 命中区域越大越好）。

点击头部的实现方式和项目里首页卡片一样：
**在 ``mouseReleaseEvent`` 里判断"没有拖动过"才算点击**，
否则以后加拖拽排序时会互相打架（首页卡片踩过这个坑）。
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gwp.data_manager.wordbook import WordCard
from gwp.ui import common

log = logging.getLogger(__name__)


class WordCardWidget(QFrame):
    """一张可折叠的单词卡。

    信号：

    * ``toggled(card, expanded)`` —— 展开状态变了（视图据此决定要不要记住）；
    * ``requested(card, action)`` —— 请求某个操作（edit / complete / delete …）。
      用字符串传动作而不是给每个动作一个信号：动作会一直加，
      信号不该跟着膨胀。
    """

    toggled = pyqtSignal(object, bool)
    requested = pyqtSignal(object, str)

    def __init__(
        self,
        card: WordCard,
        *,
        expanded: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.card = card
        self._expanded = bool(expanded)
        self._pressed = False
        self._dragged = False
        self._origin = None

        self.setObjectName("WordCard")
        self.setProperty("expanded", self._expanded)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)

        # ---- 头部：**折叠时唯一可见的东西** = 英文本身 ----
        head = QHBoxLayout()
        head.setSpacing(6)
        self.lbl_english = QLabel(card.english)
        self.lbl_english.setObjectName("WordEnglish")
        self.lbl_english.setWordWrap(False)
        self.lbl_english.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.lbl_english.setToolTip(card.english)
        head.addWidget(self.lbl_english, 1)

        # 待补齐的标记：折叠时也能一眼看出哪几张还没内容
        if not card.completed:
            self.lbl_state = QLabel("待补齐")
            self.lbl_state.setObjectName("Muted")
            self.lbl_state.setToolTip("这张卡还没有中文解释，点右键可以「AI 补齐」")
            head.addWidget(self.lbl_state)

        self.btn_more = QToolButton()
        self.btn_more.setObjectName("WordCardMore")
        self.btn_more.setText("▾" if self._expanded else "▸")
        self.btn_more.setToolTip("展开 / 折叠这张卡")
        self.btn_more.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_more.clicked.connect(self.toggle)
        head.addWidget(self.btn_more)
        root.addLayout(head)

        # ---- 详情：只在展开时可见 ----
        self.detail = QWidget()
        detail_layout = QVBoxLayout(self.detail)
        detail_layout.setContentsMargins(2, 2, 2, 0)
        detail_layout.setSpacing(4)

        # 一行摘要：音标 + 词性
        summary = "  ".join(part for part in (card.phonetic, card.part_of_speech) if part)
        if summary:
            self.lbl_summary = QLabel(summary)
            self.lbl_summary.setObjectName("Muted")
            self.lbl_summary.setWordWrap(True)
            detail_layout.addWidget(self.lbl_summary)

        if not card.has_details:
            hint = QLabel(
                "这张卡还没有内容。"
                "右键选「AI 补齐释义与例句」，或点右上角的「补齐全部」。"
            )
            hint.setObjectName("Muted")
            hint.setWordWrap(True)
            detail_layout.addWidget(hint)
        else:
            for label, text in (
                ("释义", card.meaning),
                ("例句", card.examples),
                ("搭配", card.phrases),
                ("记忆", card.tip),
                ("笔记", card.note),
            ):
                if not (text or "").strip():
                    continue
                detail_layout.addWidget(self._section(label, text))

        self.detail.setVisible(self._expanded)
        root.addWidget(self.detail)

    # ------------------------------------------------------------------

    @staticmethod
    def _section(label: str, text: str) -> QWidget:
        """一个"小标题 + 正文"块。"""
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        caption = QLabel(label)
        caption.setObjectName("WordSectionLabel")
        layout.addWidget(caption)

        body = QLabel(common.html_escape(text).replace("\n", "<br>"))
        body.setObjectName("WordSectionBody")
        body.setTextFormat(Qt.TextFormat.RichText)
        body.setWordWrap(True)
        # 正文可以被压缩（否则长例句会把卡片撑得超出面板宽度）
        body.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(body)
        return box

    # ------------------------------------------------------------------

    @property
    def expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool, *, notify: bool = False) -> None:
        expanded = bool(expanded)
        if expanded == self._expanded:
            return
        self._expanded = expanded
        self.detail.setVisible(expanded)
        self.btn_more.setText("▾" if expanded else "▸")
        # QSS 里用 [expanded="true"] 控制边框/底色，属性变了必须重新套样式
        self.setProperty("expanded", expanded)
        self.style().unpolish(self)
        self.style().polish(self)
        if notify:
            self.toggled.emit(self.card, expanded)

    def toggle(self) -> None:
        self.set_expanded(not self._expanded, notify=True)

    # ---- 单击头部切换（release 且未拖动才算点击）----

    def mousePressEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        if event.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self._dragged = False
            self._origin = event.position().toPoint()      # 记住按下点
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if self._pressed and (event.buttons() & Qt.MouseButton.LeftButton):
            origin = getattr(self, "_origin", None)
            if origin is not None:
                distance = (event.position().toPoint() - origin).manhattanLength()
                # 和首页卡片同一套阈值逻辑：超过 Qt 的拖拽起始距离才算"拖动"
                if distance > 12:
                    self._dragged = True
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        super().mouseReleaseEvent(event)
        if event.button() != Qt.MouseButton.LeftButton or not self._pressed:
            return
        self._pressed = False
        if self._dragged:
            # 拖动过就不当点击（以后加拖拽排序时不会被误触发）
            self._dragged = False
            return
        # 点在详情区里不该折叠 —— 用户可能正在选中文字
        if self._expanded and self.detail.geometry().contains(
            event.position().toPoint()
        ):
            return
        self.toggle()

    def contextMenuEvent(self, event) -> None:  # noqa: N802
        """右键：补齐 / 编辑 / 复制 / 删除。"""
        from PyQt6.QtWidgets import QMenu

        menu = QMenu(self)
        actions = (
            ("AI 补齐释义与例句", "complete"),
            ("重新补齐（覆盖现有内容）", "recomplete"),
            ("编辑…", "edit"),
            None,
            ("复制单词", "copy_word"),
            ("复制释义", "copy_meaning"),
            None,
            ("锁定（不再被自动覆盖）" if not self.card.locked else "解除锁定",
             "toggle_lock"),
            ("删除这张卡…", "delete"),
        )
        for entry in actions:
            if entry is None:
                menu.addSeparator()
                continue
            text, action = entry
            item = menu.addAction(text)
            item.triggered.connect(
                lambda _checked=False, a=action: self.requested.emit(self.card, a)
            )
        menu.exec(event.globalPos())


__all__ = ["WordCardWidget"]
