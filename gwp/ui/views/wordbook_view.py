"""单词书视图（书目页的「单词书」标签）。

需求原话：

> 在英语科目中新增单词书栏目 书内部可以添加单词卡 单词卡可折叠
> 我只需要添加英文单词/短语 就可以自动补齐中文解释/例句等等

这一页和别的标签不一样：它不是文件表格，而是**一列可折叠卡片**。
所以它不走 ``FileTable``，而是自己的滚动列表（见 ``widgets/word_card.py``）。

AI 补齐走的是"能力判断收在一处"的老路：有可用的 AI 就直接补齐，
没有就退化成"把提示词复制到剪贴板、你把回答粘回来"
（复用 ``common.ask_paste_reply``，与附件/图片提取一致）。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gwp.core.eventbus import BOOK_CONTENT_CHANGED, bus
from gwp.data_manager import wordbook
from gwp.data_manager.wordbook import WordCard
from gwp.ui import common
from gwp.ui.widgets.word_card import WordCardWidget

log = logging.getLogger(__name__)


class WordbookView(QWidget):
    """单词书：一列可折叠的单词卡。"""

    status_message = pyqtSignal(str)

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self.subject_name = ""
        self.book_name = ""
        self.cards: list[WordCard] = []
        self._widgets: list[WordCardWidget] = []
        #: 展开状态按"英文"记住，刷新后不丢（刷新是常事：补齐一张就刷一次）
        self._expanded: set[str] = set()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ---- 顶部操作条 ----
        bar = QHBoxLayout()
        bar.setSpacing(6)
        self.btn_add = QPushButton("添加单词")
        self.btn_add.setProperty("accent", True)
        self.btn_add.setToolTip("只需填英文单词或短语，其余交给 AI 补齐")
        self.btn_add.clicked.connect(self.add_word)
        bar.addWidget(self.btn_add)

        self.btn_complete = QPushButton("补齐全部")
        self.btn_complete.setToolTip("把还没有释义的卡片交给 AI 逐张补齐")
        self.btn_complete.clicked.connect(self.complete_all)
        bar.addWidget(self.btn_complete)

        self.btn_expand = QPushButton("全部展开")
        self.btn_expand.setToolTip("展开所有卡片（再点一次全部折叠）")
        self.btn_expand.clicked.connect(self.toggle_all)
        bar.addWidget(self.btn_expand)

        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("搜索英文或中文…")
        self.input_search.setClearButtonEnabled(True)
        self.input_search.setMinimumWidth(120)
        self.input_search.setMaximumWidth(240)
        self.input_search.textChanged.connect(lambda _t: self.render())
        bar.addWidget(self.input_search)
        bar.addStretch(1)

        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("Muted")
        bar.addWidget(self.lbl_count)
        layout.addLayout(bar)

        # ---- 卡片列表 ----
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        host = QWidget()
        self.list_layout = QVBoxLayout(host)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(host)
        layout.addWidget(self.scroll, 1)

        self.lbl_empty = QLabel("")
        self.lbl_empty.setObjectName("EmptyHint")
        self.lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_empty.setWordWrap(True)
        layout.addWidget(self.lbl_empty)

    # ==================================================================
    # 数据
    # ==================================================================

    def set_target(self, subject_name: str, book_name: str) -> None:
        """记下当前打开的是哪本书。

        **单词书的内容与这两个名字无关**（所有科目共用一个单词书），
        留着它们只是为了提示语更贴心、以及发事件时能带上来源。
        """
        self.subject_name = subject_name or ""
        self.book_name = book_name or ""

    def folder(self) -> Path | None:
        """单词书目录 —— **全局共用**，不在书目下面。

        需求："所有科目公用一个文件夹"。所以这里只认
        ``<user data>/wordbook``，跟当前打开哪本书无关。
        """
        paths = getattr(self.context, "paths", None)
        if paths is None:
            return None
        return Path(paths.wordbook_dir)

    def refresh(self) -> None:
        folder = self.folder()
        self.cards = wordbook.list_cards(folder) if folder is not None else []
        self.render()

    def render(self) -> None:
        """按搜索词重建卡片列表。"""
        keyword = (self.input_search.text() or "").strip().lower()

        def matches(card: WordCard) -> bool:
            if not keyword:
                return True
            haystack = " ".join((
                card.english, card.meaning, card.examples,
                card.phrases, card.tip, card.note,
            )).lower()
            return keyword in haystack

        shown = [card for card in self.cards if matches(card)]

        for widget in self._widgets:
            widget.setParent(None)
            widget.deleteLater()
        self._widgets.clear()

        for card in shown:
            widget = WordCardWidget(
                card,
                expanded=card.english.strip().lower() in self._expanded,
                parent=self,
            )
            widget.toggled.connect(self._on_card_toggled)
            widget.requested.connect(self._on_card_requested)
            # 插在末尾的 stretch 之前
            self.list_layout.insertWidget(self.list_layout.count() - 1, widget)
            self._widgets.append(widget)

        self.lbl_count.setText(wordbook.summarize(self.cards))
        self._update_empty_hint(shown)

    def _update_empty_hint(self, shown: list[WordCard]) -> None:
        """空状态要说清"为什么空"和"下一步做什么"。"""
        if self.cards and not shown:
            self.lbl_empty.setText(
                f"没有匹配「{self.input_search.text().strip()}」的单词卡。"
            )
            self.lbl_empty.setVisible(True)
            self.scroll.setVisible(False)
            return
        if not self.cards:
            self.lbl_empty.setText(
                "这个单词书还是空的。\n\n"
                "点左上角「添加单词」，只填英文（单词或短语）即可 ——\n"
                "中文释义、音标、例句、搭配会由 AI 自动补齐。\n\n"
                "卡片默认**折叠**，只显示英文；**单击卡片**就能展开看释义。"
            )
            self.lbl_empty.setVisible(True)
            self.scroll.setVisible(False)
            return
        self.lbl_empty.setVisible(False)
        self.scroll.setVisible(True)

    def _on_card_toggled(self, card: WordCard, expanded: bool) -> None:
        key = card.english.strip().lower()
        if expanded:
            self._expanded.add(key)
        else:
            self._expanded.discard(key)

    # ==================================================================
    # 添加
    # ==================================================================

    def add_word(self, word: str = "") -> None:
        """添加一张单词卡。**只问英文**，其余交给 AI。"""
        folder = self.folder()
        if folder is None:
            common.warn(self, "请先打开一个书目。", "无法添加单词")
            return

        text = (word or "").strip()
        if not text:
            text = common.ask_text(
                self, "添加单词", "英文单词或短语（其余交给 AI 补齐）",
                ok_text="添加",
            ) or ""
            text = text.strip()
        if not text:
            return

        existing = wordbook.find_card(folder, text)
        if existing is not None:
            common.info(
                self,
                f"「{existing.english}」已经在单词书里了。",
                "单词已存在",
            )
            return

        card = WordCard(english=text)
        try:
            wordbook.save_card(card, folder)
        except OSError as exc:
            common.error(self, f"保存失败：{exc}", "无法添加单词")
            return
        self.status_message.emit(f"已添加：{text}")
        self.refresh()
        self._announce_and_notify(folder)

        # 立刻尝试补齐 —— 用户只填了英文，等他自己再点一次太啰嗦
        if common.confirm(
            self,
            f"「{text}」已加入。\n\n现在就让 AI 补齐中文释义与例句吗？",
            "补齐解释",
            detail="以后也可以右键卡片选「AI 补齐」，或点「补齐全部」。",
        ):
            self.complete_card(card)

    # ==================================================================
    # AI 补齐
    # ==================================================================

    def complete_card(self, card: WordCard, *, force: bool = False) -> bool:
        """补齐一张卡。返回是否成功写入了内容。"""
        folder = self.folder()
        if folder is None:
            return False
        card = wordbook.find_card(folder, card.english) or card
        if card.locked and not force:
            common.info(
                self,
                f"「{card.english}」已锁定，不会被自动覆盖。\n"
                "要重新补齐请右键选「重新补齐（覆盖现有内容）」。",
                "已锁定",
            )
            return False

        prompt = wordbook.build_prompt(card.english)
        from gwp.ai.providers import web_bridge

        try:
            reply = web_bridge.send_to_ai(
                prompt,
                provider_id=self._active_provider_id(),
                context=self.context,
                parent=self,
                title=f"补齐单词：{card.english}",
            )
        except Exception as exc:  # noqa: BLE001 - 单张失败不该让整批中断
            log.warning("补齐单词失败：%s", card.english, exc_info=True)
            common.error(self, f"补齐「{card.english}」失败：{exc}", "AI 补齐失败")
            return False

        text = (reply or "").strip()
        if not text:
            self.status_message.emit(f"已跳过：{card.english}")
            return False

        fresh, error = wordbook.parse_completion(text, card.english)
        if fresh is None:
            common.warn(
                self,
                f"「{card.english}」：{error}\n\n"
                "你可以右键选「编辑…」手动填写。",
                "没能自动补齐",
            )
            return False
        if error:
            # 例如 AI 说"查不到该词" —— 这种情况**不写入**，避免污染卡片
            common.warn(self, f"「{card.english}」：{error}", "没能自动补齐")
            return False

        merged = wordbook.merge_into(wordbook.WordCard.from_dict(card.to_dict()),
                                     fresh, force=force)
        # 保留用户自己的笔记与锁定状态
        merged.note = card.note
        merged.locked = card.locked
        try:
            wordbook.save_card(merged, folder)
        except OSError as exc:
            common.error(self, f"保存失败：{exc}", "无法保存")
            return False
        self.status_message.emit(f"已补齐：{card.english}")
        self.refresh()
        self._announce_and_notify(folder)
        return True

    def complete_all(self) -> None:
        """把还没有内容的卡片逐张补齐。"""
        folder = self.folder()
        if folder is None:
            return
        pending = [card for card in self.cards if not card.completed]
        if not pending:
            common.info(self, "所有单词卡都已有内容了。", "无需补齐")
            return
        if not common.confirm(
            self,
            f"有 {len(pending)} 张卡还没有中文解释。\n\n"
            "会**逐张**让 AI 补齐（每张都要等一会儿）。现在开始吗？",
            "补齐全部",
            detail="中途可以关掉弹窗来跳过某一张。",
        ):
            return
        done = 0
        for card in pending:
            if self.complete_card(card):
                done += 1
        self.status_message.emit(f"补齐完成：成功 {done} / {len(pending)} 张")
        if done < len(pending):
            common.info(
                self,
                f"成功补齐 {done} 张，跳过 {len(pending) - done} 张。\n"
                "被跳过的卡片仍可右键单独补齐，或手动编辑。",
                "补齐完成",
            )

    def _active_provider_id(self) -> str:
        try:
            manager = getattr(self.context, "ai", None)
            if manager is not None and manager.active_id:
                return str(manager.active_id)
        except Exception:  # noqa: BLE001
            pass
        return ""

    def _announce_and_notify(self, folder: Path) -> None:
        """告诉其它页面"书目的内容变了"（首页统计等要跟着变）。"""
        try:
            bus.emit(BOOK_CONTENT_CHANGED,
                     subject=self.subject_name, book=self.book_name)
        except Exception:  # noqa: BLE001
            log.debug("广播书目变更失败", exc_info=True)

    # ==================================================================
    # 卡片操作
    # ==================================================================

    def _on_card_requested(self, card: WordCard, action: str) -> None:
        if action == "complete":
            self.complete_card(card)
        elif action == "recomplete":
            if common.confirm(
                self,
                f"重新补齐「{card.english}」？\n\n"
                "**会覆盖现有的释义与例句**（你自己写的笔记不受影响）。",
                "重新补齐",
                dangerous=True,
            ):
                self.complete_card(card, force=True)
        elif action == "edit":
            self.edit_card(card)
        elif action == "copy_word":
            self._copy(card.english, "单词已复制")
        elif action == "copy_meaning":
            if card.meaning.strip():
                self._copy(card.meaning, "释义已复制")
            else:
                common.info(self, "这张卡还没有释义。", "没有可复制的内容")
        elif action == "toggle_lock":
            self._toggle_lock(card)
        elif action == "delete":
            self.delete_card(card)

    def _copy(self, text: str, message: str) -> None:
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text)
            self.status_message.emit(message)

    def _toggle_lock(self, card: WordCard) -> None:
        folder = self.folder()
        if folder is None:
            return
        card.locked = not card.locked
        try:
            wordbook.save_card(card, folder)
        except OSError as exc:
            common.error(self, f"保存失败：{exc}", "无法保存")
            return
        self.status_message.emit(
            f"已锁定「{card.english}」" if card.locked
            else f"已解除锁定「{card.english}」"
        )
        self.refresh()

    def edit_card(self, card: WordCard) -> None:
        """编辑一张卡。用一个 json 风格的多行框 —— 字段少，不值得单独做表单。"""
        folder = self.folder()
        if folder is None:
            return
        text = common.ask_multiline(
            self,
            f"编辑单词卡：{card.english}",
            "按「字段名: 值」逐行填写（多行内容用 \\n 代替）。"
            "可以改的字段：phonetic / part_of_speech / meaning / "
            "examples / phrases / tip / note",
            self._card_to_lines(card),
        )
        if text is None:
            return
        data = self._lines_to_data(text)
        data["english"] = card.english          # 英文不在这个框里改（改名要换文件）
        updated = WordCard.from_dict(data)
        updated.english = card.english
        updated.created_at = card.created_at
        updated.locked = card.locked
        updated.completed = updated.has_details or card.completed
        try:
            wordbook.save_card(updated, folder)
        except OSError as exc:
            common.error(self, f"保存失败：{exc}", "无法保存")
            return
        self.status_message.emit(f"已保存：{card.english}")
        self.refresh()

    @staticmethod
    def _card_to_lines(card: WordCard) -> str:
        lines = []
        for name in ("phonetic", "part_of_speech", "meaning",
                     "examples", "phrases", "tip", "note"):
            value = str(getattr(card, name, "") or "").replace("\n", "\\n")
            lines.append(f"{name}: {value}")
        return "\n".join(lines)

    @staticmethod
    def _lines_to_data(text: str) -> dict:
        """把"字段名: 值"逐行解析成 dict。认不出的行忽略。"""
        known = {"english", "phonetic", "part_of_speech", "meaning",
                 "examples", "phrases", "tip", "note"}
        data: dict = {}
        current = ""
        buffer: list[str] = []
        for line in (text or "").splitlines():
            if ":" in line:
                head, _, tail = line.partition(":")
                key = head.strip().lower()
                if key in known:
                    if current:
                        data[current] = "\n".join(buffer).strip()
                    current = key
                    buffer = [tail.strip()]
                    continue
            if current:
                buffer.append(line)
        if current:
            data[current] = "\n".join(buffer).strip()
        for key, value in list(data.items()):
            data[key] = str(value).replace("\\n", "\n")
        return data

    def delete_card(self, card: WordCard) -> None:
        target = card.path
        if target is None:
            folder = self.folder()
            target = wordbook.card_path(folder, card.english) if folder else None
        if target is None:
            return
        if not common.confirm(
            self,
            f"删除单词卡「{card.english}」？\n\n这个操作不可撤销"
            "（文件已从磁盘移除，不进回收站）。",
            "删除单词卡",
            dangerous=True,
            detail=f"文件位置：{target}",
        ):
            return
        if wordbook.delete_card(target):
            self.status_message.emit(f"已删除：{card.english}")
            self._expanded.discard(card.english.strip().lower())
            self.refresh()
            self._announce_and_notify(target.parent)

    # ==================================================================

    def toggle_all(self) -> None:
        """全部展开 / 全部折叠。"""
        if not self._widgets:
            return
        any_collapsed = any(not w.expanded for w in self._widgets)
        for widget in self._widgets:
            widget.set_expanded(any_collapsed, notify=True)
        self.btn_expand.setText("全部折叠" if any_collapsed else "全部展开")
        self.status_message.emit(
            "已展开全部单词卡" if any_collapsed else "已折叠全部单词卡"
        )


__all__ = ["WordbookView"]
