"""导出 PDF 对话框：选择位置、纸张、边距，并实时预览。

导出分两步（因为 Markdown 排版前没有"页"的概念）：

1. 后台把完整 PDF 排版到一个临时文件，得到总页数；
2. 弹出 :class:`~gwp.ui.dialogs.page_range_dialog.PageRangeDialog`，
   询问是否加页码、要导出哪些页（支持 ``1-3, 5`` 与 ``e`` 这类写法），
   然后抽取页面并写页码，产出最终文件。

整个过程在后台线程里跑，界面不卡，且可以随时取消。
"""

from __future__ import annotations

import logging
import os
import tempfile
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressDialog,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from gwp.ai.worker import SimpleWorker
from gwp.bootstrap import AppContext
from gwp.services import pdf_exporter
from gwp.services.markdown_renderer import RenderOptions, render_document
from gwp.ui import common
from gwp.ui.dialogs.page_range_dialog import PageRangeDialog

log = logging.getLogger(__name__)


class PrepareWorker(QThread):
    """后台把 Markdown 排版成完整 PDF（临时文件），并在结束时报告页数。"""

    progress = pyqtSignal(str, int, str)
    ready = pyqtSignal(int)          # 总页数
    failed = pyqtSignal(str)

    def __init__(self, parent, markdown_text: str, options, temp_path: Path, base_dir: Path) -> None:
        super().__init__(parent)
        self._text = markdown_text
        self._options = options
        self._temp_path = temp_path
        self._base_dir = base_dir
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:  # noqa: D102 - QThread 接口
        try:
            pdf_exporter.export_markdown_to_pdf(
                self._text,
                self._temp_path,
                self._options,
                base_dir=self._base_dir,
                on_progress=lambda message, percent: self.progress.emit(message, percent, ""),
                should_cancel=lambda: self._cancel,
                style="prepare",
            )
            pages = pdf_exporter.count_pdf_pages(self._temp_path)
        except pdf_exporter.PDFExportCancelled:
            self.failed.emit("已取消导出")
        except Exception as exc:  # noqa: BLE001
            # 记下完整堆栈，方便用户把日志发回来排查
            log.error("排版阶段失败：%s\n%s", exc, traceback.format_exc())
            self.failed.emit(str(exc))
        else:
            if self._cancel:
                self.failed.emit("已取消导出")
            else:
                self.ready.emit(pages)


