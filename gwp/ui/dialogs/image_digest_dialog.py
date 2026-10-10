"""「图片提取为 Markdown」对话框。

需求原话：

> 增加文件夹内多图片AI提取内容（无把握识别准确就直接插入图片）并合并为md功能

界面只做四件事，判断逻辑全在 :mod:`gwp.services.image_digest`：

1. 列出文件夹里的图片（自然排序，``第2页`` 在 ``第10页`` 前）；
2. 逐张把图片 + 提示词送进 AI（走 :func:`gwp.ai.providers.web_bridge.send_to_ai`：
   配了视觉模型就全自动，否则网页版桥接 + 粘贴回答）；
3. 每张显示"提取成功 / 改为插图"的状态，并且**允许用户手动改判**
   （他看过原图，他说不准就是不准）；
4. 合并成一份 md 落盘，并给出预览。

设计上刻意保留"人可以直接干预"的位置：
用户能改正文、能标记没把握、能只处理选中项 —— 因为 AI 识别不可靠时，
**人的一眼比任何启发式判断都准**。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gwp.ai.providers import web_bridge
from gwp.services import image_digest as digest
from gwp.services import file_ops
from gwp.ui import common

log = logging.getLogger(__name__)

#: 状态文案 -> 表格里那一列的颜色提示
_STATUS_OK = "已提取"
_STATUS_IMAGE = "插入原图"
_STATUS_TODO = "待处理"


class ImageDigestDialog(QDialog):
    """把文件夹里的图片提取成一份 Markdown。"""

    def __init__(
        self,
        context,
        folder: Path,
        *,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.context = context
        self.folder = Path(folder)
        self.results: list[digest.ImageResult] = []
        self.saved_path: Path | None = None

        self.setWindowTitle("图片提取为 Markdown")
        self.resize(980, 680)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # ---- 顶部：说明 + 选项 ----
        self.lbl_head = QLabel()
        self.lbl_head.setWordWrap(True)
        layout.addWidget(self.lbl_head)

        options = QHBoxLayout()
        options.setSpacing(10)
        self.check_recursive = QCheckBox("包含子文件夹里的图片")
        self.check_recursive.setToolTip(
            "适合「一章一个子文件夹」的相册式整理；勾选后会按路径顺序一起处理"
        )
        self.check_recursive.toggled.connect(self.reload)
        options.addWidget(self.check_recursive)
        options.addStretch(1)

        self.lbl_ai = QLabel()
        self.lbl_ai.setObjectName("Muted")
        self.lbl_ai.setWordWrap(True)
        options.addWidget(self.lbl_ai)
        layout.addLayout(options)

        # ---- 中部：列表 + 预览 ----
        splitter = QSplitter(Qt.Orientation.Vertical)

        table_area = QWidget()
        table_layout = QVBoxLayout(table_area)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(6)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["图片", "尺寸", "状态", "说明"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        table_layout.addWidget(self.table, 1)

        row_buttons = QHBoxLayout()
        row_buttons.setSpacing(6)
        self.btn_extract_sel = QPushButton("提取选中的")
        self.btn_extract_sel.setToolTip("只处理表格里选中的图片")
        self.btn_extract_sel.clicked.connect(self.extract_selected)
        self.btn_extract_all = QPushButton("全部提取")
        self.btn_extract_all.setProperty("accent", True)
        self.btn_extract_all.setToolTip("从第一张开始，逐张处理所有「待处理」的图片")
        self.btn_extract_all.clicked.connect(self.extract_all)
        self.btn_unsure = QPushButton("标记为没把握")
        self.btn_unsure.setToolTip("选中的图片改为「插入原图」，不多写一个字")
        self.btn_unsure.clicked.connect(self.mark_unsure)
        self.btn_sure = QPushButton("改为用文字")
        self.btn_sure.setToolTip("取消「没把握」标记，恢复成正文")
        self.btn_sure.clicked.connect(self.mark_sure)
        self.btn_edit = QPushButton("编辑正文…")
        self.btn_edit.setToolTip("手动修改 AI 提取的文字（改过之后不再自动判为不可信）")
        self.btn_edit.clicked.connect(self.edit_selected)
        self.btn_prompt = QPushButton("只看提示词")
        self.btn_prompt.setToolTip("不调用 AI，只显示该发给它的提示词（方便自己粘到别处）")
        self.btn_prompt.clicked.connect(self.show_prompt)
        for button in (
            self.btn_extract_sel, self.btn_extract_all, self.btn_unsure,
            self.btn_sure, self.btn_edit, self.btn_prompt,
        ):
            row_buttons.addWidget(button)
        row_buttons.addStretch(1)
        table_layout.addLayout(row_buttons)
        splitter.addWidget(table_area)

        preview_area = QWidget()
        preview_layout = QVBoxLayout(preview_area)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(6)
        preview_layout.addWidget(QLabel("合并结果预览（保存前先看一眼）："))
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText("还没有内容。点「全部提取」开始。")
        preview_layout.addWidget(self.preview, 1)
        splitter.addWidget(preview_area)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

        # ---- 底部：保存 ----
        bottom = QHBoxLayout()
        self.lbl_summary = QLabel()
        self.lbl_summary.setObjectName("Muted")
        bottom.addWidget(self.lbl_summary)
        bottom.addStretch(1)
        self.check_open_after = QCheckBox("保存后打开")
        self.check_open_after.setChecked(True)
        bottom.addWidget(self.check_open_after)
        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.reject)
        self.btn_save = QPushButton("保存为 Markdown")
        self.btn_save.setProperty("accent", True)
        self.btn_save.clicked.connect(self.save)
        bottom.addWidget(btn_close)
        bottom.addWidget(self.btn_save)
        layout.addLayout(bottom)

        self.reload()

    # ------------------------------------------------------------------
    # 列表
    # ------------------------------------------------------------------

    def reload(self) -> None:
        """重新扫描文件夹（勾选"包含子文件夹"后也会走这里）。"""
        images = digest.collect_images(
            self.folder, recursive=self.check_recursive.isChecked()
        )
        self.results = [digest.ImageResult(image=path) for path in images]
        self.lbl_head.setText(
            f"文件夹：<code>{common.html_escape(str(self.folder))}</code><br>"
            f"找到 <b>{len(images)}</b> 张图片。逐张提取；"
            f"<b>识别没把握的会直接插入原图</b>，不会编内容。"
        )
        self._update_ai_hint()
        self._fill_table()
        self._refresh_preview()

    def _update_ai_hint(self) -> None:
        """告诉用户这次会走哪条路（全自动识别 / 网页版粘贴）。"""
        provider = self._vision_provider()
        if provider:
            self.lbl_ai.setText(f"识别方式：<b>{provider}</b> 直接看图（全自动，无需粘贴）")
        else:
            self.lbl_ai.setText(
                "识别方式：<b>网页版桥接</b> —— 图片与提示词会自动进剪贴板，"
                "打开网页后粘进去，再把回答粘回来。"
                "<br>（想全自动识别：在「设置 → AI」里填一个支持视觉的模型"
                "并打开「发送图片」）"
            )

    def _vision_provider(self) -> str:
        """当前有没有"能直接看图"的提供方；有就返回它的显示名。"""
        try:
            manager = getattr(self.context, "ai", None)
            config = getattr(self.context, "config", None)
            if manager is None or config is None:
                return ""
            if not bool(config.get("ai.send_images", False)):
                return ""
            for provider_id in manager.provider_ids():
                setting = config.get(f"ai.providers.{provider_id}", {}) or {}
                if not bool(setting.get("supports_vision")):
                    continue
                adapter = manager.get(provider_id)
                if adapter is not None and adapter.is_configured()[0]:
                    return str(setting.get("label") or provider_id)
        except Exception:  # noqa: BLE001 - 只是提示文案，失败不影响功能
            log.debug("判断是否有视觉模型失败", exc_info=True)
        return ""

    def _fill_table(self) -> None:
        self.table.setRowCount(len(self.results))
        for row, result in enumerate(self.results):
            self.table.setItem(row, 0, QTableWidgetItem(result.image.name))
            self.table.setItem(row, 1, QTableWidgetItem(self._size_text(result.image)))
            self.table.setItem(row, 2, QTableWidgetItem(""))
            self.table.setItem(row, 3, QTableWidgetItem(""))
        self._refresh_rows()

    @staticmethod
    def _size_text(path: Path) -> str:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return "无法读取"
        return f"{pixmap.width()}×{pixmap.height()}"

    def _refresh_rows(self) -> None:
        """刷新每行的状态列与说明列。"""
        for row, result in enumerate(self.results):
            verdict = result.verdict
            if result.usable:
                status, detail = _STATUS_OK, verdict.reason_text
            elif result.text.strip() or result.user_unsure:
                status, detail = _STATUS_IMAGE, verdict.reason_text
            else:
                status, detail = _STATUS_TODO, ""
            status_item = self.table.item(row, 2)
            detail_item = self.table.item(row, 3)
            if status_item is None or detail_item is None:
                continue
            status_item.setText(status)
            detail_item.setText(detail)
            # 靠状态列上色：绿=成功、橙=插图、灰=待处理
            colors = {_STATUS_OK: "#1B7F3B", _STATUS_IMAGE: "#B26A00"}
            status_item.setForeground(QBrush(QColor(colors.get(status, "#8A8F98"))))
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        self.lbl_summary.setText(digest.summary_line(self.results))

    def _refresh_preview(self) -> None:
        text = digest.build_markdown(
            self.results, base_dir=self.folder, title=self.folder.name
        )
        self.preview.setPlainText(text)

    def _selected_rows(self) -> list[int]:
        return sorted({index.row() for index in self.table.selectedIndexes()})

    # ------------------------------------------------------------------
    # 提取
    # ------------------------------------------------------------------

    def extract_all(self) -> None:
        rows = [
            row for row, result in enumerate(self.results)
            if not result.text.strip() and not result.user_unsure
        ]
        if not rows:
            common.info(self, "所有图片都处理过了。", "图片提取")
            return
        self._extract_rows(rows)

    def extract_selected(self) -> None:
        rows = self._selected_rows()
        if not rows:
            common.warn(self, "先在列表里选中要处理的图片。", "图片提取")
            return
        self._extract_rows(rows)

    def _extract_rows(self, rows: list[int]) -> None:
        """逐张走一遍提取流程。用户随时可以"跳过"，跳过的按插图处理。"""
        total = len(self.results)
        for order, row in enumerate(rows, start=1):
            result = self.results[row]
            prompt = digest.build_prompt(row + 1, total, result.image.name)
            self.lbl_head.setText(
                f"正在处理第 {order}/{len(rows)} 张（总第 {row + 1}/{total}）："
                f"<b>{common.html_escape(result.image.name)}</b>"
            )
            self.table.selectRow(row)
            self._process_row(row, prompt)
            self._refresh_rows()
            self._refresh_preview()
        self.lbl_head.setText(
            f"文件夹：<code>{common.html_escape(str(self.folder))}</code><br>"
            f"处理完成 —— {digest.summary_line(self.results)}"
        )

    def _process_row(self, row: int, prompt: str) -> None:
        """处理单张：送 AI → 拿回答 → 判断可靠性。"""
        result = self.results[row]
        try:
            reply = web_bridge.send_to_ai(
                prompt,
                provider_id=self._active_provider_id(),
                context=self.context,
                parent=self,
                title=f"识别第 {row + 1} 张：{result.image.name}",
                image_path=result.image,
            )
        except Exception as exc:  # noqa: BLE001 - 单张失败不该中断整批
            log.warning("处理图片失败：%s", result.image, exc_info=True)
            result.text = ""
            result.user_unsure = True
            common.warn(
                self,
                f"「{result.image.name}」处理失败：{exc}\n\n"
                "这一张会改为直接插入原图。",
                "图片提取",
            )
            return

        text = (reply or "").strip()
        if not text:
            # 用户跳过 / 没粘回内容 → 按"没把握"处理，插原图
            result.text = ""
            result.user_unsure = True
            return

        result.text = text
        result.user_unsure = False
        result.edited = False
        verdict = result.verdict
        if not verdict.reliable:
            # 自动判为不可信：保留原文（放注释里备查），按插图处理
            result.user_unsure = True
            common.info(
                self,
                f"「{result.image.name}」这次识别**没有被采信**：\n\n"
                f"{verdict.reason_text}\n\n"
                "已改为在结果里直接插入原图。"
                "如果你看过原图、觉得这段其实是准的，"
                "可以选中它点「改为用文字」。",
                "这一张改为插图",
            )

    def _active_provider_id(self) -> str:
        try:
            manager = getattr(self.context, "ai", None)
            if manager is not None and manager.active_id:
                return str(manager.active_id)
        except Exception:  # noqa: BLE001
            pass
        return ""

    # ------------------------------------------------------------------
    # 手动干预
    # ------------------------------------------------------------------

    def mark_unsure(self) -> None:
        rows = self._selected_rows()
        if not rows:
            common.warn(self, "先选中要标记的图片。", "标记")
            return
        for row in rows:
            self.results[row].user_unsure = True
        self._refresh_rows()
        self._refresh_preview()

    def mark_sure(self) -> None:
        """取消"没把握"标记，恢复成用文字。

        只有本来就有正文的才真的能恢复；其余情况给出说明 ——
        否则用户会以为点了就能凭空变出文字来。
        """
        rows = self._selected_rows()
        if not rows:
            common.warn(self, "先选中要恢复的图片。", "改为用文字")
            return
        blocked = [row for row in rows if not self.results[row].text.strip()]
        for row in rows:
            if self.results[row].text.strip():
                self.results[row].user_unsure = False
        self._refresh_rows()
        self._refresh_preview()
        if blocked:
            common.info(
                self,
                f"有 {len(blocked)} 张还没有正文（没提取过或当时跳过了），"
                "所以只能继续插图。你可以先「提取选中的」，或点「编辑正文…」手动输入。",
                "改为用文字",
            )

    def edit_selected(self) -> None:
        rows = self._selected_rows()
        if len(rows) != 1:
            common.warn(self, "请选中**一张**图片再编辑正文。", "编辑正文")
            return
        row = rows[0]
        result = self.results[row]
        text = common.ask_multiline(
            self,
            f"编辑正文：{result.image.name}",
            "这一张的 Markdown 正文（清空表示改为插图）：",
            result.text,
        )
        if text is None:
            return
        result.text = text.strip()
        if result.text:
            result.edited = True      # 人改过的就是权威，不再自动判不可信
            result.user_unsure = False
        else:
            result.user_unsure = True
        self._refresh_rows()
        self._refresh_preview()

    def show_prompt(self) -> None:
        rows = self._selected_rows() or [0]
        row = rows[0]
        total = len(self.results)
        prompt = digest.build_prompt(row + 1, total, self.results[row].image.name)
        common.ask_multiline(
            self,
            "发给 AI 的提示词",
            f"处理「{self.results[row].image.name}」时会发这段（只读，可复制）：",
            prompt,
            readonly=True,
        )

    # ------------------------------------------------------------------
    # 保存
    # ------------------------------------------------------------------

    def save(self) -> None:
        if not self.results:
            common.warn(self, "这个文件夹里没有图片。", "无法保存")
            return
        markdown = digest.build_markdown(
            self.results, base_dir=self.folder, title=self.folder.name
        )
        target = self.folder / digest.suggest_filename(self.folder.name)
        # 同名就自动改名，绝不覆盖（和其它导入路径一致）
        target = file_ops.unique_path(target)
        try:
            target.write_text(markdown, encoding="utf-8")
        except OSError as exc:
            common.error(self, f"写入失败：{exc}", "保存失败")
            return
        self.saved_path = target
        self._refresh_preview()
        detail = digest.summary_line(self.results)
        common.info(
            self,
            f"已保存到：\n{target}\n\n{detail}\n\n"
            "识别没成功的部分已经插入了原图，图片用的是相对路径，"
            "整个文件夹搬走也不会失效。",
            "保存成功",
        )
        if self.check_open_after.isChecked():
            self.accept()


__all__ = ["ImageDigestDialog"]
