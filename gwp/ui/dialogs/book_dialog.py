"""书目对话框：新建 / 编辑书目名称、说明、颜色。"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gwp.data_manager.models import Book
from gwp.data_manager.store import validate_name
from gwp.ui import common
from gwp.ui.widgets.color_picker import ColorPicker
from gwp.core import constants as C


class BookDialog(QDialog):
    """新建或编辑书目。"""

    def __init__(self, parent: QWidget | None = None, book: Book | None = None, subject_name: str = "") -> None:
        super().__init__(parent)
        self.book = book
        self.is_new = book is None
        self.subject_name = subject_name or (book.subject_name if book else "")

        self.setWindowTitle("新建书目" if self.is_new else f"编辑书目：{book.title}")
        self.setMinimumWidth(470)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.input_name = QLineEdit(book.name if book else "")
        self.input_name.setPlaceholderText("例如：数学分析（会成为文件夹名）")
        form.addRow("书目名称", self.input_name)

        self.input_desc = QPlainTextEdit(book.description if book else "")
        self.input_desc.setPlaceholderText("可选：这本书的说明")
        self.input_desc.setFixedHeight(68)
        form.addRow("说明", self.input_desc)
        layout.addLayout(form)

        layout.addWidget(QLabel("卡片颜色"))
        self.color_picker = ColorPicker(book.color if book else "")
        layout.addWidget(self.color_picker)

        hint = QLabel(
            f"创建后会自动生成：{C.INTRO_FILE}、"
            f"{'、'.join(C.BOOK_TEMPLATE_DIRS)}；"
            f"AI 总结会输出为「书名{C.SUMMARY_SUFFIX}」并排在最前面。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("Muted")
        layout.addWidget(hint)
        layout.addStretch(1)

        buttons = QDialogButtonBox()
        self.btn_ok = buttons.addButton("创建" if self.is_new else "保存", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_ok.setProperty("accent", True)
        buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.input_name.setFocus()
        self.input_name.selectAll()

    def _accept(self) -> None:
        error = validate_name(self.input_name.text())
        if error:
            common.warn(self, error, "名称不合法")
            return
        self.accept()

    def values(self) -> dict:
        return {
            "name": self.input_name.text().strip(),
            "description": self.input_desc.toPlainText().strip(),
            "color": self.color_picker.color(),
        }


__all__ = ["BookDialog"]
