"""Summary 版本管理对话框：查看上一版、恢复、对比。"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gwp.bootstrap import AppContext
from gwp.core.eventbus import SUMMARY_BACKUP_RESTORED, bus
from gwp.data_manager.summary_backup import BackupManager, BackupRecord
from gwp.services.markdown_renderer import RenderOptions, render_document
from gwp.ui import common


class BackupDialog(QDialog):
    """管理某本书的 summary 历史版本（默认只保留一个上一版）。"""

    def __init__(
        self,
        context: AppContext,
        subject_name: str,
        book_name: str,
        summary_path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.context = context
        self.subject_name = subject_name
        self.book_name = book_name
        self.summary_path = summary_path
        self.backups = BackupManager(context.config, context.paths)

        self.setWindowTitle(f"版本管理：{book_name}")
        self.resize(920, 600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)

        info = QLabel(
            f"当前配置：保留最近 {self.backups.keep} 个上一版本"
            "（可在「设置 → 总结」中修改）。恢复时会先把当前版本另存一份，方便反悔。"
        )
        info.setWordWrap(True)
        info.setObjectName("Muted")
        layout.addWidget(info)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(QLabel("历史版本（新 → 旧）"))
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_select)
        left_layout.addWidget(self.list, 1)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)
        self.lbl_preview = QLabel("选择左侧版本查看内容")
        self.lbl_preview.setObjectName("Muted")
        right_layout.addWidget(self.lbl_preview)
        self.preview = QTextBrowser()
        right_layout.addWidget(self.preview, 1)

        restore_row = QHBoxLayout()
        self.btn_restore = QPushButton("恢复此版本")
        self.btn_restore.setEnabled(False)
        self.btn_restore.clicked.connect(self._restore)
        restore_row.addWidget(self.btn_restore)
        self.btn_compare = QPushButton("与当前版本对比")
        self.btn_compare.setEnabled(False)
        self.btn_compare.clicked.connect(self._compare)
        restore_row.addWidget(self.btn_compare)
        restore_row.addStretch(1)
        self.btn_delete_all = QPushButton("删除所有历史版本")
        self.btn_delete_all.clicked.connect(self._delete_all)
        restore_row.addWidget(self.btn_delete_all)
        right_layout.addLayout(restore_row)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        buttons = QDialogButtonBox()
        buttons.addButton("关闭", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._records: list[BackupRecord] = []
        self.reload()

    # ------------------------------------------------------------------

    def reload(self) -> None:
        self._records = self.backups.list_backups(self.subject_name, self.book_name)
        self.list.clear()
        if not self._records:
            self.list.addItem("（暂无历史版本）")
            self._records = []
            self.btn_delete_all.setEnabled(False)
            self.lbl_preview.setText("这本书还没有历史版本。再次生成总结时会自动保存上一版。")
            return
        for record in self._records:
            item = QListWidgetItem(f"{record.created_label}   ({record.size_label})")
            if record.note:
                item.setToolTip(record.note)
            self.list.addItem(item)
        self.list.setCurrentRow(0)
        self.btn_delete_all.setEnabled(True)

    def _current(self) -> BackupRecord | None:
        row = self.list.currentRow()
        if 0 <= row < len(self._records):
            return self._records[row]
        return None

    def _on_select(self, _row: int) -> None:
        record = self._current()
        if record is None:
            self.btn_restore.setEnabled(False)
            self.btn_compare.setEnabled(False)
            return
        self.btn_restore.setEnabled(True)
        self.btn_compare.setEnabled(True)
        text = self.backups.read_backup_text(record)
        self.lbl_preview.setText(f"{record.created_label}：{record.file.name if record.file else ''}")
        self.preview.setHtml(
            render_document(text, RenderOptions(theme=self.context.theme, title=record.book))
        )

    def _restore(self) -> None:
        record = self._current()
        if record is None:
            return
        if not common.confirm(
            self,
            "确定把选中的版本恢复为当前总结吗？\n（当前的总结会先被另存为一个新的历史版本）",
            "恢复历史版本",
        ):
            return
        ok = self.backups.restore(self.subject_name, self.book_name, self.summary_path, record)
        if not ok:
            common.warn(self, "恢复失败：备份文件可能已被清理。")
            return
        bus.emit(SUMMARY_BACKUP_RESTORED, subject=self.subject_name, book=self.book_name)
        common.info(self, "已恢复所选版本。", "恢复完成")
        self.reload()

    def _compare(self) -> None:
        record = self._current()
        if record is None:
            return
        old = self.backups.read_backup_text(record)
        try:
            current = self.summary_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            current = ""
        dialog = DiffDialog(old, current, record.created_label, self)
        dialog.exec()

    def _delete_all(self) -> None:
        if not common.confirm(self, "确定删除这本书的全部历史版本吗？此操作不可撤销。", "删除历史版本"):
            return
        self.backups.delete_all(self.subject_name, self.book_name)
        self.reload()


class DiffDialog(QDialog):
    """简单的行级差异对比。"""

    def __init__(self, old: str, new: str, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"对比：{label}")
        self.resize(960, 640)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)

        from difflib import HtmlDiff

        table = HtmlDiff(tabsize=2, wrapcolumn=90).make_table(
            old.splitlines(), new.splitlines(), "历史版本", "当前版本"
        )
        view = QTextBrowser()
        view.setHtml(
            "<html><head><meta charset='utf-8'><style>"
            "table.diff { font-family: Consolas, monospace; font-size: 9pt; border-collapse: collapse; width: 100%; }"
            "table.diff td { padding: 2px 6px; vertical-align: top; }"
            ".diff_header { background: #EEF3FF; color: #4F7CFF; }"
            ".diff_add { background: #E8F7EC; } .diff_sub { background: #FDECEC; } .diff_chg { background: #FFF6E5; }"
            "</style></head><body>" + table + "</body></html>"
        )
        layout.addWidget(view, 1)

        buttons = QDialogButtonBox()
        buttons.addButton("关闭", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


__all__ = ["BackupDialog", "DiffDialog"]
