"""文档视图：Markdown 查看/编辑 + AI 双栏（需求文档第八节）。

* 查看模式：只读渲染预览；
* 编辑模式：左侧编辑、右侧实时预览，同时保留 AI 交互；
* 右上角按钮切换 AI 双栏；
* 双击书目里的 Markdown 会用这个视图打开。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from gwp.ai.chat_session import session_key
from gwp.bootstrap import AppContext
from gwp.core.eventbus import AI_FALLBACK, bus
from gwp.ui import common
from gwp.ui.widgets.chat_panel import ChatPanel
from gwp.ui.widgets.md_editor import FindBar, MarkdownEditor


class DocumentView(QWidget):
    """单个 Markdown 文件的查看/编辑视图。"""

    closed = pyqtSignal(object)                 # self
    status_message = pyqtSignal(str)
    request_pdf_export = pyqtSignal(Path)

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.path: Path | None = None
        self._ai_ever_shown = False
        self._session_key = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # ---- 顶部工具条 ----
        toolbar = QHBoxLayout()
        toolbar.setSpacing(6)

        self.lbl_path = QLabel("")
        self.lbl_path.setObjectName("SectionTitle")
        self.lbl_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        toolbar.addWidget(self.lbl_path, 1)

        self.lbl_state = QLabel("")
        self.lbl_state.setObjectName("Muted")
        toolbar.addWidget(self.lbl_state)

        self.btn_mode = QPushButton("编辑")
        self.btn_mode.setToolTip("在查看模式与编辑模式之间切换")
        self.btn_mode.clicked.connect(self.toggle_edit_mode)
        toolbar.addWidget(self.btn_mode)

        self.btn_ai = QPushButton("AI 双栏")
        self.btn_ai.setCheckable(True)
        self.btn_ai.setToolTip("显示/隐藏右侧 AI 聊天面板")
        self.btn_ai.toggled.connect(self.set_ai_visible)
        toolbar.addWidget(self.btn_ai)

        self.btn_save = QPushButton("保存")
        self.btn_save.setProperty("accent", True)
        self.btn_save.setShortcut(QKeySequence.StandardKey.Save)
        self.btn_save.clicked.connect(lambda: self.save())
        toolbar.addWidget(self.btn_save)

        self.btn_pdf = QPushButton("导出 PDF")
        self.btn_pdf.clicked.connect(lambda: self.path and self.request_pdf_export.emit(self.path))
        toolbar.addWidget(self.btn_pdf)

        self.btn_system = QPushButton("用其它程序打开")
        self.btn_system.clicked.connect(self._open_external)
        toolbar.addWidget(self.btn_system)

        self.btn_close = QPushButton("关闭")
        self.btn_close.clicked.connect(lambda: self.closed.emit(self))
        toolbar.addWidget(self.btn_close)
        layout.addLayout(toolbar)

        # ---- 主体 ----
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        # 公式图片目录：预览时把 LaTeX 渲染成图片（QTextBrowser 不认识 LaTeX）
        _equation_dir = None
        try:
            _equation_dir = context.paths.else_data / "equations"
        except Exception:  # noqa: BLE001 - 拿不到路径时退化成"显示源码"
            _equation_dir = None
        self.editor = MarkdownEditor(context.config, equation_dir=_equation_dir)
        self.editor.modified_changed.connect(self._on_modified)
        self.editor.cursor_info.connect(self._on_cursor)
        self.splitter.addWidget(self.editor)

        self.chat = ChatPanel(context)
        self.chat.insert_requested.connect(self._insert_ai_text)
        self.chat.status_message.connect(self.status_message.emit)
        self.splitter.addWidget(self.chat)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 2)
        self.chat.setVisible(False)
        layout.addWidget(self.splitter, 1)

        self.find_bar = FindBar(self.editor.editor)
        self.find_bar.setVisible(False)
        layout.addWidget(self.find_bar)
        find_shortcut = QShortcut(QKeySequence.StandardKey.Find, self)
        find_shortcut.activated.connect(self.find_bar.start)

        # 自动保存
        self._autosave = QTimer(self)
        self._autosave.timeout.connect(self._maybe_autosave)
        seconds = int(context.config.get("editor.autosave_seconds", 20) or 0)
        if seconds > 0:
            self._autosave.start(seconds * 1000)

        bus.subscribe(AI_FALLBACK, self._on_fallback)

    # ==================================================================

    def open_file(self, path: Path) -> bool:
        path = Path(path)
        if not self.editor.load_file(path):
            common.error(self, f"无法打开文件：{path}", "打开失败")
            return False
        self.path = path
        try:
            relative = path.relative_to(self.context.paths.user_data).as_posix()
        except ValueError:
            relative = str(path)
        self.lbl_path.setText(f"{path.name}")
        self.lbl_path.setToolTip(str(path))
        self.set_ai_visible(False)
        self.editor.apply_mode(MarkdownEditor.MODE_PREVIEW)
        self.editor.set_read_only(True)
        self._update_mode_button()
        self._update_state()

        self._session_key = session_key(relative)
        self.chat.bind_document(path, self._session_key, title=relative)
        self._ai_ever_shown = False
        self.setWindowTitleHint()
        return True

    def setWindowTitleHint(self) -> None:
        window = self.window()
        if window is not None and hasattr(window, "setWindowTitle"):
            window.setWindowTitle(f"{self.path.name if self.path else '文档'} — Great White Planet")

    # ==================================================================

    @property
    def is_editing(self) -> bool:
        return self.editor.mode != MarkdownEditor.MODE_PREVIEW

    @property
    def has_unsaved(self) -> bool:
        return self.editor.is_dirty

    def toggle_edit_mode(self) -> None:
        if self.is_editing:
            self.editor.apply_mode(MarkdownEditor.MODE_PREVIEW)
            self.editor.set_read_only(True)
            self.status_message.emit("已切换到查看模式")
        else:
            self.editor.apply_mode(MarkdownEditor.MODE_SPLIT)
            self.editor.set_read_only(False)
            self.editor.editor.setFocus()
            self.status_message.emit("已切换到编辑模式")
        self._update_mode_button()

    def _update_mode_button(self) -> None:
        self.btn_mode.setText("查看" if self.is_editing else "编辑")
        self.btn_save.setEnabled(True)

    def set_ai_visible(self, visible: bool) -> None:
        self.chat.setVisible(visible)
        self.btn_ai.setChecked(visible)
        if not visible:
            self.chat.save_session()
        if visible:
            sizes = self.splitter.sizes()
            if sizes and sizes[1] < 200:
                total = sum(sizes)
                self.splitter.setSizes([int(total * 0.6), int(total * 0.4)])
        if visible and not self._ai_ever_shown:
            # 需求文档：首次在文件中打开 AI 时自动发送当前文件。
            # 这里直接调用（不依赖定时器），保证行为可预期；AI 请求本身在后台线程执行，不会卡界面。
            self._ai_ever_shown = True
            if bool(self.context.config.get("ai.auto_send_current_file", True)):
                self.chat.resend_file(force=False)

    def _on_fallback(self, from_provider: str = "", to_provider: str = "", to_label: str = "", reason: str = "", **_kwargs) -> None:
        if self.chat.isVisible():
            common.warn(
                self,
                f"主 AI 不可用，已自动切换到「{to_label or to_provider}」继续。\n\n原因：{reason}",
                "已切换到兜底 AI",
            )

    # ==================================================================

    def save(self, force: bool = False) -> bool:
        if self.path is None:
            return False
        if not self.editor.is_dirty and not force:
            self.status_message.emit("没有需要保存的修改")
            return True
        if self.editor.save():
            self._update_state()
            self.status_message.emit(f"已保存：{self.path.name}")
            return True
        common.error(self, f"保存失败：{self.path}", "保存失败")
        return False

    def _maybe_autosave(self) -> None:
        if self.editor.is_dirty and self.path is not None:
            if self.editor.save():
                self._update_state()
                self.status_message.emit("已自动保存")

    def _on_modified(self, dirty: bool) -> None:
        self._update_state()

    def _update_state(self) -> None:
        dirty = " · 未保存" if self.editor.is_dirty else ""
        self.lbl_state.setText(f"{'只读' if not self.is_editing else '编辑中'}{dirty}")

    def _on_cursor(self, line: int, column: int) -> None:
        self.status_message.emit(f"第 {line} 行，第 {column} 列")

    def _insert_ai_text(self, text: str) -> None:
        if not self.is_editing:
            self.toggle_edit_mode()
        self.editor.insert_text(text)
        self.status_message.emit("已把 AI 回答插入文档")
        self._update_state()

    def _open_external(self) -> None:
        if self.path is None:
            return
        from gwp.services import file_ops

        if not file_ops.open_with_system(self.path):
            common.warn(self, "无法用系统默认程序打开该文件。")

    # ==================================================================

    def confirm_close(self) -> bool:
        """确认可以关闭；返回 False 表示用户取消。"""
        if self.chat.is_busy():
            if not common.confirm(self, "AI 正在回答，确定要关闭吗？", "确认关闭"):
                return False
            self.chat.wait_for_idle()
        else:
            self.chat.save_session()

        if not self.editor.is_dirty:
            return True
        box_text = f"「{self.path.name if self.path else '文档'}」有未保存的修改，要保存吗？"
        from PyQt6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle("未保存的修改")
        box.setText(box_text)
        box.setIcon(QMessageBox.Icon.Question)
        save_button = box.addButton("保存", QMessageBox.ButtonRole.AcceptRole)
        discard_button = box.addButton("不保存", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is save_button:
            return self.save()
        if clicked is discard_button:
            return True
        return False

    def apply_theme(self) -> None:
        editor = self.editor.editor
        self.editor.highlighter = self.editor.highlighter.__class__(
            editor.document(), str(self.context.config.get("ui.theme", "light"))
        )
        self.editor.refresh_preview()
        editor.refresh_theme()
        self.chat._render()


__all__ = ["DocumentView"]
