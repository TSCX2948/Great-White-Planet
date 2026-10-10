"""导出 PDF 的第二步询问框：是否加页码 + 要哪些页。

为什么放在这一步才问
--------------------
Markdown 在排版之前没有"页"的概念，也不存在 `e`（最后一页）这样的页码。
所以流程是：

1. 先把完整 PDF 排版到临时文件（此时才知道总页数）；
2. 弹出本对话框，告诉用户"文档共 N 页"，让他选页码范围并决定是否加页码；
3. 按选择抽取页面并写页码，产出最终文件。

页码写法（与常见打印对话框一致）
--------------------------------
* `1-3, 5, 8-10`：第 1~3、5、8~10 页
* `e`：最后一页；`e-1`：倒数第二页；`3-e`：第 3 页到最后一页
* 输入不合法会**当场提示**（例如 `2-1` 会提示区间反了），确定按钮同时禁用
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gwp.services import page_range as ranges
from gwp.ui import common


class PageRangeDialog(QDialog):
    """询问"是否加页码 + 导出哪些页"。"""

    def __init__(self, total_pages: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.total_pages = max(1, int(total_pages))
        self.setWindowTitle("导出设置确认")
        self.setMinimumWidth(520)
        self._parsed: ranges.PageRange | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(12)

        header = QLabel(
            f"文档已排版完成，共 <b>{self.total_pages}</b> 页。<br>"
            "请确认是否添加页码，以及要导出哪些页面。"
        )
        header.setTextFormat(Qt.TextFormat.RichText)
        header.setWordWrap(True)
        layout.addWidget(header)

        form = QFormLayout()
        form.setSpacing(10)

        self.check_numbers = QCheckBox("在每页页脚添加页码")
        self.check_numbers.setChecked(True)
        self.check_numbers.setToolTip("格式为「- 页码 / 总页数 -」，显示的是原文档中的页号")
        form.addRow("", self.check_numbers)

        row = QHBoxLayout()
        self.input_range = QLineEdit(self._default_range())
        self.input_range.setPlaceholderText("例如 1-3, 5, 8-10；留空表示全部")
        self.input_range.textChanged.connect(self._validate)
        row.addWidget(self.input_range, 1)
        self.btn_all = QPushButton("全部")
        self.btn_all.setToolTip("重置为导出全部页面")
        self.btn_all.clicked.connect(self._reset_all)
        row.addWidget(self.btn_all)
        holder = QWidget()
        holder.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        form.addRow("导出页范围", holder)

        layout.addLayout(form)

        hint = QLabel(
            "支持写法：<code>1-3</code>（区间）、<code>5</code>（单页）、"
            "<code>1-3, 7, 9-10</code>（多段）；<br>"
            "<code>e</code> 表示最后一页，<code>e-1</code> 是倒数第二页，"
            "<code>3-e</code> 是第 3 页到最后一页。"
        )
        hint.setTextFormat(Qt.TextFormat.RichText)
        hint.setWordWrap(True)
        hint.setObjectName("Muted")
        layout.addWidget(hint)

        self.lbl_result = QLabel("")
        self.lbl_result.setWordWrap(True)
        self.lbl_result.setObjectName("Subtitle")
        layout.addWidget(self.lbl_result)

        layout.addStretch(1)

        buttons = QDialogButtonBox()
        self.btn_ok = buttons.addButton("开始导出", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_ok.setProperty("accent", True)
        buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._validate()
        self.input_range.setFocus()
        self.input_range.selectAll()

    # ------------------------------------------------------------------

    def _default_range(self) -> str:
        return f"1-{self.total_pages}" if self.total_pages > 1 else "1"

    def _reset_all(self) -> None:
        self.input_range.setText(self._default_range())

    def _validate(self) -> None:
        """实时校验输入，把结果或错误显示出来，并控制确定按钮。"""
        text = self.input_range.text()
        try:
            parsed = ranges.parse_page_range(text, self.total_pages)
        except ranges.PageRangeError as exc:
            self._parsed = None
            self.lbl_result.setText(f"⚠ {exc}".replace("\n", " "))
            self.lbl_result.setStyleSheet("color: #D9534F;")
            self.btn_ok.setEnabled(False)
            return

        self._parsed = parsed
        self.lbl_result.setStyleSheet("")
        self.lbl_result.setText("将导出 " + ranges.describe(parsed.pages, self.total_pages))
        self.btn_ok.setEnabled(True)

    # ------------------------------------------------------------------

    @property
    def add_page_numbers(self) -> bool:
        return self.check_numbers.isChecked()

    def selected_pages(self) -> list[int]:
        """当前选中的页码（1 基）。输入非法时返回全部页。"""
        if self._parsed is None:
            return list(range(1, self.total_pages + 1))
        return list(self._parsed.pages)

    def accept(self) -> None:  # noqa: D102 - Qt 接口
        if self._parsed is None:
            # 理论上按钮已禁用，这里兜底再拦一次
            common.warn(self, self.lbl_result.text(), "页码范围有误")
            return
        super().accept()


__all__ = ["PageRangeDialog"]
