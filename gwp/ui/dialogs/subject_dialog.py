"""科目对话框：新建 / 编辑科目名称、类型、说明、卡片颜色、卡片图片。"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gwp.core import constants as C
from gwp.data_manager.models import Subject
from gwp.data_manager.store import validate_name
from gwp.ui import common
from gwp.ui.widgets.color_picker import ColorPicker


class SubjectDialog(QDialog):
    """新建或编辑科目。"""

    def __init__(
        self,
        parent: QWidget | None = None,
        subject: Subject | None = None,
        cover_path: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.subject = subject
        self.is_new = subject is None
        self.cover_source: Path | None = None

        self.setWindowTitle("新建科目" if self.is_new else f"编辑科目：{subject.title}")
        self.setMinimumWidth(470)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.input_name = QLineEdit(subject.name if subject else "")
        self.input_name.setPlaceholderText("例如：高等代数（会成为文件夹名）")
        form.addRow("科目名称", self.input_name)

        # 科目类型：决定 Book 的目录结构与标签（日记 / 校修课 / 自学课）
        self.combo_type = QComboBox()
        for kind in C.SUBJECT_TYPES:
            label, description = C.SUBJECT_TYPE_LABELS[kind]
            self.combo_type.addItem(f"{label} — {description}", kind)
        current_type = (
            subject.subject_type if subject is not None else C.DEFAULT_SUBJECT_TYPE
        )
        self._original_type = current_type
        index = self.combo_type.findData(current_type)
        self.combo_type.setCurrentIndex(max(0, index))
        self.combo_type.currentIndexChanged.connect(self._on_type_changed)

        # 已有科目能不能改类型，取决于"结构是否兼容"：
        #   自学课 <-> 校修课：目录完全一样，随便换（只是「练习」/「作业」的叫法不同）
        #   日记 <-> 普通科目：结构完全不同，换不了
        self._type_switchable = (
            self.is_new
            or (
                current_type != C.SUBJECT_DIARY
                and C.template_dirs_for_type(current_type)
                == C.template_dirs_for_type(C.SUBJECT_SELF_STUDY)
            )
        )
        if not self.is_new and not self._type_switchable:
            self.combo_type.setEnabled(False)
            self.combo_type.setToolTip(
                "日记类型的目录结构与普通科目不同，不能直接转换；\n"
                "请新建一个目标类型的科目，再手工搬文件。"
            )
        form.addRow("科目类型", self.combo_type)

        self.lbl_type_hint = QLabel("")
        self.lbl_type_hint.setObjectName("Muted")
        self.lbl_type_hint.setWordWrap(True)
        form.addRow("", self.lbl_type_hint)

        self.input_desc = QPlainTextEdit(subject.description if subject else "")
        self.input_desc.setPlaceholderText("可选：这个科目的说明、目标或备注")
        self.input_desc.setFixedHeight(72)
        form.addRow("说明", self.input_desc)
        layout.addLayout(form)

        # 卡片图片
        cover_row = QHBoxLayout()
        cover_row.setSpacing(10)
        self.cover_preview = QLabel()
        self.cover_preview.setFixedSize(132, 84)
        self.cover_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_preview.setStyleSheet(
            "border: 1px dashed rgba(128,140,160,0.6); border-radius: 10px; color: #6B7787;"
        )
        cover_row.addWidget(self.cover_preview)

        cover_buttons = QVBoxLayout()
        cover_buttons.setSpacing(6)
        self.btn_pick_cover = QPushButton("选择图片…")
        self.btn_pick_cover.setToolTip("支持 jpg / png；图片会保存到 else data 资源目录，不放进用户数据")
        self.btn_pick_cover.clicked.connect(self._pick_cover)
        cover_buttons.addWidget(self.btn_pick_cover)
        self.btn_clear_cover = QPushButton("移除图片")
        self.btn_clear_cover.clicked.connect(self._clear_cover)
        cover_buttons.addWidget(self.btn_clear_cover)
        cover_buttons.addStretch(1)
        cover_row.addLayout(cover_buttons)
        cover_row.addStretch(1)

        cover_wrap = QVBoxLayout()
        cover_label = QLabel("卡片图片（jpg / png）")
        cover_wrap.addWidget(cover_label)
        cover_wrap.addLayout(cover_row)
        layout.addLayout(cover_wrap)

        # 颜色
        layout.addWidget(QLabel("卡片颜色"))
        self.color_picker = ColorPicker(subject.color if subject else "")
        layout.addWidget(self.color_picker)

        layout.addStretch(1)

        buttons = QDialogButtonBox()
        self.btn_ok = buttons.addButton("创建" if self.is_new else "保存", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_ok.setProperty("accent", True)
        buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        initial_cover = cover_path
        if initial_cover is not None and Path(initial_cover).is_file():
            self._set_cover_preview(Path(initial_cover))
            self.cover_source = Path(initial_cover)
        elif subject is not None and not self.is_new:
            self.btn_clear_cover.setEnabled(bool(subject.cover))
            self._set_cover_placeholder("已有图片" if subject.cover else "未设置")

        self.input_name.setFocus()
        self.input_name.selectAll()
        self._on_type_changed()

    # ------------------------------------------------------------------

    @property
    def subject_type(self) -> str:
        """当前选择的科目类型。"""
        value = self.combo_type.currentData()
        return str(value) if value else C.DEFAULT_SUBJECT_TYPE

    def _on_type_changed(self, *_args) -> None:
        """切换类型时说明会生成什么结构，避免用户建完才发现不一样。"""
        kind = self.subject_type
        if kind == C.SUBJECT_DIARY:
            hint = (
                f"会创建一个日记本，并自动建好默认书目「{C.DIARY_DEFAULT_BOOK}」，"
                f"内含：{'、'.join(C.DIARY_TEMPLATE_DIRS)}。\n"
                "AI 负责两件事：归纳思想（AI summary）与合并整理（AI diary）。"
            )
        elif kind == C.SUBJECT_SCHOOL:
            hint = (
                "Book 结构：简介、笔记、作业、易错题、教材。\n"
                f"其中「{C.HOMEWORK_FOLDER}」叫「作业」；教材与作业不参与 AI 总结。"
            )
        else:
            hint = (
                "Book 结构：简介、笔记、练习、易错题、教材。\n"
                f"其中「{C.HOMEWORK_FOLDER}」叫「练习」（功能与作业相同）；"
                "教材与练习不参与 AI 总结。"
            )
        # 改类型时明确告诉用户会发生什么（尤其是"不会动文件"这点）
        if not self.is_new and self._type_switchable and kind != self._original_type:
            hint += (
                f"\n\n将把本科目从「{C.type_label(self._original_type)}」"
                f"改为「{C.type_label(kind)}」。\n"
                "两者目录结构完全相同，**不会移动或删除任何文件** —— "
                "只是把「练习」/「作业」这个栏目的叫法换一下。"
            )
        self.lbl_type_hint.setText(hint)

    def _set_cover_placeholder(self, text: str) -> None:
        self.cover_preview.setPixmap(QPixmap())
        self.cover_preview.setText(text)

    def _set_cover_preview(self, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self._set_cover_placeholder("无法读取")
            return
        self.cover_preview.setText("")
        self.cover_preview.setPixmap(
            pixmap.scaled(
                self.cover_preview.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _pick_cover(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择卡片图片", "", "图片 (*.jpg *.jpeg *.png)"
        )
        if not path:
            return
        candidate = Path(path)
        if candidate.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            common.warn(self, "卡片图片仅支持 jpg / png。")
            return
        self.cover_source = candidate
        self._set_cover_preview(candidate)

    def _clear_cover(self) -> None:
        self.cover_source = Path()          # 空 Path 表示"移除"
        self._set_cover_placeholder("未设置")

    def _accept(self) -> None:
        error = validate_name(self.input_name.text())
        if error:
            common.warn(self, error, "名称不合法")
            return
        self.accept()

    # ------------------------------------------------------------------

    def values(self) -> dict:
        result = {
            "name": self.input_name.text().strip(),
            "description": self.input_desc.toPlainText().strip(),
            "color": self.color_picker.color(),
            "cover_source": self.cover_source,
            "subject_type": self.subject_type,
        }
        return result


__all__ = ["SubjectDialog"]
