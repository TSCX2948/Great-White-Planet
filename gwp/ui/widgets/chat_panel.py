"""AI 聊天面板（需求文档第八节的"AI 双栏模式"右侧）。

功能：
* 与当前 AI 对话，支持流式输出；
* AI 不确定时弹窗提问，用户回答后自动继续；
* 首次打开自动发送当前文件；
* 关闭时保存聊天记录；
* 可切换 AI、清空记录、把回答插入文档。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gwp.ai.types import AIError, AiQuestion, ChatMessage, ChatOptions
from gwp.ai.worker import AIWorker
from gwp.bootstrap import AppContext
from gwp.services import attachment as attach
from gwp.ui import common
from gwp.ui.dialogs.question_dialog import AiQuestionDialog

log = logging.getLogger(__name__)


class _AttachmentChip(QFrame):
    """输入框上方那一条附件标签（名字 + 状态 + 删除按钮）。"""

    removed = pyqtSignal(object)      # Attachment

    def __init__(self, item: attach.Attachment, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item
        self.setObjectName("AttachChip")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 4, 3)
        layout.setSpacing(6)

        label = QLabel(f"📎 {item.name}")
        label.setToolTip(f"{item.path}\n{item.describe()}")
        layout.addWidget(label)

        # 状态直接写出来 —— 用户必须知道"这份附件到底传没传进去"，
        # 否则会相信一个其实没读过文件的回答。
        state = QLabel(item.describe())
        state.setObjectName("Muted")
        state.setToolTip(item.describe())
        if item.kind == attach.KIND_TEXT and item.usable:
            state.setStyleSheet("color: #1B7F3B;")
        else:
            state.setStyleSheet("color: #B26A00;")
        layout.addWidget(state)

        button = QToolButton()
        button.setText("✕")
        button.setToolTip("移除这份附件")
        button.clicked.connect(lambda: self.removed.emit(self.item))
        layout.addWidget(button)


class ChatPanel(QFrame):
    """AI 聊天面板。"""

    insert_requested = pyqtSignal(str)          # 把回答插入文档
    status_message = pyqtSignal(str)

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        #: 当前待发送的附件（需求：AI 助手新增附件上传功能）
        self.attachments: list[attach.Attachment] = []
        self.setObjectName("Panel")
        self.session: Any = None                 # ChatSession
        self.document_path: Path | None = None
        self.daily_mode = False                  # True = 不绑定文件的日常对话
        self._worker: AIWorker | None = None
        self._stream_buffer: list[str] = []
        self._pending_question_dialog: AiQuestionDialog | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # ---- 顶部：当前 AI + 操作 ----
        header = QHBoxLayout()
        header.setSpacing(6)
        self.title_label = QLabel("AI 助手")
        self.title_label.setObjectName("SectionTitle")
        header.addWidget(self.title_label)
        self.combo_ai = QComboBox()
        self.combo_ai.setMinimumWidth(150)
        self.combo_ai.setToolTip("切换当前使用的 AI")
        self.combo_ai.currentIndexChanged.connect(self._on_ai_changed)
        header.addWidget(self.combo_ai, 1)
        self.btn_refresh = QToolButton()
        self.btn_refresh.setText("↻")
        self.btn_refresh.setToolTip("刷新 AI（重新连接并自检）")
        self.btn_refresh.clicked.connect(self._refresh_ai)
        header.addWidget(self.btn_refresh)
        self.btn_settings = QToolButton()
        self.btn_settings.setText("⚙")
        self.btn_settings.setToolTip("AI 设置")
        self.btn_settings.clicked.connect(self.open_settings)
        header.addWidget(self.btn_settings)
        layout.addLayout(header)

        # ---- 对话区 ----
        self.view = QTextBrowser()
        self.view.setOpenExternalLinks(True)
        self.view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.view, 1)

        # ---- 输入区 ----
        # 附件条：有附件时才显示（平时不占地方）
        self.attach_bar = QWidget()
        self.attach_layout = QHBoxLayout(self.attach_bar)
        self.attach_layout.setContentsMargins(0, 0, 0, 0)
        self.attach_layout.setSpacing(6)
        self.attach_bar.setVisible(False)
        layout.addWidget(self.attach_bar)

        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("向 AI 提问……（Ctrl+Enter 发送）")
        self.input.setFixedHeight(92)
        layout.addWidget(self.input)

        buttons = QHBoxLayout()
        buttons.setSpacing(6)
        self.btn_send = QPushButton("发送")
        self.btn_send.setProperty("accent", True)
        self.btn_send.clicked.connect(self.send_current_input)
        buttons.addWidget(self.btn_send)

        self.btn_stop = QPushButton("停止")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop)
        buttons.addWidget(self.btn_stop)

        # 附件（需求：AI 助手新增附件上传功能）
        self.btn_attach = QPushButton("附件")
        self.btn_attach.setToolTip(
            "添加附件给 AI 看：\n"
            "· PDF / Word / PPT / Excel / CSV / 文本 / 代码 → **本地提取正文**后一起发送；\n"
            "· 图片 → 需要视觉模型（或用「工具 → 图片提取为 Markdown」）"
        )
        self.btn_attach.clicked.connect(self.add_attachments)
        buttons.addWidget(self.btn_attach)

        self.btn_resend = QPushButton("重发文件")
        self.btn_resend.setToolTip("把当前文件内容重新发送给 AI")
        self.btn_resend.clicked.connect(lambda: self.resend_file(force=True))
        buttons.addWidget(self.btn_resend)

        self.btn_insert = QPushButton("插入文档")
        self.btn_insert.setToolTip("把最后一条 AI 回答插入到文档内容")
        self.btn_insert.clicked.connect(self._insert_last_answer)
        buttons.addWidget(self.btn_insert)

        self.btn_clear = QPushButton("清空")
        self.btn_clear.setToolTip("删除本次聊天记录")
        self.btn_clear.clicked.connect(self.clear_session)
        buttons.addWidget(self.btn_clear)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        # 快捷键
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self.input)
        shortcut.activated.connect(self.send_current_input)
        shortcut2 = QShortcut(QKeySequence("Ctrl+Enter"), self.input)
        shortcut2.activated.connect(self.send_current_input)

        self.reload_providers()
        self._render()

    # ==================================================================
    # 提供方
    # ==================================================================

    def reload_providers(self) -> None:
        self.combo_ai.blockSignals(True)
        self.combo_ai.clear()
        entries = self.context.ai.available()
        active_id = self.context.ai.active_id
        current_index = 0
        for index, (provider_id, label, ok, reason) in enumerate(entries):
            text = label if ok else f"{label}（不可用）"
            self.combo_ai.addItem(text, provider_id)
            if not ok and reason:
                self.combo_ai.setItemData(index, reason, Qt.ItemDataRole.ToolTipRole)
            if provider_id == active_id:
                current_index = index
        self.combo_ai.setCurrentIndex(current_index)
        self.combo_ai.blockSignals(False)
        self._update_ai_hint()

    def _update_ai_hint(self) -> None:
        provider_id = self.context.ai.active_id
        adapter = self.context.ai.get(provider_id)
        if adapter is None:
            self.btn_send.setEnabled(False)
            self.btn_send.setToolTip("没有可用的 AI，请在 AI 设置中配置")
            return
        ok, reason = adapter.is_configured()
        self.btn_send.setEnabled(True)
        self.btn_send.setToolTip("" if ok else f"当前 AI 不可用：{reason}（发送时会自动尝试兜底 AI）")

    def _on_ai_changed(self, index: int) -> None:
        provider_id = self.combo_ai.itemData(index)
        if not provider_id:
            return
        try:
            self.context.ai.set_active(provider_id)
        except AIError as exc:
            common.warn(self, str(exc))
            return
        self._update_ai_hint()
        self.status_message.emit(f"已切换到 {self.context.ai.describe_active()}")

    def _refresh_ai(self) -> None:
        self.status_message.emit("正在刷新 AI ……")
        ok, message = self.context.ai.refresh()
        self.context.ai.invalidate()
        self.reload_providers()
        if ok:
            common.info(self, message, "刷新 AI")
        else:
            common.warn(self, message, "刷新 AI")
        self.status_message.emit(message)

    def open_settings(self) -> None:
        from gwp.ui.dialogs.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self.context, self.window(), initial_page="ai")
        if dialog.exec():
            self.context.ai.invalidate()
            self.reload_providers()
            self.status_message.emit("AI 设置已保存")

    # ==================================================================
    # 会话
    # ==================================================================

    def bind_document(self, path: Path | None, session_key: str, title: str = "") -> None:
        """切换面板所绑定的文档（会载入对应的聊天记录）。

        ``path`` 为 None 时表示**不绑定文件**的日常对话（见 GlobalChatWindow）。
        """
        from gwp.ai.chat_session import ChatSession

        if self.session is not None and self.session.key == session_key:
            self.document_path = path
            return
        self.save_session()
        self.document_path = path
        self.daily_mode = path is None
        session = self.context.chats.load(session_key)
        if not session.key:
            session = ChatSession(key=session_key)
        if session.key:
            session.title = title or session.title
        if path is not None:
            session.document_path = str(path)
        self.session = session
        self.title_label.setText("AI 助手" if path is not None else "AI 日常对话")
        # 不绑定文件时，"重发文件"和"插入文档"没有意义
        self.btn_resend.setVisible(path is not None)
        self.btn_insert.setVisible(path is not None)
        self._render()

    def save_session(self) -> None:
        if self.session is not None and not self.session.is_empty:
            self.session.provider = self.context.ai.active_id
            self.context.chats.save(self.session)

    def clear_session(self) -> None:
        if self.session is None:
            return
        if self.session.is_empty:
            return
        if not common.confirm(self, "确定要删除本次聊天记录吗？", "清空聊天记录"):
            return
        self.session.clear()
        self.context.chats.delete(self.session.key)
        self._render()
        self.status_message.emit("聊天记录已清空")

    def resend_file(self, force: bool = False) -> None:
        """把当前文件内容发给 AI（首次打开时自动调用）。"""
        if self.session is None or self.document_path is None:
            return
        if self.session.file_sent and not force:
            return
        try:
            content = self.document_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            common.warn(self, f"无法读取文件：{exc}")
            return
        limit = int(self.context.config.get("ai.max_file_chars", 60000) or 60000)
        truncated = len(content) > limit
        if truncated:
            content = content[:limit] + "\n\n（文件过长，已截断）"
        relative = self._relative_label()
        message = (
            f"【当前文件：{relative}】\n\n```markdown\n{content}\n```\n\n"
            "请阅读这份文件。我先不提问；如果内容有需要我澄清的地方，按系统要求向我提问。"
        )
        self.session.file_sent = True
        self._send(message, show_user_bubble=False, label=f"已发送文件：{relative}")
        self.save_session()

    def _relative_label(self) -> str:
        path = self.document_path
        if path is None:
            return ""
        try:
            return path.relative_to(self.context.paths.user_data).as_posix()
        except ValueError:
            return str(path)

    # ==================================================================
    # 发送
    # ==================================================================

    def send_current_input(self) -> None:
        text = self.input.toPlainText().strip()
        if not text:
            # 允许"只发附件"：用户可能就是想问"这份讲义的重点是什么"
            if not self.attachments:
                return
            text = "请阅读我上传的附件，并总结要点。"
        self.input.clear()
        self._send(text)

    # ==================================================================
    # 附件（需求：AI 助手新增附件上传功能）
    # ==================================================================
    #
    # 为什么是"提取正文"而不是真的"上传"：
    # 当前 AI 是文本模型，API 收不了文件；而 PDF/Word/Excel 的正文
    # 可以**本地确定性提取**（比让 AI 看图猜字可靠得多）。
    # 图片则交给视觉模型或「图片提取为 Markdown」流程。
    # 详见 gwp/services/attachment.py 的模块说明。

    def add_attachments(self) -> None:
        """选文件并提取内容。图片会被单独标出来（它需要视觉模型）。"""
        filters = (
            "可提取的文件 (*.pdf *.docx *.doc *.pptx *.ppt *.xlsx *.xls *.csv "
            "*.md *.markdown *.txt *.png *.jpg *.jpeg *.webp *.bmp *.gif);;"
            "文档 (*.pdf *.docx *.doc *.pptx *.ppt *.xlsx *.xls *.csv);;"
            "图片 (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;"
            "所有文件 (*.*)"
        )
        paths = common.pick_open_files(self, "选择要发给 AI 的附件", filters)
        if not paths:
            return
        self.attach_files(paths)

    def attach_files(self, paths: list[Path]) -> None:
        """把一批文件加进附件区（已加过的跳过，避免重复占上下文）。"""
        per_file, _total = attach.budget_from_config(self.context.config)
        known = {item.path.resolve() for item in self.attachments}
        added: list[attach.Attachment] = []
        skipped: list[str] = []
        for path in paths:
            target = Path(path)
            try:
                resolved = target.resolve()
            except OSError:
                resolved = target
            if resolved in known:
                skipped.append(target.name)
                continue
            item = attach.extract_attachment(target, per_file_chars=per_file)
            self.attachments.append(item)
            added.append(item)
            known.add(resolved)

        self._refresh_attachments()
        if added:
            self.status_message.emit(attach.summarize(self.attachments))
        if skipped:
            common.info(
                self,
                "这些文件已经在附件里了，已跳过：\n" + "、".join(skipped),
                "附件",
            )
        # 图片必须单独提醒：它**没有**被送进对话，用户不能以为 AI 看到了
        images = [item for item in added if item.kind == attach.KIND_IMAGE]
        if images:
            self._warn_about_images(images)

    def _warn_about_images(self, images: list[attach.Attachment]) -> None:
        """如实告诉用户图片没被送进去，并给出可行的做法。"""
        vision = self._vision_provider_label()
        names = "、".join(item.name for item in images)
        if vision:
            common.info(
                self,
                f"{names}\n\n会用「{vision}」直接识别（已在设置里允许发送图片）。",
                "图片附件",
            )
            return
        common.warn(
            self,
            f"{names}\n\n"
            "**这些图片的内容不会包含在对话里** —— 当前的 AI 看不了图片。\n\n"
            "你有两个办法：\n"
            "1. 在「设置 → AI」里勾选「允许把图片发送给 AI」，"
            "并配一个支持视觉的模型（通义千问 qwen-vl、智谱 glm-4v、gpt-4o 等）；\n"
            "2. 用「工具 → 图片提取为 Markdown」先把图片转成文字，"
            "再把生成的 md 作为附件发给我。",
            "图片没法直接发送",
        )

    def _vision_provider_label(self) -> str:
        """现在有没有可用的视觉模型；有就返回它的显示名。"""
        try:
            from gwp.ai.providers.web_bridge import _provider_sees_images

            manager = self.context.ai
            for provider_id in manager.provider_ids():
                adapter = manager.get(provider_id)
                if adapter is None:
                    continue
                if not _provider_sees_images(self.context, provider_id, adapter):
                    continue
                if adapter.is_configured()[0]:
                    setting = self.context.config.get(
                        f"ai.providers.{provider_id}", {}
                    ) or {}
                    return str(setting.get("label") or provider_id)
        except Exception:  # noqa: BLE001 - 只是提示，失败不影响功能
            log.debug("判断视觉模型失败", exc_info=True)
        return ""

    def remove_attachment(self, item: attach.Attachment) -> None:
        self.attachments = [a for a in self.attachments if a is not item]
        self._refresh_attachments()
        self.status_message.emit(attach.summarize(self.attachments) or "附件已清空")

    def clear_attachments(self) -> None:
        self.attachments = []
        self._refresh_attachments()

    def _refresh_attachments(self) -> None:
        """重画附件条（没有附件就整条隐藏，不占地方）。"""
        while self.attach_layout.count():
            entry = self.attach_layout.takeAt(0)
            widget = entry.widget()
            if widget is not None:
                widget.deleteLater()
        for item in self.attachments:
            chip = _AttachmentChip(item, self.attach_bar)
            chip.removed.connect(self.remove_attachment)
            self.attach_layout.addWidget(chip)
        if self.attachments:
            clear = QToolButton()
            clear.setText("全部移除")
            clear.setToolTip("清空所有附件")
            clear.clicked.connect(self.clear_attachments)
            self.attach_layout.addWidget(clear)
            self.attach_layout.addStretch(1)
        self.attach_bar.setVisible(bool(self.attachments))

    def attachment_block(self) -> str:
        """拼好要附在提问后面的附件内容（没有可用附件时返回空串）。"""
        if not self.attachments:
            return ""
        _per_file, total = attach.budget_from_config(self.context.config)
        return attach.build_attachment_block(self.attachments, total_chars=total)

    def _send(self, text: str, show_user_bubble: bool = True, label: str = "") -> None:
        if self.session is None:
            common.warn(self, "请先打开一个 Markdown 文件再使用 AI。")
            return
        if self._worker is not None and self._worker.isRunning():
            common.warn(self, "AI 正在回答，请先等待或点击停止。")
            return

        # 附件内容拼进**这一条**用户消息里，而不是塞进系统提示词 ——
        # 这样它只影响本次提问，不会在后续对话里反复占用上下文。
        block = self.attachment_block()
        payload = f"{text}\n\n{block}" if block else text
        attach_names = [item.name for item in self.attachments]

        if show_user_bubble:
            self.session.add("user", text)
        else:
            self.session.add("user", text, system_note=True)
        labels = ([self._relative_label()] if self.document_path else []) + attach_names
        self.session.attachments = labels
        self._render()
        if label:
            self.status_message.emit(label)

        messages = self._build_messages()
        # `_build_messages` 的最后一条一定就是刚才那条用户消息
        # （它以 "请继续。" 兜底，所以列表必非空），把附件内容替换进去。
        # 附件放在**用户消息**里而不是系统提示词里：只影响本次提问，
        # 不会在后续每一轮里反复占用上下文。
        messages[-1] = ChatMessage(
            role="user",
            content=payload,
            images=self._vision_image_paths(),
        )
        # 附件内容已经进了聊天记录（后续追问仍能看到），
        # 所以把输入区的附件**清掉**：否则用户每问一句都会重发一遍全文，
        # 既烧 token 又会把上下文挤满、让回答变差。
        if self.attachments:
            self.clear_attachments()
            self.status_message.emit(
                f"附件的 {len(attach_names)} 份内容已随本条消息发送"
            )
        options = ChatOptions(
            temperature=float(self.context.config.get("ai.temperature", 0.3) or 0.3),
            max_tokens=int(self.context.config.get("ai.max_tokens", 8192) or 8192),
            stream=bool(self.context.config.get("ai.stream", True)),
            system=self._system_prompt(),
        )
        self._stream_buffer = []
        self._begin_assistant_bubble()

        worker = AIWorker(
            task=lambda **helpers: self._chat_task(messages, options, helpers),
            parent=self,
            label="AI 对话",
        )
        worker.chunk.connect(self._on_chunk)
        worker.progress.connect(lambda message, percent, detail: self.status_message.emit(message))
        worker.question.connect(self._on_question)
        worker.finished_ok.connect(self._on_finished)
        worker.failed.connect(self._on_failed)
        worker.cancelled.connect(self._on_cancelled)
        self._worker = worker
        self._set_busy(True)
        worker.start()

    def _vision_image_paths(self) -> list[str]:
        """图片附件里**可以真的发给模型**的那些路径。

        只有在用户打开「允许把图片发送给 AI」、且当前有支持视觉的模型时
        才返回路径 —— 否则返回空，附件块里已经如实写明了原因。
        """
        images = [a for a in self.attachments if a.kind == attach.KIND_IMAGE]
        if not images:
            return []
        if not bool(self.context.config.get("ai.send_images", False)):
            return []
        if not self._vision_provider_label():
            return []
        return [str(a.path) for a in images]

    def _chat_task(self, messages: list[ChatMessage], options: ChatOptions, helpers: dict) -> str:
        """在工作线程里执行；提问由 worker 转成信号交给界面。"""
        text, provider_id = self.context.ai.chat_with_fallback(
            messages,
            options,
            on_chunk=helpers["on_chunk"],
            question_handler=helpers["on_question"],
            should_cancel=helpers["should_cancel"],
        )
        return {"text": text, "provider": provider_id}

    def _system_prompt(self) -> str:
        # 日常对话（不绑定文件）用另一套提示词：不假装读过用户的资料
        key = "prompts.daily_chat_system" if self.daily_mode else "prompts.chat_system"
        fallback_key = "prompts.chat_system"
        base = str(self.context.config.get(key, "") or "").strip()
        if not base:
            base = str(self.context.config.get(fallback_key, "") or "")
        rules = str(self.context.config.get("prompts.uncertainty_rules", "") or "").strip()
        return f"{base}\n\n{rules}" if rules else base

    def _build_messages(self) -> list[ChatMessage]:
        messages: list[ChatMessage] = []
        for message in self.session.messages:
            if message.meta.get("system_note"):
                continue
            messages.append(ChatMessage(role=message.role, content=message.content))
        # 保证最后一条是用户消息
        if not messages or messages[-1].role != "user":
            messages.append(ChatMessage(role="user", content="请继续。"))
        limit = int(self.context.config.get("ai.history_limit", 24) or 24)
        if len(messages) > limit:
            messages = messages[-limit:]
        return messages

    # ==================================================================
    # 工作线程回调
    # ==================================================================

    def _set_busy(self, busy: bool) -> None:
        self.btn_send.setEnabled(not busy)
        self.btn_stop.setEnabled(busy)
        self.combo_ai.setEnabled(not busy)
        self.btn_resend.setEnabled(not busy)

    def _begin_assistant_bubble(self) -> None:
        self.session.add("assistant", "")
        self._render()

    def _on_chunk(self, text: str) -> None:
        self._stream_buffer.append(text)
        if self.session.messages:
            self.session.messages[-1].content = "".join(self._stream_buffer)
        self._render(scroll=True)

    def _on_question(self, question: AiQuestion, holder: dict) -> None:
        """在工作线程提问时弹出对话框（信号已在界面线程）。"""
        dialog = AiQuestionDialog(question, self.window())
        dialog.exec()
        answer = dialog.answer()
        worker = self._worker
        if worker is not None:
            worker.answer_question(answer)
        if answer:
            self.session.add("assistant", f"（AI 提问：{question.question}）", question=True)
            self.session.add("user", answer, question_answer=True)
            self._stream_buffer.clear()
            self._begin_assistant_bubble()
            self._render(scroll=True)
        self.status_message.emit("已提交回答" if answer else "已取消提问")

    def _on_finished(self, payload: Any) -> None:
        self._set_busy(False)
        text = ""
        provider = ""
        if isinstance(payload, dict):
            text = str(payload.get("text", ""))
            provider = str(payload.get("provider", ""))
        if self.session.messages:
            self.session.messages[-1].content = text or "".join(self._stream_buffer)
        self.session.provider = provider or self.context.ai.active_id
        self._stream_buffer.clear()
        self._render(scroll=True)
        self.save_session()
        if provider and provider != self.context.ai.active_id:
            self.status_message.emit(f"已由兜底 AI（{provider}）完成回答")
        else:
            self.status_message.emit("回答完成")

    def _on_failed(self, message: str) -> None:
        self._set_busy(False)
        if self.session.messages and self.session.messages[-1].role == "assistant":
            if not self.session.messages[-1].content.strip():
                self.session.messages.pop()
        self._stream_buffer.clear()
        self._render()
        common.error(self, message, "AI 调用失败")
        self.status_message.emit("AI 调用失败")

    def _on_cancelled(self) -> None:
        self._set_busy(False)
        self._stream_buffer.clear()
        self._render()
        self.status_message.emit("已停止")

    def stop(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self.status_message.emit("正在停止……")

    def is_busy(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def wait_for_idle(self, timeout_ms: int = 4000) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            self._worker.wait(timeout_ms)

    # ==================================================================
    # 渲染
    # ==================================================================

    def _render(self, scroll: bool = False) -> None:
        from gwp.services import themes

        colors = themes.palette(self.context.theme)
        rows: list[str] = []
        if self.session is None:
            rows.append("<p class='muted'>请先打开一个 Markdown 文件，AI 会自动读取它。</p>")
        elif self.session.is_empty:
            if self.daily_mode:
                rows.append(
                    "<p class='muted'>这里是<strong>日常对话</strong>，不绑定任何文件。"
                    "可以直接提问、让我解释概念、帮你梳理思路或写点东西。<br>"
                    "如果想谈某份资料的内容，请打开它，再用文档里的「AI 双栏」。</p>"
                )
            else:
                rows.append(
                    "<p class='muted'>还没有对话。首次打开文件时，AI 会自动发送当前文件；"
                    "你也可以直接在下面提问。</p>"
                )
        else:
            for message in self.session.messages:
                rows.append(self._render_message(message, colors))

        html = f"""
        <html><head><meta charset="utf-8"><style>
        body {{ font-family: 'Microsoft YaHei UI','Microsoft YaHei',sans-serif; font-size: 10pt;
                color: {colors['text']}; background: transparent; }}
        .row {{ margin: 8px 0; }}
        .bubble {{ padding: 8px 11px; border-radius: 10px; }}
        .user {{ background: {colors['accent_soft']}; }}
        .assistant {{ background: {colors['surface_alt']}; border: 1px solid {colors['border']}; }}
        .note {{ color: {colors['text_muted']}; font-size: 9pt; }}
        .role {{ color: {colors['text_muted']}; font-size: 8.6pt; margin-bottom: 3px; }}
        pre {{ background: {colors['code_bg']}; border: 1px solid {colors['border']};
               border-radius: 8px; padding: 8px; white-space: pre-wrap; }}
        code {{ font-family: Consolas, monospace; }}
        table {{ border-collapse: collapse; }}
        td, th {{ border: 1px solid {colors['border']}; padding: 4px 6px; }}
        </style></head><body>{''.join(rows)}</body></html>
        """
        self.view.setHtml(html)
        if scroll:
            self.view.verticalScrollBar().setValue(self.view.verticalScrollBar().maximum())

    def _render_message(self, message: ChatMessage, colors: dict) -> str:
        from gwp.services.markdown_renderer import RenderOptions, render_document

        if message.meta.get("system_note"):
            preview = common.elide(message.content, 90)
            return f"<div class='row note'>▸ 已发送文件：{common.html_escape(preview)}</div>"

        role_label = {"user": "我", "assistant": "AI", "system": "系统"}.get(message.role, message.role)
        role_label = f"{role_label} · {message.meta.get('model', '')}".strip(" ·")
        css_class = "user" if message.role == "user" else "assistant"
        if message.content.strip():
            body_html = render_document(
                message.content,
                RenderOptions(
                    base_dir=self.document_path.parent if self.document_path else None,
                    theme=self.context.theme,
                    body_only=True,
                ),
            )
        else:
            body_html = "<p class='muted'>（正在生成……）</p>"
        return (
            f"<div class='row'><div class='role'>{common.html_escape(role_label)}</div>"
            f"<div class='bubble {css_class}'>{body_html}</div></div>"
        )

    # ==================================================================

    def _insert_last_answer(self) -> None:
        if self.session is None:
            return
        for message in reversed(self.session.messages):
            if message.role == "assistant" and message.content.strip():
                self.insert_requested.emit(message.content)
                return
        common.warn(self, "还没有可插入的 AI 回答。")


__all__ = ["ChatPanel"]
