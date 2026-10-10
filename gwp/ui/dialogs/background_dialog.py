"""主界面背景图选择对话框。

功能：

* 列出 ``else data/background`` 里的全部图片（点击即预览）；
* 「导入图片…」把新图片复制进图库（**不删除**旧图，文件名只递增后半部分数字）；
* 「不使用背景」清空设置但**保留**图片文件；
* 「打开背景文件夹」方便自己往里丢图片；
* 可调蒙层深浅与填充方式，实时看效果提示。
"""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from gwp.bootstrap import AppContext
from gwp.services import file_ops
from gwp.ui import common


class BackgroundDialog(QDialog):
    """选背景、导入新图、调整显示效果。"""

    changed = pyqtSignal()

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.manager = context.backgrounds
        self.setWindowTitle("主界面背景")
        self.resize(860, 560)
        self._pending: Path | None = None      # 选中但尚未确定的那张

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(12)

        # ---- 左：图库列表 ----
        left = QVBoxLayout()
        left.setSpacing(8)
        left.addWidget(QLabel("背景图库"))
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        self.list.itemDoubleClicked.connect(lambda _item: self.accept())
        left.addWidget(self.list, 1)

        left_buttons = QHBoxLayout()
        self.btn_import = QPushButton("导入图片…")
        self.btn_import.setToolTip("把图片复制进图库；旧背景会保留，不会删除")
        self.btn_import.clicked.connect(self._import)
        left_buttons.addWidget(self.btn_import)
        self.btn_open_dir = QPushButton("打开背景文件夹")
        self.btn_open_dir.clicked.connect(self._open_directory)
        left_buttons.addWidget(self.btn_open_dir)
        left_buttons.addStretch(1)
        left.addLayout(left_buttons)

        self.lbl_hint = QLabel("")
        self.lbl_hint.setObjectName("Muted")
        self.lbl_hint.setWordWrap(True)
        left.addWidget(self.lbl_hint)

        left_holder = QWidget()
        left_holder.setLayout(left)
        layout.addWidget(left_holder, 3)

        # ---- 右：预览与效果 ----
        right = QVBoxLayout()
        right.setSpacing(8)
        right.addWidget(QLabel("预览"))

        self.preview = QLabel("（选择一张图片查看效果）")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(320, 200)
        self.preview.setWordWrap(True)
        self.preview.setObjectName("Panel")
        right.addWidget(self.preview, 1)

        form = QFormLayout()
        form.setSpacing(10)

        self.check_enabled = QCheckBox("启用背景图")
        self.check_enabled.setChecked(bool(context.config.get("ui.background_enabled", True)))
        self.check_enabled.toggled.connect(self._on_option_changed)
        form.addRow("", self.check_enabled)

        self.combo_fit = QComboBox()
        for label, value in (
            ("铺满（裁掉多余部分）", "cover"),
            ("完整显示（可能有留白）", "contain"),
            ("拉伸填满", "stretch"),
            ("原始大小居中", "center"),
        ):
            self.combo_fit.addItem(label, value)
        current_fit = str(context.config.get("ui.background_fit", "cover") or "cover")
        index = max(0, self.combo_fit.findData(current_fit))
        self.combo_fit.setCurrentIndex(index)
        self.combo_fit.currentIndexChanged.connect(self._on_option_changed)
        form.addRow("显示方式", self.combo_fit)

        self.slider_overlay = QSlider(Qt.Orientation.Horizontal)
        self.slider_overlay.setRange(0, 90)
        try:
            initial = int(float(context.config.get("ui.background_overlay", 0.35) or 0) * 100)
        except (TypeError, ValueError):
            initial = 35
        self.slider_overlay.setValue(initial)
        self.slider_overlay.valueChanged.connect(self._on_option_changed)
        self.lbl_overlay = QLabel("")
        self.lbl_overlay.setObjectName("Muted")
        overlay_row = QHBoxLayout()
        overlay_row.addWidget(self.slider_overlay, 1)
        overlay_row.addWidget(self.lbl_overlay)
        holder = QWidget()
        holder.setLayout(overlay_row)
        overlay_row.setContentsMargins(0, 0, 0, 0)
        form.addRow("蒙层深浅", holder)
        self._update_overlay_label(initial)

        right.addLayout(form)

        self.btn_none = QPushButton("不使用背景")
        self.btn_none.setToolTip("清空设置，图库里的图片会保留")
        self.btn_none.clicked.connect(self._use_none)
        right.addWidget(self.btn_none)
        right.addStretch(1)

        buttons = QDialogButtonBox()
        self.btn_ok = buttons.addButton("应用", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_ok.setProperty("accent", True)
        buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        right.addWidget(buttons)

        right_holder = QWidget()
        right_holder.setLayout(right)
        layout.addWidget(right_holder, 2)

        self.reload()

    # ------------------------------------------------------------------

    def reload(self) -> None:
        """刷新图库列表。"""
        self.list.blockSignals(True)
        self.list.clear()
        current_row = -1
        selected = self._pending or self.manager.current_path()
        for index, entry in enumerate(self.manager.entries()):
            label = entry.name
            if entry.is_current:
                label += "　✔ 当前使用"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(entry.path))
            item.setToolTip(f"{entry.path}\n{entry.size_label}")
            self.list.addItem(item)
            if selected is not None and entry.path == selected:
                current_row = index
        self.list.blockSignals(False)

        if self.list.count() == 0:
            self.lbl_hint.setText(
                f"图库还是空的：{self.manager.directory}\n"
                "点「导入图片…」选一张，或直接把图片丢进这个文件夹再重新打开本窗口。"
            )
        else:
            self.lbl_hint.setText(
                f"图库位置：{self.manager.directory}\n"
                "支持 jpg / png / webp / bmp；导入新图不会删除旧图。"
            )
        if current_row >= 0:
            self.list.setCurrentRow(current_row)
        else:
            self._update_preview(None)

    def _current_entry_path(self) -> Path | None:
        item = self.list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return Path(value) if value else None

    def _on_select(self, _current: QListWidgetItem | None, _previous=None) -> None:
        path = self._current_entry_path()
        self._pending = path
        self._update_preview(path)

    def _update_preview(self, path: Path | None) -> None:
        if path is None or not path.is_file():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("（选择一张图片查看效果）")
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText("无法预览这张图片")
            return
        self.preview.setText("")
        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size() * 0.96,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _update_overlay_label(self, value: int) -> None:
        self.lbl_overlay.setText(f"{value}%")

    def _on_option_changed(self, *_args) -> None:
        self._update_overlay_label(self.slider_overlay.value())

    # ------------------------------------------------------------------

    def _import(self) -> None:
        path = common.pick_open_image(self, "选择背景图片")
        if not path:
            return
        try:
            target = self.manager.add(path)
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "导入背景图失败")
            return
        self._pending = target
        self.reload()
        common.info(
            self,
            f"已导入：{target.name}\n\n旧背景图仍然保留在图库里，可以随时切回来。",
            "导入背景图",
        )

    def _open_directory(self) -> None:
        directory = self.manager.ensure_directory()
        file_ops.reveal_in_explorer(directory)

    def _use_none(self) -> None:
        self.manager.clear()
        self._pending = None
        self.reload()
        self.changed.emit()

    # ------------------------------------------------------------------

    def _apply(self) -> None:
        """写入选择并让主窗口刷新。"""
        options = {
            "ui": {
                "background_enabled": self.check_enabled.isChecked(),
                "background_fit": self.combo_fit.currentData(),
                "background_overlay": round(self.slider_overlay.value() / 100.0, 2),
            }
        }
        self.context.config.update(options)
        self.context.config.save()

        if self._pending is not None:
            self.manager.set_current(self._pending)
        self.changed.emit()
        self.accept()


__all__ = ["BackgroundDialog"]
