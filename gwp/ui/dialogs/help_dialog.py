"""帮助对话框：设计思想 / 功能说明 / 使用说明 / 更新记录。"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gwp.bootstrap import AppContext
from gwp.services.markdown_renderer import RenderOptions, render_document
from gwp.ui import common, help_content


class HelpDialog(QDialog):
    """内置帮助窗口。找不到外部文档时显示内置内容。"""

    def __init__(self, context: AppContext, page: str = "使用说明", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("帮助 — Great White Planet")
        self.resize(980, 700)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(12)

        self.nav = QListWidget()
        self.nav.setFixedWidth(170)
        names = list(help_content.help_documents())
        for name in names:
            self.nav.addItem(QListWidgetItem(name))
        self.nav.currentRowChanged.connect(self._on_nav)
        layout.addWidget(self.nav)

        right = QVBoxLayout()
        right.setSpacing(8)

        self.lbl_source = QLabel("")
        self.lbl_source.setObjectName("Muted")
        right.addWidget(self.lbl_source)

        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        right.addWidget(self.view, 1)

        buttons = QDialogButtonBox()
        self.btn_folder = buttons.addButton("打开文档目录", QDialogButtonBox.ButtonRole.ActionRole)
        self.btn_folder.clicked.connect(self._open_document_dir)
        buttons.addButton("关闭", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        right.addWidget(buttons)
        layout.addLayout(right, 1)

        index = names.index(page) if page in names else 0
        self.nav.setCurrentRow(index)

    # ------------------------------------------------------------------

    def _on_nav(self, row: int) -> None:
        names = list(help_content.help_documents())
        if not (0 <= row < len(names)):
            return
        name = names[row]
        text, source = help_content.document_text(name)
        self.lbl_source.setText(
            f"来源：{source}" if source else "来源：软件内置文档（磁盘上没有对应文件）"
        )
        self.view.setHtml(
            render_document(
                text,
                RenderOptions(theme=self.context.theme, base_dir=source.parent if source else None),
            )
        )
        self.view.verticalScrollBar().setValue(0)

    def _open_document_dir(self) -> None:
        from gwp.core.paths import document_dir
        from gwp.services import file_ops

        directory = document_dir()
        if directory.is_dir():
            file_ops.reveal_in_explorer(directory)
        else:
            common.warn(self, f"文档目录不存在：{directory}")


__all__ = ["HelpDialog"]
