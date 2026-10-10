"""AI 提问对话框（需求文档第七节：AI 对内容不确定时弹窗询问用户）。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gwp.ai.types import AiQuestion


class AiQuestionDialog(QDialog):
    """把 AI 的问题变成一个有选项的对话框；用户也可以自己输入答案。"""

    def __init__(self, question: AiQuestion, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._answer: str | None = None
        self.setWindowTitle("AI 需要确认")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(10)

        header = QLabel("AI 在继续处理前，需要你确认以下信息：")
        header.setObjectName("Muted")
        layout.addWidget(header)

        label = QLabel(question.question)
        label.setWordWrap(True)
        label.setObjectName("Title")
        layout.addWidget(label)

        if question.context:
            context = QLabel(question.context)
            context.setWordWrap(True)
            context.setObjectName("Muted")
            layout.addWidget(context)

        self.list = QListWidget()
        self.list.setVisible(bool(question.options))
        for option in question.options:
            item = QListWidgetItem(option)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            self.list.addItem(item)
        if question.options:
            self.list.setCurrentRow(0)
            self.list.itemDoubleClicked.connect(lambda _item: self._accept_current())
        layout.addWidget(self.list)

        self.input = QLineEdit()
        self.input.setPlaceholderText(
            "也可以直接输入你的回答" if question.allow_custom else "请选择上面的选项"
        )
        self.input.setEnabled(question.allow_custom)
        self.input.returnPressed.connect(self._accept_input)
        layout.addWidget(self.input)

        buttons = QDialogButtonBox()
        self.btn_ok = buttons.addButton("确定", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_cancel = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._accept_current)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if question.options:
            self.list.setFocus()
        else:
            self.input.setFocus()

    # ------------------------------------------------------------------

    def _accept_current(self) -> None:
        item = self.list.currentItem()
        if item is not None and not self.input.text().strip():
            self._answer = item.text()
            self.accept()
            return
        self._accept_input()

    def _accept_input(self) -> None:
        text = self.input.text().strip()
        if text:
            self._answer = text
            self.accept()
            return
        item = self.list.currentItem()
        if item is not None:
            self._answer = item.text()
            self.accept()

    def answer(self) -> str | None:
        return self._answer


__all__ = ["AiQuestionDialog"]
