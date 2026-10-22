"""新增 / 编辑论坛的对话框。

需求
----
> 论坛添加新增/删除论坛功能，需要用户提供论坛名称 网址

设计上的几个取舍：

* **两个字段就够**（名称 + 网址）。多一个字段就多一个要解释的东西，
  而论坛这件事本来就只需要"叫什么、去哪"。
* **网址自动补协议**：用户写 ``cs9.x-way.work`` 是很正常的，
  自动变成 ``https://cs9.x-way.work`` 比报错让他重填友好得多。
* **边输边校验**：点确定时才报错，用户要来回改；
  输入框下方实时显示提示，一眼就知道差什么。
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from gwp.data_manager import forum_store
from gwp.ui import common


class ForumDialog(QDialog):
    """一个论坛的名称 + 网址。

    ``existing`` 传入时是"编辑"（名称预填、校验重复时排除自己）；
    ``taken`` 是已被占用的名称列表。
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        existing: forum_store.Forum | None = None,
        taken: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._existing = existing
        self._taken = [n for n in (taken or [])
                       if existing is None or n != existing.name]
        self.setWindowTitle("编辑论坛" if existing else "新增论坛")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_edit = QLineEdit(existing.name if existing else "")
        self.name_edit.setPlaceholderText("例如：牢大CS")
        self.name_edit.setMaxLength(forum_store.MAX_NAME_LEN)
        form.addRow("名称", self.name_edit)

        self.url_edit = QLineEdit(existing.url if existing else "")
        self.url_edit.setPlaceholderText("例如：cs9.x-way.work（可省略 https://）")
        form.addRow("网址", self.url_edit)

        layout.addLayout(form)

        self.hint = QLabel("")
        self.hint.setObjectName("Muted")
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)

        note = QLabel(
            "点菜单里的论坛名称会用**系统默认浏览器**打开它 —— "
            "登录态、Cookie 都和你平时上网一致。"
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        layout.addWidget(note)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "保存" if existing else "添加"
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._buttons = buttons

        self.name_edit.textChanged.connect(self._refresh_hint)
        self.url_edit.textChanged.connect(self._refresh_hint)
        self._refresh_hint()

    # -- 校验 ---------------------------------------------------------------

    def _problems(self) -> tuple[str, str]:
        """返回 ``(名称的问题, 网址的问题)``，空串表示没问题。"""
        name_error = forum_store.validate_name(
            self.name_edit.text(), taken=self._taken
        )
        url_error = forum_store.validate_url(self.url_edit.text())
        return name_error, url_error

    def _refresh_hint(self) -> None:
        """实时提示：错了说错在哪，对了就把补全后的网址显示出来。"""
        name_error, url_error = self._problems()
        ok = not name_error and not url_error
        self._buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)
        if ok:
            normalized = forum_store.normalize_url(self.url_edit.text())
            if normalized and normalized != self.url_edit.text().strip():
                # 让用户看到"我会帮你补成什么样"，避免点确定后觉得被偷偷改了
                self.hint.setText(f"将打开：{normalized}")
            else:
                self.hint.setText("")
            return
        self.hint.setText(name_error or url_error)

    def _on_accept(self) -> None:
        name_error, url_error = self._problems()
        if name_error or url_error:
            common.warn(self, name_error or url_error, "无法保存论坛")
            return
        self.accept()

    # -- 取值 ---------------------------------------------------------------

    def result_forum(self) -> forum_store.Forum:
        """取用户填的内容（已补全协议、已去首尾空格）。"""
        return forum_store.Forum(
            name=self.name_edit.text().strip(),
            url=forum_store.normalize_url(self.url_edit.text()),
        )


__all__ = ["ForumDialog"]
