"""生成总结前的"资料清单"对话框。

用途变了
--------
这个对话框原来叫「资料预览」，让用户在花掉 AI 额度之前确认哪些文件会参与
**AI 写正文**。

需求变更后（*"summary中板块，不需要你补充内容了，按照用户上传的文件来，
不要AI识别文字了，直接插入图片或文件"*），**AI 不再写正文**，
所以"提示词预览""额外要求"这些都没有意义了 —— 留着反而会让用户以为
AI 还会改写内容。

现在它只做一件事：**如实列出会被插入 summary 的文件**（名字、来自哪个
栏目、多大），以及能算出多少页。这样用户在点下"生成总结"之前就知道
会得到什么，而不用等排完几百张图。
"""

from __future__ import annotations

from pathlib import Path

import fitz
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

#: 只对这些后缀去数页数（其余按 1 页算，省得为了预览把每份文档都解析一遍）
_PAGE_COUNT_SUFFIXES = {".pdf"}


def count_pages(path: Path) -> int:
    """数一个文件会插进来几页。数不出来就返回 1（当作一张图）。"""
    if Path(path).suffix.lower() not in _PAGE_COUNT_SUFFIXES:
        return 1
    try:
        with fitz.open(str(path)) as document:
            return max(1, document.page_count)
    except Exception:  # noqa: BLE001 - 预览而已，数不出来不该报错
        return 1


class SummarySourcesDialog(QDialog):
    """展示"将要插入 summary 的资料"清单。"""

    def __init__(
        self,
        book_title: str,
        sources: list[tuple[str, Path]],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"将插入的资料：{book_title}")
        self.resize(880, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)

        total_pages = 0
        total_bytes = 0
        rows: list[tuple[str, str, int, int]] = []
        for label, path in sources:
            path = Path(path)
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            pages = count_pages(path)
            total_pages += pages
            total_bytes += size
            rows.append((path.name, label, size, pages))

        head = QLabel(
            f"共 **{len(sources)}** 份资料，预计插入 **{total_pages}** 张图片，"
            f"源文件合计 {total_bytes / 1024 / 1024:.1f} MB。\n"
            "内容会**原样转成图片**插入 summary，AI 不改写文字；"
            "勾选「让 AI 重排页序」才会调用一次 AI（只读每页开头一小段）。"
        )
        head.setWordWrap(True)
        head.setTextFormat(Qt.TextFormat.MarkdownText)
        layout.addWidget(head)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["文件", "来自", "大小", "页/张"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 420)
        self.table.setColumnWidth(1, 240)
        self.table.setColumnWidth(2, 100)
        self.table.setRowCount(len(rows))
        for row, (name, label, size, pages) in enumerate(rows):
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(label))
            self.table.setItem(row, 2, QTableWidgetItem(f"{size / 1024:.0f} KB"))
            self.table.setItem(row, 3, QTableWidgetItem(str(pages)))
        self.table.resizeRowsToContents()
        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox()
        self.btn_go = buttons.addButton("开始生成", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_go.setProperty("accent", True)
        buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


__all__ = ["SummarySourcesDialog", "count_pages"]
