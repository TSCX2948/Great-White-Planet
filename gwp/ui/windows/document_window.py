"""独立文档窗口（需求文档第八节：打开文件时另开窗口）。"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMainWindow, QWidget

from gwp.bootstrap import AppContext
from gwp.services import themes
from gwp.ui import common
from gwp.ui.views.document_view import DocumentView


class DocumentWindow(QMainWindow):
    """把 :class:`DocumentView` 装进独立窗口，让用户能同时看多份资料。"""

    closed = pyqtSignal(object)
    status_message = pyqtSignal(str)
    export_pdf_requested = pyqtSignal(Path)

    def __init__(self, context: AppContext, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self.view = DocumentView(context, self)
        self.view.status_message.connect(self.status_message.emit)
        self.view.request_pdf_export.connect(self.export_pdf_requested.emit)
        self.view.closed.connect(lambda _view: self.close())
        self.setCentralWidget(self.view)

        self.resize(1180, 820)
        self.setWindowIcon(common.app_icon(config=context.config))
        self.apply_theme()
        self.view.open_file(path)

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
        self.view.apply_theme()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt 接口
        if self.view.confirm_close():
            self.closed.emit(self)
            event.accept()
        else:
            event.ignore()


__all__ = ["DocumentWindow"]
