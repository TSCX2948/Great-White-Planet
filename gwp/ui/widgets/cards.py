"""首页/科目页使用的卡片控件与自适应网格。

需求文档第三节：首页采用图形化显示，默认是彩色长方体卡片。
本文件用自绘实现圆角卡片，支持背景图片、悬停高亮、右键菜单占位。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QMenu,
    QSizePolicy,
    QWidget,
)

from gwp.data_manager.models import Book, Subject
from gwp.ui import common


def _trace(message: str) -> None:
    """拖拽排查日志：只有设置 ``GWP_TRACE_DRAG=1`` 时才输出。

    拖拽依赖窗口系统，普通单元测试覆盖不到"真实手感"，所以留一个开关，
    让用户在真机上操作时能留下证据。
    """
    if not os.environ.get("GWP_TRACE_DRAG"):
        return
    try:
        from gwp.core.logging_setup import get_logger

        get_logger(__name__).info("[拖拽] %s", message)
    except Exception:  # noqa: BLE001 - 日志绝不能影响交互
        pass


#: 拖拽用的 MIME 类型。科目与收纳箱分开，接收方才能判断该怎么处理：
#: * 科目拖到**收纳箱**上 = 收进箱子；
#: * 科目拖到**科目**上、收纳箱拖到**收纳箱**上 = 调整顺序。
SUBJECT_MIME = "application/x-gwp-subject"
BOX_MIME = "application/x-gwp-box"


def _readable_text_color(background: QColor) -> QColor:
    """根据背景亮度选黑或白，保证卡片标题可读。"""
    luminance = (0.299 * background.red() + 0.587 * background.green() + 0.114 * background.blue()) / 255
    return QColor("#1F2733") if luminance > 0.62 else QColor("#FFFFFF")


class InfoCard(QFrame):
    """卡片基类：圆角矩形 + 可选背景图 + 标题/副标题 + 数量。"""

    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    context_requested = pyqtSignal(QPoint)
    #: (拖过来的 MIME 类型, 负载文本)。由 CardGrid 统一决定是收纳还是重排。
    card_dropped = pyqtSignal(str, str)

    def __init__(
        self,
        parent: QWidget | None = None,
        width: int = 196,
        height: int = 124,
        radius: int = 14,
    ) -> None:
        super().__init__(parent)
        self._width = width
        self._height = height
        self._radius = radius
        self._color = QColor("#4F7CFF")
        self._image: QPixmap | None = None
        self._image_path: Path | None = None
        self._title = ""
        self._subtitle = ""
        self._badge = ""
        self._pinned = False
        self._hover = False
        self._selected = False
        #: 是否画一圈边框。收纳箱用它来和普通科目卡片区分（样式其余部分完全一致）
        self._bordered = False
        self._border_color = QColor("#FFFFFF")
        #: 拖拽起点（按住左键后记录，用于判断是否达到拖拽阈值）
        self._drag_origin: QPoint | None = None
        #: 是否有东西悬停在这张卡片上、以及落点在左半还是右半
        self._drop_active = False
        self._drop_before = True
        #: 这次按下是否演变成了拖拽（拖拽后就不再算单击）
        self._dragged = False
        self.setAcceptDrops(False)
        self.setFixedSize(QSize(width, height))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.context_requested.emit)

    # -- 数据 -----------------------------------------------------------

    def set_title(self, text: str) -> "InfoCard":
        self._title = text or ""
        self.update()
        return self

    def set_subtitle(self, text: str) -> "InfoCard":
        self._subtitle = text or ""
        self.update()
        return self

    def set_badge(self, text: str) -> "InfoCard":
        self._badge = text or ""
        self.update()
        return self

    def set_color(self, color: str | QColor) -> "InfoCard":
        value = QColor(color) if not isinstance(color, QColor) else color
        if value.isValid():
            self._color = value
            self.update()
        return self

    def set_pinned(self, pinned: bool) -> "InfoCard":
        self._pinned = bool(pinned)
        self.update()
        return self

    def set_image(self, path: Path | None) -> "InfoCard":
        """设置背景图片（jpg/png）。找不到或格式不支持时自动忽略。"""
        self._image_path = path
        self._image = None
        if path is not None:
            candidate = Path(path)
            if candidate.is_file():
                pixmap = QPixmap(str(candidate))
                if not pixmap.isNull():
                    self._image = pixmap
        self.update()
        return self

    def set_selected(self, selected: bool) -> "InfoCard":
        if self._selected != bool(selected):
            self._selected = bool(selected)
            self.update()
        return self

    def set_bordered(self, bordered: bool, color: QColor | str | None = None) -> "InfoCard":
        """画一圈固定边框。

        收纳箱要求"样式和 Subject 卡片保持一致，但增加边框表示区分"，
        因此其余绘制（渐变、徽标、标题、副标题）全部复用基类，
        只额外多描一圈边。
        """
        self._bordered = bool(bordered)
        if color is not None:
            value = QColor(color) if not isinstance(color, QColor) else color
            if value.isValid():
                self._border_color = value
        self.update()
        return self

    @property
    def title(self) -> str:
        return self._title

    # -- 交互 -----------------------------------------------------------

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.position().toPoint()
            self._dragged = False
            _trace(f"press {type(self).__name__}:{self._trace_name()} origin={self._drag_origin}")
            # 注意：**不在这里发 clicked**。
            # 收纳箱卡片"单击即展开"，如果在按下时就发，拖拽会被展开动作吞掉
            # （一按下就跳进箱子，根本拖不动）。改为在释放时发。
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        """按住左键拖出一定距离才开始拖拽，避免误触。"""
        origin = getattr(self, "_drag_origin", None)
        if origin is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return
        payload = self._drag_payload()
        if payload is None:
            super().mouseMoveEvent(event)
            return
        distance = (event.position().toPoint() - origin).manhattanLength()
        _trace(
            f"move {type(self).__name__}:{self._trace_name()} "
            f"dist={distance} 阈值={QApplication.startDragDistance()}"
        )
        if distance < QApplication.startDragDistance():
            super().mouseMoveEvent(event)
            return

        from PyQt6.QtCore import QMimeData
        from PyQt6.QtGui import QDrag

        _trace(f"启动拖拽 {type(self).__name__}:{payload}")
        self._dragged = True
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self._drag_mime(), str(payload).encode("utf-8"))
        drag.setMimeData(mime)
        drag.setPixmap(self.grab().scaledToWidth(max(60, self.width() // 2)))
        result = drag.exec(Qt.DropAction.MoveAction)
        _trace(f"拖拽结束 result={result}")
        self._drag_origin = None
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        origin = getattr(self, "_drag_origin", None)
        dragged = getattr(self, "_dragged", False)
        self._drag_origin = None
        # 只有"按在卡片上、没有拖动、同一张卡片上松开"才算单击
        if event.button() == Qt.MouseButton.LeftButton and origin is not None and not dragged:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def _drag_mime(self) -> str:
        """拖拽负载的 MIME 类型；返回空串表示这张卡片不可拖动。"""
        return ""

    def _trace_name(self) -> str:
        """调试日志里用来标识这张卡片。"""
        for attr in ("subject", "box", "book"):
            value = getattr(self, attr, None)
            name = getattr(value, "name", None) or getattr(value, "title", None)
            if name:
                return str(name)
        return getattr(self, "title", "?")

    def _drag_payload(self) -> str | None:
        """拖拽负载（可拖动卡片返回字符串，否则 None）。"""
        return None

    # -- 拖放目标：所有卡片都能接收，用于"拖到某张卡片上调整顺序" --------

    def _accepts_drag(self, mime: str) -> bool:
        """默认卡片不接收任何拖放；子类按需覆盖。"""
        return False

    def dragEnterEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        if self._accepts_drag(event.mimeData()):
            event.acceptProposedAction()
            self._drop_active = True
            self._drop_before = self._is_before_half(event)
            self.update()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if not self._accepts_drag(event.mimeData()):
            event.ignore()
            return
        before = self._is_before_half(event)
        if before != self._drop_before:
            self._drop_before = before
            self.update()
        event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._drop_active = False
        self.update()
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        self._drop_active = False
        self.update()
        mime = event.mimeData()
        if not self._accepts_drag(mime):
            event.ignore()
            return
        kind = self._mime_kind(mime)
        raw = bytes(mime.data(kind)).decode("utf-8", errors="replace")
        payload = raw.strip()
        if not payload:
            event.ignore()
            return
        self.card_dropped.emit(kind, payload)
        event.acceptProposedAction()

    def _is_before_half(self, event) -> bool:
        """落点在该卡片左半边还是右半边（决定插到前面还是后面）。"""
        try:
            position = event.position()
        except AttributeError:  # pragma: no cover - 旧版 Qt
            position = event.pos()
        return float(position.x()) < self.width() / 2

    def _mime_kind(self, mime) -> str:
        """从 mimeData 里挑出我们认识的那个类型。"""
        for candidate in (SUBJECT_MIME, BOX_MIME):
            if mime.hasFormat(candidate):
                return candidate
        return ""

    def paint_drop_indicator(self, painter: QPainter) -> None:
        """画出"将要插入的位置"提示条（左/右边缘）。"""
        if not self._drop_active:
            return
        pen = painter.pen()
        pen.setColor(QColor("#FFD166"))
        pen.setWidthF(3.0)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        x = 2 if self._drop_before else self.width() - 5
        painter.drawRoundedRect(
            QRect(x, 2, 3, self.height() - 4), 1.5, 1.5
        )

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)

    # -- 绘制 -----------------------------------------------------------

    def paintEvent(self, event) -> None:  # noqa: N802 - 自绘
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        rect = QRect(0, 0, self.width() - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(
            float(rect.x()), float(rect.y()), float(rect.width()), float(rect.height()),
            float(self._radius), float(self._radius),
        )
        painter.setClipPath(path)

        if self._image is not None:
            scaled = self._image.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            offset_x = (scaled.width() - self.width()) // 2
            offset_y = (scaled.height() - self.height()) // 2
            painter.drawPixmap(-offset_x, -offset_y, scaled)
            overlay = QLinearGradient(0, 0, 0, self.height())
            overlay.setColorAt(0.0, QColor(0, 0, 0, 60))
            overlay.setColorAt(1.0, QColor(0, 0, 0, 165))
            painter.fillRect(rect, overlay)
            title_color = QColor("#FFFFFF")
            subtitle_color = QColor(255, 255, 255, 205)
        else:
            gradient = QLinearGradient(0, 0, self.width(), self.height())
            base = QColor(self._color)
            gradient.setColorAt(0.0, base.lighter(118))
            gradient.setColorAt(1.0, base.darker(118))
            painter.fillRect(rect, gradient)
            title_color = _readable_text_color(base)
            subtitle_color = QColor(title_color)
            subtitle_color.setAlpha(205)

        # 右上角数量徽标
        if self._badge:
            painter.setBrush(QColor(255, 255, 255, 58 if self._image else 70))
            painter.setPen(Qt.PenStyle.NoPen)
            badge_font = QFont(painter.font())
            badge_font.setPointSizeF(max(7.5, badge_font.pointSizeF() - 1.2))
            painter.setFont(badge_font)
            metrics = QFontMetrics(badge_font)
            text_width = metrics.horizontalAdvance(self._badge) + 18
            badge_rect = QRect(self.width() - text_width - 12, 12, text_width, 22)
            painter.drawRoundedRect(badge_rect, 11, 11)
            painter.setPen(title_color)
            painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, self._badge)

        # 图钉标记
        if self._pinned:
            painter.setBrush(QColor(255, 255, 255, 90))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(self.width() - 30, 12, 18, 18)
            pin_font = QFont(painter.font())
            pin_font.setPointSizeF(max(8.0, pin_font.pointSizeF() - 1.0))
            painter.setFont(pin_font)
            painter.setPen(title_color)
            painter.drawText(
                QRect(self.width() - 30, 12, 18, 18), Qt.AlignmentFlag.AlignCenter, "★"
            )

        # 标题（最多两行）
        title_font = QFont(painter.font())
        title_font.setPointSizeF(max(10.0, title_font.pointSizeF() + 1.6))
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(title_color)
        metrics = QFontMetrics(title_font)
        text_rect = QRect(16, self.height() - 62, self.width() - 32, 40)
        lines = _wrap_two_lines(metrics, self._title, text_rect.width())
        for index, line in enumerate(lines):
            painter.drawText(
                text_rect.adjusted(0, index * metrics.height(), 0, 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                line,
            )

        # 副标题
        if self._subtitle:
            sub_font = QFont(painter.font())
            sub_font.setPointSizeF(max(7.8, sub_font.pointSizeF() - 3.0))
            sub_font.setWeight(QFont.Weight.Normal)
            painter.setFont(sub_font)
            painter.setPen(subtitle_color)
            sub_metrics = QFontMetrics(sub_font)
            painter.drawText(
                QRect(16, self.height() - 22, self.width() - 32, 18),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                sub_metrics.elidedText(self._subtitle, Qt.TextElideMode.ElideRight, self.width() - 32),
            )

        # 描边
        painter.setClipping(False)
        if self._bordered:
            # 外层 2px 实色 + 内层 1px 半透明，形成"双框"观感更清楚；
            # 拖拽悬停时换成醒目的黄色，给出"可以放进来"的反馈。
            outer_color = QColor("#FFD166") if getattr(self, "_drop_active", False) \
                else QColor(self._border_color)
            outer = painter.pen()
            outer.setColor(outer_color)
            outer.setWidthF(2.0)
            painter.setPen(outer)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                QRect(1, 1, self.width() - 3, self.height() - 3),
                self._radius - 1, self._radius - 1,
            )
            inner = QColor(outer_color)
            inner.setAlpha(120)
            pen2 = painter.pen()
            pen2.setColor(inner)
            pen2.setWidthF(1.0)
            painter.setPen(pen2)
            painter.drawRoundedRect(
                QRect(5, 5, self.width() - 11, self.height() - 11),
                self._radius - 3, self._radius - 3,
            )
        elif self._selected or self._hover:
            pen = painter.pen()
            pen.setColor(QColor("#FFFFFF") if self._selected else QColor(255, 255, 255, 180))
            pen.setWidthF(2.4)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                QRect(1, 1, self.width() - 3, self.height() - 3),
                self._radius - 1, self._radius - 1,
            )
        # 拖放落点提示（左/右边缘的竖条）
        self.paint_drop_indicator(painter)
        painter.end()


def _wrap_two_lines(metrics: QFontMetrics, text: str, width: int, max_lines: int = 2) -> list[str]:
    """把标题折成最多两行，超长用省略号。"""
    text = (text or "").strip()
    if not text:
        return [""]
    lines: list[str] = []
    remaining = text
    while remaining and len(lines) < max_lines:
        if metrics.horizontalAdvance(remaining) <= width:
            lines.append(remaining)
            remaining = ""
            break
        cut = len(remaining)
        while cut > 1 and metrics.horizontalAdvance(remaining[:cut]) > width:
            cut -= 1
        lines.append(remaining[:cut])
        remaining = remaining[cut:].lstrip()
    if remaining:
        last = lines[-1]
        while last and metrics.horizontalAdvance(last + "…") > width:
            last = last[:-1]
        lines[-1] = last + "…"
    return lines


# --------------------------------------------------------------------------

class BoxCard(InfoCard):
    """收纳箱卡片。

    样式与 :class:`SubjectCard` **完全一致**（同样的尺寸、圆角、渐变、徽标、
    标题与副标题排版），区别只在于多了一圈固定边框 —— 这是需求要求的
    "增加边框表示区分"。另外徽标显示的是箱内的科目数。

    它同时是拖放目标：

    * 拖来**科目** -> 收进这个箱子（``subjects_dropped``）；
    * 拖来**另一个收纳箱** -> 调整顺序（``card_dropped``）。
    """

    #: (收纳箱 id, 科目目录名列表)
    subjects_dropped = pyqtSignal(str, list)

    def __init__(
        self,
        box,                                   # Box（避免导入循环，鸭子类型）
        subjects: list[Subject] | None = None,
        cover: Path | None = None,
        parent: QWidget | None = None,
        width: int = 196,
        height: int = 124,
        radius: int = 14,
        border_color: str = "#FFFFFF",
    ) -> None:
        super().__init__(parent, width, height, radius)
        self.box = box
        self.subjects = list(subjects or [])
        self.set_bordered(True, border_color)
        self.setAcceptDrops(True)
        self._refresh()
        if cover is not None:
            self.set_image(cover)

    # -- 拖放 -----------------------------------------------------------

    def _accepts_drag(self, mime) -> bool:
        return mime.hasFormat(SUBJECT_MIME) or mime.hasFormat(BOX_MIME)

    def _drag_mime(self) -> str:
        return BOX_MIME

    def _drag_payload(self) -> str | None:
        return self.box.id if self.box is not None else None

    def dropEvent(self, event) -> None:  # noqa: N802
        mime = event.mimeData()
        self._drop_active = False
        self.update()
        if mime.hasFormat(SUBJECT_MIME):
            raw = bytes(mime.data(SUBJECT_MIME)).decode("utf-8", errors="replace")
            names = [name for name in raw.split("\n") if name]
            if names:
                self.subjects_dropped.emit(self.box.id, names)
                event.acceptProposedAction()
                return
        # 收纳箱拖到收纳箱上 = 调整顺序（交给 HomeView 处理）
        super().dropEvent(event)

    def _refresh(self) -> None:
        box = self.box
        names = [subject.title for subject in self.subjects]
        self.set_title(box.title)
        self.set_color(box.color or "#4F7CFF")
        self.set_badge(f"{len(names)} 个科目")
        self.set_subtitle(common.elide("、".join(names) if names else "空收纳箱", 28))
        self.setToolTip(
            f"收纳箱：{box.title}\n"
            f"包含 {len(names)} 个科目\n\n"
            + ("\n".join(f"· {name}" for name in names) if names else "（还没有放入科目）")
            + "\n\n单击打开收纳箱；右键可以重命名、换色或删除（不会删除科目）"
            + "\n拖动可调整收纳箱顺序；把科目拖到这里即可收进箱子"
        )

    def update_from(self, box, subjects: list[Subject] | None = None,
                    cover: Path | None = None) -> None:
        self.box = box
        self.subjects = list(subjects or [])
        self._refresh()
        self.set_image(cover)


class SubjectCard(InfoCard):
    """科目卡片。

    可拖动（拖到收纳箱=收进去，拖到别的科目=调整顺序），
    也可以作为拖放目标（拖来收纳箱=调整收纳箱顺序）。
    """

    def __init__(self, subject: Subject, cover: Path | None = None, parent: QWidget | None = None,
                 width: int = 196, height: int = 124, radius: int = 14) -> None:
        super().__init__(parent, width, height, radius)
        self.subject = subject
        self.setAcceptDrops(True)
        self._refresh()
        if cover is not None:
            self.set_image(cover)

    def _accepts_drag(self, mime) -> bool:
        return mime.hasFormat(SUBJECT_MIME) or mime.hasFormat(BOX_MIME)

    def _refresh(self) -> None:
        subject = self.subject
        self.set_title(subject.title)
        self.set_color(subject.color or "#4F7CFF")
        self.set_badge(f"{subject.book_count} 本")
        self.set_pinned(subject.pinned)
        subtitle = subject.description or f"{subject.file_count} 个文件"
        self.set_subtitle(common.elide(f"{subject.type_label} · {subtitle}", 28) if subject.type_label else common.elide(subtitle, 28))
        self.setToolTip(
            f"{subject.title}（{subject.type_label}）\n"
            f"位置：{subject.path}\n"
            f"书目：{subject.book_count} 本\n"
            f"文件：{subject.file_count} 个（{subject.size_label}）\n"
            f"创建：{subject.created_label}"
        )

    def update_from(self, subject: Subject, cover: Path | None = None) -> None:
        self.subject = subject
        self._refresh()
        self.set_image(cover)

    # -- 拖拽：把科目卡片拖到收纳箱上即可收进去 ---------------------

    def _drag_mime(self) -> str:
        return SUBJECT_MIME

    def _drag_payload(self) -> str | None:
        return self.subject.name if self.subject is not None else None


class BookCard(InfoCard):
    """书目卡片。"""

    def __init__(self, book: Book, parent: QWidget | None = None,
                 width: int = 196, height: int = 124, radius: int = 14) -> None:
        super().__init__(parent, width, height, radius)
        self.book = book
        self._refresh()

    def _refresh(self) -> None:
        book = self.book
        self.set_title(book.title)
        self.set_color(book.color or "#4F7CFF")
        self.set_badge(f"{book.summary_source_count} 份资料")
        self.set_pinned(book.pinned)
        status = "已生成总结" if book.has_summary else "尚未生成总结"
        self.set_subtitle(status)
        self.setToolTip(
            f"{book.title}\n"
            f"位置：{book.path}\n"
            f"笔记与易错题：{book.summary_source_count} 份\n"
            f"总结更新时间：{book.summary_label}\n"
            f"{book.description}" if book.description else ""
        )

    def update_from(self, book: Book) -> None:
        self.book = book
        self._refresh()


# --------------------------------------------------------------------------
# 自适应网格
# --------------------------------------------------------------------------

class CardGrid(QWidget):
    """按可用宽度自动换行的卡片网格。

    卡片数量由数据决定（扫描结果），因此行数/列数都不写死。
    """

    card_activated = pyqtSignal(object)          # 单击
    card_opened = pyqtSignal(object)             # 双击
    card_context = pyqtSignal(object, QPoint)    # 右键
    empty_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None, spacing: int = 16, padding: int = 4) -> None:
        super().__init__(parent)
        self._cards: list[InfoCard] = []
        self._spacing = spacing
        self._padding = padding
        self._selected: InfoCard | None = None
        #: 外面告诉我们的"最多能有多宽"（0 = 还没告诉，按自身宽度算）。
        #:
        #: **为什么需要它**：列数原来是按 ``self.width()`` 算的，而宽度又由
        #: ``minimumSizeHint()``（= 所有卡片排成一行的宽度）决定 —— 两者互相
        #: 依赖，网格就永远"不肯变窄"。
        #: 于是窗口变窄、或者展开右侧日程栏时，网格仍然是 816px 宽，
        #: 第三列被滚动区右缘裁掉 —— 用户看到的现象是
        #: "日程栏把科目卡片遮住了"（其实是裁掉了）。
        #: 有了这个值，列数就跟着**可见宽度**走，窄了就自动少排几列。
        self._available_width = 0
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

    # -- 内容 -----------------------------------------------------------

    def clear(self) -> None:
        for card in self._cards:
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()
        self._selected = None
        self._relayout()

    def add_card(self, card: InfoCard) -> None:
        card.setParent(self)
        card.clicked.connect(lambda c=card: self._on_clicked(c))
        card.double_clicked.connect(lambda c=card: self.card_opened.emit(_card_identity(c)))
        card.context_requested.connect(lambda pos, c=card: self._on_context(c, pos))
        card.show()
        self._cards.append(card)
        self._relayout()

    def set_cards(self, cards: list[InfoCard]) -> None:
        self.clear()
        for card in cards:
            self.add_card_no_relayout(card)
        self._relayout()

    def add_card_no_relayout(self, card: InfoCard) -> None:
        card.setParent(self)
        card.clicked.connect(lambda c=card: self._on_clicked(c))
        card.double_clicked.connect(lambda c=card: self.card_opened.emit(_card_identity(c)))
        card.context_requested.connect(lambda pos, c=card: self._on_context(c, pos))
        card.show()
        self._cards.append(card)

    @property
    def cards(self) -> list[InfoCard]:
        return list(self._cards)

    @property
    def count(self) -> int:
        return len(self._cards)

    # -- 交互 -----------------------------------------------------------

    def _on_clicked(self, card: InfoCard) -> None:
        if self._selected is not None and self._selected is not card:
            self._selected.set_selected(False)
        self._selected = card
        card.set_selected(True)
        self.card_activated.emit(_card_identity(card))

    def _on_context(self, card: InfoCard, pos: QPoint) -> None:
        self._on_clicked(card)
        global_pos = card.mapToGlobal(pos)
        # 与 card_opened / card_activated 保持一致：**派发卡片本身**。
        # 曾经这里派发 _card_model(card)（科目会变成 Subject 模型），
        # 接收方按卡片判断就静默失败，表现是"右键没反应"。
        self.card_context.emit(_card_identity(card), global_pos)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            if self._selected is not None:
                self._selected.set_selected(False)
                self._selected = None
            self.empty_clicked.emit()
        super().mousePressEvent(event)

    # -- 布局 -----------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def sizeHint(self) -> QSize:  # noqa: N802
        """理想尺寸：所有卡片排成一行。

        这只是"如果空间足够，我想这么宽"，**不是最小需求** ——
        最小需求见 :meth:`minimumSizeHint`。
        """
        return self._compute_size(columns=len(self._cards) or 1)

    def minimumSizeHint(self) -> QSize:  # noqa: N802
        """**最小**需求：只放一列。

        这一点很关键：以前这里返回的是"排成一行"的宽度，
        于是整个科目区的最小宽度被钉在 816px —— 窗口再窄、
        右侧日程栏再怎么占地方，布局都不肯把科目区压小，
        结果就是卡片被裁掉。
        现在最小需求只有一列宽，科目区可以随窗口自由收缩。
        """
        return self._compute_size(columns=1)

    def set_available_width(self, width: int) -> None:
        """告诉网格"你最多能有多宽"，并立即重新排布。

        由 ``HomeView`` 在滚动区尺寸变化时调用（传入视口宽度）。
        传 0 表示取消限制。
        """
        width = int(width)
        if width == self._available_width:
            return
        self._available_width = width
        self._relayout()

    # -- 布局 -----------------------------------------------------------

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def _layout_width(self) -> int:
        """算列数时该用的宽度。

        优先用外面告诉我们的可用宽度；没有的话退回自身宽度。
        """
        if self._available_width > 0:
            return self._available_width
        return self.width()

    def _columns(self) -> int:
        if not self._cards:
            return 1
        card_width = self._cards[0].width()
        available = max(card_width, self._layout_width() - self._padding * 2)
        columns = max(1, (available + self._spacing) // (card_width + self._spacing))
        return int(columns)

    def _relayout(self) -> None:
        if not self._cards:
            self.setMinimumHeight(10)
            self.updateGeometry()
            return
        card_height = self._cards[0].height()
        columns = self._columns()
        for index, card in enumerate(self._cards):
            row, column = divmod(index, columns)
            x = self._padding + column * (card.width() + self._spacing)
            y = self._padding + row * (card_height + self._spacing)
            card.move(int(x), int(y))
        self.setMinimumHeight(self._compute_size(columns=columns).height())
        self.updateGeometry()

    def _compute_size(self, columns: int | None = None) -> QSize:
        if not self._cards:
            return QSize(0, 10)
        card_width = self._cards[0].width()
        card_height = self._cards[0].height()
        if columns is None:
            columns = self._columns()
        columns = max(1, int(columns))
        rows = (len(self._cards) + columns - 1) // columns
        width = columns * card_width + (columns - 1) * self._spacing + self._padding * 2
        height = rows * card_height + (rows - 1) * self._spacing + self._padding * 2
        return QSize(int(width), int(height))


def _card_identity(card: InfoCard) -> Any:
    """单击/双击信号派发用的对象。

    **始终返回卡片本身**。曾经这里会在科目卡片上返回 ``Subject`` 模型
    （因为 ``SubjectCard.subject`` 非空），结果是接收方拿到的有时是卡片、
    有时是模型，判断 ``isinstance(card, BoxCard)``/``getattr(card, "subject")``
    就会静默失败 —— 表现就是"点击科目卡片没反应"。
    接收方需要数据时自己从卡片上取（``card.subject`` / ``card.box``）。
    """
    return card


def build_context_menu(
    parent: QWidget,
    actions: list,
) -> QMenu:
    """根据动作列表生成右键菜单。

    每一项可以是：

    * ``None`` -> 分隔线；
    * ``(标题, 回调)`` -> 普通可点项；
    * ``(标题, 回调, False)`` -> **禁用**项（灰掉但仍显示，用来说明"为什么不能点"）。
    """
    menu = QMenu(parent)
    for entry in actions:
        if entry is None:
            menu.addSeparator()
            continue
        text = entry[0]
        callback = entry[1] if len(entry) > 1 else None
        enabled = entry[2] if len(entry) > 2 else True
        action = QAction(text, menu)
        action.setEnabled(bool(enabled) and callback is not None)
        if callback is not None:
            action.triggered.connect(lambda _checked=False, cb=callback: cb())
        menu.addAction(action)
    return menu


__all__ = [
    "BookCard",
    "BoxCard",
    "CardGrid",
    "InfoCard",
    "SubjectCard",
    "build_context_menu",
]
