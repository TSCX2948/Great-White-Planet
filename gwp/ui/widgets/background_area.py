"""主界面背景容器：用 QPainter 自己画背景图。

为什么不用 QSS ``background-image``
----------------------------------
实测（见开发记录）在 Qt 里同时满足这三个条件时，``background-image`` 会**完全不绘制**：

1. 应用级样式表里存在 ``QMainWindow { background: ... }``；
2. 该样式表与背景规则被 setStyleSheet 合并到同一个 widget；
3. 背景规则写在中英控件（central widget）上。

换 ``border-image`` 能画出来，但那会拉伸/裁切不当，且无法做"蒙层"。
因此改成自绘：控制精确、不依赖 Qt 的样式表内部行为，也便于做
cover/contain/stretch/center 四种填充方式与半透明蒙层。

性能：只在尺寸或图片变化时重新缩放（缓存 QPixmap），
``paintEvent`` 里只做一次 drawPixmap，拖动窗口不会卡。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QPainter, QPixmap
from PyQt6.QtWidgets import QWidget

log = logging.getLogger(__name__)


class BackgroundImageWidget(QWidget):
    """一种把背景图当作自己"底色"的容器控件。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._source: Path | None = None
        self._pixmap: QPixmap | None = None
        self._scaled: QPixmap | None = None
        self._scaled_for: tuple[int, int] = (0, 0)
        self._fit = "cover"
        self._overlay = 0.0
        self._overlay_color = QColor(0, 0, 0)

    # ------------------------------------------------------------------
    # 配置
    # ------------------------------------------------------------------

    def set_background(
        self,
        image: Path | None,
        fit: str = "cover",
        overlay: float = 0.0,
        overlay_color: tuple[int, int, int] = (0, 0, 0),
    ) -> None:
        """设置背景图与显示参数；``image=None`` 表示不使用背景。"""
        changed = Path(image) != self._source if image else self._source is not None
        self._source = Path(image) if image else None
        self._fit = str(fit or "cover").lower()
        try:
            self._overlay = max(0.0, min(0.95, float(overlay or 0.0)))
        except (TypeError, ValueError):
            self._overlay = 0.0
        self._overlay_color = QColor(*overlay_color)

        if changed or self._pixmap is None:
            self._pixmap = None
            self._scaled = None
            self._scaled_for = (0, 0)
        self.update()

    def clear_background(self) -> None:
        self.set_background(None)

    @property
    def has_background(self) -> bool:
        return self._source is not None

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _load(self) -> QPixmap | None:
        if self._source is None:
            return None
        if self._pixmap is None:
            pixmap = QPixmap(str(self._source))
            if pixmap.isNull():
                log.warning("背景图无法加载（可能格式不支持）：%s", self._source)
                self._pixmap = QPixmap()      # 记住失败，避免每帧重试
            else:
                self._pixmap = pixmap
        return self._pixmap if not self._pixmap.isNull() else None

    def _scaled_pixmap(self, size: tuple[int, int]) -> QPixmap | None:
        pixmap = self._load()
        if pixmap is None:
            return None
        width, height = size
        if width <= 0 or height <= 0:
            return None
        if self._scaled is not None and self._scaled_for == (width, height):
            return self._scaled

        ratio = self.devicePixelRatioF() or 1.0
        target_w = max(1, int(width * ratio))
        target_h = max(1, int(height * ratio))

        if self._fit == "stretch":
            result = pixmap.scaled(
                target_w,
                target_h,
                Qt.AspectRatioMode.IgnoreAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        elif self._fit == "center":
            result = pixmap                      # 原尺寸居中，不缩放
        else:
            # cover / contain：先按比例缩放
            mode = (
                Qt.AspectRatioMode.KeepAspectRatioByExpanding
                if self._fit == "cover"
                else Qt.AspectRatioMode.KeepAspectRatio
            )
            result = pixmap.scaled(
                target_w, target_h, mode, Qt.TransformationMode.SmoothTransformation
            )
        result.setDevicePixelRatio(ratio)

        self._scaled = result
        self._scaled_for = (width, height)
        return result

    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        self._scaled = None
        self._scaled_for = (0, 0)
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        painter = QPainter(self)
        try:
            pixmap = self._scaled_pixmap((self.width(), self.height()))
            if pixmap is None:
                return
            area = QRect(0, 0, self.width(), self.height())
            if self._fit == "center":
                # 原尺寸居中
                x = (self.width() - pixmap.width()) // 2
                y = (self.height() - pixmap.height()) // 2
                painter.drawPixmap(x, y, pixmap)
            elif self._fit == "contain":
                # 完整显示，居中；四周留白
                scaled = pixmap
                x = (self.width() - scaled.width()) // 2
                y = (self.height() - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            else:
                # cover / stretch：铺满并居中裁切
                source_x = max(0, (pixmap.width() - self.width()) // 2)
                source_y = max(0, (pixmap.height() - self.height()) // 2)
                painter.drawPixmap(
                    area, pixmap, QRect(source_x, source_y, self.width(), self.height())
                )

            if self._overlay > 0:
                # 半透明压暗：alpha 必须带上，否则 fillRect 会直接用不透明色糊掉背景
                tint = QColor(self._overlay_color)
                tint.setAlphaF(self._overlay)
                painter.fillRect(area, tint)
        finally:
            painter.end()


__all__ = ["BackgroundImageWidget"]
