"""聊天记录管理对话框（AI 菜单 → 删除聊天记录）。"""

from __future__ import annotations

import time

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from gwp.bootstrap import AppContext
from gwp.ui import common


class ChatManagerDialog(QDialog):
    """列出并删除 AI 聊天记录。"""

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.setWindowTitle("AI 聊天记录")
        self.resize(680, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)

        info = QLabel(
            "聊天记录存放在 else data/chats。按需求文档的默认设置，"
            "关闭软件时会自动清空全部记录；也可以在这里手动清理。"
        )
        info.setWordWrap(True)
        info.setObjectName("Muted")
        layout.addWidget(info)

        self.list = QListWidget()
        layout.addWidget(self.list, 1)

        row = QHBoxLayout()
        self.check_keep = QCheckBox("只删除更早的记录，保留最近")
        row.addWidget(self.check_keep)
        self.spin_days = QSpinBox()
        self.spin_days.setRange(1, 365)
        self.spin_days.setValue(int(self.context.config.get("ai.clear_chat_days", 7) or 7))
        self.spin_days.setSuffix(" 天")
        self.spin_days.setEnabled(False)
        self.check_keep.toggled.connect(self.spin_days.setEnabled)
        row.addWidget(self.spin_days)
        row.addStretch(1)

        self.btn_delete_selected = QPushButton("删除选中")
        self.btn_delete_selected.clicked.connect(self._delete_selected)
        row.addWidget(self.btn_delete_selected)
        self.btn_clear = QPushButton("全部清空")
        self.btn_clear.clicked.connect(self._clear_all)
        row.addWidget(self.btn_clear)
        layout.addLayout(row)

        buttons = QDialogButtonBox()
        buttons.addButton("关闭", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.reload()

    # ------------------------------------------------------------------

    def reload(self) -> None:
        self.list.clear()
        self._sessions = self.context.chats.list_sessions()
        if not self._sessions:
            self.list.addItem("（暂无聊天记录）")
            self.btn_delete_selected.setEnabled(False)
            self.btn_clear.setEnabled(False)
            return
        self.btn_delete_selected.setEnabled(True)
        self.btn_clear.setEnabled(True)
        for item in self._sessions:
            updated = time.strftime("%Y-%m-%d %H:%M", time.localtime(item["updated_at"]))
            text = f"{item['title'] or item['key']}   ·   {item['message_count']} 条   ·   {updated}"
            row = QListWidgetItem(text)
            row.setData(Qt.ItemDataRole.UserRole, item["key"])
            row.setToolTip(item["key"])
            self.list.addItem(row)

    def _delete_selected(self) -> None:
        items = self.list.selectedItems()
        if not items:
            common.warn(self, "请先选中要删除的记录。")
            return
        for item in items:
            key = item.data(Qt.ItemDataRole.UserRole)
            if key:
                self.context.chats.delete(key)
        self.reload()

    def _clear_all(self) -> None:
        if not common.confirm(self, "确定清空全部聊天记录吗？此操作不可撤销。", "清空聊天记录"):
            return
        days = self.spin_days.value() if self.check_keep.isChecked() else 0
        removed = self.context.chats.clear_all(keep_days=days)
        common.info(self, f"已清除 {removed} 条聊天记录。", "清空聊天记录")
        self.reload()


__all__ = ["ChatManagerDialog"]
