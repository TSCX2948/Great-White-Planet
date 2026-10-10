"""设置对话框。

对应需求文档第九节的「设置」菜单，并按模块分页：
界面 / 编辑器 / AI / 总结 / 导入导出 / 路径 / 启动 / 高级。

新增配置项时，只需要在对应页里加一个控件，并在 :meth:`SettingsDialog.collect` 里取值。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
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
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gwp.bootstrap import AppContext
from gwp.core import constants as C
from gwp.services import dependencies, shell_ops
from gwp.ui import common
from gwp.ui.widgets.color_picker import ColorPicker

log = logging.getLogger(__name__)

PAGES = (
    ("appearance", "界面"),
    ("editor", "编辑器"),
    ("ai", "AI"),
    ("summary", "总结"),
    ("io", "导入与导出"),
    ("paths", "存储路径"),
    ("startup", "启动与集成"),
    ("prompts", "提示词"),
    ("about", "关于"),
)


class SettingsDialog(QDialog):
    def __init__(self, context: AppContext, parent: QWidget | None = None, initial_page: str = "") -> None:
        super().__init__(parent)
        self.context = context
        self.config = context.config
        self.setWindowTitle("设置")
        self.resize(880, 620)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(12)

        # 左侧导航
        self.nav = QListWidget()
        self.nav.setFixedWidth(150)
        for key, label in PAGES:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._on_nav)
        layout.addWidget(self.nav)

        # 右侧内容
        right = QVBoxLayout()
        right.setSpacing(10)
        self.stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}
        for key, _label in PAGES:
            page = self._build_page(key)
            self._pages[key] = page
            self.stack.addWidget(page)
        right.addWidget(self.stack, 1)

        buttons = QDialogButtonBox()
        self.btn_save = buttons.addButton("保存", QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_save.setProperty("accent", True)
        self.btn_apply = buttons.addButton("应用", QDialogButtonBox.ButtonRole.ApplyRole)
        buttons.addButton("取消", QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        self.btn_apply.clicked.connect(self._apply_only)
        right.addWidget(buttons)
        layout.addLayout(right, 1)

        keys = [key for key, _ in PAGES]
        index = keys.index(initial_page) if initial_page in keys else 0
        self.nav.setCurrentRow(index)

    # ==================================================================
    # 页面构建
    # ==================================================================

    def _page(self, title: str, description: str = "") -> tuple[QWidget, QFormLayout]:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(10)
        header = QLabel(title)
        header.setObjectName("Title")
        outer.addWidget(header)
        if description:
            hint = QLabel(description)
            hint.setWordWrap(True)
            hint.setObjectName("Muted")
            outer.addWidget(hint)
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        outer.addLayout(form)
        outer.addStretch(1)
        return widget, form

    def _build_page(self, key: str) -> QWidget:
        builder = getattr(self, f"_page_{key}", None)
        if builder is None:
            widget, _form = self._page("（未实现）")
            return widget
        return builder()

    # -- 界面 -----------------------------------------------------------

    def _page_appearance(self) -> QWidget:
        widget, form = self._page("界面外观", "调整主题、字体与卡片尺寸。修改后点「应用」即可立即生效。")

        self.combo_theme = QComboBox()
        self.combo_theme.addItem("浅色", "light")
        self.combo_theme.addItem("深色", "dark")
        self.combo_theme.setCurrentIndex(1 if self.config.get("ui.theme") == "dark" else 0)
        form.addRow("主题", self.combo_theme)

        self.color_accent = ColorPicker(str(self.config.get("ui.accent", "#4F7CFF")))
        form.addRow("主色调", self.color_accent)

        self.input_font = QLineEdit(str(self.config.get("ui.font_family", "Microsoft YaHei UI")))
        form.addRow("界面字体", self.input_font)

        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 20)
        self.spin_font_size.setValue(int(self.config.get("ui.font_size", 10) or 10))
        form.addRow("界面字号", self.spin_font_size)

        self.spin_card_w = QSpinBox()
        self.spin_card_w.setRange(120, 420)
        self.spin_card_w.setValue(int(self.config.get("ui.card.width", 196) or 196))
        form.addRow("卡片宽度", self.spin_card_w)

        self.spin_card_h = QSpinBox()
        self.spin_card_h.setRange(80, 320)
        self.spin_card_h.setValue(int(self.config.get("ui.card.height", 124) or 124))
        form.addRow("卡片高度", self.spin_card_h)

        self.check_confirm_delete = QCheckBox("删除科目/书目之前先确认")
        self.check_confirm_delete.setChecked(bool(self.config.get("ui.confirm_on_delete", True)))
        form.addRow("", self.check_confirm_delete)

        # 首页右侧信息条（日期 / 时间 / 天气）
        self.check_clock_bar = QCheckBox("首页显示日期与时间")
        self.check_clock_bar.setChecked(bool(self.config.get("ui.show_clock_bar", True)))
        form.addRow("", self.check_clock_bar)

        self.check_weather = QCheckBox("显示天气（会联网获取，按大致定位）")
        self.check_weather.setToolTip(
            "天气走公开免费接口，不需要 Key；关掉后只显示日期与时间，不联网。"
        )
        self.check_weather.setChecked(bool(self.config.get("ui.weather_enabled", True)))
        form.addRow("", self.check_weather)

        # 关闭到后台（需求：主界面关闭后进程继续运行）
        self.check_background = QCheckBox("关闭主窗口时最小化到后台（不退出进程）")
        self.check_background.setToolTip(
            "勾选时：点关闭只是把窗口藏起来，软件继续在后台运行 ——\n"
            "下次打开是**瞬间**的，不用再等一次启动。\n"
            "唤回窗口：双击右下角托盘里的星球图标，或再双击一次桌面快捷方式。\n"
            "完全退出：右键托盘图标 →「完全退出」。\n\n"
            "取消勾选时：点关闭就真正退出进程。"
        )
        self.check_background.setChecked(
            bool(self.config.get("ui.close_to_background", True))
        )
        form.addRow("", self.check_background)

        return widget

    # -- 编辑器 ---------------------------------------------------------

    def _page_editor(self) -> QWidget:
        widget, form = self._page("编辑器", "Markdown 编辑器与预览的行为。")

        self.input_editor_font = QLineEdit(str(self.config.get("editor.font_family", "Consolas")))
        form.addRow("代码字体", self.input_editor_font)

        self.spin_editor_size = QSpinBox()
        self.spin_editor_size.setRange(8, 24)
        self.spin_editor_size.setValue(int(self.config.get("editor.font_size", 11) or 11))
        form.addRow("代码字号", self.spin_editor_size)

        self.spin_tab = QSpinBox()
        self.spin_tab.setRange(2, 8)
        self.spin_tab.setValue(int(self.config.get("editor.tab_width", 4) or 4))
        form.addRow("Tab 宽度", self.spin_tab)

        self.spin_autosave = QSpinBox()
        self.spin_autosave.setRange(0, 600)
        self.spin_autosave.setSuffix(" 秒（0 = 关闭）")
        self.spin_autosave.setValue(int(self.config.get("editor.autosave_seconds", 20) or 0))
        form.addRow("自动保存间隔", self.spin_autosave)

        self.check_live_preview = QCheckBox("编辑时实时刷新预览")
        self.check_live_preview.setChecked(bool(self.config.get("editor.preview_live", True)))
        form.addRow("", self.check_live_preview)

        return widget

    # -- AI -------------------------------------------------------------

    def _page_ai(self) -> QWidget:
        widget, form = self._page(
            "AI 设置",
            "可插拔的 AI 提供方。API Key 保存在 else data/secrets.json，不会写进代码，也不会进用户数据目录。",
        )

        self.combo_active_ai = QComboBox()
        for provider_id in self.context.ai.provider_ids():
            adapter = self.context.ai.get(provider_id)
            label = adapter.display_label if adapter else provider_id
            self.combo_active_ai.addItem(label, provider_id)
        active = self.context.ai.active_id
        index = self.combo_active_ai.findData(active)
        if index >= 0:
            self.combo_active_ai.setCurrentIndex(index)
        form.addRow("当前 AI", self.combo_active_ai)

        # 每个提供方的配置
        row = QHBoxLayout()
        self.combo_provider = QComboBox()
        for provider_id in self.context.ai.provider_ids():
            adapter = self.context.ai.get(provider_id)
            self.combo_provider.addItem(adapter.display_label if adapter else provider_id, provider_id)
        self.combo_provider.currentIndexChanged.connect(self._load_provider_fields)
        row.addWidget(self.combo_provider, 1)
        self.btn_test = QPushButton("测试连接")
        self.btn_test.clicked.connect(self._test_provider)
        row.addWidget(self.btn_test)
        form.addRow("提供方", self._wrap(row))

        self.input_api_key = QLineEdit()
        self.input_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_api_key.setPlaceholderText("留空则使用环境变量或 secrets.json 中的值")
        form.addRow("API Key", self.input_api_key)

        self.input_base_url = QLineEdit()
        form.addRow("接口地址", self.input_base_url)

        self.input_model = QLineEdit()
        form.addRow("模型", self.input_model)

        self.input_api_path = QLineEdit()
        self.input_api_path.setPlaceholderText("例如 /chat/completions")
        form.addRow("接口路径", self.input_api_path)

        self.input_provider_url = QLineEdit()
        self.input_provider_url.setPlaceholderText("网页版地址，例如 https://chat.deepseek.com/")
        form.addRow("网页地址", self.input_provider_url)

        self.input_command = QLineEdit()
        self.input_command.setPlaceholderText("本地 AI 命令，例如 tianxi --chat")
        form.addRow("本地命令", self.input_command)

        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(10, 1800)
        self.spin_timeout.setSuffix(" 秒")
        self.spin_timeout.setValue(int(self.config.get("ai.request_timeout", 180) or 180))
        form.addRow("请求超时", self.spin_timeout)

        self.spin_temperature = QDoubleSpinBox()
        self.spin_temperature.setRange(0.0, 2.0)
        self.spin_temperature.setSingleStep(0.1)
        self.spin_temperature.setValue(float(self.config.get("ai.temperature", 0.3) or 0.3))
        form.addRow("温度", self.spin_temperature)

        self.spin_max_tokens = QSpinBox()
        self.spin_max_tokens.setRange(256, 200000)
        self.spin_max_tokens.setValue(int(self.config.get("ai.max_tokens", 8192) or 8192))
        form.addRow("最大输出长度", self.spin_max_tokens)

        self.input_fallback = QLineEdit(
            ", ".join(str(x) for x in (self.config.get("ai.fallback_chain", []) or []))
        )
        self.input_fallback.setPlaceholderText("逗号分隔的提供方 id，主 AI 失败时依次尝试")
        form.addRow("兜底顺序", self.input_fallback)

        self.check_stream = QCheckBox("使用流式输出（逐字显示）")
        self.check_stream.setChecked(bool(self.config.get("ai.stream", True)))
        form.addRow("", self.check_stream)

        self.check_auto_send = QCheckBox("首次在文件中打开 AI 时自动发送当前文件")
        self.check_auto_send.setChecked(bool(self.config.get("ai.auto_send_current_file", True)))
        form.addRow("", self.check_auto_send)

        # 图片识别的开关（需求：图片 AI 提取）。
        # 默认关闭是**有意**的：发图有隐私含义（作业照片、身份证、笔记原图），
        # 必须由用户显式同意，不能因为"配了个支持视觉的模型"就自动往外发。
        self.check_send_images = QCheckBox(
            "允许把图片发送给 AI（「图片提取为 Markdown」需要它；支持视觉的模型才有效）"
        )
        self.check_send_images.setChecked(bool(self.config.get("ai.send_images", False)))
        self.check_send_images.setToolTip(
            "打开后，「图片提取为 Markdown」会把图片直接发给声明支持视觉的模型，"
            "全自动识别、不需要手工粘贴。\n"
            "关掉时该功能改用网页版桥接（图片只放进你自己的剪贴板，由你决定粘给谁）。"
        )
        form.addRow("", self.check_send_images)

        self.check_notify_fallback = QCheckBox("切换到兜底 AI 时弹窗提示")
        self.check_notify_fallback.setChecked(bool(self.config.get("ai.notify_on_fallback", True)))
        form.addRow("", self.check_notify_fallback)

        self.check_clear_on_exit = QCheckBox("关闭软件时清除所有 AI 聊天记录（需求文档默认开启）")
        self.check_clear_on_exit.setChecked(bool(self.config.get("ai.clear_chat_on_exit", True)))
        form.addRow("", self.check_clear_on_exit)

        self.check_persist_chat = QCheckBox("关闭 AI 面板时保存聊天记录")
        self.check_persist_chat.setChecked(bool(self.config.get("ai.persist_chat_on_close", True)))
        form.addRow("", self.check_persist_chat)

        self._provider_keys: dict[str, str] = {}
        self._load_provider_fields()
        return widget

    @staticmethod
    def _wrap(layout) -> QWidget:
        holder = QWidget()
        holder.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        return holder

    def _current_provider(self) -> str:
        return self.combo_provider.currentData() or ""

    def _load_provider_fields(self) -> None:
        """切换提供方时，先把当前输入存起来，再载入新提供方的配置。"""
        if self._provider_keys:
            self._provider_keys[self._last_provider] = self.input_api_key.text()
        provider_id = self._current_provider()
        self._last_provider = provider_id
        node = dict(self.config.get(f"ai.providers.{provider_id}", {}) or {})
        self.input_api_key.setText(
            self._provider_keys.get(provider_id, self.config.api_key_for(provider_id))
            if self._provider_keys
            else self.config.api_key_for(provider_id)
        )
        self.input_base_url.setText(str(node.get("base_url", "") or ""))
        self.input_model.setText(str(node.get("model", "") or ""))
        self.input_api_path.setText(str(node.get("path", "") or ""))
        self.input_provider_url.setText(str(node.get("url", "") or ""))
        self.input_command.setText(str(node.get("command", "") or ""))

        kind = str(node.get("type", "openai_compatible"))
        for widget_, visible in (
            (self.input_api_key, kind == "openai_compatible"),
            (self.input_base_url, kind == "openai_compatible"),
            (self.input_model, kind == "openai_compatible"),
            (self.input_api_path, kind == "openai_compatible"),
            (self.input_provider_url, kind == "web_bridge"),
            (self.input_command, kind == "local_command"),
        ):
            widget_.setVisible(visible)
            label = self._label_for(widget_)
            if label is not None:
                label.setVisible(visible)

    def _label_for(self, widget: QWidget) -> QWidget | None:
        form = widget.parentWidget()
        if form is None:
            return None
        layout = form.layout()
        if not isinstance(layout, QFormLayout):
            return None
        for row in range(layout.rowCount()):
            item = layout.itemAt(row, QFormLayout.ItemRole.FieldRole)
            if item is not None and item.widget() is widget:
                label_item = layout.itemAt(row, QFormLayout.ItemRole.LabelRole)
                return label_item.widget() if label_item else None
        return None

    def _test_provider(self) -> None:
        provider_id = self._current_provider()
        adapter = self.context.ai.get(provider_id, refresh=True)
        if adapter is None:
            common.warn(self, f"找不到提供方：{provider_id}")
            return
        ok, reason = adapter.is_configured()
        if not ok:
            common.warn(self, f"配置不完整：{reason}", "测试连接")
            return
        busy = common.BusyDialog(self, "测试连接", f"正在连接 {adapter.display_label} ……")
        busy.show()
        ok, message = adapter.test_connection()
        busy.close()
        if ok:
            common.info(self, message, "测试连接")
        else:
            common.warn(self, message, "测试连接失败")

    # -- 总结 -----------------------------------------------------------

    def _page_summary(self) -> QWidget:
        widget, form = self._page(
            "总结设置",
            "决定 summary 如何生成、如何备份。参与总结的内容固定为 Introduct.md + notebook + error-prone，book 目录永不参与。",
        )

        self.input_sources = QLineEdit(", ".join(str(x) for x in (self.config.get("summary.sources", []) or [])))
        self.input_sources.setPlaceholderText(f"{C.INTRO_FILE}, {C.NOTEBOOK_FOLDER}, {C.ERROR_FOLDER}")
        form.addRow("参与总结的来源", self.input_sources)

        self.spin_chunk = QSpinBox()
        self.spin_chunk.setRange(2000, 200000)
        self.spin_chunk.setSingleStep(1000)
        self.spin_chunk.setValue(int(self.config.get("summary.chunk_chars", 18000) or 18000))
        form.addRow("单次送入字符数", self.spin_chunk)

        self.spin_backup_keep = QSpinBox()
        self.spin_backup_keep.setRange(0, 20)
        self.spin_backup_keep.setValue(int(self.config.get("summary.backup_keep", 1) or 0))
        self.spin_backup_keep.setToolTip("需求文档要求只保留一个上一版；设为 0 表示不备份")
        form.addRow("保留历史版本数", self.spin_backup_keep)

        self.check_images = QCheckBox("扫描件/图片型 PDF 自动转为图片插入")
        self.check_images.setChecked(bool(self.config.get("summary.include_images", True)))
        form.addRow("", self.check_images)

        self.spin_min_chars = QSpinBox()
        self.spin_min_chars.setRange(0, 2000)
        self.spin_min_chars.setValue(int(self.config.get("summary.min_text_chars_per_page", 80) or 0))
        self.spin_min_chars.setToolTip("每页平均文字少于这个数，就判定为扫描件")
        form.addRow("每页最少字符数", self.spin_min_chars)

        self.spin_image_width = QSpinBox()
        self.spin_image_width.setRange(400, 4000)
        self.spin_image_width.setValue(int(self.config.get("summary.image_max_width", 1600) or 1600))
        form.addRow("图片最大宽度", self.spin_image_width)

        self.check_open_after = QCheckBox("生成后自动打开总结文件")
        self.check_open_after.setChecked(bool(self.config.get("summary.auto_open_after_generate", True)))
        form.addRow("", self.check_open_after)

        return widget

    # -- 导入导出 -------------------------------------------------------

    def _page_io(self) -> QWidget:
        widget, form = self._page("导入与导出", "导入文件与导出 PDF 的行为。")

        self.check_copy = QCheckBox("导入时复制文件（不移动原文件）")
        self.check_copy.setChecked(bool(self.config.get("import.copy_files", True)))
        form.addRow("", self.check_copy)

        self.check_ask_overwrite = QCheckBox("同名文件先询问")
        self.check_ask_overwrite.setChecked(bool(self.config.get("import.ask_before_overwrite", True)))
        form.addRow("", self.check_ask_overwrite)

        self.input_suffix = QLineEdit(str(self.config.get("import.suffix_on_conflict", "_1")))
        self.input_suffix.setToolTip("同名时追加的后缀，支持 {n} 占位符，例如 _1 或 ({n})")
        form.addRow("冲突后缀", self.input_suffix)

        self.combo_page_size = QComboBox()
        for size in ("A4", "A5", "B5", "Letter", "Legal"):
            self.combo_page_size.addItem(size, size)
        current = str(self.config.get("export.pdf_page_size", "A4") or "A4")
        index = self.combo_page_size.findData(current)
        self.combo_page_size.setCurrentIndex(max(0, index))
        form.addRow("PDF 纸张", self.combo_page_size)

        self.spin_margin = QDoubleSpinBox()
        self.spin_margin.setRange(5.0, 50.0)
        self.spin_margin.setSuffix(" mm")
        self.spin_margin.setValue(float(self.config.get("export.pdf_margin_mm", 18) or 18))
        form.addRow("PDF 页边距", self.spin_margin)

        return widget

    # -- 路径 -----------------------------------------------------------

    def _page_paths(self) -> QWidget:
        widget, form = self._page(
            "存储路径",
            "用户数据放在 user data，软件产生的数据放在 else data（需求文档第十节）。修改数据根目录后需要重启软件。",
        )

        row = QHBoxLayout()
        self.input_data_root = QLineEdit(str(self.context.paths.data_root))
        row.addWidget(self.input_data_root, 1)
        self.btn_pick_root = QPushButton("浏览…")
        self.btn_pick_root.clicked.connect(self._pick_data_root)
        row.addWidget(self.btn_pick_root)
        form.addRow("数据根目录", self._wrap(row))

        self.lbl_user_data = QLabel(str(self.context.paths.user_data))
        self.lbl_user_data.setWordWrap(True)
        form.addRow("用户数据", self.lbl_user_data)
        self.lbl_else_data = QLabel(str(self.context.paths.else_data))
        self.lbl_else_data.setWordWrap(True)
        form.addRow("软件数据", self.lbl_else_data)
        self.lbl_config_file = QLabel(str(self.context.paths.config_file))
        self.lbl_config_file.setWordWrap(True)
        form.addRow("配置文件", self.lbl_config_file)

        buttons = QHBoxLayout()
        self.btn_open_user_data = QPushButton("打开用户数据目录")
        self.btn_open_user_data.clicked.connect(
            lambda: self._open_path(self.context.paths.user_data)
        )
        buttons.addWidget(self.btn_open_user_data)
        self.btn_open_else_data = QPushButton("打开软件数据目录")
        self.btn_open_else_data.clicked.connect(
            lambda: self._open_path(self.context.paths.else_data)
        )
        buttons.addWidget(self.btn_open_else_data)
        self.btn_open_config = QPushButton("打开配置文件")
        self.btn_open_config.clicked.connect(lambda: self._open_path(self.context.paths.config_file))
        buttons.addWidget(self.btn_open_config)
        buttons.addStretch(1)
        form.addRow("", self._wrap(buttons))

        return widget

    def _pick_data_root(self) -> None:
        directory = common.pick_directory(self, "选择数据根目录", self.input_data_root.text())
        if directory:
            self.input_data_root.setText(str(directory))
            self.lbl_user_data.setText(str(directory / "user data"))
            self.lbl_else_data.setText(str(directory / "else data"))

    @staticmethod
    def _open_path(path: Path) -> None:
        from gwp.services import file_ops

        target = Path(path)
        if target.is_file():
            file_ops.open_with_system(target)
        elif target.exists():
            file_ops.reveal_in_explorer(target)
        else:
            common.warn(None, f"路径不存在：{target}")

    # -- 启动 -----------------------------------------------------------

    def _page_startup(self) -> QWidget:
        widget, form = self._page("启动与系统集成", "开机自启会写入注册表 HKCU\\...\\Run，可随时关闭。")

        self.check_prewarm = QCheckBox("启动时后台预扫描（减少等待）")
        self.check_prewarm.setChecked(bool(self.config.get("startup.prewarm_scan", True)))
        form.addRow("", self.check_prewarm)

        self.check_autostart = QCheckBox("开机自动启动")
        self.check_autostart.setChecked(bool(self.config.get("startup.autostart", False)))
        form.addRow("", self.check_autostart)

        row = QHBoxLayout()
        self.btn_shortcut = QPushButton("创建桌面快捷方式")
        self.btn_shortcut.clicked.connect(self._create_shortcut)
        row.addWidget(self.btn_shortcut)
        self.btn_remove_shortcut = QPushButton("删除桌面快捷方式")
        self.btn_remove_shortcut.clicked.connect(self._remove_shortcut)
        row.addWidget(self.btn_remove_shortcut)
        row.addStretch(1)
        form.addRow("", self._wrap(row))

        # ---- 程序图标 ----
        icon_row = QHBoxLayout()
        icon_row.setSpacing(10)
        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(48, 48)
        self.lbl_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_row.addWidget(self.lbl_icon)

        icon_buttons = QVBoxLayout()
        icon_buttons.setSpacing(6)
        self.btn_pick_icon = QPushButton("更换程序图标…")
        self.btn_pick_icon.setToolTip(
            "选择一张正方形图片，自动转成多分辨率图标；窗口图标立即生效，"
            "桌面快捷方式需要重建一次"
        )
        self.btn_pick_icon.clicked.connect(self._pick_icon)
        icon_buttons.addWidget(self.btn_pick_icon)
        self.btn_reset_icon = QPushButton("恢复内置图标（太白金星）")
        self.btn_reset_icon.clicked.connect(self._reset_icon)
        icon_buttons.addWidget(self.btn_reset_icon)
        icon_buttons.addStretch(1)
        icon_row.addLayout(icon_buttons)
        icon_row.addStretch(1)
        form.addRow("程序图标", self._wrap(icon_row))
        self._refresh_icon_preview()

        return widget

    # ---- 图标 ----

    def _refresh_icon_preview(self) -> None:
        self.lbl_icon.setPixmap(common.app_pixmap(44, config=self.config))

    def _pick_icon(self) -> None:
        path = common.pick_open_image(self, "选择程序图标（建议正方形、512×512 以上）")
        if not path:
            return
        from gwp.resources import app_icon as icon_module

        try:
            ico = icon_module.install_image(path, size=512)
        except Exception as exc:  # noqa: BLE001
            common.error(self, f"图标转换失败：{exc}", "更换图标")
            return
        self.config.set("ui.app_icon", str(ico))
        self.config.save()
        self._refresh_icon_preview()
        common.info(
            self,
            f"图标已更新：\n{ico}\n\n窗口图标立即生效；桌面快捷方式请在本页点一次"
            "「创建桌面快捷方式」来刷新。",
            "更换图标",
        )

    def _reset_icon(self) -> None:
        self.config.set("ui.app_icon", "")
        self.config.save()
        self._refresh_icon_preview()
        common.info(self, "已恢复内置的「太白金星」图标。", "更换图标")

    def _create_shortcut(self) -> None:
        ok, message = shell_ops.create_desktop_shortcut()
        if ok:
            common.info(self, message, "创建快捷方式")
        else:
            common.warn(self, message, "创建快捷方式")

    def _remove_shortcut(self) -> None:
        if shell_ops.remove_desktop_shortcut():
            common.info(self, "已删除桌面快捷方式。", "删除快捷方式")
        else:
            common.warn(self, "桌面没有找到快捷方式。", "删除快捷方式")

    # -- 提示词 ---------------------------------------------------------

    def _page_prompts(self) -> QWidget:
        widget, form = self._page(
            "提示词",
            "这些文字会直接发给 AI。想调整 summary 的风格（更详细、更侧重解题等），改这里即可，不用动代码。",
        )

        self.text_summary_system = QPlainTextEdit(str(self.config.get("prompts.summary_system", "")))
        self.text_summary_system.setFixedHeight(150)
        form.addRow("整合总结", self.text_summary_system)

        self.text_chunk_system = QPlainTextEdit(str(self.config.get("prompts.summary_chunk_system", "")))
        self.text_chunk_system.setFixedHeight(110)
        form.addRow("分块提炼", self.text_chunk_system)

        self.text_merge_system = QPlainTextEdit(str(self.config.get("prompts.summary_merge_system", "")))
        self.text_merge_system.setFixedHeight(110)
        form.addRow("合并成文", self.text_merge_system)

        self.text_chat_system = QPlainTextEdit(str(self.config.get("prompts.chat_system", "")))
        self.text_chat_system.setFixedHeight(90)
        form.addRow("对话助手", self.text_chat_system)

        self.text_uncertainty = QPlainTextEdit(str(self.config.get("prompts.uncertainty_rules", "")))
        self.text_uncertainty.setFixedHeight(130)
        form.addRow("提问规则", self.text_uncertainty)

        row = QHBoxLayout()
        self.btn_reset_prompts = QPushButton("恢复默认提示词")
        self.btn_reset_prompts.clicked.connect(self._reset_prompts)
        row.addWidget(self.btn_reset_prompts)
        row.addStretch(1)
        form.addRow("", self._wrap(row))
        return widget

    def _reset_prompts(self) -> None:
        from gwp.core.config import DEFAULT_CONFIG

        defaults = DEFAULT_CONFIG.get("prompts", {})
        self.text_summary_system.setPlainText(defaults.get("summary_system", ""))
        self.text_chunk_system.setPlainText(defaults.get("summary_chunk_system", ""))
        self.text_merge_system.setPlainText(defaults.get("summary_merge_system", ""))
        self.text_chat_system.setPlainText(defaults.get("chat_system", ""))
        self.text_uncertainty.setPlainText(defaults.get("uncertainty_rules", ""))

    # -- 关于 -----------------------------------------------------------

    def _page_about(self) -> QWidget:
        widget, form = self._page("关于与自检", "查看运行环境、依赖状态与数据概览。")

        from gwp import __version__

        info_lines = [
            f"Great White Planet v{__version__}",
            f"程序目录：{self.context.root}",
            f"数据目录：{self.context.paths.data_root}",
            f"科目数量：{len(self.context.library.subjects())}",
            f"当前 AI：{self.context.ai.describe_active()}",
            f"自动启动：{'已开启' if shell_ops.is_autostart_enabled() else '未开启'}",
        ]
        label = QLabel("\n".join(info_lines))
        label.setWordWrap(True)
        form.addRow(label)

        self.text_deps = QPlainTextEdit(dependencies.summary())
        self.text_deps.setReadOnly(True)
        self.text_deps.setFixedHeight(190)
        form.addRow("依赖状态", self.text_deps)

        row = QHBoxLayout()
        self.btn_check_deps = QPushButton("重新检查")
        self.btn_check_deps.clicked.connect(lambda: self.text_deps.setPlainText(dependencies.summary()))
        row.addWidget(self.btn_check_deps)
        self.btn_install_deps = QPushButton("复制安装命令")
        self.btn_install_deps.clicked.connect(self._copy_install_command)
        row.addWidget(self.btn_install_deps)
        row.addStretch(1)
        form.addRow("", self._wrap(row))
        return widget

    def _copy_install_command(self) -> None:
        command = dependencies.install_command()
        if not command:
            common.info(self, "依赖完整，无需安装。", "依赖检查")
            return
        from PyQt6.QtWidgets import QApplication

        QApplication.clipboard().setText(command)
        common.info(self, f"已复制到剪贴板：\n{command}", "依赖检查")

    # ==================================================================
    # 保存
    # ==================================================================

    def _on_nav(self, row: int) -> None:
        if 0 <= row < self.stack.count():
            self.stack.setCurrentIndex(row)

    def collect(self) -> dict:
        """把界面上的值收集成配置补丁。"""
        patch: dict = {
            "ui": {
                "theme": self.combo_theme.currentData(),
                "accent": self.color_accent.color(),
                "font_family": self.input_font.text().strip(),
                "font_size": self.spin_font_size.value(),
                "card": {
                    "width": self.spin_card_w.value(),
                    "height": self.spin_card_h.value(),
                },
                "confirm_on_delete": self.check_confirm_delete.isChecked(),
                "show_clock_bar": self.check_clock_bar.isChecked(),
                "weather_enabled": self.check_weather.isChecked(),
                "close_to_background": self.check_background.isChecked(),
            },
            "editor": {
                "font_family": self.input_editor_font.text().strip(),
                "font_size": self.spin_editor_size.value(),
                "tab_width": self.spin_tab.value(),
                "autosave_seconds": self.spin_autosave.value(),
                "preview_live": self.check_live_preview.isChecked(),
            },
            "ai": {
                "active_provider": self.combo_active_ai.currentData(),
                "request_timeout": self.spin_timeout.value(),
                "temperature": round(self.spin_temperature.value(), 2),
                "max_tokens": self.spin_max_tokens.value(),
                "fallback_chain": [
                    item.strip() for item in self.input_fallback.text().split(",") if item.strip()
                ],
                "stream": self.check_stream.isChecked(),
                "auto_send_current_file": self.check_auto_send.isChecked(),
                "send_images": self.check_send_images.isChecked(),
                "notify_on_fallback": self.check_notify_fallback.isChecked(),
                "clear_chat_on_exit": self.check_clear_on_exit.isChecked(),
                "persist_chat_on_close": self.check_persist_chat.isChecked(),
            },
            "summary": {
                "sources": [item.strip() for item in self.input_sources.text().split(",") if item.strip()],
                "chunk_chars": self.spin_chunk.value(),
                "backup_keep": self.spin_backup_keep.value(),
                "include_images": self.check_images.isChecked(),
                "min_text_chars_per_page": self.spin_min_chars.value(),
                "image_max_width": self.spin_image_width.value(),
                "auto_open_after_generate": self.check_open_after.isChecked(),
            },
            "import": {
                "copy_files": self.check_copy.isChecked(),
                "ask_before_overwrite": self.check_ask_overwrite.isChecked(),
                "suffix_on_conflict": self.input_suffix.text().strip() or "_1",
            },
            "export": {
                "pdf_page_size": self.combo_page_size.currentData(),
                "pdf_margin_mm": round(self.spin_margin.value(), 1),
            },
            "paths": {
                "data_root": self.input_data_root.text().strip(),
            },
            "startup": {
                "prewarm_scan": self.check_prewarm.isChecked(),
                "autostart": self.check_autostart.isChecked(),
            },
            "prompts": {
                "summary_system": self.text_summary_system.toPlainText(),
                "summary_chunk_system": self.text_chunk_system.toPlainText(),
                "summary_merge_system": self.text_merge_system.toPlainText(),
                "chat_system": self.text_chat_system.toPlainText(),
                "uncertainty_rules": self.text_uncertainty.toPlainText(),
            },
        }
        return patch

    def _write_provider_settings(self) -> None:
        """保存当前提供方的字段与 API Key。"""
        provider_id = self._current_provider()
        if not provider_id:
            return
        node = dict(self.config.get(f"ai.providers.{provider_id}", {}) or {})
        node["base_url"] = self.input_base_url.text().strip()
        node["model"] = self.input_model.text().strip()
        node["path"] = self.input_api_path.text().strip()
        node["url"] = self.input_provider_url.text().strip()
        node["command"] = self.input_command.text().strip()
        self.config.set(f"ai.providers.{provider_id}", node)

        key_text = self.input_api_key.text().strip()
        current_key = self.config.api_key_for(provider_id)
        if key_text != current_key:
            self.config.set_api_key(provider_id, key_text)

    def _apply(self) -> bool:
        patch = self.collect()
        old_root = str(self.context.paths.data_root)
        old_theme = self.context.theme
        old_autostart = bool(self.config.get("startup.autostart", False))

        self._write_provider_settings()
        self.config.update(patch)
        self.config.save()

        # 开机自启
        want_autostart = bool(patch["startup"]["autostart"])
        if want_autostart != old_autostart:
            ok, message = shell_ops.set_autostart(want_autostart)
            if not ok:
                common.warn(self, message, "开机自启")
                self.config.set("startup.autostart", shell_ops.is_autostart_enabled())
                self.config.save()

        self.context.ai.invalidate()
        changed_root = patch["paths"]["data_root"].strip() != old_root
        if changed_root:
            self.context.reload_paths()
        return old_theme != self.context.theme

    def _apply_only(self) -> None:
        theme_changed = self._apply()
        common.info(self, "设置已保存。", "设置")
        if theme_changed:
            window = self.parent()
            if hasattr(window, "apply_theme"):
                window.apply_theme()
        if hasattr(self.parent(), "refresh_settings"):
            self.parent().refresh_settings()

    def _save(self) -> None:
        theme_changed = self._apply()
        if theme_changed:
            window = self.parent()
            if hasattr(window, "apply_theme"):
                window.apply_theme()
        self.accept()


__all__ = ["SettingsDialog"]
