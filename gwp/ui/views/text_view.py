"""纯文本查看器：在软件内部打开 JSON / 源码 / 配置类文件。

为什么要它
----------

需求是"双击文件时在**软件内部**打开"，而 JSON 又要求优先用 VSCode。
但 VSCode 不一定装了（或者装在奇怪的位置），这时必须有个兜底 ——
总不能又弹回资源管理器或者让系统随便找个程序打开。

所以：

* **JSON**：先试 VSCode（见 ``file_ops.open_in_vscode``），失败落到这里；
* **其它文本/源码**（yaml / ini / py / log …）：直接在这里打开；
* 只读展示 + 查找，不做编辑 —— 这些文件不是用户的学习资料，
  改它们应该在 VSCode 里改（这里也就不必承担"改坏了"的责任）。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QWidget,
)

from gwp.bootstrap import AppContext
from gwp.ui import common
from gwp.ui.views.base_view import BaseView

log = logging.getLogger(__name__)

#: 超过这个大小就不整个读进来（避免把几百 MB 的日志拖死界面）
MAX_BYTES = 4 * 1024 * 1024


class TextView(BaseView):
    """只读文本查看页。"""

    closed = pyqtSignal(object)           # self

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self._path: Path | None = None

        self.add_action("✕ 关闭", lambda: self.closed.emit(self),
                        tooltip="关掉这个查看页")
        self.btn_vscode = self.add_action(
            "用 VSCode 打开", self._open_in_vscode,
            tooltip="用 VSCode 打开这个文件（可以编辑）",
        )
        self.btn_reload = self.add_action("重新载入", self.reload, tooltip="从磁盘重新读取")
        self.btn_copy = self.add_action("复制全部", self._copy_all, tooltip="把全文复制到剪贴板")

        head = QHBoxLayout()
        head.setSpacing(8)
        self.lbl_info = QLabel("")
        self.lbl_info.setObjectName("Muted")
        head.addWidget(self.lbl_info)
        head.addStretch(1)
        self.check_wrap = QCheckBox("自动换行")
        self.check_wrap.setChecked(False)
        self.check_wrap.toggled.connect(self._apply_wrap)
        head.addWidget(self.check_wrap)
        self.body.addLayout(head)

        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.set_text_font()
        self.body.addWidget(self.editor, 1)

    # ------------------------------------------------------------------

    def set_text_font(self) -> None:
        family = str(self.context.config.get("editor.font_family", "Consolas") or "Consolas")
        size = int(self.context.config.get("editor.font_size", 11) or 11)
        font = QFont(family, size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.editor.setFont(font)

    def open_file(self, path: Path | str) -> bool:
        """载入一个文本文件。失败会弹提示并返回 False。"""
        target = Path(path)
        if not target.is_file():
            common.warn(self, f"文件不存在：\n{target}", "无法打开")
            return False
        try:
            size = target.stat().st_size
            if size > MAX_BYTES:
                common.warn(
                    self,
                    f"文件太大（{size / 1024 / 1024:.1f} MB），不在软件内打开。\n\n"
                    "可以用「用 VSCode 打开」或右键「在资源管理器中显示」。",
                    "文件过大",
                )
                return False
            # JSON 可能是 UTF-8，也可能带 BOM；用 errors="replace" 保证不崩
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            common.error(self, f"读取失败：{exc}", "无法打开")
            return False
        self._path = target
        self.editor.setPlainText(text)
        self.set_title(target.name, str(target))
        self.lbl_info.setText(
            f"{target.suffix.lstrip('.').upper() or '文本'} · "
            f"{size} 字节 · {len(text.splitlines())} 行（只读）"
        )
        return True

    def reload(self) -> None:
        if self._path is not None:
            self.open_file(self._path)

    def _apply_wrap(self, checked: bool) -> None:
        self.editor.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth if checked
            else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def _copy_all(self) -> None:
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(self.editor.toPlainText())
        self.status_message.emit("已复制全部内容")

    def _open_in_vscode(self) -> None:
        from gwp.services import file_ops

        if self._path is None:
            return
        if file_ops.open_in_vscode(self._path):
            self.status_message.emit(f"已用 VSCode 打开：{self._path.name}")
        else:
            common.warn(
                self,
                "没有找到 VSCode。\n\n"
                "可以安装 VSCode（装完会自动加入 PATH），"
                "或右键文件选「在资源管理器中显示」自己打开。",
                "找不到 VSCode",
            )

    def refresh(self) -> None:
        pass


__all__ = ["TextView"]
