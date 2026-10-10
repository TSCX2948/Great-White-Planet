"""颜色选择控件：预设色板 + 自定义颜色。"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QColorDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gwp.core.constants import DEFAULT_CARD_COLORS


class ColorPicker(QWidget):
    """一排颜色按钮 + "自定义"。"""

    color_changed = pyqtSignal(str)

    def __init__(self, color: str = "", parent: QWidget | None = None, columns: int = 5) -> None:
        super().__init__(parent)
        self._color = color or DEFAULT_CARD_COLORS[0]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        grid = QGridLayout()
        grid.setSpacing(6)
        self._buttons: list[QToolButton] = []
        for index, value in enumerate(DEFAULT_CARD_COLORS):
            button = QToolButton()
            button.setCheckable(True)
            button.setAutoRaise(True)
            button.setIconSize(QSize(22, 22))
            button.setIcon(self._swatch_icon(value))
            button.setToolTip(value)
            button.clicked.connect(lambda _checked=False, c=value: self.set_color(c, emit=True))
            grid.addWidget(button, index // columns, index % columns)
            self._buttons.append(button)
        layout.addLayout(grid)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.preview = QLabel()
        self.preview.setFixedSize(28, 28)
        row.addWidget(self.preview)
        self.btn_custom = QPushButton("自定义颜色…")
        self.btn_custom.clicked.connect(self._pick_custom)
        row.addWidget(self.btn_custom)
        row.addStretch(1)
        layout.addLayout(row)

        self._sync()

    # ------------------------------------------------------------------

    @staticmethod
    def _swatch_icon(color: str) -> QIcon:
        pixmap = QPixmap(22, 22)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 22, 22, 6, 6)
        painter.end()
        return QIcon(pixmap)

    def color(self) -> str:
        return self._color

    def set_color(self, color: str, emit: bool = False) -> None:
        value = QColor(color)
        if not value.isValid():
            return
        self._color = value.name()
        self._sync()
        if emit:
            self.color_changed.emit(self._color)

    def _sync(self) -> None:
        for button in self._buttons:
            button.setChecked(button.toolTip().lower() == self._color.lower())
        self.preview.setStyleSheet(
            f"background: {self._color}; border: 1px solid rgba(0,0,0,0.18); border-radius: 8px;"
        )

    def _pick_custom(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "选择颜色")
        if color.isValid():
            self.set_color(color.name(), emit=True)


__all__ = ["ColorPicker"]
