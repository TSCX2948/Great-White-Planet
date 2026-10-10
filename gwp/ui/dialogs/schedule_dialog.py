"""新建 / 编辑"其它日程"的对话框：名称 + 时间 + 备注。

"其它日程"指不属于任何作业的待办 —— 考试、报名截止、要交的材料、要办的手续。
"""

from __future__ import annotations

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

from gwp.data_manager import schedule as sch
from gwp.data_manager.store import validate_name
from gwp.ui import common


class ScheduleDialog(QDialog):
    """新建日程（``item=None``）或编辑已有日程。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        item: sch.ScheduleItem | None = None,
    ) -> None:
        super().__init__(parent)
        self.item = item
        self.is_new = item is None
        self.setWindowTitle("新建日程" if self.is_new else f"编辑日程：{item.title}")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.input_title = QLineEdit("" if self.is_new else item.title)
        self.input_title.setPlaceholderText("例如：交学费、英语六级报名截止")
        form.addRow("日程名称", self.input_title)

        due_row = QWidget()
        due_layout = QHBoxLayout(due_row)
        due_layout.setContentsMargins(0, 0, 0, 0)
        due_layout.setSpacing(8)
        self.check_due = QCheckBox("设置时间")
        # 日期用日历选、时分用上下按钮/滚轮调（需求：不要手打数字）
        self.edit_due = common.make_datetime_edit(
            QDateTime.currentDateTime().addDays(1)
        )
        due_layout.addWidget(self.check_due)
        due_layout.addWidget(self.edit_due, 1)
        form.addRow("时间 / DDL", due_row)

        self.input_note = QPlainTextEdit("" if self.is_new else item.note)
        self.input_note.setPlaceholderText("可选：在哪办、需要带什么、注意事项……")
        self.input_note.setFixedHeight(80)
        form.addRow("备注", self.input_note)

        layout.addLayout(form)

        hint = QLabel(
            f"会保存到数据根目录的 <code>{sch.SCHEDULE_FILE}</code> 里，"
            "与科目、书目无关；首页右侧日程栏按 DDL 排序显示。"
        )
        hint.setObjectName("Muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

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

        if item is not None and item.due_at is not None:
            moment = item.due_at
            self.check_due.setChecked(True)
            self.edit_due.setDateTime(
                QDateTime(
                    QDate(moment.year, moment.month, moment.day),
                    QTime(moment.hour, moment.minute),
                )
            )
        self.check_due.toggled.connect(self.edit_due.setEnabled)
        self.edit_due.setEnabled(self.check_due.isChecked())

        self.input_title.setFocus()
        self.input_title.selectAll()

    # ------------------------------------------------------------------

    @property
    def title_text(self) -> str:
        return self.input_title.text().strip()

    @property
    def due_text(self) -> str:
        if not self.check_due.isChecked():
            return ""
        from gwp.data_manager.homework import format_due

        return format_due(self.edit_due.dateTime().toPyDateTime())

    @property
    def note_text(self) -> str:
        return self.input_note.toPlainText().strip()

    def _accept(self) -> None:
        error = validate_name(self.input_title.text())
        if error:
            common.warn(self, error, "日程名称不合法")
            return
        self.accept()


__all__ = ["ScheduleDialog"]