class ExportPdfDialog(QDialog):
    """把一份 Markdown 导出为 PDF（完全本地完成，不需要联网）。"""

    def __init__(self, context: AppContext, source: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.source = Path(source)
        self.output_path: Path | None = None
        # 后台导出期间的状态（未导出时保持为 None）
        self._prepared: Path | None = None
        self._pages: list[int] | None = None
        self._worker: QThread | None = None
        self.progress: QProgressDialog | None = None
        self.setWindowTitle(f"导出 PDF：{self.source.name}")
        self.resize(880, 660)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(12)

        # 左侧：预览
        self.preview = QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        try:
            text = self.source.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            text = f"读取失败：{exc}"
        self.preview.setHtml(
            render_document(
                text,
                RenderOptions(
                    base_dir=self.source.parent,
                    theme="light",
                    title=self.source.stem,
                ),
            )
        )
        layout.addWidget(self.preview, 3)

        # 右侧：选项
        side = QVBoxLayout()
        side.setSpacing(10)

        title = QLabel("导出设置")
        title.setObjectName("SectionTitle")
        side.addWidget(title)

        # 明确告诉用户到底导出的是哪份文件（曾经因为"总是导出总结"而误会）
        source_label = QLabel(
            f"将导出：<b>{common.html_escape(self.source.name)}</b>"
            f"<br><span style='color:#6B7787'>{common.html_escape(str(self.source.parent))}</span>"
        )
        source_label.setTextFormat(Qt.TextFormat.RichText)
        source_label.setWordWrap(True)
        source_label.setObjectName("Subtitle")
        side.addWidget(source_label)

        form = QFormLayout()
        form.setSpacing(10)

        row = QHBoxLayout()
        self.input_path = QLineEdit(str(self.default_output()))
        row.addWidget(self.input_path, 1)
        browse = QPushButton("浏览…")
        browse.clicked.connect(self._pick_path)
        row.addWidget(browse)
        holder = QWidget()
        holder.setLayout(row)
        row.setContentsMargins(0, 0, 0, 0)
        form.addRow("保存到", holder)

        self.combo_size = QComboBox()
        for size in pdf_exporter.PAGE_SIZES:
            self.combo_size.addItem(size, size)
        current = str(context.config.get("export.pdf_page_size", "A4") or "A4")
        index = self.combo_size.findData(current)
        self.combo_size.setCurrentIndex(max(0, index))
        form.addRow("纸张", self.combo_size)

        self.spin_margin = QDoubleSpinBox()
        self.spin_margin.setRange(5.0, 50.0)
        self.spin_margin.setSuffix(" mm")
        self.spin_margin.setValue(float(context.config.get("export.pdf_margin_mm", 18) or 18))
        form.addRow("页边距", self.spin_margin)

        self.check_embed = QCheckBox("把图片嵌入 PDF（推荐）")
        self.check_embed.setChecked(bool(context.config.get("export.pdf_embed_images", True)))
        self.check_embed.setToolTip("图片转为内嵌数据，导出的 PDF 不依赖原文件位置，可直接分享")
        form.addRow("", self.check_embed)

        self.check_page_numbers = QCheckBox("页脚显示页码")
        self.check_page_numbers.setChecked(bool(context.config.get("export.pdf_page_numbers", True)))
        self.check_page_numbers.setToolTip("在每页底部居中插入「- 页码 / 总页数 -」")
        form.addRow("", self.check_page_numbers)

        self.check_ask_range = QCheckBox("导出前询问页码范围")
        self.check_ask_range.setChecked(bool(context.config.get("export.ask_page_range", True)))
        self.check_ask_range.setToolTip(
            "排版完成后弹窗，可选择导出哪些页（支持 1-3, 5、e 表示最后一页）"
        )
        form.addRow("", self.check_ask_range)

        self.check_remember = QCheckBox("记住这次的选择作为默认值")
        self.check_remember.setChecked(True)
        form.addRow("", self.check_remember)
        side.addLayout(form)

        hint = QLabel(
            "提示：PDF 由本机直接生成，不经过网络；导出在后台进行，可随时取消。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("Muted")
        side.addWidget(hint)
        side.addStretch(1)

        buttons = QDialogButtonBox()
        self.btn_export = buttons.addButton("开始导出", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_export.setProperty("accent", True)
        buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._export)
        buttons.rejected.connect(self.reject)
        side.addWidget(buttons)

        container = QWidget()
        container.setLayout(side)
        container.setFixedWidth(340)
        layout.addWidget(container)

    # ------------------------------------------------------------------

    def default_output(self) -> Path:
        last_dir = str(self.context.config.get("export.last_dir", "") or "")
        start = Path(last_dir) if last_dir and Path(last_dir).is_dir() else self.source.parent
        return start / pdf_exporter.suggested_filename(self.source)

    def _pick_path(self) -> None:
        path = common.pick_save_file(
            self,
            "导出 PDF",
            default_name=Path(self.input_path.text()).name or pdf_exporter.suggested_filename(self.source),
            filters="PDF 文件 (*.pdf)",
            start=Path(self.input_path.text()).parent if self.input_path.text() else None,
        )
        if path:
            self.input_path.setText(str(path))

    def _export(self) -> None:
        target = Path(self.input_path.text().strip())
        if target.suffix.lower() != ".pdf":
            target = target.with_suffix(".pdf")
        if target.exists() and not common.confirm(self, f"文件已存在，要覆盖吗？\n{target}", "覆盖确认"):
            return

        try:
            text = self.source.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            common.error(self, f"读取源文件失败：{exc}", "导出失败")
            return

        options = pdf_exporter.PDFExportOptions(
            page_size=self.combo_size.currentData(),
            margin_mm=self.spin_margin.value(),
            theme=str(self.context.config.get("ui.theme", "light") or "light"),
            embed_images=self.check_embed.isChecked(),
            page_numbers=self.check_page_numbers.isChecked(),
            title=self.source.stem,
        )

        # 后台线程排版：本方法立即返回，对话框保持可见，
        # 界面（含"取消"按钮）由 Qt 事件循环正常处理。
        self._target = target
        self._options = options
        self._markdown = text
        self._prepared: Path | None = None
        self._pages: list[int] | None = None

        handle = tempfile.NamedTemporaryFile(
            prefix="gwp_export_", suffix=".pdf", delete=False
        )
        handle.close()
        self._prepared = Path(handle.name)

        self.progress = QProgressDialog("正在排版……", "取消", 0, 100, self)
        self.progress.setWindowTitle("导出 PDF")
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setMinimumWidth(420)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.setValue(0)
        self.progress.show()

        self.btn_export.setEnabled(False)
        self.btn_export.setText("正在导出…")

        self._worker = PrepareWorker(
            self, text, options, self._prepared, self.source.parent
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.ready.connect(self._on_pages_ready)
        self._worker.failed.connect(self._on_export_failed)
        self.progress.canceled.connect(self._worker.cancel)
        self._worker.start()

    # -- 后台导出的回调 ------------------------------------------------

    def _on_progress(self, message: str, percent: int, _detail: str) -> None:
        if getattr(self, "progress", None) is None:
            return
        self.progress.setLabelText(message)
        if percent is None or percent < 0:
            self.progress.setRange(0, 0)
        else:
            if self.progress.maximum() == 0:
                self.progress.setRange(0, 100)
            self.progress.setValue(max(0, min(100, percent)))

    def _on_pages_ready(self, total_pages: int) -> None:
        """排版完成：问用户页码与范围，然后后台抽取。"""
        self._close_progress()

        pages: list[int] | None = None
        add_numbers = bool(self._options.page_numbers)
        if self.check_ask_range.isChecked():
            dialog = PageRangeDialog(total_pages, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                self._discard_prepared()
                self._reset_buttons()
                common.info(self, "已取消导出。", "导出 PDF")
                return
            pages = dialog.selected_pages()
            add_numbers = dialog.add_page_numbers
        else:
            pages = list(range(1, total_pages + 1))
            # 没弹窗时，页数信息补到进度里
            self.status_message_emit(f"文档共 {total_pages} 页，正在写入……")

        self._pages = pages
        self._options.page_numbers = add_numbers

        self.progress = QProgressDialog("正在写入文件……", "取消", 0, 100, self)
        self.progress.setWindowTitle("导出 PDF")
        self.progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress.setMinimumWidth(420)
        self.progress.setAutoClose(False)
        self.progress.setAutoReset(False)
        self.progress.setValue(95)
        self.progress.show()

        self._worker = SimpleWorker(
            task=self._run_finalize,
            parent=self,
            label="写入 PDF",
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_export_done)
        self._worker.failed.connect(self._on_export_failed)
        self.progress.canceled.connect(self._worker.cancel)
        self._worker.start()

    def _run_finalize(self, **helpers) -> object:
        """后台：用已排版好的临时文件切页/编号，写出最终文件。"""
        if self._prepared is None:
            raise pdf_exporter.PDFExportError("排版结果丢失，无法写出文件。")
        return pdf_exporter.export_markdown_to_pdf(
            "",
            self._target,
            self._options,
            base_dir=self.source.parent,
            on_progress=lambda message, percent: helpers["on_progress"](message, percent, ""),
            should_cancel=helpers["should_cancel"],
            page_numbers=self._options.page_numbers,
            prepared_path=self._prepared,
            pages=self._pages,
        )

    def _discard_prepared(self) -> None:
        prepared = getattr(self, "_prepared", None)
        if prepared is not None:
            try:
                if prepared.exists():
                    prepared.unlink()
            except OSError:
                pass
            self._prepared = None

    def _close_progress(self) -> None:
        if getattr(self, "progress", None) is not None:
            self.progress.close()
            self.progress.deleteLater()
            self.progress = None

    def _reset_buttons(self) -> None:
        self.btn_export.setEnabled(True)
        self.btn_export.setText("开始导出")

    def _on_export_done(self, output) -> None:
        self._close_progress()
        self._discard_prepared()
        if output is None:
            self._reset_buttons()
            common.warn(self, "导出未完成（可能已取消）。", "导出 PDF")
            return

        if self.check_remember.isChecked():
            self.context.config.update(
                {
                    "export": {
                        "pdf_page_size": self._options.page_size,
                        "pdf_margin_mm": round(self._options.margin_mm, 1),
                        "pdf_embed_images": self._options.embed_images,
                        "pdf_page_numbers": self._options.page_numbers,
                        "ask_page_range": self.check_ask_range.isChecked(),
                        "last_dir": str(self._target.parent),
                    }
                }
            )
            self.context.save_config()

        self.output_path = Path(output)
        page_note = ""
        if self._pages:
            page_note = f"\n共导出 {len(self._pages)} 页"
            if not self._options.page_numbers:
                page_note += "（未加页码）"
        try:
            size_kb = self.output_path.stat().st_size / 1024
            detail = f"已导出（{size_kb:.0f} KB）：\n{self.output_path}{page_note}"
        except OSError:
            detail = f"已导出：\n{self.output_path}{page_note}"
        common.info(self, detail, "导出完成")
        self.accept()

    def _on_export_failed(self, message: str) -> None:
        self._close_progress()
        self._discard_prepared()
        self._reset_buttons()
        text = str(message or "")
        if "取消" in text:
            common.info(self, "已取消导出。", "导出 PDF")
            return
        common.error(self, text, "导出失败")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        """关闭对话框时，若仍在导出则请求取消，避免线程被强杀。"""
        worker = getattr(self, "_worker", None)
        if worker is not None and worker.isRunning():
            worker.cancel()
            worker.wait(5000)
        self._close_progress()
        self._discard_prepared()
        super().closeEvent(event)

    def status_message_emit(self, message: str) -> None:
        """把消息透传给父窗口的状态栏（如果父窗口支持）。"""
        parent = self.parent()
        if parent is not None and hasattr(parent, "status_message"):
            try:
                parent.status_message.emit(message)
            except Exception:  # noqa: BLE001
                pass


__all__ = ["ExportPdfDialog"]
