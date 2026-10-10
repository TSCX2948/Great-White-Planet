"""新建 / 编辑作业的对话框：作业内容 + DDL + 提交方式。

三项都由用户自己填，软件**不做任何猜测**：

* **作业内容**：多行文本，会写成作业文件夹里的 Markdown 文件；
* **DDL**：日期 + 时间，可以只填日期，也可以完全不填；
* **提交方式**：一个网址，填好之后在列表里可点。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QDate, QDateTime, QTime, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from gwp.data_manager import homework as hw
from gwp.data_manager.store import sanitize_name, validate_name
from gwp.ui import common


class HomeworkDialog(QDialog):
    """新建作业（``homework=None``）或编辑已有作业。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        homework: hw.Homework | None = None,
        *,
        folder: Path | None = None,
        default_url: str = "",
    ) -> None:
        super().__init__(parent)
        self.homework = homework
        self.is_new = homework is None
        self.folder = folder
        self._default_url = hw.normalize_url(default_url or "") if default_url else ""
        self.setWindowTitle("新建作业" if self.is_new else f"编辑作业：{homework.name}")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # -- 作业名（= 文件夹名）--------------------------------------
        #
        # **编辑时也允许改名**（用户报障："更改作业名称功能异常"）。
        # 之前这里写的是 `setEnabled(self.is_new)`，注释理由是"改名会动文件夹" ——
        # 结果界面上根本**没有**改作业名的入口：右键菜单里没有重命名，
        # 对话框里输入框又是灰的。
        # 改名确实要移动文件夹，但那由 `homework.rename()` 负责（含回滚），
        # 不该因此把功能关掉。
        default_name = "" if self.is_new else homework.name
        self.input_name = QLineEdit(default_name)
        self.input_name.setPlaceholderText("例如：第三章习题（会成为文件夹名）")
        form.addRow("作业名称", self.input_name)

        # -- DDL -------------------------------------------------------
        due_row = QWidget()
        due_layout = QHBoxLayout(due_row)
        due_layout.setContentsMargins(0, 0, 0, 0)
        due_layout.setSpacing(8)
        self.check_due = QCheckBox("设置 DDL")
        # 日期用日历选、时分用上下按钮/滚轮调（需求：不要手打数字）
        self.edit_due = common.make_datetime_edit(
            QDateTime.currentDateTime().addDays(7)
        )
        due_layout.addWidget(self.check_due)
        due_layout.addWidget(self.edit_due, 1)
        form.addRow("截止时间", due_row)

        # -- 提交方式 --------------------------------------------------
        self.input_url = QLineEdit()
        self.input_url.setPlaceholderText("提交网址，例如 https://xxx.edu/upload")
        self.lbl_url_hint = QLabel("")
        self.lbl_url_hint.setObjectName("Muted")
        self.lbl_url_hint.setWordWrap(True)
        form.addRow("提交方式", self.input_url)
        form.addRow("", self.lbl_url_hint)

        # -- 作业内容 --------------------------------------------------
        self.input_content = QPlainTextEdit()
        self.input_content.setPlaceholderText(
            "作业内容：题目、要求、要交的东西……\n"
            "会保存成作业文件夹里的 Markdown 文件，随时可以继续编辑。"
        )
        self.input_content.setMinimumHeight(150)
        form.addRow("作业内容", self.input_content)

        layout.addLayout(form)

        self.lbl_where = QLabel("")
        self.lbl_where.setObjectName("Muted")
        self.lbl_where.setWordWrap(True)
        layout.addWidget(self.lbl_where)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "创建" if self.is_new else "保存"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # -- 回填 ------------------------------------------------------
        if homework is not None:
            self.input_content.setPlainText(homework.content)
            moment = homework.due_at
            if moment is not None:
                self.check_due.setChecked(True)
                self.edit_due.setDateTime(
                    QDateTime(
                        QDate(moment.year, moment.month, moment.day),
                        QTime(moment.hour, moment.minute),
                    )
                )
            self.input_url.setText(homework.submit_url)
        elif self._default_url:
            # 新建作业时**沿用这本书上一份作业的提交网址**（需求：
            # "新建作业的提交方式的网址默认为该book的作业之前的提交方式的网址，
            #  避免用户每次输入"）。
            # 同一门课的作业提交入口通常是同一个（雨课堂 / 教务系统的同一页），
            # 所以这个默认值大概率正是用户要填的。
            self.input_url.setText(self._default_url)
        self.check_due.toggled.connect(self.edit_due.setEnabled)
        self.edit_due.setEnabled(self.check_due.isChecked())
        self.input_url.textChanged.connect(self._on_url_changed)
        self._on_url_changed(self.input_url.text())

        if self.folder is not None:
            self.lbl_where.setText(f"将创建在：{self.folder}")
        elif not self.is_new:
            self.lbl_where.setText(
                "改作业名会**同时重命名作业文件夹**，"
                "里面的文件（含作业内容）都会一起跟着走。"
            )
        if self.is_new and self._default_url:
            # 说明这个值是**从哪来的**，并告诉用户清空是允许的 ——
            # 不然用户会以为"这是必填的默认值，改不掉"。
            self.lbl_where.setText(
                "提交方式已按这本书**上一份作业**填好"
                "（同一门课的提交入口通常是同一个）；"
                "不需要就清空它。"
            )
        self.input_name.setFocus()
        self.input_name.selectAll()

    # ------------------------------------------------------------------

    @property
    def folder_name(self) -> str:
        return sanitize_name(self.input_name.text())

    def _name_changed(self) -> bool:
        """编辑模式下作业名是否被改动过（决定要不要走"重命名"那条路）。"""
        if self.is_new or self.homework is None:
            return False
        return sanitize_name(self.input_name.text()) != self.homework.name

    @property
    def name_changed(self) -> bool:
        """公开给调用方用：这次保存需不需要重命名文件夹。"""
        return self._name_changed()

    @property
    def due_text(self) -> str:
        if not self.check_due.isChecked():
            return ""
        return hw.format_due(self.edit_due.dateTime().toPyDateTime())

    @property
    def submit_url(self) -> str:
        """最终要保存的提交网址 —— 就是输入框里的内容（用户清空即为空）。

        规则刻意做得**单一**：输入框有预填值，用户改或清都按输入框算。
        不做"清空后再把默认值塞回去"这种小聪明 ——
        那会让"我想让这份作业没有提交网址"变得做不到。
        """
        return hw.normalize_url(self.input_url.text())

    @property
    def content_text(self) -> str:
        return self.input_content.toPlainText().strip()

    def _on_url_changed(self, text: str) -> None:
        raw = (text or "").strip()
        if not raw:
            self.lbl_url_hint.setText(
                "可留空。填入网址后在作业列表里可以直接点开。"
            )
            return
        normalized = hw.normalize_url(raw)
        if hw.is_valid_url(normalized):
            if normalized != raw:
                self.lbl_url_hint.setText(f"将保存为：{normalized}")
            else:
                self.lbl_url_hint.setText("链接有效，列表里可以直接点开。")
        else:
            self.lbl_url_hint.setText(
                "⚠ 只支持 http / https 网址，例如 https://example.com/submit"
            )

    def _accept(self) -> None:
        # 新建时必填；编辑时也校验（改名同样要是一个合法文件夹名）
        if self.is_new or self._name_changed():
            error = validate_name(self.input_name.text())
            if error:
                common.warn(self, error, "作业名不合法")
                return
        raw_url = self.input_url.text().strip()
        if raw_url and not hw.is_valid_url(hw.normalize_url(raw_url)):
            common.warn(
                self,
                "提交方式必须是一个 http / https 网址（可以留空）。\n\n"
                f"当前填写：{raw_url}",
                "提交方式不合法",
            )
            return
        self.accept()


__all__ = ["HomeworkDialog"]
