"""生成总结时的进度对话框：显示阶段、百分比，并支持取消。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class SummaryProgressDialog(QDialog):
    """展示 AI 生成 summary 的全过程，并把流式输出实时显示出来。"""

    def __init__(self, title: str = "生成学习总结", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 460)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self._cancelled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        self.lbl_stage = QLabel("准备中……")
        self.lbl_stage.setObjectName("SectionTitle")
        layout.addWidget(self.lbl_stage)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        layout.addWidget(self.bar)

        self.lbl_detail = QLabel("")
        self.lbl_detail.setObjectName("Muted")
        self.lbl_detail.setWordWrap(True)
        layout.addWidget(self.lbl_detail)

        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlaceholderText("AI 的输出会实时显示在这里……")
        layout.addWidget(self.output, 1)

        buttons = QDialogButtonBox()
        self.btn_cancel = buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        self.btn_cancel.clicked.connect(self._on_cancel)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def set_stage(self, message: str, percent: int = -1, detail: str = "") -> None:
        self.lbl_stage.setText(message)
        if detail:
            self.lbl_detail.setText(detail)
        if percent is None or percent < 0:
            if self.bar.maximum() != 0:
                self.bar.setRange(0, 0)
        else:
            if self.bar.maximum() == 0:
                self.bar.setRange(0, 100)
            self.bar.setValue(max(0, min(100, int(percent))))

    def append_chunk(self, text: str) -> None:
        self.output.moveCursor(self.output.textCursor().MoveOperation.End)
        self.output.insertPlainText(text)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def set_result_text(self, text: str) -> None:
        self.output.setPlainText(text)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def finish(self, message: str = "完成") -> None:
        self.bar.setRange(0, 100)
        self.bar.setValue(100)
        self.lbl_stage.setText(message)

    def _on_cancel(self) -> None:
        self._cancelled = True
        self.lbl_stage.setText("正在取消……")


__all__ = ["SummaryProgressDialog"]
