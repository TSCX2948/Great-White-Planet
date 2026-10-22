"""主窗口：单窗口设计 + 完整菜单栏（需求文档第八、九节）。

* 单窗口：首页 / 科目页 / 书目页 / 文档页共用一个窗口，用 QStackedWidget 切换；
* 菜单栏：文件、编辑、查看、工具、AI、设置、帮助；
* 菜单栏右上角常驻 AI 入口（切换 AI + 打开「AI 日常对话」）；
* 打开文件默认另开窗口（可在设置里改成在主窗口打开）。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QCloseEvent, QKeySequence
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QSystemTrayIcon,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gwp import __app_name__, __version__
from gwp.bootstrap import AppContext, cleanup_on_exit
from gwp.core import constants as C
from gwp.core.eventbus import AI_FALLBACK, STATUS_MESSAGE, bus
from gwp.data_manager import forum_store
from gwp.services import dependencies, file_ops, shell_ops, themes
from gwp.ui import common
from gwp.ui.dialogs.book_dialog import BookDialog
from gwp.ui.dialogs.chat_manager_dialog import ChatManagerDialog
from gwp.ui.dialogs.export_dialog import ExportPdfDialog
from gwp.ui.dialogs.help_dialog import HelpDialog
from gwp.ui.dialogs.settings_dialog import SettingsDialog
from gwp.ui.startup_tasks import StartupWorker, check_startup_environment
from gwp.ui.views.book_view import BookView
from gwp.ui.views.document_view import DocumentView
from gwp.ui.views.text_view import TextView
from gwp.ui.views.home_view import HomeView
from gwp.ui.views.subject_view import SubjectView
from gwp.ui.widgets.background_area import BackgroundImageWidget
from gwp.ui.windows.document_window import DocumentWindow
from gwp.ui.windows.global_chat_window import GlobalChatWindow

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """软件唯一的常驻窗口。"""

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self._documents: list[DocumentView] = []
        self._text_views: list[TextView] = []
        self._windows: list[DocumentWindow] = []
        self._chat_window: GlobalChatWindow | None = None
        self._startup_worker: StartupWorker | None = None
        self._toast: common.Toast | None = None
        #: 系统托盘图标（延迟创建：用户真的关到后台时才建）
        self._tray: QSystemTrayIcon | None = None
        #: 用户是否通过托盘/菜单要求"真正退出"（关闭事件里据此放行）
        self._really_quit = False
        #: 盯着"唤回请求"文件（另一个进程双击快捷方式时写它）
        from gwp.core.wakeup import WakeWatcher

        self._wake_watcher = WakeWatcher(context.paths.else_data)
        self._wake_timer = QTimer(self)
        self._wake_timer.setInterval(600)
        self._wake_timer.timeout.connect(self._poll_wake_request)

        #: 后台监听 user data 的变化（外部改了文件就自动刷新）。
        #: 在 _start_watch_and_identity 里真正建起来 —— 那时窗口已经好了。
        self._data_watcher = None

        self.setWindowTitle(f"{__app_name__} — 本地知识管理与 AI 辅助学习")
        self.resize(1280, 860)
        self.setMinimumSize(960, 640)
        self.setWindowIcon(common.app_icon(config=context.config))

        # ---- 页面 ----
        # 结构：背景容器(自绘背景图) → 内容容器 → 页面堆叠
        # 背景由 BackgroundImageWidget 亲自绘制，不走 QSS：
        # 实测 QSS 的 background-image 在存在 QMainWindow 背景规则时完全不绘制。
        self.stack = QStackedWidget()
        # 顶层页面栈要给个名字：背景样式表只清它和它的直接子页面。
        # 不能笼统写 "QStackedWidget > QWidget" —— QTabWidget 内部也有一个
        # QStackedWidget（qt_tabwidget_stackedwidget），文件表格正是它的直接子控件，
        # 用笼统选择器会把表格也清成透明，文字就压在壁纸上看不清了。
        self.stack.setObjectName("MainPageStack")
        self.background_area = BackgroundImageWidget()
        self.background_area.setObjectName("MainBackgroundArea")
        area_layout = QVBoxLayout(self.background_area)
        area_layout.setContentsMargins(0, 0, 0, 0)
        area_layout.setSpacing(0)
        self.area_layout = area_layout

        # 内容容器：默认透明（让背景透出）；个别容器由 QSS 保留自己的底色
        self.content_area = QWidget()
        self.content_area.setObjectName("MainContentArea")
        content_layout = QVBoxLayout(self.content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self.stack)
        area_layout.addWidget(self.content_area)
        self.setCentralWidget(self.background_area)

        self.home_view = HomeView(context)
        self.subject_view = SubjectView(context)
        self.book_view = BookView(context)
        self.stack.addWidget(self.home_view)
        self.stack.addWidget(self.subject_view)
        self.stack.addWidget(self.book_view)

        self.home_view.subject_opened.connect(self.open_subject)
        self.home_view.homework_opened.connect(self.open_homework_in_app)
        self.home_view.status_message.connect(self.show_status)
        self.subject_view.book_opened.connect(self.open_book)
        self.subject_view.back_requested.connect(self.show_home)
        self.subject_view.status_message.connect(self.show_status)
        self.book_view.back_requested.connect(self.show_subject)
        self.book_view.open_document.connect(self.open_document)
        self.book_view.open_text.connect(self.open_text_file)
        self.book_view.status_message.connect(self.show_status)

        # 页面切换时同步"依赖当前页面"的菜单项（例如首页不能新建 Markdown）
        self.stack.currentChanged.connect(lambda _index: self._sync_markdown_action())

        # ---- 状态栏 ----
        self.status_ai = QLabel("")
        self.status_path = QLabel("")
        self.statusBar().addPermanentWidget(self.status_path)
        self.statusBar().addPermanentWidget(self.status_ai)
        self.statusBar().showMessage("就绪")

        self._build_menus()
        self._build_menu_corner()
        self.apply_theme()
        self.refresh_status()

        bus.subscribe(STATUS_MESSAGE, lambda message, **_: self.show_status(message))
        bus.subscribe(AI_FALLBACK, self._on_fallback)

        # ---- 启动后台任务 ----
        QTimer.singleShot(80, self._post_start)

        self.show_home()
        # show_home() 里 setCurrentWidget 在"初始页面"时不一定触发 currentChanged，
        # 所以显式同步一次依赖当前页面的菜单项（首页必须禁用「新建 Markdown」）
        self._sync_markdown_action()

    # ==================================================================
    # 菜单
    # ==================================================================

    def _build_menus(self) -> None:
        bar = self.menuBar()

        # 已注册的「更改背景」子菜单（查看 / 设置 两处，内容同步刷新）
        self.background_menus: list = []

        # 文件
        menu = bar.addMenu("文件(&F)")
        self._add_action(menu, "新建科目…", self.new_subject, "Ctrl+Shift+N")
        self._add_action(menu, "新建书目…", self.new_book, "Ctrl+N")
        # 新建 Markdown 必须落在"某个书目的 notebook"里；首页/科目页没有书目上下文，
        # 因此这项会被动态禁用（见 _sync_markdown_action），避免文件落到未知目录。
        self.act_new_markdown = self._add_action(
            menu, "新建 Markdown 文件…", self.new_markdown, "Ctrl+Alt+N"
        )
        menu.addSeparator()
        self._add_action(menu, "打开 Markdown 文件…", self.open_file_dialog, QKeySequence.StandardKey.Open)
        self.act_open_folder = self._add_action(menu, "打开数据文件夹", self.open_data_folder)
        menu.addSeparator()
        self._add_action(menu, "保存当前文档", lambda: self._with_document(lambda view: view.save()),
                          QKeySequence.StandardKey.Save)
        self._add_action(menu, "保存全部", self.save_all, "Ctrl+Shift+S")
        self._add_action(menu, "关闭当前文档", self.close_current_document, QKeySequence.StandardKey.Close)
        menu.addSeparator()
        self._add_action(menu, "导出当前文档为 PDF…", self.export_current_pdf, "Ctrl+P")
        menu.addSeparator()
        self.act_startup = self._add_action(menu, "开机自动启动", self.toggle_autostart, checkable=True)
        # 同步勾选状态时必须**屏蔽 toggled 信号**：
        # setChecked() 会触发 toggled -> toggle_autostart -> set_autostart，
        # 于是"每次启动都往注册表写开机自启"。结果是用户没勾也会被勾上，
        # 在受限环境还会报 PermissionError。
        self.act_startup.blockSignals(True)
        self.act_startup.setChecked(shell_ops.is_autostart_enabled())
        self.act_startup.blockSignals(False)
        self._add_action(menu, "创建桌面快捷方式", self.create_shortcut)
        menu.addSeparator()
        # 「隐藏到后台」与「退出」要分开、并且都写明白：
        # 开了后台驻留后，点窗口的关闭按钮 = 隐藏（不是退出），
        # 所以菜单里必须有一个**明确的**退出入口，否则用户会以为退不掉。
        self.act_hide_background = self._add_action(
            menu, "隐藏到后台（继续运行）", self.hide_to_background,
            tooltip="把窗口藏起来，软件继续在后台运行；"
                    "双击托盘图标或再双击桌面快捷方式即可唤回",
        )
        self.act_hide_background.setVisible(self._close_to_background_enabled())
        self._add_action(menu, "退出", self.quit_completely, QKeySequence.StandardKey.Quit)

        # 编辑
        menu = bar.addMenu("编辑(&E)")
        self.act_undo = self._add_action(menu, "撤销", lambda: self._with_editor("undo"), QKeySequence.StandardKey.Undo)
        self.act_redo = self._add_action(menu, "重做", lambda: self._with_editor("redo"), QKeySequence.StandardKey.Redo)
        menu.addSeparator()
        self.act_cut = self._add_action(menu, "剪切", lambda: self._with_editor("cut"), QKeySequence.StandardKey.Cut)
        self.act_copy = self._add_action(menu, "复制", lambda: self._with_editor("copy"), QKeySequence.StandardKey.Copy)
        self.act_paste = self._add_action(menu, "粘贴", lambda: self._with_editor("paste"), QKeySequence.StandardKey.Paste)
        self._add_action(menu, "全选", lambda: self._with_editor("selectAll"), QKeySequence.StandardKey.SelectAll)
        menu.addSeparator()
        self._add_action(menu, "查找…", lambda: self._with_document(lambda view: view.find_bar.start()),
                         QKeySequence.StandardKey.Find)
        self.act_edit_mode = self._add_action(menu, "切换编辑/查看模式", self.toggle_edit_mode, "Ctrl+E")

        # 查看
        menu = bar.addMenu("查看(&V)")
        self._add_action(menu, "首页", self.show_home, "Alt+Home")
        self._add_action(menu, "上一级", self.show_parent, "Alt+Up")
        menu.addSeparator()
        self.act_theme = self._add_action(menu, "深色模式", self.toggle_theme, checkable=True)
        self.act_theme.setChecked(self.context.theme == "dark")
        self._add_action(menu, "刷新（重新扫描）", self.refresh_all, QKeySequence.StandardKey.Refresh)
        menu.addSeparator()

        # 背景图（需求：主界面背景可改，旧图保留）
        # 放在"查看"菜单里，因为它属于外观；"设置"菜单里保留同一份入口，两处内容一致。
        self._add_background_submenu(menu)
        menu.addSeparator()

        self.act_ai_panel = self._add_action(menu, "显示 AI 双栏", self.toggle_ai_panel, "Ctrl+Shift+A", checkable=True)

        # 工具
        menu = bar.addMenu("工具(&T)")
        self._add_action(menu, "生成学习总结…", self.generate_summary, "Ctrl+G")
        self._add_action(menu, "预览将总结的资料…", self.preview_materials)
        self._add_action(menu, "总结版本管理…", self.open_backups)
        menu.addSeparator()
        self._add_action(menu, "导入文件到当前书目…", self.import_files, "Ctrl+I")
        self._add_action(
            menu, "图片提取为 Markdown…", self.extract_images,
            tooltip="把当前文件夹里的多张图片用 AI 提取成一份 Markdown；"
                    "识别没把握的直接插入原图",
        )
        # 需求："更主要的功能是文档合并" —— 与顶栏「生成总结」同一件事
        self._add_action(
            menu, "生成总结…", self.merge_sources_into_summary,
            tooltip="把笔记 / 易错题里的 PDF、Word、PPT、Excel、图片等"
                    "直接插入当前书目的 summary；PDF 每页转成图片插入，"
                    "可选让 AI 按主题重排页序",
        )
        self._add_action(menu, "打开当前书目文件夹", self.open_book_folder)
        self._add_action(menu, "重建扫描缓存", self.rebuild_cache)
        menu.addSeparator()
        self._add_action(menu, "清理聊天记录…", self.clear_chats)
        self._add_action(menu, "依赖自检…", self.check_dependencies)
        menu.addSeparator()
        self._add_action(menu, "打开数据目录", self.open_data_folder)
        self._add_action(menu, "打开日志目录", lambda: file_ops.reveal_in_explorer(self.context.paths.log_dir))

        # AI
        menu = bar.addMenu("AI(&A)")
        self.menu_ai = menu
        menu.aboutToShow.connect(self._rebuild_ai_menu)
        self._rebuild_ai_menu()

        # 设置
        menu = bar.addMenu("设置(&S)")
        self._add_action(menu, "常规设置…", lambda: self.open_settings("appearance"))
        self._add_action(menu, "AI 设置…", lambda: self.open_settings("ai"))
        self._add_action(menu, "总结设置…", lambda: self.open_settings("summary"))
        self._add_action(menu, "存储路径…", lambda: self.open_settings("paths"))
        self._add_action(menu, "提示词…", lambda: self.open_settings("prompts"))
        menu.addSeparator()

        # 背景图：与「查看 → 更改背景」是同一套内容（两处入口，行为一致）
        self._add_background_submenu(menu)

        menu.addSeparator()
        self._add_action(menu, "打开配置文件", self.open_config_file)
        self._add_action(menu, "恢复默认设置（保留数据）…", self.reset_settings)

        # 论坛：用户自己维护的列表（名称 + 网址），点一下用系统默认浏览器打开
        #
        # 需求："论坛添加新增/删除论坛功能，需要用户提供论坛名称 网址"
        #
        # 菜单**每次展开时重建**（见 `_rebuild_forum_menu`）：
        # 增删改之后不用重启软件就能看到新的一项。
        self.menu_forum = bar.addMenu("论坛(&O)")
        # 每次展开都重建：增删改之后立刻生效，不用重启软件
        self.menu_forum.aboutToShow.connect(self._rebuild_forum_menu)
        self._rebuild_forum_menu()

        # 帮助
        menu = bar.addMenu("帮助(&H)")
        self._add_action(menu, "设计思想", lambda: self.open_help("设计思想"), "F1")
        self._add_action(menu, "功能说明", lambda: self.open_help("功能说明"))
        self._add_action(menu, "使用说明", lambda: self.open_help("使用说明"))
        self._add_action(menu, "更新记录", lambda: self.open_help("更新记录"))
        menu.addSeparator()
        self._add_action(menu, "打开文档目录", self.open_document_dir)
        self._add_action(menu, "关于 Great White Planet", self.show_about)

    def _add_action(
        self,
        menu,
        text: str,
        callback,
        shortcut=None,
        checkable: bool = False,
        tooltip: str = "",
    ) -> QAction:
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tooltip:
            action.setToolTip(tooltip)
            action.setStatusTip(tooltip)
        action.setCheckable(checkable)
        if checkable:
            action.toggled.connect(callback)
        else:
            action.triggered.connect(lambda _checked=False, cb=callback: cb())
        menu.addAction(action)
        return action

    # ==================================================================
    # 论坛（用户自己维护的列表）
    # ==================================================================

    def _forum_list(self) -> list:
        """读出论坛列表（含老配置搬家，见 data_manager/forum_store）。"""
        try:
            return forum_store.load(self.context.config)
        except Exception:  # noqa: BLE001 - 配置坏了不该让菜单炸掉
            log.exception("读取论坛列表失败")
            return []

    def _rebuild_forum_menu(self) -> None:
        """重建「论坛」菜单。

        每次展开时重建（`aboutToShow`），所以增删改**立刻生效**，
        不需要重启软件 —— 用户加完一个论坛马上就能点。
        """
        menu = getattr(self, "menu_forum", None)
        if menu is None:
            return
        menu.clear()
        forums = self._forum_list()

        if not forums:
            menu.addAction("（还没有论坛，点下面「新增论坛…」）").setEnabled(False)
        for index, forum in enumerate(forums):
            action = menu.addAction(forum.name)
            action.setToolTip(f"用系统默认浏览器打开 {forum.url}")
            action.triggered.connect(
                lambda _checked=False, f=forum: self.open_forum(f.name, f.url)
            )
            # 右键某个论坛 -> 编辑 / 删除 / 调顺序
            action.setData(forum)
        if forums:
            menu.addSeparator()
            sub = menu.addMenu("编辑 / 删除")
            for forum in forums:
                item = sub.addMenu(forum.name)
                item.addAction(
                    "编辑…",
                    lambda _c=False, f=forum: self.edit_forum(f),
                )
                item.addAction(
                    "删除…",
                    lambda _c=False, f=forum: self.delete_forum(f),
                )
                item.addSeparator()
                item.addAction(
                    "上移",
                    lambda _c=False, f=forum: self.move_forum(f, -1),
                )
                item.addAction(
                    "下移",
                    lambda _c=False, f=forum: self.move_forum(f, +1),
                )
        menu.addSeparator()
        menu.addAction("新增论坛…", self.add_forum)

    def add_forum(self) -> None:
        """菜单「新增论坛…」：问名称 + 网址，然后存进配置。"""
        from gwp.ui.dialogs.forum_dialog import ForumDialog

        taken = [f.name for f in self._forum_list()]
        if len(taken) >= forum_store.MAX_FORUMS:
            common.warn(
                self,
                f"最多只能有 {forum_store.MAX_FORUMS} 个论坛。\n"
                "想加新的，先删掉几个不用的。",
                "无法新增",
            )
            return
        dialog = ForumDialog(self, taken=taken)
        if dialog.exec() != ForumDialog.DialogCode.Accepted:
            return
        forum = dialog.result_forum()
        try:
            forum_store.add(self.context.config, forum.name, forum.url)
        except Exception as exc:  # noqa: BLE001 - 写配置失败要说清楚
            log.exception("保存论坛失败")
            common.error(self, f"保存失败：{exc}", "无法新增论坛")
            return
        self._rebuild_forum_menu()
        self.statusBar().showMessage(f"已新增论坛：{forum.name}", 4000)

    def edit_forum(self, forum) -> None:
        """改某个论坛的名称或网址（就地替换，保持它在列表里的位置）。"""
        from gwp.ui.dialogs.forum_dialog import ForumDialog

        taken = [f.name for f in self._forum_list()]
        dialog = ForumDialog(self, existing=forum, taken=taken)
        if dialog.exec() != ForumDialog.DialogCode.Accepted:
            return
        updated = dialog.result_forum()
        try:
            forum_store.rename(
                self.context.config, forum.name, updated.name, updated.url
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("修改论坛失败")
            common.error(self, f"保存失败：{exc}", "无法修改论坛")
            return
        self._rebuild_forum_menu()
        self.statusBar().showMessage(f"已保存论坛：{updated.name}", 4000)

    def delete_forum(self, forum) -> None:
        """删一个论坛。**先确认**（误点删掉就得重新输名称和网址）。"""
        if not common.confirm(
            self,
            f"确定删除论坛「{forum.name}」吗？\n\n"
            f"它指向：{forum.url}\n\n"
            "（只是从菜单里去掉，不会影响那个网站本身。之后想加回来，"
            "重新填一次名称和网址即可。）",
            "删除论坛",
            dangerous=True,
        ):
            return
        try:
            forum_store.remove(self.context.config, forum.name)
        except Exception as exc:  # noqa: BLE001
            log.exception("删除论坛失败")
            common.error(self, f"删除失败：{exc}", "无法删除论坛")
            return
        self._rebuild_forum_menu()
        self.statusBar().showMessage(f"已删除论坛：{forum.name}", 4000)

    def move_forum(self, forum, delta: int) -> None:
        """把论坛在菜单里上移/下移（菜单顺序 = 列表顺序）。"""
        try:
            forum_store.move(self.context.config, forum.name, delta)
        except Exception:  # noqa: BLE001 - 顺序调不动不是大事
            log.exception("调整论坛顺序失败")
            return
        self._rebuild_forum_menu()

    def open_forum(self, title: str = "", url: str = "") -> None:
        """用系统默认浏览器打开一个论坛。

        用浏览器打开是**最省事、最不容易出问题**的做法：
        登录态、Cookie、字体、脚本全都和用户平时上网一致，
        不用担心内嵌内核的兼容性；代价只是会多一个浏览器窗口。
        """
        if not url:
            # 兼容老调用：没给网址就按名称去列表里找
            found = next((f for f in self._forum_list() if f.name == title), None)
            if found is None:
                common.warn(self, f"找不到论坛「{title}」。", "打开论坛失败")
                return
            url = found.url
        if not shell_ops.open_url(url):
            common.warn(
                self,
                f"无法打开网址：\n{url}\n\n可以手动复制到浏览器打开。",
                "打开论坛失败",
            )
            return
        self.statusBar().showMessage(f"已在浏览器中打开：{title or url}", 4000)

    def _rebuild_ai_menu(self) -> None:
        """AI 菜单每次展开时重建，保证提供方状态是最新的。"""
        menu = self.menu_ai
        menu.clear()

        current = self.context.ai.describe_active()
        label = QAction(f"当前 AI：{current}", self)
        label.setEnabled(False)
        menu.addAction(label)
        menu.addSeparator()

        # 与文件无关的日常对话（菜单栏右上角也有同一个入口）
        menu.addAction(self._make_action("AI 日常对话…", self.open_chat_window, "Ctrl+Shift+T"))
        menu.addAction(self._make_action("新对话", self.new_daily_conversation))
        menu.addSeparator()

        for provider_id, provider_label, ok, reason in self.context.ai.available():
            action = QAction(provider_label, self)
            action.setCheckable(True)
            action.setChecked(provider_id == self.context.ai.active_id)
            if not ok:
                action.setToolTip(reason)
            action.triggered.connect(
                lambda _checked=False, pid=provider_id: self.switch_ai(pid)
            )
            menu.addAction(action)

        menu.addSeparator()
        menu.addAction(self._make_action("刷新 AI", self.refresh_ai, "F5"))
        menu.addAction(self._make_action("重新发送文件", self.resend_file))
        menu.addAction(self._make_action("删除聊天记录", self.clear_chats))
        menu.addSeparator()
        menu.addAction(self._make_action("AI 设置…", lambda: self.open_settings("ai")))
        menu.addAction(self._make_action("AI 诊断…", self.ai_diagnostics))

    def _make_action(self, text: str, callback, shortcut=None) -> QAction:
        action = QAction(text, self)
        if shortcut:
            action.setShortcut(shortcut)
        action.triggered.connect(lambda _checked=False, cb=callback: cb())
        return action

    # ==================================================================
    # 菜单栏右上角的 AI 入口
    # ==================================================================

    def _build_menu_corner(self) -> None:
        """在菜单栏右上角放一个常驻 AI 入口。

        需求：能随时进行与文件无关的日常对话。
        * 主按钮：打开「AI 日常对话」窗口；
        * 下拉箭头：切换 AI / 刷新 / AI 设置 / 清空聊天记录。
        """
        corner = QWidget()
        corner.setObjectName("MenuCorner")
        layout = QHBoxLayout(corner)
        layout.setContentsMargins(6, 0, 8, 0)
        layout.setSpacing(4)

        self.btn_chat = QPushButton("AI 对话")
        self.btn_chat.setObjectName("CornerPrimary")
        self.btn_chat.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_chat.clicked.connect(self.open_chat_window)
        layout.addWidget(self.btn_chat)

        self.btn_chat_menu = QToolButton()
        self.btn_chat_menu.setObjectName("CornerDrop")
        self.btn_chat_menu.setText("▾")
        self.btn_chat_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_chat_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.menu_corner = QMenu(self)
        self.menu_corner.aboutToShow.connect(self._rebuild_corner_menu)
        self.btn_chat_menu.setMenu(self.menu_corner)
        layout.addWidget(self.btn_chat_menu)

        self.menuBar().setCornerWidget(corner, Qt.Corner.TopRightCorner)
        self._refresh_corner_button()

    def _refresh_corner_button(self) -> None:
        """让右上角按钮显示当前 AI，配置缺失时给出提示色。"""
        adapter = self.context.ai.active()
        if adapter is None:
            self.btn_chat.setText("AI 对话")
            self.btn_chat.setToolTip("还没有可用的 AI，点右侧箭头进入 AI 设置")
            return
        ok, reason = adapter.is_configured()
        name = adapter.display_label
        short = name.split("（")[0]
        self.btn_chat.setText(f"AI 对话 · {short}")
        self.btn_chat.setToolTip(
            f"当前 AI：{name}\n点击打开「AI 日常对话」（不读取文件）"
            + ("" if ok else f"\n注意：{reason}")
        )

    def _rebuild_corner_menu(self) -> None:
        menu = self.menu_corner
        menu.clear()

        header = QAction(f"当前 AI：{self.context.ai.describe_active()}", self)
        header.setEnabled(False)
        menu.addAction(header)
        menu.addSeparator()

        menu.addAction(self._make_action("打开 AI 日常对话", self.open_chat_window, "Ctrl+Shift+T"))
        menu.addAction(self._make_action("新对话（清空当前对话）", self.new_daily_conversation))
        menu.addSeparator()

        for provider_id, label, ok, reason in self.context.ai.available():
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(provider_id == self.context.ai.active_id)
            if not ok:
                action.setToolTip(reason)
            action.triggered.connect(lambda _checked=False, pid=provider_id: self._switch_ai(pid))
            menu.addAction(action)

        menu.addSeparator()
        menu.addAction(self._make_action("刷新 AI", self.refresh_ai))
        menu.addAction(self._make_action("AI 设置…", lambda: self.open_settings("ai")))
        menu.addAction(self._make_action("删除聊天记录…", self.clear_chats))

    def _switch_ai(self, provider_id: str) -> None:
        self.switch_ai(provider_id)
        self._refresh_corner_button()

    # -- 日常对话窗口 ---------------------------------------------------

    def open_chat_window(self) -> GlobalChatWindow:
        """打开（或置前）AI 日常对话窗口。"""
        window = self._chat_window
        if window is None:
            window = GlobalChatWindow(self.context, None)
            window.status_message.connect(self.show_status)
            window.destroyed.connect(lambda _obj=None: self._on_chat_window_destroyed())
            self._chat_window = window
            # 居中到主窗口附近，避免跑到屏幕角落
            self._place_near_main(window)
        window.show()
        window.raise_()
        window.activateWindow()
        window.focus_input()
        self.show_status("已打开 AI 日常对话（不读取文件）")
        return window

    def _on_chat_window_destroyed(self) -> None:
        self._chat_window = None

    def _place_near_main(self, window: QWidget) -> None:
        try:
            geometry = self.frameGeometry()
            window.move(
                geometry.center().x() - window.width() // 2,
                geometry.center().y() - window.height() // 2,
            )
        except Exception:  # noqa: BLE001 - 多显示器等情况下定位失败也无所谓
            pass

    def new_daily_conversation(self) -> None:
        self.open_chat_window().new_conversation()

    def close_chat_window(self) -> None:
        if self._chat_window is not None:
            self._chat_window.close()

    # ==================================================================
    # 主界面背景
    # ==================================================================

    def _add_background_submenu(self, parent_menu) -> None:
        """在给定菜单下挂一个「更改背景」子菜单（查看/设置两处共用）。"""
        submenu = parent_menu.addMenu("更改背景")
        submenu.aboutToShow.connect(
            lambda target=submenu: self._rebuild_background_menu(target)
        )
        self.background_menus.append(submenu)
        self._rebuild_background_menu(submenu)

    def _rebuild_background_menu(self, menu=None) -> None:
        """重建背景菜单内容（每次展开时调用，保证显示图库现状）。

        ``menu`` 为空时刷新所有已注册的背景子菜单。
        """
        if menu is None:
            for registered in list(getattr(self, "background_menus", [])):
                self._rebuild_background_menu(registered)
            return

        menu.clear()
        manager = self.context.backgrounds
        current = manager.current_path()

        if current is None:
            header = QAction("当前：未设置背景", self)
        else:
            header = QAction(f"当前：{current.name}", self)
        header.setEnabled(False)
        menu.addAction(header)
        menu.addSeparator()

        menu.addAction(self._make_action("选择背景图…", self.choose_background, "Ctrl+Shift+B"))

        entries = manager.entries()
        if entries:
            # 最多列 12 张，避免菜单过长
            for entry in entries[:12]:
                text = ("✔ " if entry.is_current else "") + entry.name
                action = QAction(text, self)
                action.setToolTip(str(entry.path))
                action.triggered.connect(
                    lambda _checked=False, path=entry.path: self.use_background(path)
                )
                menu.addAction(action)
            if len(entries) > 12:
                more = QAction(f"（还有 {len(entries) - 12} 张，用「选择背景图…」查看）", self)
                more.setEnabled(False)
                menu.addAction(more)
        else:
            empty = QAction("图库为空，先导入一张图片", self)
            empty.setEnabled(False)
            menu.addAction(empty)

        menu.addSeparator()
        toggle = QAction("启用背景图", self)
        toggle.setCheckable(True)
        toggle.setChecked(bool(self.context.config.get("ui.background_enabled", True)))
        toggle.setEnabled(current is not None)
        toggle.toggled.connect(self.toggle_background)
        menu.addAction(toggle)
        menu.addAction(self._make_action("不使用背景（图片保留）", self.clear_background))
        menu.addAction(self._make_action("打开背景文件夹", self.open_background_folder))

    def choose_background(self) -> None:
        """打开背景选择对话框（导入、切换、调效果都在里面）。"""
        from gwp.ui.dialogs.background_dialog import BackgroundDialog

        dialog = BackgroundDialog(self.context, self)
        dialog.changed.connect(self.apply_background)
        dialog.exec()
        self.apply_background()

    def use_background(self, path) -> None:
        """直接把某张图设为当前背景。"""
        manager = self.context.backgrounds
        manager.set_current(Path(path))
        self.apply_background()
        self.show_status(f"背景已切换为：{Path(path).name}")

    def toggle_background(self, enabled: bool) -> None:
        self.context.config.set("ui.background_enabled", bool(enabled))
        self.context.save_config()
        self.apply_background()
        self.show_status("已启用背景图" if enabled else "已临时关闭背景图（设置保留）")

    def clear_background(self) -> None:
        manager = self.context.backgrounds
        if manager.current_path() is None:
            common.info(self, "当前没有使用背景图。")
            return
        manager.clear()
        self.apply_background()
        common.info(
            self,
            "已停止使用背景图。\n\n图片文件仍然保留在 else data\\background 里，可以随时切回来。",
            "主界面背景",
        )

    def open_background_folder(self) -> None:
        directory = self.context.backgrounds.ensure_directory()
        file_ops.reveal_in_explorer(directory)

    def apply_background(self) -> None:
        """把背景样式重新应用到主窗口（其余窗口不受影响）。"""
        self.apply_theme()

    def _lock_action_widths(self) -> None:
        """按当前字体把各页标题栏的按钮宽度锁定为"文字完整显示"所需值。

        必须在样式表应用之后调用：字体与内边距都会改变所需宽度。
        换主题、改字号后要重新锁一次，否则会按旧字体的宽度截断文字。
        """
        for view in (
            self.home_view, self.subject_view, self.book_view, *self._documents
        ):
            lock = getattr(view, "lock_action_widths", None)
            if callable(lock):
                lock()

    def apply_theme(self) -> None:
        from gwp.services.background import background_qss, content_margins, resolve_background

        config, paths = self.context.config, self.context.paths
        self.setStyleSheet(
            themes.app_qss(
                theme=self.context.theme,
                accent=str(config.get("ui.accent", "") or ""),
                font_family=str(config.get("ui.font_family", "") or ""),
                font_size=int(config.get("ui.font_size", 10) or 10),
            )
            + background_qss(config, paths)
        )

        # 背景图由控件自绘（QSS 的 background-image 在本项目里不生效）
        self.background_area.set_background(*resolve_background(config, paths))

        # 有背景图时按配置留边（默认 0 = 背景铺满工作区）
        margin = content_margins(config, paths)
        self.area_layout.setContentsMargins(margin, margin, margin, margin)
        # 圆角只在"浮在背景上"时有意义；铺满时留着会露出四角
        self.content_area.setProperty("floating", margin > 0)
        self.content_area.style().unpolish(self.content_area)
        self.content_area.style().polish(self.content_area)
        self.setWindowIcon(common.app_icon(config=self.context.config))
        self._lock_action_widths()
        if self.act_theme is not None:
            self.act_theme.setChecked(self.context.theme == "dark")
        for view in self._documents:
            view.apply_theme()
        for window in self._windows:
            window.apply_theme()
        if self._toast is not None:
            self._toast.setParent(None)
            self._toast = None

    def refresh_settings(self) -> None:
        """设置改动后刷新界面。"""
        self.apply_theme()
        for view in (self.home_view, self.subject_view, self.book_view):
            hook = getattr(view, "refresh_settings", None)
            if callable(hook):
                hook()
            else:
                view.refresh()
        self.refresh_status()

    def toggle_theme(self, checked: bool) -> None:
        self.context.config.set("ui.theme", "dark" if checked else "light")
        self.context.save_config()
        self.apply_theme()

    def show_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 6000)

    def refresh_status(self) -> None:
        self.status_ai.setText(self.context.ai.describe_active())
        self.status_path.setText(str(self.context.paths.data_root))
        self._refresh_corner_button()

    def _on_fallback(self, from_provider: str = "", to_provider: str = "", to_label: str = "", reason: str = "", **_kwargs) -> None:
        # 这条通知可能来自**后台线程**（AIWorker 里调 chat_with_fallback，
        # 主 AI 失败时会发事件）。状态栏是控件，必须在 GUI 线程里改。
        def _apply() -> None:
            self.show_status(f"已切换到兜底 AI：{to_label or to_provider}")
            self.refresh_status()

        common.run_in_gui(self, _apply)

    # ==================================================================
    # 导航
    # ==================================================================

    def show_home(self) -> None:
        # 点「首页」应当回到最外层，而不是停在某个收纳箱里
        self.home_view.leave_box()
        self.stack.setCurrentWidget(self.home_view)
        self.home_view.on_shown()

    def open_subject(self, subject_name: str) -> None:
        self.subject_view.show_subject(subject_name)
        self.stack.setCurrentWidget(self.subject_view)

    def open_book(self, subject_name: str, book_name: str) -> None:
        self.book_view.show_book(subject_name, book_name)
        self.stack.setCurrentWidget(self.book_view)

    def open_homework_in_app(
        self, subject_name: str, book_name: str, folder: str = ""
    ) -> None:
        """在软件内打开某本书目的**作业栏目**，并定位到某个作业。

        需求："日程栏打开按键点击后在软件内打开对应 Book 的 homework 栏目，
        不是打开本地文件夹"。

        顺序很重要：``show_book()`` 内部会 refresh（把当前浏览位置重置），
        所以**必须**先切书目、再 ``enter_folder()``；反过来的话
        ``enter_folder`` 设的位置会被随后的 refresh 冲掉。

        ``subject`` / ``book`` 可能来自旧数据而为空 —— 那就退一步，
        从作业目录的结构反推（``…/subjects/<科目>/<书目>/homework/<作业>``）。
        """
        folder_path = Path(folder) if folder else None
        if (not subject_name or not book_name) and folder_path is not None:
            guess_subject, guess_book = self._guess_subject_book(folder_path)
            subject_name = subject_name or guess_subject
            book_name = book_name or guess_book
        if not subject_name or not book_name:
            log.warning("无法确定作业属于哪个书目：%s", folder)
            self.show_status("找不到这个作业所属的书目")
            return

        self.open_book(subject_name, book_name)
        view = self.book_view
        # 切到作业栏目（按内部 key 找，不要按显示文案 ——
        # 自学课同一栏目叫「练习」，按文案找会漏）
        view._select_tab_key("homework")
        if folder_path is not None and folder_path.is_dir():
            view.enter_folder(folder_path)
        log.info("已从日程栏打开作业：%s / %s / %s",
                 subject_name, book_name, folder_path)

    @staticmethod
    def _guess_subject_book(folder: Path) -> tuple[str, str]:
        """从作业路径反推科目名与书目名。

        数据布局是 ``…/subjects/<科目>/<书目>/homework/<作业>``，所以：

        1. 有 ``homework`` 这一段 → 取它前面两段（最可靠）；
        2. 没有的话，找 ``subjects`` 这一段 → 取它后面两段；
        3. **都找不到就返回空**，绝不"取最后两段"硬凑 ——
           那会把 ``D:\\x`` 猜成科目 ``D:\\``、书目 ``x``，
           然后在界面上弹一个莫名其妙的"找不到书目"。
           宁可让调用方明确报"定位失败"，也不要猜错。
        """
        parts = list(Path(folder).parts)
        lowered = [part.lower() for part in parts]

        homework_name = C.HOMEWORK_FOLDER.lower()
        if homework_name in lowered:
            index = lowered.index(homework_name)
            if index >= 2:
                return parts[index - 2], parts[index - 1]

        subjects_name = C.DEFAULT_SUBJECTS_DIR.lower()   # "subjects"
        if subjects_name in lowered:
            index = lowered.index(subjects_name)
            if index + 2 <= len(parts) - 1:
                return parts[index + 1], parts[index + 2]
        return "", ""

    def show_subject(self) -> None:
        self.subject_view.on_shown()
        self.stack.setCurrentWidget(self.subject_view)

    def show_parent(self) -> None:
        current = self.stack.currentWidget()
        if isinstance(current, DocumentView):
            self._close_document(current, force=False)
        elif current is self.book_view:
            self.show_subject()
        elif current is self.subject_view:
            self.show_home()

    def refresh_all(self) -> None:
        self.context.library.invalidate()
        self.home_view.refresh()
        self.subject_view.refresh()
        self.book_view.refresh()
        self.refresh_status()
        self.show_status("已重新扫描数据目录")

    # ==================================================================
    # 文档
    # ==================================================================

    def open_document(self, path: Path | str) -> None:
        path = Path(path)
        if not path.exists():
            common.warn(self, f"文件不存在：{path}")
            return
        if path.suffix.lower() in (".md", ".markdown", ".txt"):
            if bool(self.context.config.get("ui.open_files_in_new_window", True)):
                self.open_document_window(path)
            else:
                self._open_document_inline(path)
            return
        if path.suffix.lower() in C.JSON_EXTENSIONS:
            # JSON 优先用 VSCode（需求），没有 VSCode 就落到内置查看器
            if file_ops.open_in_vscode(path):
                self.show_status(f"已用 VSCode 打开：{path.name}")
                return
            self.open_text_file(path)
            return
        if path.suffix.lower() in C.CODE_EXTENSIONS:
            self.open_text_file(path)
            return
        # 其它类型（图片、PDF、Office 等）交给系统默认程序
        file_ops.open_with_system(path)

    def open_text_file(self, path: Path | str) -> None:
        """用内置的只读文本查看器打开（JSON 兜底、源码/配置等）。"""
        path = Path(path)
        for view in self._text_views:
            if view._path == path:                 # noqa: SLF001 - 同类内部访问
                self.stack.setCurrentWidget(view)
                return
        view = TextView(self.context, self)
        view.status_message.connect(self.show_status)
        if not view.open_file(path):
            view.deleteLater()
            return
        view.closed.connect(lambda v: self._close_text_view(v))
        self.stack.addWidget(view)
        self._text_views.append(view)
        self.stack.setCurrentWidget(view)

    def _close_text_view(self, view) -> None:
        if view in self._text_views:
            self._text_views.remove(view)
        self.stack.removeWidget(view)
        view.deleteLater()

    def open_document_window(self, path: Path) -> None:
        for window in list(self._windows):
            if window.view.path == path:
                window.raise_()
                window.activateWindow()
                return
        window = DocumentWindow(self.context, path, None)
        window.status_message.connect(self.show_status)
        window.export_pdf_requested.connect(self._export_pdf_for)
        window.closed.connect(self._on_window_closed)
        window.show()
        self._windows.append(window)
        self.show_status(f"已在新窗口打开：{path.name}")

    def _on_window_closed(self, window: DocumentWindow) -> None:
        if window in self._windows:
            self._windows.remove(window)

    def _open_document_inline(self, path: Path) -> None:
        for view in self._documents:
            if view.path == path:
                self.stack.setCurrentWidget(view)
                return
        view = DocumentView(self.context, self)
        view.status_message.connect(self.show_status)
        view.request_pdf_export.connect(self._export_pdf_for)
        view.closed.connect(lambda v: self._close_document(v, force=False))
        if not view.open_file(path):
            view.deleteLater()
            return
        self.stack.addWidget(view)
        self._documents.append(view)
        self.stack.setCurrentWidget(view)

    def _current_document(self) -> DocumentView | None:
        current = self.stack.currentWidget()
        if isinstance(current, DocumentView):
            return current
        for window in self._windows:
            if window.isActiveWindow():
                return window.view
        return None

    def _close_document(self, view: DocumentView, force: bool = False) -> None:
        if not force and not view.confirm_close():
            return
        if view in self._documents:
            self._documents.remove(view)
        self.stack.removeWidget(view)
        view.deleteLater()
        self.show_parent()

    def close_current_document(self) -> None:
        view = self._current_document()
        if view is None:
            common.info(self, "当前没有打开的文档。")
            return
        if view in self._documents:
            self._close_document(view)
        else:
            for window in self._windows:
                if window.view is view:
                    window.close()
                    return

    def save_all(self) -> None:
        saved = 0
        for view in self._documents:
            if view.has_unsaved and view.save():
                saved += 1
        for window in self._windows:
            if window.view.has_unsaved and window.view.save():
                saved += 1
        self.show_status(f"已保存 {saved} 个文档" if saved else "没有需要保存的文档")

    def _with_document(self, callback) -> None:
        view = self._current_document()
        if view is None:
            common.info(self, "请先打开一个 Markdown 文档。")
            return
        callback(view)

    def _with_editor(self, method: str) -> None:
        view = self._current_document()
        if view is None:
            return
        editor = view.editor.editor
        getattr(editor, method)()
        editor.setFocus()

    def toggle_edit_mode(self) -> None:
        view = self._current_document()
        if view is None:
            common.info(self, "请先打开一个 Markdown 文档。")
            return
        view.toggle_edit_mode()

    def toggle_ai_panel(self, checked: bool) -> None:
        view = self._current_document()
        if view is None:
            # 主窗口里没有文档：把当前书目页的总结/简介打开再说
            common.info(self, "请先打开一个 Markdown 文档，再使用 AI 双栏。")
            if self.act_ai_panel is not None:
                self.act_ai_panel.setChecked(False)
            return
        view.set_ai_visible(checked)

    def _markdown_target_dir(self):
        """新建 Markdown 的目标目录；没有书目上下文时返回 (None, 原因)。

        需求：**首页（以及科目页）不允许新建 Markdown**。
        因为这两处没有"书目"上下文，文件只能落到某个猜出来的目录里
        （旧实现是 ``subjects/未分类``），那就是"未知区域"——
        用户之后找不到文件，AI 总结也不会读到它（总结只扫具体书目的
        Intel/notebook/error-prone）。
        """
        current = self.stack.currentWidget()
        if current is not self.book_view:
            return None, "请先进入某个书目"
        book = self.book_view.book()
        if book is None:
            return None, "请先进入某个书目"
        return book.path / C.NOTEBOOK_FOLDER, ""

    def _sync_markdown_action(self) -> None:
        """根据当前页面启用/禁用「新建 Markdown 文件」。"""
        action = getattr(self, "act_new_markdown", None)
        if action is None:
            return
        target, reason = self._markdown_target_dir()
        action.setEnabled(target is not None)
        action.setToolTip(
            "在本书目的「笔记」目录里新建 Markdown"
            if target is not None
            else f"{reason}：Markdown 会放进该书的 notebook 目录"
        )

    def new_markdown(self) -> None:
        """在**当前书目**的 notebook 目录里新建一个 Markdown 文件。

        首页/科目页没有书目上下文，这里会直接拦住并说明原因（需求：避免
        文件被创建到未知区域）。
        """
        target_dir, reason = self._markdown_target_dir()
        if target_dir is None:
            common.warn(
                self,
                f"{reason}。\n\n"
                "新建的 Markdown 会被放进书目的「笔记」（notebook）目录，"
                "因此需要先选定一本书；\n"
                "在首页/科目页新建会让文件落到不确定的位置，所以这里不提供该操作。",
                "无法新建 Markdown",
            )
            return

        name, ok = QInputDialog.getText(self, "新建 Markdown 文件", "文件名（无需扩展名）：")
        if not ok or not name.strip():
            return
        file_name = name.strip()
        if not file_name.lower().endswith((".md", ".markdown", ".txt")):
            file_name += ".md"
        path = target_dir / file_name
        if path.exists():
            common.warn(self, f"文件已存在：{path}")
            return
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {Path(file_name).stem}\n\n", encoding="utf-8")
        except OSError as exc:
            common.error(self, f"创建失败：{exc}", "新建文件")
            return
        self.show_status(f"已创建：{path.name}（位于 {target_dir.name}）")
        self.open_document(path)
        self.book_view.refresh()

    def open_file_dialog(self) -> None:
        start = str(self.context.paths.user_data)
        path, _ = QFileDialog.getOpenFileName(
            self,
            "打开 Markdown 文件",
            start,
            "Markdown 与文本 (*.md *.markdown *.txt);;所有文件 (*.*)",
        )
        if path:
            self.open_document(Path(path))

    # ==================================================================
    # 科目 / 书目操作
    # ==================================================================

    def new_subject(self) -> None:
        self.show_home()
        self.home_view.create_subject()

    def new_book(self) -> None:
        current = self.stack.currentWidget()
        if current is self.subject_view:
            self.subject_view.create_book()
            return
        if current is self.book_view:
            self.open_subject(self.book_view.subject_name)
            self.subject_view.create_book()
            return
        # 在首页：让用户先选科目
        subjects = self.context.library.subjects()
        if not subjects:
            common.info(self, "请先创建一个科目，再新建书目。")
            self.new_subject()
            return
        names = [subject.title for subject in subjects]
        choice, ok = QInputDialog.getItem(self, "新建书目", "选择所属科目：", names, 0, False)
        if not ok:
            return
        subject = subjects[names.index(choice)]
        dialog = BookDialog(self, subject_name=subject.name)
        if not dialog.exec():
            return
        values = dialog.values()
        try:
            book = self.context.library.create_book(
                subject.name, values["name"], description=values["description"]
            )
            if values.get("color"):
                self.context.library.update_book(subject.name, book.name, color=values["color"])
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "新建书目失败")
            return
        self.open_book(subject.name, book.name)

    def import_files(self) -> None:
        current = self.stack.currentWidget()
        if current is self.book_view:
            self.book_view.import_files()
        else:
            common.info(self, "请先进入一个书目，再导入文件。")

    def extract_images(self) -> None:
        """把当前文件夹里的图片用 AI 提取成一份 Markdown（工具菜单入口）。"""
        current = self.stack.currentWidget()
        if current is not self.book_view:
            common.info(self, "请先进入一个书目，再使用图片提取。", "图片提取")
            return
        self.book_view.extract_images()

    def merge_sources_into_summary(self) -> None:
        """把资料插进 summary（工具菜单入口）。

        需求变更后这和「生成总结」是同一件事，所以共用同一个实现；
        菜单项保留是为了让"从菜单找生成"的用户也能找到。
        """
        current = self.stack.currentWidget()
        if current is not self.book_view:
            common.info(
                self, "请先进入一个书目，再生成总结。", "生成总结",
            )
            return
        self.book_view.build_summary_from_sources()

    def open_book_folder(self) -> None:
        current = self.stack.currentWidget()
        if current is self.book_view:
            self.book_view.reveal_book()
        elif self.subject_view.subject_name:
            subject = self.context.library.subject(self.subject_view.subject_name)
            if subject is not None:
                file_ops.reveal_in_explorer(subject.path)

    def open_data_folder(self) -> None:
        file_ops.reveal_in_explorer(self.context.paths.user_data)

    def open_document_dir(self) -> None:
        from gwp.core.paths import document_dir

        directory = document_dir()
        if directory.is_dir():
            file_ops.reveal_in_explorer(directory)
        else:
            common.warn(self, f"文档目录不存在：{directory}\n可以先用「帮助 → 使用说明」查看内置文档。")

    def open_config_file(self) -> None:
        if not self.context.paths.config_file.exists():
            self.context.save_config()
        file_ops.open_with_system(self.context.paths.config_file)

    def open_settings(self, page: str = "") -> None:
        dialog = SettingsDialog(self.context, self, initial_page=page)
        if dialog.exec():
            self.refresh_settings()
            self.refresh_ai_menu_state()

    def reset_settings(self) -> None:
        if not common.confirm(
            self,
            "确定把所有设置恢复为默认值吗？\n\n科目、书目、笔记、总结等用户数据不会被删除。",
            "恢复默认设置",
        ):
            return
        from gwp.core.config import DEFAULT_CONFIG

        self.context.config.update(DEFAULT_CONFIG)
        self.context.config.save()
        self.context.ai.invalidate()
        self.refresh_settings()
        common.info(self, "已恢复默认设置。", "设置")

    # ==================================================================
    # AI
    # ==================================================================

    def switch_ai(self, provider_id: str) -> None:
        try:
            self.context.ai.set_active(provider_id)
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "切换 AI 失败")
            return
        self.refresh_ai_menu_state()
        adapter = self.context.ai.get(provider_id)
        ok, reason = adapter.is_configured() if adapter else (False, "找不到该提供方")
        if not ok:
            common.warn(
                self,
                f"已切换到 {adapter.display_label if adapter else provider_id}，但它还不可用：\n{reason}\n"
                "可以在「AI → AI 设置」里补全配置。",
                "AI 不可用",
            )
        else:
            self.show_status(f"当前 AI：{self.context.ai.describe_active()}")

    def refresh_ai_menu_state(self) -> None:
        self.refresh_status()
        for view in self._documents:
            view.chat.reload_providers()
        for window in self._windows:
            window.view.chat.reload_providers()
        if self._chat_window is not None:
            self._chat_window.chat.reload_providers()
        self._refresh_corner_button()

    def refresh_ai(self) -> None:
        busy = common.BusyDialog(self, "刷新 AI", "正在重新连接并自检……")
        busy.show()
        ok, message = self.context.ai.refresh()
        busy.close()
        self.context.ai.invalidate()
        self.refresh_ai_menu_state()
        if ok:
            common.info(self, message, "刷新 AI")
        else:
            common.warn(self, message, "刷新 AI")
        self.show_status(message)

    def resend_file(self) -> None:
        view = self._current_document()
        if view is None:
            common.info(self, "请先打开一个 Markdown 文档。")
            return
        if not view.chat.isVisible():
            view.set_ai_visible(True)
            if self.act_ai_panel is not None:
                self.act_ai_panel.setChecked(True)
        view.chat.resend_file(force=True)

    def clear_chats(self) -> None:
        dialog = ChatManagerDialog(self.context, self)
        dialog.exec()

    def ai_diagnostics(self) -> None:
        lines = ["AI 诊断", ""]
        for provider_id, label, ok, reason in self.context.ai.available():
            adapter = self.context.ai.get(provider_id)
            mark = "可用" if ok else "不可用"
            lines.append(f"[{mark}] {label}（{provider_id}）")
            if not ok and reason:
                lines.append(f"        {reason}")
            if adapter is not None:
                lines.append(f"        实现：{adapter.__class__.__name__} · 类型：{adapter.kind}")
        lines.append("")
        lines.append(f"当前 AI：{self.context.ai.active_id}")
        lines.append(f"兜底顺序：{', '.join(self.context.ai.fallback_chain())}")
        lines.append(f"密钥文件：{self.context.paths.secrets_file}")
        common.info(self, "\n".join(lines), "AI 诊断")

    # ==================================================================
    # 工具
    # ==================================================================

    def generate_summary(self) -> None:
        current = self.stack.currentWidget()
        if current is self.book_view:
            self.book_view.generate_summary()
            return
        # 在其它页面：让用户选一本书
        options: list[tuple[str, str, str]] = []
        for subject in self.context.library.subjects():
            for book in subject.books:
                options.append((f"{subject.title} / {book.title}", subject.name, book.name))
        if not options:
            common.info(self, "还没有书目。请先创建科目和书目，并放入笔记或易错题。")
            return
        names = [item[0] for item in options]
        choice, ok = QInputDialog.getItem(self, "生成学习总结", "选择书目：", names, 0, False)
        if not ok:
            return
        index = names.index(choice)
        self.open_book(options[index][1], options[index][2])
        QTimer.singleShot(120, self.book_view.generate_summary)

    def preview_materials(self) -> None:
        current = self.stack.currentWidget()
        if current is self.book_view:
            self.book_view.preview_materials()
        else:
            common.info(self, "请先进入一个书目。")

    def open_backups(self) -> None:
        """打开总结版本管理；不在书目页时先让用户选一本书。"""
        current = self.stack.currentWidget()
        if current is self.book_view:
            self.book_view.open_backups()
            return

        options: list[tuple[str, str, str]] = []
        for subject in self.context.library.subjects():
            for book in subject.books:
                options.append((f"{subject.title} / {book.title}", subject.name, book.name))
        if not options:
            common.info(self, "还没有书目，暂时没有可管理的总结版本。")
            return
        names = [item[0] for item in options]
        choice, ok = QInputDialog.getItem(self, "总结版本管理", "选择书目：", names, 0, False)
        if not ok:
            return
        index = names.index(choice)
        self.open_book(options[index][1], options[index][2])
        QTimer.singleShot(80, self.book_view.open_backups)

    def export_current_pdf(self) -> None:
        view = self._current_document()
        if view is None or view.path is None:
            current = self.stack.currentWidget()
            if current is self.book_view:
                self.book_view.export_pdf()
            else:
                common.info(self, "请先打开一个 Markdown 文档或进入书目页。")
            return
        self._export_pdf_for(view.path)

    def _export_pdf_for(self, path: Path) -> None:
        dialog = ExportPdfDialog(self.context, Path(path), self)
        if dialog.exec():
            self.show_status(f"已导出 PDF：{dialog.output_path}")

    def rebuild_cache(self) -> None:
        self.context.cache.clear()
        self.context.cache.save()
        self.refresh_all()
        common.info(self, "扫描缓存已重建。", "缓存")

    def check_dependencies(self) -> None:
        text = dependencies.summary()
        missing = dependencies.missing()
        if missing:
            text += f"\n\n需要安装：\n{dependencies.install_command()}"
        else:
            text += "\n\n依赖完整。"
        common.info(self, text, "依赖自检")

    def toggle_autostart(self, checked: bool) -> None:
        ok, message = shell_ops.set_autostart(checked)
        if ok:
            self.context.config.set("startup.autostart", checked)
            self.context.save_config()
            self.show_status(message)
        else:
            common.warn(self, message, "开机自启")
            if self.act_startup is not None:
                # 回滚勾选状态时同样要屏蔽信号，否则 setChecked 又会触发
                # toggle_autostart -> set_autostart，形成重复写注册表甚至递归
                self.act_startup.blockSignals(True)
                self.act_startup.setChecked(shell_ops.is_autostart_enabled())
                self.act_startup.blockSignals(False)

    def create_shortcut(self) -> None:
        ok, message = shell_ops.create_desktop_shortcut()
        if ok:
            common.info(self, message, "创建快捷方式")
        else:
            common.warn(self, message, "创建快捷方式")

    # ==================================================================
    # 帮助
    # ==================================================================

    def open_help(self, page: str) -> None:
        dialog = HelpDialog(self.context, page, self)
        dialog.exec()

    def show_about(self) -> None:
        text = (
            f"<b>{__app_name__}</b> v{__version__}<br><br>"
            "本地知识管理与 AI 辅助学习软件。<br>"
            "管理课程、教材、笔记、易错题；用 AI 把零散资料整合成完整的学习文档。<br><br>"
            f"程序目录：{self.context.root}<br>"
            f"数据目录：{self.context.paths.data_root}<br>"
            f"当前 AI：{self.context.ai.describe_active()}<br><br>"
            "所有内容都是普通文件，可随时手工备份或迁移。"
        )
        box = QMessageBox(self)
        box.setWindowTitle("关于")
        box.setTextFormat(Qt.TextFormat.RichText)
        box.setText(text)
        box.setIconPixmap(common.app_pixmap(64, config=self.context.config))
        box.exec()

    # ==================================================================
    # 启动与退出
    # ==================================================================

    def _post_start(self) -> None:
        warnings = check_startup_environment(self.context)
        for message in warnings:
            common.warn(self, message, "环境检查")

        # 开始监听"另一个进程请求唤回窗口"（双击快捷方式时写请求文件）
        self._start_watch_and_identity()

        if bool(self.context.config.get("startup.prewarm_scan", True)):
            self._startup_worker = StartupWorker(self.context, self)
            self._startup_worker.finished_scan.connect(self._on_prewarm_done)
            self._startup_worker.start()

    def _on_prewarm_done(self, count: int) -> None:
        log.info("预扫描完成：%s 个科目", count)
        self.home_view.refresh()
        self.show_status(f"预扫描完成，共 {count} 个科目")

    # ==================================================================
    # 关闭到后台 / 系统托盘
    # ==================================================================
    #
    # 需求：**当主界面关闭，软件在后台运行，除非用户手动用任务管理器终止**。
    #
    # 理由是启动一次要重建整个界面并预热扫描，开销明显；
    # 留在后台之后"再次打开"就只是把窗口显示出来，是瞬间的。
    #
    # 但"只能靠任务管理器终止"是不能接受的（用户会骂）：
    # 所以配上系统托盘图标 —— 双击唤回、右键「完全退出」。
    # 另外再双击一次桌面快捷方式也能唤回（单实例机制会走
    # ``app._report_already_running`` → 把隐藏的窗口重新显示出来）。

    def _close_to_background_enabled(self) -> bool:
        return bool(self.context.config.get("ui.close_to_background", True))

    def _ensure_tray(self) -> QSystemTrayIcon | None:
        """按需创建托盘图标。

        延迟创建（而不是启动时就建）有两个好处：
        * 不占启动时间；
        * 托盘只在"真的用到后台运行"时才出现，不会平白多一个常驻图标。
        """
        if self._tray is not None:
            return self._tray
        if not QSystemTrayIcon.isSystemTrayAvailable():
            log.warning("系统托盘不可用，关闭后将真正退出")
            return None

        tray = QSystemTrayIcon(common.app_icon(config=self.context.config), self)
        tray.setToolTip(f"{__app_name__}（在后台运行）")

        menu = QMenu(self)
        action_show = QAction(f"显示 {__app_name__}", self)
        action_show.triggered.connect(self.restore_from_background)
        menu.addAction(action_show)

        menu.addSeparator()
        action_quit = QAction("完全退出", self)
        action_quit.triggered.connect(self.quit_completely)
        menu.addAction(action_quit)

        tray.setContextMenu(menu)
        # 双击托盘图标 = 唤回窗口（Windows 上的通用习惯）
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self._tray = tray
        return tray

    def _on_tray_activated(self, reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.DoubleClick,
            QSystemTrayIcon.ActivationReason.Trigger,
        ):
            self.restore_from_background()

    def hide_to_background(self, *_args) -> bool:
        """把主窗口藏起来，进程继续在后台运行。返回是否成功进入后台。

        接收 ``*_args`` 是为了能直接当菜单回调用（``triggered`` 会传一个
        ``checked`` 布尔值），也能当普通函数调用。

        **托盘不可用时的降级**（很关键）：不静默退出，而是退成
        "最小化到任务栏" —— 窗口还在任务栏上，用户点得到；
        同时再双击一次桌面快捷方式也能唤回（``app._report_already_running``
        里的 ``show_and_activate_window``）。这样至少不会出现
        "关了窗口、没有托盘、只能开任务管理器"的最坏情况。
        """
        tray = self._ensure_tray()
        if tray is None:
            # 降级：最小化而不是隐藏，保住任务栏入口
            self.showMinimized()
            self.show_status(
                "托盘不可用，已最小化到任务栏；再双击一次快捷方式也能唤回"
            )
            log.info("托盘不可用，改为最小化到任务栏（进程继续运行）")
            return True

        self.hide()
        tray.show()
        log.info("主窗口已隐藏到后台，进程继续运行（托盘图标可唤回）")

        # 第一次隐藏时提示一次，说清"怎么找回来"和"怎么彻底退出"。
        # 只提示一次，避免每次关窗口都被打扰。
        if not bool(self.context.config.get("ui.close_to_background_notified", False)):
            tray.showMessage(
                f"{__app_name__} 还在后台运行",
                "双击托盘图标可以重新打开；右键托盘图标可以「完全退出」。\n"
                "（也可以再双击一次桌面快捷方式唤回窗口）",
                QSystemTrayIcon.MessageIcon.Information,
                6000,
            )
            self.context.config.set("ui.close_to_background_notified", True)
            try:
                self.context.config.save()
            except OSError:
                log.debug("保存「已提示过后台运行」失败", exc_info=True)
        return True

    def _poll_wake_request(self) -> None:
        """看看有没有别的进程请求"把窗口唤回来"。

        为什么用轮询而不是原生事件：见 :mod:`gwp.core.wakeup` 的模块说明 ——
        在 PyQt6 6.11 上覆盖 ``QWidget.nativeEvent`` 会直接崩溃，
        所以选了这个"笨但可靠"的做法。600ms 一次，开销可以忽略。
        """
        try:
            if not self._wake_watcher.poll():
                return
        except Exception:  # noqa: BLE001 - 定时器回调里不能抛
            log.debug("检查唤回请求失败", exc_info=True)
            return
        log.info("收到另一个进程的唤回请求")
        self.restore_from_background()

    def _start_wake_watch(self) -> None:
        """开始监听唤回请求（把当前状态设为基准，避免误判）。"""
        self._wake_watcher.mark_current()
        self._wake_timer.start()

    def _start_watch_and_identity(self) -> None:
        """启动时的一次性整理：唤回监听 + 数据变化监听 + 修快捷方式的应用标识。"""
        self._start_wake_watch()
        self._start_data_watch()
        # 桌面快捷方式可能是旧版本创建的（没有应用标识），
        # 那会让"双击快捷方式"启动的进程与快捷方式不是同一个任务栏分组，
        # 任务栏仍然显示解释器图标（用户报障）。顺手补上，失败无所谓。
        try:
            from gwp.services import shell_ops

            shell_ops.ensure_shortcut_identity()
        except Exception:  # noqa: BLE001 - 纯锦上添花，绝不影响启动
            log.debug("补快捷方式应用标识失败", exc_info=True)

    # ------------------------------------------------------------------
    # 后台监听数据目录变化
    # ------------------------------------------------------------------

    def _start_data_watch(self) -> None:
        """开始盯着 ``user data``，有外部改动就刷新界面。

        需求："软件后台要不断扫描user data文件夹，更新文件变动，
        但不要耗费cpu太多性能"。

        省 CPU 的三条（详见 :mod:`gwp.ui.data_watcher`）：
        用 ``os.scandir``（比 rglob 快 23 倍）、只在真变化时才重建界面、
        窗口看不见时**完全停掉**。
        """
        try:
            from gwp.ui.data_watcher import DEFAULT_INTERVAL_MS, DataWatcher

            interval = int(self.context.config.get(
                "ui.data_scan_interval_ms", DEFAULT_INTERVAL_MS
            ) or DEFAULT_INTERVAL_MS)
            self._data_watcher = DataWatcher(
                self.context.paths.subjects_dir, self, interval_ms=interval
            )
            self._data_watcher.changed.connect(self._on_data_changed)
            if bool(self.context.config.get("ui.auto_refresh_on_change", True)):
                self._data_watcher.start()
            else:
                log.info("已按配置关闭「数据变化自动刷新」")
        except Exception:  # noqa: BLE001 - 监听失败不该影响启动
            log.warning("启动数据变化监听失败", exc_info=True)

    def _on_data_changed(self, added: list, removed: list) -> None:
        """数据目录真的变了：让缓存失效并刷新当前页面。"""
        log.info("检测到数据目录变化，刷新界面（+%d / -%d）",
                 len(added or []), len(removed or []))
        try:
            self.context.library.invalidate()
            # 当前停在书目页就刷新它，否则刷新首页
            current = self.stack.currentWidget()
            if current is self.book_view:
                self.book_view.refresh()
            elif current is self.home_view:
                self.home_view.refresh()
            else:
                self.home_view.refresh()
            self.show_status("已根据文件变化自动刷新")
        except Exception:  # noqa: BLE001 - 刷新失败不能让定时器把异常抛出去
            log.exception("自动刷新失败")

    def _set_data_watch_enabled(self, enabled: bool) -> None:
        """窗口可见性变化时启停监听（隐藏就不扫，省 CPU）。"""
        watcher = getattr(self, "_data_watcher", None)
        if watcher is None:
            return
        if not bool(self.context.config.get("ui.auto_refresh_on_change", True)):
            return
        if enabled:
            if not watcher.running:
                watcher.start()
        else:
            watcher.stop()

    def restore_from_background(self) -> None:
        """把隐藏的窗口重新显示出来（并从最小化状态还原）。"""
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()
        self.raise_()
        self.activateWindow()
        # **从后台回来必须强制重绘一次。**
        # 实测：窗口被 hide() 之后，如果只靠外部 ShowWindow 让它"可见"，
        # Qt 不会重绘，用户看到全黑窗口（见 core/wakeup.py 的说明）。
        # 背景是自绘的（BackgroundImageWidget），漏一次 paint 就是一片黑。
        self.update()
        # 从后台回来的窗口应当能立刻交互，顺手把状态栏提示换成一句明确的
        self.show_status("已从后台唤回")
        log.info("主窗口已从后台唤回")

    # ------------------------------------------------------------------
    # 窗口可见性 -> 数据监听的启停
    # ------------------------------------------------------------------
    #
    # 用 Qt 的事件而不是"在 hide/show 的每个调用点手动补一句"：
    # 隐藏、最小化、被系统收起……都会走到这里，**漏不掉**。
    # （这个项目已经因为"每个调用点都要记得做某件事"栽过一次 —— 见
    #   core/threads.py 的说明。）

    def showEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        super().showEvent(event)
        if not self._watcher_paused_for_minimize():
            self._set_data_watch_enabled(True)

    def hideEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        super().hideEvent(event)
        self._set_data_watch_enabled(False)

    def changeEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        super().changeEvent(event)
        from PyQt6.QtCore import QEvent

        if event.type() == QEvent.Type.WindowStateChange:
            # 最小化时也别扫：没人看，白烧 CPU
            self._set_data_watch_enabled(not self.isMinimized())

    def _watcher_paused_for_minimize(self) -> bool:
        return bool(self.isMinimized())

    def quit_completely(self) -> None:
        """真正退出进程（托盘菜单入口 / 程序化退出）。

        置标志位后走 ``close()``，让 ``closeEvent`` 里的
        "确认未保存文档 → 清理 → 释放资源"这条既有链路照常执行，
        不另写一份退出逻辑（两份一定会不一致）。
        """
        self._really_quit = True
        if self._tray is not None:
            self._tray.hide()
        self.close()

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt 接口
        # 1) 检查未保存的文档
        for view in list(self._documents):
            if not view.confirm_close():
                event.ignore()
                return
        for window in list(self._windows):
            window.close()
            if window.isVisible():
                event.ignore()
                return

        # 1.5) AI 日常对话窗口：它自己会保存聊天记录
        if self._chat_window is not None and self._chat_window.isVisible():
            self._chat_window.close()
            if self._chat_window is not None and self._chat_window.isVisible():
                event.ignore()          # 用户在"AI 正在回答"的确认框里选了取消
                return

        # 1.8) **隐藏到后台**（需求：主界面关闭后进程继续运行）。
        #      放在"检查未保存文档"之后：有未保存内容时仍要先问用户，
        #      不能因为"反正不退出"就跳过保存确认。
        if (
            not self._really_quit
            and self._close_to_background_enabled()
            and self.hide_to_background()
        ):
            event.ignore()              # 不真正关闭窗口，只是藏起来
            return

        # 2) 保存聊天记录并按配置清空
        cleanup_on_exit(self.context)

        # 真退出了：不用再盯着唤回请求
        wake_timer = getattr(self, "_wake_timer", None)
        if wake_timer is not None:
            wake_timer.stop()

        # 3) 停掉首页的时钟/天气线程，否则退出时会有线程还在跑
        clock = getattr(self.home_view, "clock_bar", None)
        if clock is not None:
            clock.stop()

        # 3.5) **等所有后台线程结束**（这是防"闪退"的关键一步）。
        #
        # 原来这里只对 StartupWorker wait(3000)，而预扫描 7 个科目要 20 多秒 ——
        # 3 秒一到就放弃，窗口照常销毁，线程还在跑，
        # 于是 Qt qFatal 中止进程（0xC0000409）。
        # 现在统一交给 core/threads：先脱钩、再分两轮等。
        # 顺序在这里也是对的：必须在窗口销毁**之前**调用。
        try:
            from gwp.core import threads as _threads

            still = _threads.shutdown()
            if still:
                log.warning("退出时仍有 %d 个线程未结束", still)
        except Exception:  # noqa: BLE001 - 退出流程绝不能再抛
            log.debug("等待后台线程失败", exc_info=True)

        if self._tray is not None:
            self._tray.hide()

        log.info("软件退出")
        event.accept()


__all__ = ["MainWindow"]
