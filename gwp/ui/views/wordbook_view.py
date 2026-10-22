"""单词书视图（书目页的「单词书」标签）。

需求原话：

> 在英语科目中新增单词书栏目 书内部可以添加单词卡 单词卡可折叠
> 我只需要添加英文单词/短语 就可以自动补齐中文解释/例句等等

这一页和别的标签不一样：它不是文件表格，而是**一列可折叠卡片**。
所以它不走 ``FileTable``，而是自己的滚动列表（见 ``widgets/word_card.py``）。

**AI 补齐必须在后台线程跑**（v2.1 修的一个真 bug）：

原来是在界面线程里同步调用 AI —— 单张会"点一下卡半天"，
「补齐全部」更是逐张串行请求，N 张卡就把界面冻住 N 次网络往返的时间
（用户报障："单词补齐功能障碍，会导致程序卡死"）。

现在照 AI summary 的做法走 ``AIWorker``：

* 后台线程只负责**取 AI 的回答**（``send_to_ai(allow_paste=False)``）；
* 界面线程负责**解析、合并、读写卡片文件**（磁盘 IO 很快，不会卡）；
* 进度通过信号回到界面，可随时取消。

只有"网页版粘贴"那条路仍留在界面线程 —— 它本来就要等用户手动操作，
而且**绝不能**在后台线程里弹窗（Qt 不允许在非 GUI 线程建控件）。
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

from gwp.ai.providers import web_bridge
from gwp.ai.worker import AIWorker
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
        #: 正在跑补齐任务的后台线程（None = 没在跑）
        self._worker: AIWorker | None = None
        #: 补齐进度框（只有"补齐全部"才弹）
        self._busy: common.BusyDialog | None = None
        #: 本次补齐是否强制覆盖已有字段（由 _start_completion 设置）
        self._completion_force: bool = False

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

    @property
    def is_completing(self) -> bool:
        """是否有补齐任务在跑（测试与按钮状态都用它）。"""
        worker = self._worker
        try:
            return worker is not None and worker.isRunning()
        except RuntimeError:          # 底层 C++ 对象已销毁
            return False

    def _direct_ai_available(self) -> bool:
        """现在能不能**直接调用** AI（不用手工粘贴）。"""
        try:
            return web_bridge.has_direct_provider(self.context,
                                                  self._active_provider_id())
        except Exception:  # noqa: BLE001
            return False

    def complete_card(self, card: WordCard, *, force: bool = False) -> bool:
        """补齐一张卡。返回**是否已发起**。

        **这个函数不再阻塞界面**：AI 调用在后台线程，结果通过信号回来。
        原来的实现是在界面线程里同步调 API —— 网络一慢，界面就假死
        （用户报障："单词补齐功能障碍，会导致程序卡死"）。

        例外：如果当前**只能走网页版粘贴**，会留在界面线程里同步完成。
        那种流程本来就要等用户手动复制粘贴，是用户主动参与的模态过程；
        而且它**绝不能**放到后台线程——Qt 不允许在非 GUI 线程建控件。
        """
        folder = self.folder()
        if folder is None:
            return False
        if self.is_completing:
            self.status_message.emit("正在补齐中，请稍等…")
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

        if self._direct_ai_available():
            self._start_completion([card], force=force, batch=False)
            return True
        return self._complete_via_paste(card, force=force)

    def _complete_via_paste(self, card: WordCard, *, force: bool = False) -> bool:
        """走「复制提示词 + 让用户粘贴回答」这条路（**必须在 GUI 线程**）。"""
        folder = self.folder()
        if folder is None:
            return False

        prompt = wordbook.build_prompt(card.english)
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

    # -- 后台补齐 -------------------------------------------------------

    def _start_completion(
        self, cards: list[WordCard], *, force: bool, batch: bool
    ) -> None:
        """起一个后台任务去取 AI 回答（界面线程只等信号）。"""
        folder = self.folder()
        if folder is None or not cards:
            return
        names = [card.english for card in cards]
        total = max(1, len(names))
        provider_id = self._active_provider_id()
        context = self.context

        def task(*, on_progress=None, should_cancel=None, **_kwargs):
            """在线程里跑：**只取回答，不碰界面、不碰文件**。"""
            results: list[tuple[str, str, str]] = []
            for index, name in enumerate(names, 1):
                if should_cancel is not None and should_cancel():
                    log.info("单词补齐被取消（已完成 %d/%d）", index - 1, total)
                    break
                if on_progress is not None:
                    on_progress(
                        f"正在补齐 {index}/{total}：{name}",
                        int((index - 1) * 100 / total),
                        name,
                    )
                try:
                    reply = web_bridge.send_to_ai(
                        wordbook.build_prompt(name),
                        provider_id=provider_id,
                        context=context,
                        parent=None,
                        title=f"补齐单词：{name}",
                        # **后台线程绝不能弹粘贴框**（Qt 不允许非 GUI 线程建控件），
                        # 批量时还会开一堆浏览器窗口。
                        allow_paste=False,
                    )
                except Exception as exc:  # noqa: BLE001 - 单张失败继续下一张
                    log.warning("补齐 %s 失败：%s", name, exc, exc_info=True)
                    results.append((name, "", str(exc)))
                    continue
                results.append((name, (reply or "").strip(), ""))
            if on_progress is not None:
                on_progress("整理结果…", 100, "")
            return results

        worker = AIWorker(task, parent=self, label="补齐单词")
        worker.progress.connect(self._on_completion_progress)
        # 注意：这里连的是**成员方法**而不是 lambda。
        # 跨线程信号要投递回 GUI 线程，需要一个 QObject 接收者来确定线程归属；
        # 连普通函数/lambda 时 PyQt 的线程语义更微妙（可能变成直接调用，
        # 那就等于在后台线程里改界面了）。用成员方法最稳。
        self._completion_force = force
        worker.finished_ok.connect(self._on_completion_finished)
        worker.failed.connect(self._on_completion_failed)
        worker.cancelled.connect(self._on_completion_cancelled)
        self._worker = worker
        self._set_completing_ui(True)
        if batch:
            self._busy = common.BusyDialog(self, "正在补齐单词", "准备中…")
            self._busy.canceled.connect(self._cancel_completion)
            self._busy.show()
        else:
            self._busy = None
            self.status_message.emit("正在让 AI 补齐…")
        worker.start()

    def _on_completion_progress(self, message: str, percent: int, detail: str) -> None:
        if self._busy is not None:
            self._busy.report(message, percent, detail)
        else:
            self.status_message.emit(message)

    def _on_completion_finished(self, results) -> None:
        """回到界面线程后才写文件（磁盘 IO 很快，不会卡）。"""
        self._close_busy()
        self._set_completing_ui(False)
        force = bool(getattr(self, "_completion_force", False))
        folder = self.folder()
        if folder is None:
            return
        done = 0
        skipped: list[str] = []
        for name, text, error in (results or []):
            if error or not text:
                skipped.append(name)
                continue
            card = wordbook.find_card(folder, name)
            if card is None:
                skipped.append(name)
                continue
            fresh, parse_error = wordbook.parse_completion(text, name)
            if fresh is None or parse_error:
                # 解析不了 / AI 说查不到 -> **不写入**，避免污染卡片
                skipped.append(name)
                continue
            merged = wordbook.merge_into(
                wordbook.WordCard.from_dict(card.to_dict()), fresh, force=force
            )
            merged.note = card.note
            merged.locked = card.locked
            try:
                wordbook.save_card(merged, folder)
            except OSError as exc:
                log.warning("保存 %s 失败：%s", name, exc, exc_info=True)
                skipped.append(name)
                continue
            done += 1

        total = len(results or [])
        self.refresh()
        self._announce_and_notify(folder)
        self.status_message.emit(f"补齐完成：成功 {done} / {total} 张")
        if skipped:
            common.info(
                self,
                f"成功补齐 {done} 张，跳过 {len(skipped)} 张"
                f"（{'、'.join(skipped[:6])}"
                f"{' 等' if len(skipped) > 6 else ''}）。\n\n"
                "被跳过的卡片仍可右键单独补齐，或右键「编辑…」手动填写。",
                "补齐完成",
            )

    def _on_completion_failed(self, message: str) -> None:
        self._close_busy()
        self._set_completing_ui(False)
        log.warning("单词补齐任务失败：%s", message)
        common.error(self, f"补齐失败：{message}", "AI 补齐失败")

    def _on_completion_cancelled(self) -> None:
        self._close_busy()
        self._set_completing_ui(False)
        self.status_message.emit("已取消补齐")

    def _cancel_completion(self) -> None:
        if self._worker is not None:
            try:
                self._worker.cancel()
            except RuntimeError:
                pass

    def _close_busy(self) -> None:
        if self._busy is not None:
            try:
                self._busy.close()
            except RuntimeError:
                pass
            self._busy = None

    def _set_completing_ui(self, active: bool) -> None:
        """补齐期间禁用会并发触发第二次补齐的按钮。"""
        for button in (getattr(self, "btn_add", None),
                       getattr(self, "btn_complete", None)):
            if button is not None:
                button.setEnabled(not active)

    def complete_all(self) -> None:
        """把还没有内容的卡片逐张补齐（**后台线程**，界面不卡）。"""
        folder = self.folder()
        if folder is None:
            return
        if self.is_completing:
            common.info(self, "正在补齐中，请稍等…", "请稍候")
            return
        pending = [card for card in self.cards if not card.completed]
        if not pending:
            common.info(self, "所有单词卡都已有内容了。", "无需补齐")
            return
        if not self._direct_ai_available():
            # 批量时绝不能让每张卡都弹一次粘贴框（会开 N 个浏览器窗口）。
            common.info(
                self,
                "「补齐全部」需要能**直接调用**的 AI。\n\n"
                "请到「AI → AI 设置」里填一个 API Key（DeepSeek / GPT / 自定义）。\n"
                "只配了网页版时，请逐张右键「AI 补齐」—— 那样每张都需要你粘贴回答。",
                "需要配置 API",
            )
            return
        if not common.confirm(
            self,
            f"有 {len(pending)} 张卡还没有中文解释。\n\n"
            "会在**后台**逐张让 AI 补齐，进度框里可以随时取消。现在开始吗？",
            "补齐全部",
            detail="补齐过程中界面可以继续用，但别关掉软件。",
        ):
            return
        self._start_completion(pending, force=False, batch=True)

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
