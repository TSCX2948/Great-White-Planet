"""Markdown 编辑器控件：源码编辑 + 实时预览 + 查找。

需求文档第八节：
* 双击 Markdown 进入查看模式；
* 编辑模式可以编辑 Markdown，并保留 AI 交互功能。

本控件只负责"显示与编辑"，不负责 AI，也不负责窗口管理。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QRegularExpression, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gwp.core.config import Config
from gwp.services.markdown_renderer import RenderOptions, render_document

log = logging.getLogger(__name__)


class LineNumberArea(QWidget):
    """行号栏。"""

    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):  # noqa: N802
        from PyQt6.QtCore import QSize

        return QSize(self.editor.line_number_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        self.editor.paint_line_numbers(event)


class MarkdownHighlighter(QSyntaxHighlighter):
    """轻量 Markdown 语法高亮（标题、强调、代码、链接、列表）。"""

    def __init__(self, document: QTextDocument, theme: str = "light") -> None:
        super().__init__(document)
        dark = str(theme).lower() == "dark"
        self.rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        def add(pattern: str, color: str, bold: bool = False, italic: bool = False) -> None:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            if italic:
                fmt.setFontItalic(True)
            self.rules.append((QRegularExpression(pattern), fmt))

        heading = "#8E63CE" if dark else "#7B4FBF"
        code = "#C3E88D" if dark else "#3E9E5F"
        link = "#6E96FF" if dark else "#2F7FA8"
        quote = "#9BA6B5" if dark else "#6B7787"
        bold = "#F2814B" if dark else "#C05A18"

        add(r"^#{1,6}\s.*$", heading, bold=True)
        add(r"\*\*[^*]+\*\*", bold, bold=True)
        add(r"(?<!\*)\*[^*]+\*(?!\*)", bold, italic=True)
        add(r"`[^`]+`", code)
        add(r"!?\[[^\]]*\]\([^)]*\)", link)
        add(r"^>\s.*$", quote, italic=True)
        add(r"^\s*[-*+]\s", "#4F7CFF")
        add(r"^\s*\d+\.\s", "#4F7CFF")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for expression, fmt in self.rules:
            iterator = expression.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class CodeEditor(QPlainTextEdit):
    """带行号的纯文本编辑器。"""

    def __init__(self, parent: QWidget | None = None, config: Config | None = None) -> None:
        super().__init__(parent)
        self.config = config or Config.load()
        self.line_area = LineNumberArea(self)
        self.blockCountChanged.connect(lambda _: self._update_line_area_width())
        self.updateRequest.connect(self._on_update_request)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._apply_font()
        self._update_line_area_width()
        self._highlight_current_line()

    def _apply_font(self) -> None:
        family = str(self.config.get("editor.font_family", "Consolas") or "Consolas")
        size = int(self.config.get("editor.font_size", 11) or 11)
        tab = int(self.config.get("editor.tab_width", 4) or 4)
        font = QFont(family, size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * tab)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

    def refresh_theme(self) -> None:
        self._highlight_current_line()
        self.line_area.update()

    def line_number_width(self) -> int:
        digits = max(3, len(str(max(1, self.blockCount()))))
        return 12 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_area_width(self) -> None:
        self.setViewportMargins(self.line_number_width(), 0, 0, 0)

    def _on_update_request(self, rect, dy: int) -> None:
        if dy:
            self.line_area.scroll(0, dy)
        else:
            self.line_area.update(0, rect.y(), self.line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        contents = self.contentsRect()
        self.line_area.setGeometry(
            contents.left(), contents.top(), self.line_number_width(), contents.height()
        )

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self.line_area)
        dark = str(self.config.get("ui.theme", "light")).lower() == "dark"
        painter.fillRect(event.rect(), QColor("#1F242D") if dark else QColor("#F7F9FC"))
        painter.setPen(QColor("#6B7787") if not dark else QColor("#7A8698"))

        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        height = self.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.drawText(
                    0, int(top), self.line_area.width() - 6, height,
                    Qt.AlignmentFlag.AlignRight, str(number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            number += 1

    def _highlight_current_line(self) -> None:
        selection = QTextEdit.ExtraSelection()
        dark = str(self.config.get("ui.theme", "light")).lower() == "dark"
        selection.format.setBackground(QColor("#252B35") if dark else QColor("#F0F4FF"))
        selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])


class MarkdownEditor(QWidget):
    """Markdown 编辑区：左源码、右预览（可切换为仅源码 / 仅预览）。"""

    modified_changed = pyqtSignal(bool)
    saved = pyqtSignal(Path)
    cursor_info = pyqtSignal(int, int)          # 行, 列

    MODE_SPLIT = "split"
    MODE_SOURCE = "source"
    MODE_PREVIEW = "preview"

    def __init__(self, config: Config | None = None, parent: QWidget | None = None,
                 *, equation_dir: Path | None = None) -> None:
        super().__init__(parent)
        self.config = config or Config.load()
        self.path: Path | None = None
        #: 公式图片目录。给定时预览会把 LaTeX 公式渲染成图片 ——
        #: 否则 QTextBrowser 只支持 HTML4/CSS2.1 的一个子集，不认识 LaTeX，
        #: 会把 ``$\varepsilon > 0$`` 原样显示成源码（用户报障："公式显示异常"）。
        self.equation_dir = equation_dir
        self._loading = False
        self._mode = self.MODE_SPLIT

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # 工具条
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)
        self.btn_bold = self._tool_button("B", "加粗 (Ctrl+B)", self._wrap_bold, bold=True)
        self.btn_italic = self._tool_button("I", "斜体 (Ctrl+I)", self._wrap_italic, italic=True)
        self.btn_h1 = self._tool_button("H1", "一级标题", lambda: self._prefix_line("# "))
        self.btn_h2 = self._tool_button("H2", "二级标题", lambda: self._prefix_line("## "))
        self.btn_h3 = self._tool_button("H3", "三级标题", lambda: self._prefix_line("### "))
        self.btn_list = self._tool_button("•", "无序列表", lambda: self._prefix_line("- "))
        self.btn_quote = self._tool_button("❝", "引用", lambda: self._prefix_line("> "))
        self.btn_code = self._tool_button("</>", "代码块", self._insert_code_block)
        self.btn_table = self._tool_button("▤", "插入表格", self._insert_table)
        self.btn_link = self._tool_button("🔗", "插入链接 (Ctrl+K)", self._insert_link)
        for button in (
            self.btn_bold, self.btn_italic, self.btn_h1, self.btn_h2, self.btn_h3,
            self.btn_list, self.btn_quote, self.btn_code, self.btn_table, self.btn_link,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch(1)

        self.lbl_mode = QLabel("双栏")
        self.lbl_mode.setObjectName("Muted")
        toolbar.addWidget(self.lbl_mode)
        self.btn_preview = QToolButton()
        self.btn_preview.setText("仅预览")
        self.btn_preview.setCheckable(True)
        self.btn_preview.setToolTip("切换：双栏 / 仅预览")
        self.btn_preview.clicked.connect(self._toggle_preview_only)
        toolbar.addWidget(self.btn_preview)
        layout.addLayout(toolbar)

        # 编辑 + 预览
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.editor = CodeEditor(self, self.config)
        self.highlighter = MarkdownHighlighter(self.editor.document(), str(self.config.get("ui.theme", "light")))
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(True)
        self.preview.setStyleSheet("QTextBrowser { background: transparent; border: none; }")

        self.splitter.addWidget(self.editor)
        self.splitter.addWidget(self.preview)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        layout.addWidget(self.splitter, 1)

        self.editor.textChanged.connect(self._on_text_changed)
        self.editor.cursorPositionChanged.connect(self._emit_cursor_info)

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(320)
        self._preview_timer.timeout.connect(self.refresh_preview)

        self._dirty = False
        self.apply_mode(self.MODE_SPLIT)
        self._install_shortcuts()

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    @property
    def mode(self) -> str:
        return self._mode

    def text(self) -> str:
        return self.editor.toPlainText()

    def set_read_only(self, read_only: bool) -> None:
        self.editor.setReadOnly(read_only)
        for button in (
            self.btn_bold, self.btn_italic, self.btn_h1, self.btn_h2, self.btn_h3,
            self.btn_list, self.btn_quote, self.btn_code, self.btn_table, self.btn_link,
        ):
            button.setEnabled(not read_only)

    # ------------------------------------------------------------------
    # 载入 / 保存
    # ------------------------------------------------------------------

    def load_file(self, path: Path) -> bool:
        path = Path(path)
        try:
            text = self._read_text(path)
        except OSError as exc:
            log.exception("读取文件失败: %s", path)
            return False
        self._loading = True
        self.path = path
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        self._dirty = False
        self.modified_changed.emit(False)
        self._loading = False
        self.refresh_preview()
        self.editor.moveCursor(QTextCursor.MoveOperation.Start)
        return True

    @staticmethod
    def _read_text(path: Path) -> str:
        for encoding in ("utf-8", "utf-8-sig", "gbk", "gb18030", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise OSError("无法解码文件内容")

    def save(self, path: Path | None = None) -> bool:
        target = Path(path) if path else self.path
        if target is None:
            return False
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            text = self.text()
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_text(text, encoding="utf-8")
            tmp.replace(target)
        except OSError:
            log.exception("保存失败: %s", target)
            return False
        self.path = target
        self._dirty = False
        self.editor.document().setModified(False)
        self.modified_changed.emit(False)
        self.saved.emit(target)
        return True

    def insert_text(self, text: str, at_cursor: bool = True) -> None:
        """把文本插到光标处（AI 回答插入文档时用）。"""
        cursor = self.editor.textCursor() if at_cursor else self.editor.textCursor()
        if not at_cursor:
            cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def replace_all(self, text: str) -> None:
        self.editor.setPlainText(text)
        self._on_text_changed()

    def selected_text(self) -> str:
        return self.editor.textCursor().selectedText()

    # ------------------------------------------------------------------
    # 预览
    # ------------------------------------------------------------------

    def refresh_preview(self) -> None:
        options = RenderOptions(
            base_dir=self.path.parent if self.path else None,
            theme=str(self.config.get("ui.theme", "light")),
            title=self.path.name if self.path else "预览",
            # 公式渲染成图片（None 时保持原样，即显示 LaTeX 源码）
            equation_dir=self.equation_dir,
        )
        try:
            html = render_document(self.text(), options)
        except Exception:  # noqa: BLE001
            log.exception("预览渲染失败")
            html = "<p>预览渲染失败，请检查 Markdown 语法。</p>"
        scroll = self.preview.verticalScrollBar().value()
        self.preview.setHtml(html)
        self.preview.verticalScrollBar().setValue(scroll)

    def _on_text_changed(self) -> None:
        if self._loading:
            return
        if not self._dirty:
            self._dirty = True
            self.modified_changed.emit(True)
        if bool(self.config.get("editor.preview_live", True)) and self._mode != self.MODE_SOURCE:
            self._preview_timer.start()

    def _emit_cursor_info(self) -> None:
        cursor = self.editor.textCursor()
        self.cursor_info.emit(cursor.blockNumber() + 1, cursor.positionInBlock() + 1)

    # ------------------------------------------------------------------
    # 模式
    # ------------------------------------------------------------------

    def apply_mode(self, mode: str) -> None:
        self._mode = mode
        show_source = mode in (self.MODE_SPLIT, self.MODE_SOURCE)
        show_preview = mode in (self.MODE_SPLIT, self.MODE_PREVIEW)
        self.editor.setVisible(show_source)
        self.preview.setVisible(show_preview)
        self.lbl_mode.setText(
            {self.MODE_SPLIT: "双栏", self.MODE_SOURCE: "仅编辑", self.MODE_PREVIEW: "仅预览"}.get(mode, "")
        )
        self.btn_preview.setChecked(mode == self.MODE_PREVIEW)
        if show_preview:
            self.refresh_preview()

    def _toggle_preview_only(self) -> None:
        self.apply_mode(self.MODE_PREVIEW if self._mode != self.MODE_PREVIEW else self.MODE_SPLIT)

    def toggle_view_mode(self) -> None:
        """查看模式（只读预览）/ 编辑模式 之间切换。"""
        if self._mode == self.MODE_PREVIEW:
            self.apply_mode(self.MODE_SPLIT)
            self.set_read_only(False)
        else:
            self.apply_mode(self.MODE_PREVIEW)
            self.set_read_only(True)

    # ------------------------------------------------------------------
    # 格式化操作
    # ------------------------------------------------------------------

    def _tool_button(self, text: str, tip: str, callback, bold: bool = False, italic: bool = False) -> QToolButton:
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tip)
        button.setAutoRaise(True)
        button.setMinimumWidth(34)
        font = button.font()
        font.setBold(bold)
        font.setItalic(italic)
        button.setFont(font)
        button.clicked.connect(callback)
        return button

    def _wrap_selection(self, prefix: str, suffix: str = "") -> None:
        cursor = self.editor.textCursor()
        if not cursor.hasSelection():
            cursor.insertText(prefix + suffix)
            cursor.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.MoveAnchor, len(suffix))
        else:
            selected = cursor.selectedText()
            cursor.insertText(f"{prefix}{selected}{suffix or prefix}")
        self.editor.setTextCursor(cursor)
        self.editor.setFocus()

    def _wrap_bold(self) -> None:
        self._wrap_selection("**")

    def _wrap_italic(self) -> None:
        self._wrap_selection("*")

    def _prefix_line(self, prefix: str) -> None:
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()
        start = cursor.selectionStart()
        end = cursor.selectionEnd()
        cursor.setPosition(start)
        cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
        cursor.insertText(prefix)
        while cursor.position() < end + len(prefix):
            if not cursor.movePosition(QTextCursor.MoveOperation.NextBlock):
                break
            cursor.insertText(prefix)
            end += len(prefix)
        cursor.endEditBlock()
        self.editor.setFocus()

    def _insert_code_block(self) -> None:
        cursor = self.editor.textCursor()
        selected = cursor.selectedText()
        block = f"```\n{selected}\n```\n" if selected else "```\n\n```\n"
        cursor.insertText(block)
        self.editor.setFocus()

    def _insert_table(self) -> None:
        template = "| 列1 | 列2 |\n| --- | --- |\n|  |  |\n"
        self.editor.textCursor().insertText(template)
        self.editor.setFocus()

    def _insert_link(self) -> None:
        cursor = self.editor.textCursor()
        selected = cursor.selectedText() or "链接文字"
        cursor.insertText(f"[{selected}](https://)")
        self.editor.setFocus()

    def _install_shortcuts(self) -> None:
        for keys, slot in (
            (QKeySequence.StandardKey.Bold, self._wrap_bold),
            (QKeySequence.StandardKey.Italic, self._wrap_italic),
        ):
            action = QAction(self)
            action.setShortcut(keys)
            action.triggered.connect(slot)
            self.addAction(action)


class FindBar(QWidget):
    """查找栏（Ctrl+F）。"""

    def __init__(self, editor: QPlainTextEdit, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.editor = editor
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.input = QLineEdit()
        self.input.setPlaceholderText("查找内容，回车跳转下一个")
        self.input.returnPressed.connect(self.find_next)
        self.input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.input, 1)
        self.btn_prev = QPushButton("上一个")
        self.btn_prev.clicked.connect(self.find_previous)
        layout.addWidget(self.btn_prev)
        self.btn_next = QPushButton("下一个")
        self.btn_next.clicked.connect(self.find_next)
        layout.addWidget(self.btn_next)
        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(self.hide)
        layout.addWidget(self.btn_close)

    def start(self) -> None:
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            self.input.setText(cursor.selectedText())
        self.show()
        self.input.setFocus()
        self.input.selectAll()

    def _pattern(self) -> str:
        return self.input.text()

    def _on_text_changed(self, text: str) -> None:
        if not text:
            return
        self.find_next()

    def find_next(self) -> bool:
        return self._find(forward=True)

    def find_previous(self) -> bool:
        return self._find(forward=False)

    def _find(self, forward: bool) -> bool:
        pattern = self._pattern()
        if not pattern:
            return False
        flags = QTextDocument.FindFlag(0)
        if not forward:
            flags |= QTextDocument.FindFlag.FindBackward
        if self.editor.find(pattern, flags):
            return True
        # 从头再来一次
        cursor = self.editor.textCursor()
        cursor.movePosition(
            QTextCursor.MoveOperation.Start if forward else QTextCursor.MoveOperation.End
        )
        self.editor.setTextCursor(cursor)
        return bool(self.editor.find(pattern, flags))


__all__ = ["CodeEditor", "FindBar", "MarkdownEditor", "MarkdownHighlighter"]
