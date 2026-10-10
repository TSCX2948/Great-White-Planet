"""提交作业确认框：先让用户看清"交的到底是哪个文件夹里的东西"，再去浏览器。

为什么要有这一步：作业的提交网址来自教务系统，一点就跳走；
用户常常需要先确认"我这份作业放在哪、要不要把附件也放进这个文件夹"。
所以点「提交作业」先弹这个框，把**当前作业文件夹的完整路径**摆在最显眼的位置。

三个出口：

* **提交作业** —— 打开浏览器跳提交网址；
* **打开文件夹** —— 在资源管理器里定位到该作业文件夹（放附件用）；
* **关闭** —— 什么都不做，只是看看。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gwp.data_manager import homework as hw
from gwp.ui import common


class SubmitHomeworkDialog(QDialog):
    """点「提交作业」时弹出的确认框。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        homework: hw.Homework | None = None,
        folder: Path | None = None,
        url: str = "",
    ) -> None:
        super().__init__(parent)
        # 允许两种入参：完整的 Homework 对象，或者只有文件夹 + 网址
        self.homework = homework
        self.folder = Path(folder) if folder is not None else (
            homework.path if homework is not None else None
        )
        self.url = url or (homework.submit_url if homework is not None else "")
        self.name = (
            homework.name if homework is not None
            else (self.folder.name if self.folder is not None else "作业")
        )
        #: 用户最终选了什么："" / "submit" / "folder"
        self.choice = ""

        self.setWindowTitle(f"提交作业：{self.name}")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        heading = QLabel(f"<b>{common.html_escape(self.name)}</b>")
        heading.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(heading)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(6)

        # ---- 作业文件夹路径（本框的重点）----
        grid.addWidget(QLabel("作业文件夹"), 0, 0, Qt.AlignmentFlag.AlignTop)
        self.input_path = QLineEdit(str(self.folder) if self.folder else "（未知）")
        self.input_path.setReadOnly(True)
        self.input_path.setCursorPosition(0)          # 从开头显示，别滚到末尾
        self.input_path.setToolTip(str(self.folder) if self.folder else "")
        grid.addWidget(self.input_path, 0, 1)

        path_actions = QHBoxLayout()
        path_actions.setSpacing(6)
        self.btn_copy_path = QPushButton("复制路径")
        self.btn_copy_path.setToolTip("把作业文件夹路径复制到剪贴板")
        self.btn_copy_path.clicked.connect(self._copy_path)
        path_actions.addWidget(self.btn_copy_path)
        self.btn_open_folder = QPushButton("打开文件夹")
        self.btn_open_folder.setToolTip("在资源管理器里打开，方便放附件")
        self.btn_open_folder.clicked.connect(self._open_folder)
        path_actions.addWidget(self.btn_open_folder)
        path_actions.addStretch(1)
        path_holder = QWidget()
        path_holder.setLayout(path_actions)
        grid.addWidget(path_holder, 1, 1)

        # ---- 提交网址 ----
        grid.addWidget(QLabel("提交方式"), 2, 0, Qt.AlignmentFlag.AlignTop)
        url_label = QLabel(self.url or "（未填写）")
        url_label.setObjectName("Muted" if not self.url else "")
        url_label.setWordWrap(True)
        url_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        grid.addWidget(url_label, 2, 1)

        # ---- DDL 与附件数（有就显示）----
        row = 3
        if self.homework is not None and self.homework.due_label:
            grid.addWidget(QLabel("DDL"), row, 0)
            grid.addWidget(QLabel(self.homework.due_label), row, 1)
            row += 1
        if self.homework is not None:
            grid.addWidget(QLabel("文件夹内文件"), row, 0)
            grid.addWidget(
                QLabel(f"{self.homework.file_count} 个（不含作业信息文件）"), row, 1
            )
            row += 1

        layout.addLayout(grid)

        hint = QLabel(
            "要交的附件请放进上面这个文件夹里；"
            "「提交作业」只会打开浏览器，不会上传任何东西。"
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QDialogButtonBox()
        self.btn_submit = buttons.addButton(
            "提交作业", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.btn_submit.setProperty("accent", True)
        self.btn_submit.setEnabled(bool(self.url))
        if not self.url:
            self.btn_submit.setToolTip("这个作业还没有填写提交网址")
        self.btn_submit.clicked.connect(self._do_submit)
        self.btn_close = buttons.addButton(
            "关闭", QDialogButtonBox.ButtonRole.RejectRole
        )
        self.btn_close.clicked.connect(self.reject)
        layout.addWidget(buttons)

        self.btn_submit.setDefault(True)
        self.btn_close.setAutoDefault(False)
        self.btn_submit.setAutoDefault(True)

    # ------------------------------------------------------------------

    def _copy_path(self) -> None:
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard is not None and self.folder is not None:
            clipboard.setText(str(self.folder))
        self.btn_copy_path.setText("已复制 ✓")

    def _open_folder(self) -> None:
        if self.folder is None:
            return
        from gwp.services import file_ops

        file_ops.reveal_in_explorer(self.folder)

    def _do_submit(self) -> None:
        self.choice = "submit"
        self.accept()


__all__ = ["SubmitHomeworkDialog"]
