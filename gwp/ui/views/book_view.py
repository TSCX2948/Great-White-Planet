"""书目页：资料管理的主界面。

布局：
* 左侧分类标签（AI 总结 / 简介 / 笔记 / 易错题 / 教材 / 全部条目，AI 总结排第一）
* 右侧详情面板（资料统计、总结状态、快速操作）
* 顶部操作：导入文件、剪切、复制、粘贴、生成总结、版本管理、导出 PDF、打开文件夹

交互：
* 拖拽文件到窗口即可导入到当前分类；
* 支持 Ctrl+C / Ctrl+X / Ctrl+V 以及右键菜单的剪切、复制、粘贴；
* 粘贴时同名文件自动改名（`名称_1`），不会覆盖已有资料；
* 剪贴板与系统剪贴板互通，可以从资源管理器复制文件后直接在这里粘贴。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gwp.ai.worker import AIWorker, SimpleWorker
from gwp.bootstrap import AppContext
from gwp.core import constants as C
from gwp.core.eventbus import BOOK_CONTENT_CHANGED, SUMMARY_UPDATED, bus
from gwp.data_manager import homework as hw
from gwp.data_manager.models import Book, BookItem
from gwp.data_manager.store import DataError, sanitize_name, validate_name
from gwp.services import file_ops
from gwp.services.file_clipboard import COPY, CUT, read_system_clipboard_files
from gwp.ui import common
from gwp.ui.dialogs.backup_dialog import BackupDialog
from gwp.ui.dialogs.materials_dialog import SummarySourcesDialog
from gwp.ui.dialogs.progress_dialog import SummaryProgressDialog
from gwp.ui.views.base_view import BaseView
from gwp.ui.views.wordbook_view import WordbookView
from gwp.ui.widgets.file_table import FileTable

log = logging.getLogger(__name__)

#: 标签页定义（按科目类型区分，见 constants.BOOK_TABS_BY_TYPE）
#: 顺序即界面顺序：AI 总结排在第一（需求文档：summary 默认位于 Book 首位）
TABS = C.BOOK_TABS_SELF_STUDY


def _all_tab_definitions() -> tuple:
    """所有类型可能用到的标签定义（去重，供预先建表用）。"""
    seen: dict[str, tuple] = {}
    for tabs in C.BOOK_TABS_BY_TYPE.values():
        for key, title, folder in tabs:
            seen.setdefault(key, (key, title, folder))
    return tuple(seen.values())


#: 「资料概览」展开时的最小宽度（低于这个值内容会挤成一团）
SIDE_MIN_WIDTH = 300


def _supplement_label() -> str:
    """「长庚知道」这个标记的文字。

    取自 :mod:`gwp.services.knowledge_supplement`（单一来源）——
    界面文案和 PDF 上印的字必须一致，否则用户会以为没生效。
    """
    from gwp.services.knowledge_supplement import LABEL

    return LABEL


def _real_data_write_blocked(target: Path) -> str:
    """判断这次写入是不是"测试环境写进了真实数据目录"。

    返回空串表示可以写；返回非空则是**拒绝的原因**。

    规则（只在设了 ``GWP_ROOT`` 时生效，所以对正常使用**零影响**）：

    * 目标路径落在 ``GWP_ROOT`` 之下 -> 允许（测试的正常沙箱）；
    * 目标路径落在 ``GWP_ROOT`` 之外 -> 拒绝，因为那多半是真实数据。

    这条规则简单、可判定、没有"我以为"。开发时为了调试而临时关掉它，
    可以设 ``GWP_ALLOW_REAL_WRITE=1`` —— 但要显式去做，
    不会再像上次那样悄无声息地覆盖掉用户的笔记。
    """
    import os

    root = os.environ.get("GWP_ROOT")
    if not root:
        return ""                      # 正常使用：不管
    if os.environ.get("GWP_ALLOW_REAL_WRITE"):
        return ""
    try:
        real_root = Path(root).resolve()
        resolved = Path(target).resolve()
    except OSError:
        return ""
    if resolved == real_root or real_root in resolved.parents:
        return ""
    # 记下调用栈：这类问题"猜不出来"，只有栈能说清是哪条路写进来的。
    # （实测：加了这个之后才定位到是哪个测试路径在写真实数据。）
    try:
        import traceback

        log.error(
            "阻止了一次「测试写真实数据」：%s\n%s",
            resolved,
            "".join(traceback.format_stack()[:-1]),
        )
    except Exception:  # noqa: BLE001
        pass
    return (f"当前处于测试环境（GWP_ROOT={real_root}），"
            f"而这次的目标在它之外。\n"
            "如果确实需要写入真实数据，请设环境变量 GWP_ALLOW_REAL_WRITE=1。")


class BookView(BaseView):
    """一个书目的资料管理页。"""

    open_document = pyqtSignal(Path)
    open_text = pyqtSignal(Path)          # 用内置纯文本查看器打开（JSON/源码等）
    back_requested = pyqtSignal()

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self.subject_name = ""
        self.book_name = ""
        #: 当前科目的类型（日记 / 校修课 / 自学课），决定标签与目录结构
        self.subject_type = C.DEFAULT_SUBJECT_TYPE
        self._tables: dict[str, FileTable] = {}
        self._worker: SimpleWorker | None = None
        self._ai_worker: AIWorker | None = None
        self._progress: SummaryProgressDialog | None = None
        self.clipboard = context.clipboard        # 全局文件剪贴板（复制/剪切/粘贴）
        #: 在软件内部进到了哪个文件夹（None = 正常按栏目显示）。
        #: 双击文件夹会进到这里，而不是弹出资源管理器。
        self._current_folder: Path | None = None

        # 标题栏空间有限：标题已经只留书名，这里再把按钮文案压到最省。
        # 每个按钮的完整含义都在 tooltip 里，鼠标一停就能看到。
        self.add_action("← 返回", self.back_requested.emit, tooltip="返回科目页，看这个科目的全部书目")
        # 在软件内部进了文件夹之后才出现的"退回上一层"
        self.btn_folder_up = self.add_action(
            "↑ 上一层", self.leave_folder,
            tooltip="退出当前文件夹，回到它所在的分类目录",
        )
        self.btn_folder_up.setVisible(False)
        # 文案只保留「导入文件」四个字：按钮多了以后"导入文件…"会被挤掉
        # 省略号也显得像没写完。具体导入到哪个位置放到悬浮提示里说明。
        self.btn_import = self.add_action(
            "导入文件", self.import_files, accent=True, tooltip="导入文件到当前位置"
        )
        # 校修课的「作业」栏目用「创建作业」取代「导入文件」：
        # 作业有条目信息（DDL、提交方式），直接丢文件是表达不了的。
        self.btn_homework = self.add_action(
            "创建作业", self.create_homework, accent=True,
            tooltip="新建一个作业：作业内容 + DDL + 提交方式",
        )
        self.btn_homework.setVisible(False)
        # 普通科目只有一个「生成总结」；日记类型有两套流程，按钮会切换（见 apply_subject_type）
        #
        # 注意：这个按钮**不再调用 AI 写正文**（需求变更：
        # "summary中板块，不需要你补充内容了，按照用户上传的文件来，
        #   不要AI识别文字了，直接插入图片或文件"）。
        # 现在是"把资料直接插进 summary"，AI 只负责可选的**页序混排**。
        self.btn_summary = self.add_action(
            "生成总结 PDF", self.generate_summary, accent=True,
            tooltip="把简介 + 笔记 + 易错题里的**全部资料合并成一个 PDF**"
                    "（每份资料转成页面图片）；旧的 Markdown 总结会被删掉，"
                    "中间产生的临时文件全部清理；可选让 AI 按主题重排页序",
        )
        self.btn_diary_thought = self.add_action(
            "思想总结", self.generate_diary_thought, accent=True,
            tooltip=f"读「{C.DIARY_MINE_FOLDER}」的全部日记，归纳成思想小结，"
                    f"写入「{C.DIARY_AI_SUMMARY_FOLDER}」",
        )
        self.btn_diary_book = self.add_action(
            "整理日记", self.generate_diary_book, accent=True,
            tooltip=(
                f"把「{C.DIARY_MINE_FOLDER}」的全部内容按日期合并成一篇格式统一的日记，"
                f"写入「{C.DIARY_AI_DIARY_FOLDER}」"
            ),
        )
        self.btn_diary_thought.setVisible(False)
        self.btn_diary_book.setVisible(False)

        # 单词书专用按钮（需求：只需要添加英文，其余由 AI 补齐）
        self.btn_word_add = self.add_action(
            "添加单词", self._add_word, accent=True,
            tooltip="只填英文单词或短语，中文释义 / 音标 / 例句由 AI 自动补齐",
        )
        self.btn_word_fill = self.add_action(
            "补齐释义", self._complete_words,
            tooltip="把还没有释义的单词卡逐张交给 AI 补齐",
        )
        self.btn_word_add.setVisible(False)
        self.btn_word_fill.setVisible(False)

        self.add_action("版本管理", self.open_backups, tooltip="查看 / 恢复上一版 summary")
        # 原来这里有一个独立的「合并资料到总结」按钮。
        # 需求变更后它和「生成总结」做的是同一件事（都是把资料直接插进 summary），
        # 两个按钮抢同一件事只会让人犹豫 —— 所以合并成一个，
        # 保留 `btn_merge` 这个名字指向同一个按钮，免得别处引用失效。
        self.btn_merge = self.btn_summary
        self.add_action("导出 PDF", self.export_pdf, tooltip="把当前文档导出为 PDF")
        self.add_action("打开目录", self.reveal_book, tooltip="在资源管理器里打开这个书目")

        # 资料概览开关：与其它操作按钮同样式（可勾选，勾选=已展开）
        self.btn_side_toggle = self.add_action(
            "资料概览",
            self.toggle_side_panel,
            checkable=True,
            tooltip="显示 / 收起右侧的「资料概览」面板",
        )

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter = self.splitter

        # 左侧：分类标签
        # 标签随**科目类型**变化（日记 / 校修课 / 自学课），因此这里先建好
        # 所有类型可能用到的表格，切科目时只重排标签，不重建控件。
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self._tables: dict[str, FileTable] = {}
        #: 每个标签页的"页面容器"：里面可以放文件表格，也可以放单词书这类专用控件。
        #: 为什么要多一层：QTabWidget 的一个 tab 只能装一个控件，
        #: 而"单词书"不是文件列表（它是可折叠卡片），必须换控件而不是换数据。
        self._pages: dict[str, QStackedWidget] = {}
        self._tab_defs: tuple = C.BOOK_TABS_SELF_STUDY
        for key, _title, _folder in _all_tab_definitions():
            table = FileTable()
            table.double_clicked_item.connect(self._on_item_double_clicked)
            table.context_requested.connect(self._on_item_context)
            table.submit_link_clicked.connect(self._on_submit_link)
            table.files_dropped.connect(self.handle_file_drop)
            table.itemSelectionChanged.connect(self._update_clipboard_buttons)
            self._tables[key] = table

            stack = QStackedWidget()
            stack.addWidget(table)                      # 第 0 页：文件表格
            if key == "wordbook":
                # 第 1 页：单词书（可折叠卡片）。默认显示单词书。
                self.wordbook_view = WordbookView(self.context)
                self.wordbook_view.status_message.connect(self.status_message.emit)
                stack.addWidget(self.wordbook_view)
                stack.setCurrentWidget(self.wordbook_view)
            self._pages[key] = stack
        # 作业栏目要多两列（DDL / 提交方式）
        self._tables["homework"].set_homework_mode(True)
        self._apply_tabs(self._tab_defs)
        self.tabs.currentChanged.connect(self._on_tab_changed)
        splitter.addWidget(self.tabs)

        # 右侧：详情面板
        self.side_panel = self._build_side_panel()
        splitter.addWidget(self.side_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setCollapsible(0, False)
        self.body.addWidget(splitter, 1)

        # 剪贴板操作条（放在标签页下面，比塞进顶部按钮区更顺手）
        self._build_clipboard_bar()
        self._install_clipboard_shortcuts()

        # 拖动分隔条时延迟保存面板宽度，避免频繁写配置
        self._side_width_timer = QTimer(self)
        self._side_width_timer.setSingleShot(True)
        self._side_width_timer.setInterval(700)
        self._side_width_timer.timeout.connect(self._save_side_width)

        self.setAcceptDrops(True)
        bus.subscribe(BOOK_CONTENT_CHANGED, lambda **_: self.refresh())
        bus.subscribe(SUMMARY_UPDATED, lambda **_: self.refresh())
        self._update_clipboard_buttons()

    # ==================================================================
    # 剪贴板操作条与快捷键
    # ==================================================================

    def _build_clipboard_bar(self) -> None:
        """在标签页下方放一条剪切/复制/粘贴操作条。"""
        bar = QWidget()
        bar.setObjectName("ClipboardBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(6)

        self.btn_cut = QPushButton("剪切")
        self.btn_cut.setToolTip("剪切选中的文件（Ctrl+X）")
        self.btn_cut.clicked.connect(lambda: self.copy_selection(mode=CUT))
        layout.addWidget(self.btn_cut)

        self.btn_copy = QPushButton("复制")
        self.btn_copy.setToolTip("复制选中的文件（Ctrl+C）")
        self.btn_copy.clicked.connect(lambda: self.copy_selection(mode=COPY))
        layout.addWidget(self.btn_copy)

        self.btn_paste = QPushButton("粘贴")
        self.btn_paste.setToolTip("粘贴到当前分类目录（Ctrl+V）")
        self.btn_paste.clicked.connect(self.paste_files)
        layout.addWidget(self.btn_paste)

        self.lbl_clipboard = QLabel("")
        self.lbl_clipboard.setObjectName("Muted")
        layout.addWidget(self.lbl_clipboard)

        # 拖拽落点提示：拖文件进来时显示"会传到哪个目录"
        # （以前完全没有反馈，用户不知道会落到哪一级 —— 这正是
        #  "传到上一目录"那个 bug 一直没被发现的原因之一）
        self.lbl_drop_hint = QLabel("")
        self.lbl_drop_hint.setObjectName("DropHint")
        self.lbl_drop_hint.setVisible(False)
        layout.addWidget(self.lbl_drop_hint)
        layout.addStretch(1)

        self.btn_clear_clipboard = QPushButton("清空剪贴板")
        self.btn_clear_clipboard.clicked.connect(self.clear_clipboard)
        self.btn_clear_clipboard.setVisible(False)      # 剪贴板非空时才显示
        layout.addWidget(self.btn_clear_clipboard)

        self.body.addWidget(bar)

    def _install_clipboard_shortcuts(self) -> None:
        """注册 Ctrl+C / Ctrl+X / Ctrl+V。

        用 WidgetWithChildrenShortcut，作用范围仅限本视图，
        避免和「编辑」菜单里针对文本的复制粘贴打架。
        """
        context = Qt.ShortcutContext.WidgetWithChildrenShortcut
        for keys, slot in (
            (QKeySequence.StandardKey.Copy, lambda: self.copy_selection(mode=COPY)),
            (QKeySequence.StandardKey.Cut, lambda: self.copy_selection(mode=CUT)),
            (QKeySequence.StandardKey.Paste, self.paste_files),
        ):
            shortcut = QShortcut(QKeySequence(keys), self)
            shortcut.setContext(context)
            shortcut.activated.connect(slot)

    def _on_tab_changed(self, _index: int) -> None:
        # 切栏目就退出"文件夹内浏览"，否则会看到另一个目录的内容
        if self._current_folder is not None:
            self._current_folder = None
            self._update_folder_hint()
            self.refresh()
        self._sync_homework_buttons()
        self._update_import_tooltip()
        self._refresh_summary_panel()
        self._update_clipboard_buttons()

    def _build_side_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setMinimumWidth(SIDE_MIN_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        # ---- 标题行（含折叠箭头）----
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        self.side_title = QLabel("资料概览")
        self.side_title.setObjectName("SectionTitle")
        header.addWidget(self.side_title)
        header.addStretch(1)
        self.btn_collapse = QToolButton()
        self.btn_collapse.setObjectName("CollapseToggle")
        self.btn_collapse.setText("▸")
        self.btn_collapse.setAutoRaise(True)
        self.btn_collapse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_collapse.clicked.connect(self.toggle_side_panel)
        header.addWidget(self.btn_collapse)
        layout.addLayout(header)
        self.side_title.mouseDoubleClickEvent = lambda _event: self.toggle_side_panel()

        # ---- 内容 ----
        self.side_content = QWidget()
        content = QVBoxLayout(self.side_content)
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(8)

        self.lbl_stats = QLabel("")
        self.lbl_stats.setWordWrap(True)
        content.addWidget(self.lbl_stats)

        self.lbl_summary_status = QLabel("")
        self.lbl_summary_status.setWordWrap(True)
        content.addWidget(self.lbl_summary_status)

        actions = QVBoxLayout()
        actions.setSpacing(6)
        self.btn_generate = QPushButton("生成 / 更新学习总结")
        self.btn_generate.setProperty("accent", True)
        self.btn_generate.clicked.connect(self.generate_summary)
        actions.addWidget(self.btn_generate)

        self.btn_preview_materials = QPushButton("预览将总结的资料")
        self.btn_preview_materials.clicked.connect(self.preview_materials)
        actions.addWidget(self.btn_preview_materials)

        self.btn_open_summary = QPushButton("查看总结文件")
        self.btn_open_summary.clicked.connect(self.open_summary)
        actions.addWidget(self.btn_open_summary)

        self.btn_restore = QPushButton("恢复上一版总结")
        self.btn_restore.clicked.connect(self.restore_latest_backup)
        actions.addWidget(self.btn_restore)

        self.btn_export = QPushButton("把总结导出为 PDF")
        self.btn_export.clicked.connect(self.export_pdf)
        actions.addWidget(self.btn_export)
        content.addLayout(actions)

        content.addWidget(QLabel("最近修改"))
        self.recent = QListWidget()
        self.recent.itemDoubleClicked.connect(self._on_recent_activated)
        content.addWidget(self.recent, 1)

        hint = QLabel(
            f"提示：{C.BOOK_FOLDER}（教材）与 {C.HOMEWORK_FOLDER}（作业）都不参与 AI 总结；"
            f"{C.NOTEBOOK_FOLDER}（笔记）与 {C.ERROR_FOLDER}（易错题）会参与。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("Muted")
        content.addWidget(hint)

        layout.addWidget(self.side_content, 1)

        # 折叠动画只用高度，宽度交给布局（不做宽度动画，避免与 splitter 互相钳制）
        self._content_anim = QPropertyAnimation(self.side_content, b"maximumHeight", self)
        self._content_anim.setDuration(170)
        self._content_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._content_anim.finished.connect(self._on_collapse_animation_finished)

        self._side_collapsed = False
        self._side_adjusting = False
        self._side_expanded_width_saved = 0
        return panel

    # ------------------------------------------------------------------
    # 资料概览的折叠
    # ------------------------------------------------------------------

    @property
    def side_collapsed(self) -> bool:
        return self._side_collapsed

    def toggle_side_panel(self) -> None:
        """折叠 / 展开右侧「资料概览」。"""
        self.set_side_collapsed(not self._side_collapsed)

    def set_side_collapsed(self, collapsed: bool, animate: bool = True, save: bool = True) -> None:
        collapsed = bool(collapsed)
        if collapsed == self._side_collapsed and animate:
            return
        self._side_collapsed = collapsed
        self._side_adjusting = True
        try:
            self._apply_side_state(collapsed, animate)
        finally:
            self._side_adjusting = False
        self._update_side_toggle_text()

        if save:
            try:
                self.context.config.set("ui.book_side_collapsed", collapsed)
                self.context.config.save()
            except Exception:  # noqa: BLE001 - 折叠状态存不下来也不该报错
                log.debug("保存折叠状态失败", exc_info=True)

    def _apply_side_state(self, collapsed: bool, animate: bool) -> None:
        """应用折叠状态。

        折叠时把面板**从 splitter 里移除**，而不是只压窄宽度。
        原因：面板内容有最小宽度，QSplitter 无法把它压到更窄，
        结果手柄停在中间、内容溢出到空白区域（曾经就是这个表现）。
        移除之后左侧列表拿到全部宽度，面板内容也不会再被绘制出来。
        """
        splitter = self.splitter
        content_height = max(120, self.side_content.sizeHint().height())
        full_width = self._side_expanded_width()

        if collapsed:
            # 记下列表占位，展开时按原比例恢复
            sizes = splitter.sizes()
            if len(sizes) == 2 and sizes[1] > SIDE_MIN_WIDTH:
                if 0 < sizes[1] < 4000:
                    self._side_expanded_width_saved = sizes[1]
            self._content_anim.stop()
            if animate and self.side_panel.isVisible():
                self.side_content.setMaximumHeight(self.side_content.height())
                self._content_anim.setStartValue(self.side_content.height())
                self._content_anim.setEndValue(0)
                self._content_anim.start()
            else:
                self._finish_collapse()
            return

        # ---- 展开 ----
        self._content_anim.stop()
        was_hidden = self.side_panel.parent() is None
        if was_hidden:
            self.splitter.insertWidget(1, self.side_panel)
        self.side_panel.setVisible(True)
        self.side_content.setVisible(True)
        self.side_content.setMaximumHeight(content_height)

        total = sum(splitter.sizes())
        if total <= 0:
            total = max(600, self.width())
        target = self._side_expanded_width_saved or full_width
        target = min(max(SIDE_MIN_WIDTH, target), max(SIDE_MIN_WIDTH, total - 360))
        splitter.setSizes([total - target, target])

    def _finish_collapse(self) -> None:
        """真正把面板移出布局。"""
        self._content_anim.stop()
        if not self._side_collapsed:
            return
        self.side_content.setVisible(True)          # 保留内部状态，展开时无需重建
        self.side_content.setMaximumHeight(16777215)
        self.side_panel.setParent(None)
        self.side_panel.setVisible(False)

    def _on_collapse_animation_finished(self) -> None:
        if self._side_collapsed:
            self._finish_collapse()

    def _update_side_toggle_text(self) -> None:
        collapsed = self._side_collapsed
        self.btn_collapse.setText("▸" if collapsed else "▾")
        self.btn_collapse.setToolTip(
            "展开资料概览" if collapsed else "折叠资料概览（双击标题文字也可以）"
        )
        if hasattr(self, "btn_side_toggle"):
            self.btn_side_toggle.setChecked(not collapsed)
            self.btn_side_toggle.setToolTip(
                "收起右侧「资料概览」" if not collapsed else "显示右侧「资料概览」"
            )

    def _side_expanded_width(self) -> int:
        """展开时的宽度：优先用配置里的值，其次按窗口比例估算。"""
        configured = int(self.context.config.get("ui.book_side_width", 0) or 0)
        if configured > 0:
            return configured
        width = self.splitter.width() or self.width()
        if width > 700:
            return max(SIDE_MIN_WIDTH, int(width * 0.36))
        return SIDE_MIN_WIDTH

    def _restore_side_state(self) -> None:
        """按配置恢复折叠状态（不播放动画、不写回配置）。"""
        self._update_side_toggle_text()
        collapsed = bool(self.context.config.get("ui.book_side_collapsed", True))
        self.set_side_collapsed(collapsed, animate=False, save=False)

    def _remember_side_width(self) -> None:
        """记住用户拖动后的面板宽度，展开时用它恢复。

        动画进行中或程序化调整期间不记录，避免把中间态当成用户偏好。
        宽度会延迟写盘（拖动过程中每秒会有很多次 resize），避免频繁 IO。
        """
        if self._side_collapsed or self._side_adjusting:
            return
        if self._content_anim.state() == QPropertyAnimation.State.Running:
            return
        if self.side_panel.parent() is None:
            return
        width = self.side_panel.width()
        if width < SIDE_MIN_WIDTH or width > 4000:
            return
        self._side_expanded_width_saved = width
        self._side_width_timer.start()

    def _save_side_width(self) -> None:
        """把用户拖出来的面板宽度写入配置（由定时器延迟触发）。"""
        if self._side_expanded_width_saved <= 0:
            return
        try:
            self.context.config.set("ui.book_side_width", int(self._side_expanded_width_saved))
            self.context.config.save()
        except Exception:  # noqa: BLE001
            log.debug("保存面板宽度失败", exc_info=True)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        super().resizeEvent(event)
        self._remember_side_width()

    # ==================================================================
    # 加载
    # ==================================================================

    def _apply_tabs(self, tab_defs: tuple) -> None:
        """按标签定义重排标签页（控件复用，只换位置与文案）。

        ``QTabWidget`` 没有"重排已有 tab"的接口，因此这里记录当前选中项后
        逐个 removeTab / addTab；表格控件本身不重建，信号连接与选择状态都保留。
        """
        if tab_defs == self._tab_defs and self.tabs.count() == len(tab_defs):
            return
        keep = self._current_tab_key()
        self._tab_defs = tuple(tab_defs)
        blocker = self.tabs.blockSignals(True)
        try:
            while self.tabs.count():
                self.tabs.removeTab(0)
            for key, title, _folder in self._tab_defs:
                page = self._pages.get(key)
                if page is not None:
                    self.tabs.addTab(page, title)
        finally:
            self.tabs.blockSignals(blocker)
        self._select_tab_key(keep or "summary")

    def _tab_label(self, key: str, title: str, count: int | None) -> str:
        """标签文字：把条目数量接在栏目名后面。

        原来这些数字挤在标题栏那行浅灰字里，既占地方又把右侧按钮挤到截断；
        放到标签上更直观（"哪个栏目有几项"一眼就有），也顺带腾出了按钮空间。
        数量为 0 时不显示，避免一排 ``0`` 造成视觉噪声。
        """
        if count is None or count <= 0:
            return title
        return f"{title} {count}"

    def _update_tab_labels(self, book: Book) -> None:
        """按当前书目刷新每个标签上的数量。"""
        counts = dict(book.item_counts or {})
        counts["root"] = len(self.context.library.list_items(book))
        blocker = self.tabs.blockSignals(True)
        try:
            for index, (key, title, _folder) in enumerate(self._tab_defs):
                if index >= self.tabs.count():
                    break
                self.tabs.setTabText(index, self._tab_label(key, title, counts.get(key, 0)))
        finally:
            self.tabs.blockSignals(blocker)

    def _select_tab_key(self, key: str) -> None:
        for index, (tab_key, _title, _folder) in enumerate(self._tab_defs):
            if tab_key == key:
                self.tabs.setCurrentIndex(index)
                return
        if self.tabs.count():
            self.tabs.setCurrentIndex(0)

    def _current_tab_key(self) -> str:
        index = self.tabs.currentIndex()
        if 0 <= index < len(self._tab_defs):
            return self._tab_defs[index][0]
        return self._tab_defs[0][0] if self._tab_defs else "summary"

    # ==================================================================

    def show_book(self, subject_name: str, book_name: str) -> None:
        self.subject_name = subject_name
        self.book_name = book_name
        self._ensure_standard_folders()
        self.refresh()

    def _ensure_standard_folders(self) -> None:
        """补齐本书缺失的标准目录（例如旧版本创建的书还没有 homework）。

        目录清单按**科目类型**决定：日记科目只会补
        ``AI summary / AI diary / my diary / else diary``，
        不会凭空长出教材、易错题这些不属于它的目录。

        只在真正打开书目时补建，因此**不会在启动扫描时改动你的数据目录**；
        补建是幂等的，失败也只记日志、不打断使用。
        """
        book = self.book()
        if book is None:
            return
        subject = self.context.library.subject(self.subject_name)
        kind = subject.subject_type if subject is not None else C.DEFAULT_SUBJECT_TYPE
        missing = [
            key for key in C.template_dirs_for_type(kind)
            if not (book.path / key).is_dir()
        ]
        if not missing:
            return
        try:
            for key in missing:
                (book.path / key).mkdir(parents=True, exist_ok=True)
            log.info(
                "已为 %s/%s（%s）补齐目录：%s",
                self.subject_name,
                self.book_name,
                kind,
                missing,
            )
            self.context.library.invalidate()
        except OSError:
            log.warning("补齐标准目录失败：%s", book.path, exc_info=True)

    def on_shown(self) -> None:
        self.refresh()

    def book(self) -> Book | None:
        return self.context.library.book(self.subject_name, self.book_name)

    def refresh(self) -> None:
        book = self.book()
        if book is None:
            self._current_folder = None
            self.set_title("书目不存在", "它可能已经被删除、重命名或移动")
            for table in self._tables.values():
                table.set_items([])
            return

        # 书目被删/换掉，或者当前文件夹已不存在 —— 退出"文件夹内浏览"
        if self._current_folder is not None and not self._current_folder.is_dir():
            self._current_folder = None

        # 标签与按钮随科目类型变化（日记 / 校修课 / 自学课）
        subject = self.context.library.subject(self.subject_name)
        subject_type = subject.subject_type if subject is not None else C.DEFAULT_SUBJECT_TYPE
        self.apply_subject_type(subject_type)

        # 标题区只留书目名：面包屑与统计都搬到标签页上去了 ——
        # 原来那一行长文字既占地方，又把右侧按钮挤成「返回」「导入文」这种截断样。
        self.set_title(book.title)

        items = self.context.library.list_items(book)
        by_name = {item.name: item for item in items}
        # 「简介」与「AI 总结」只存在于普通科目；日记类型没有这两个标签
        intro_table = self._tables.get("intro")
        if intro_table is not None:
            intro_table.set_items(
                [by_name[C.INTRO_FILE]] if C.INTRO_FILE in by_name else []
            )
        summary_table = self._tables.get("summary")
        if summary_table is not None:
            summary_table.set_items([item for item in items if item.is_summary])
        self._tables["root"].set_items(items)
        # 其余标签按各自登记的目录填充（日记类型的目录名与普通类型不同）
        for key, _title, folder in self._tab_defs:
            if not folder or key not in self._tables:
                continue
            self._tables[key].set_items(self.context.library.list_folder(book.path / folder))

        # 作业栏目：额外挂上每个作业的 DDL / 提交方式
        self._refresh_homework_table(book)
        # 单词书栏目：卡片列表来自 wordbook/ 目录
        self._refresh_wordbook()
        # 每个栏目显示自己的条目数
        self._update_tab_labels(book)

        self._refresh_summary_panel()
        self._refresh_recent(book)
        self._update_import_tooltip()
        self._restore_side_state()
        self._update_folder_hint()

        # **重新画出"当前所在文件夹"的内容**（用户报障：删除文件后会跳回上一层）。
        #
        # 上面的代码只填了**各标签的根目录**；如果用户是靠 enter_folder()
        # 进到某个子文件夹里（作业、资料夹…），那么刷新后表格里就变成了
        # 根目录的列表 —— 看起来就是"被弹回上一层"。
        # 注意 `_current_folder` 与标题其实一直是对的，只有表格内容错了，
        # 所以这个 bug 表现为"位置没变、但东西变了"，很容易被当成"刷新错了"。
        #
        # 凡是"在某个目录里做的操作"（删除、重命名、导入、拖拽、新建文件夹）
        # 都要走 refresh()，所以修在这里能一次覆盖全部操作。
        if self._current_folder is not None:
            self._render_current_tab()

    def _homework_dir(self) -> Path | None:
        """当前书目的作业目录。"""
        book = self.book()
        if book is None:
            return None
        return book.path / C.HOMEWORK_FOLDER

    # ==================================================================
    # 单词书（需求：新增单词书栏目 + 可折叠单词卡 + 只填英文自动补齐）
    # ==================================================================

    def _refresh_wordbook(self) -> None:
        """把当前书目的单词卡交给单词书视图渲染。"""
        view = getattr(self, "wordbook_view", None)
        if view is None:
            return
        book = self.book()
        if book is None:
            return
        view.set_target(self.subject_name, book.name)
        view.refresh()

    def _wordbook_visible(self) -> bool:
        """当前是不是停在单词书标签上（按钮动作据此决定要不要切过去）。"""
        return self._current_tab_key() == "wordbook"

    def _add_word(self) -> None:
        """顶栏「添加单词」：在单词书页加一张卡。"""
        view = getattr(self, "wordbook_view", None)
        if view is None:
            return
        if not self._wordbook_visible():
            self._select_tab_key("wordbook")
        view.add_word()

    def _complete_words(self) -> None:
        """顶栏「补齐释义」：把还没有内容的卡片逐张补齐。"""
        view = getattr(self, "wordbook_view", None)
        if view is None:
            return
        if not self._wordbook_visible():
            self._select_tab_key("wordbook")
        view.complete_all()

    def _refresh_homework_table(self, book: Book) -> None:
        """给作业表格挂上作业元信息，并按当前标签决定按钮显隐。"""
        table = self._tables.get("homework")
        if table is None:
            return
        mapping: dict[str, object] = {}
        for homework in hw.list_homework(book.path):
            mapping[str(homework.path)] = homework
        table.set_homework_map(mapping)          # type: ignore[arg-type]
        # 重新渲染一遍，DDL 列才会填上；这里用"一个作业一行"的列表，
        # 不能把作业内部的 homework.json / 内容文件也铺出来。
        table.set_items(self.context.library.list_homework_items(book))
        self._sync_homework_buttons()

    def _sync_homework_buttons(self) -> None:
        """按**当前位置**决定顶栏显示哪些按钮。

        规则（用户报障后定下来的）：

        * **作业栏目的根目录** → 显示「创建作业」，不显示「导入文件」。
          作业是**校修课的作业栏目**专属：自学课的同一目录叫「练习」，
          仍然按普通文件夹用，不做作业管理。
        * **已经进了某个作业（或某个子文件夹）里** → 只显示「导入文件」。
          原因：在 `homework/2.4 作业` 里面再点「创建作业」是**不合语境**的
          （新作业只能建在作业栏目根目录）；而且这里正是最需要上传附件的地方，
          原来却既没有「创建作业」的合理语义、又没有导入入口，
          用户只能靠拖拽（截图反馈："作业栏目无上传文件按钮"）。
        * **单词书栏目** → 换成它自己的两个按钮（添加单词 / 补齐释义）。
          这一页不是文件列表，导入文件、创建作业在这里都没有意义。
        """
        key = self._current_tab_key()
        is_wordbook = key == "wordbook"
        is_homework_tab = key == "homework"
        can_manage = (
            is_homework_tab
            and self.subject_type == C.SUBJECT_SCHOOL
            and self.book() is not None
        )
        # 在子文件夹里时，"新建作业"没有意义
        at_root = self._current_folder is None

        self.btn_homework.setVisible(can_manage and at_root)
        # 单词书页不显示"导入文件"（它的内容是卡片，不是用户导入的文件）
        self.btn_import.setVisible(not is_wordbook and not (can_manage and at_root))
        # 单词书专用按钮
        self.btn_word_add.setVisible(is_wordbook)
        self.btn_word_fill.setVisible(is_wordbook)
        # 按钮的显隐变了，锁定的宽度要重算（否则会留着上一个页面的宽度）
        lock = getattr(self, "lock_action_widths", None)
        if callable(lock):
            lock()

    def _refresh_summary_panel(self) -> None:
        book = self.book()
        if book is None:
            return
        summarizer = self.context.summarizer
        stats = summarizer.stats(book)
        # 按当前类型的标签来组织：既显示"参与总结"的，也显示"不参与"的
        # （日记类型只有两个来源，且都不叫 notebook）
        sources = summarizer.source_spec(self.subject_type)
        source_labels = [label for label, _ in sources if label != "intro"]
        involved = " · ".join(
            f"{self._source_title(label)} {stats.get(label, 0)}" for label in source_labels
        )
        involved_dirs = {
            Path(relative).name for _label, relative in sources
        }
        excluded = [
            (title, folder) for _key, title, folder in self._tab_defs
            if folder and folder not in involved_dirs
        ]
        excluded_text = " · ".join(
            f"{title} {stats.get(folder, 0)}" for title, folder in excluded
        )

        lines = [f"<b>参与总结</b>：简介 {stats.get('intro', 0)}"]
        if involved:
            lines[0] += f" · {involved}"
        if excluded_text:
            lines.append(f"<b>不参与总结</b>：{excluded_text}")
        lines.append(f"<b>书目位置</b>：{book.path}")
        self.lbl_stats.setText("<br>".join(lines))
        backups = self.context.backups.list_backups(self.subject_name, self.book_name)
        backup_text = f"有 {len(backups)} 个历史版本（最近：{backups[0].created_label}）" if backups else "暂无历史版本"
        self.lbl_summary_status.setText(
            f"<b>总结文件</b>：{book.summary_name}<br>"
            f"<b>状态</b>：{'已生成' if book.has_summary else '尚未生成'}"
            f"（{book.summary_label}）<br>"
            f"<b>版本</b>：{backup_text}"
        )
        self.btn_open_summary.setEnabled(book.has_summary)
        self.btn_restore.setEnabled(bool(backups))
        self.btn_export.setEnabled(book.has_summary)

    def _source_title(self, label: str) -> str:
        """把来源标签换成当前类型的界面用词（例如 homework -> 练习）。"""
        for _key, title, folder in self._tab_defs:
            if folder and (folder == label or folder.replace(" ", "-") == label):
                return title
        return label

    def _refresh_recent(self, book: Book) -> None:
        self.recent.clear()
        candidates: list[BookItem] = []
        for key in (C.NOTEBOOK_FOLDER, C.HOMEWORK_FOLDER, C.ERROR_FOLDER):
            # **递归**：这里要的是所有文件按修改时间排，不关心在哪一层。
            # 这是唯一需要 recursive=True 的调用点（见 store.list_folder 的说明）。
            candidates.extend(
                self.context.library.list_folder(book.path / key, recursive=True)
            )
        for item in (book.summary_path, book.intro_path):
            if item is not None and item.exists():
                stat = item.stat()
                candidates.append(
                    BookItem(name=item.name, path=item, is_dir=False, size=stat.st_size, mtime=stat.st_mtime)
                )
        candidates.sort(key=lambda item: item.mtime, reverse=True)
        for item in candidates[:12]:
            row = QListWidgetItem(f"{item.name}   ·   {item.mtime_label}")
            row.setData(Qt.ItemDataRole.UserRole, str(item.path))
            row.setToolTip(str(item.path))
            self.recent.addItem(row)

    def _on_recent_activated(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.open_document.emit(Path(path))

    # ==================================================================
    # 条目操作
    # ==================================================================

    def _target_folder(self) -> Path | None:
        """当前分类对应的真实目录（用于**新建**条目）。

        直接用标签定义里登记的目录名，因此日记类型的
        ``my diary`` / ``else diary`` 等也能正常导入。
        虚拟栏目（AI 总结 / 简介 / 全部条目）返回 ``None``。
        """
        book = self.book()
        if book is None:
            return None
        key = self._current_tab_key()
        for tab_key, _title, folder in self._tab_defs:
            if tab_key == key and folder:
                return book.path / folder
        return None

    def drop_target_folder(self) -> Path | None:
        """拖拽上传 / 导入的**真正落点**。

        和 :meth:`_target_folder` 的区别很关键（这是一个真实 bug 的修复）：

        * ``_target_folder()`` 只看标签登记，**完全不管你现在浏览到哪一层**。
          于是"进入 `others/第一章` 之后拖文件进来"，文件会被丢到
          ``others``（也就是**上一级目录**）——用户反馈的正是这个现象。
        * 这里改成：**正在浏览某个文件夹时，落点就是那个文件夹**；
          只有在栏目根目录时才回退到标签登记的目录。

        作业栏目有个额外的便利：在**某个作业那一行**上松手，
        文件会进那个作业的文件夹（而不是作业根目录），少一步手工移动。
        """
        book = self.book()
        if book is None:
            return None
        if self._current_folder is not None:
            return self._current_folder
        return self._target_folder() or (book.path / C.NOTEBOOK_FOLDER)

    def _row_folder_at(self, pos) -> Path | None:
        """拖拽落点正好在某个文件夹那一行上时，返回那个文件夹。

        用途：把文件**直接拖进某个作业 / 子文件夹**，
        省掉"先传到当前目录、再手工移进去"这一步。
        返回 ``None`` 表示落点不在文件夹行上，按当前浏览的目录处理。
        """
        table = self._current_table()
        row = table.row_at(pos)
        if row < 0:
            return None
        item = table.item_at(row)
        if item is not None and item.is_dir:
            return item.path
        return None

    def _on_item_double_clicked(self, item: BookItem) -> None:
        if item is None:
            return
        if item.is_dir:
            # 需求：**不要弹资源管理器**，在软件内部进到文件夹里看
            self.enter_folder(item.path)
            return
        self.open_file(item.path)

    # ==================================================================
    # 文件夹内浏览（不弹资源管理器）
    # ==================================================================

    def _folder_root(self) -> Path | None:
        """当前栏目对应的目录（用来判断"退回上一层"能退到哪）。"""
        return self._target_folder()

    def enter_folder(self, folder: Path) -> None:
        """在**软件内部**进入一个文件夹，只列出它里面的内容。"""
        folder = Path(folder)
        if not folder.is_dir():
            common.warn(self, f"文件夹不存在：\n{folder}", "无法打开")
            self.refresh()
            return
        self._current_folder = folder
        self._render_current_tab()
        self.status_message.emit(f"已进入文件夹：{folder.name}")

    def leave_folder(self) -> None:
        """从当前文件夹退回它所在的分类目录。"""
        current = self._current_folder
        if current is None:
            return
        root = self._folder_root()
        parent = current.parent
        # 退到栏目根目录（或更外一层）就结束内部浏览
        if root is None or parent == root or root not in parent.parents:
            self._current_folder = None
        else:
            self._current_folder = parent
        self._render_current_tab()
        self.status_message.emit("已返回上一层")

    def _render_current_tab(self) -> None:
        """按当前的"文件夹内浏览"状态重画当前栏目。"""
        table = self._tables.get(self._current_tab_key())
        book = self.book()
        if table is None or book is None:
            return
        folder = self._current_folder
        if folder is None:
            self.refresh()
            return
        key = self._current_tab_key()
        if key == "homework" and folder == book.path / C.HOMEWORK_FOLDER:
            # 作业**栏目根目录**：列结构不同（有 DDL / 提交方式），
            # 而且必须是"一个作业一行"，所以走专门的列表函数。
            table.set_items(self.context.library.list_homework_items(book))
        else:
            # 其它情况（含**进了某个作业里面**）一律列该目录的真实内容。
            #
            # 这里曾经是一个 bug：作业栏目无论在哪一层都用
            # ``list_homework_items`` 再按 ``path.parent == folder`` 过滤，
            # 而那个函数只列作业根目录下第一层的作业文件夹 ——
            # 进了 ``homework/2.4 作业`` 之后，里面的 md、图片、homework.json
            # 都不是"作业条目"，过滤结果恒为空，界面一片空白
            # （用户反馈："本地文件夹有内容 但是软件内不显示"）。
            items = [
                item for item in self.context.library.list_folder(folder)
                if item.path.parent == folder
            ]
            table.set_items(items)
        self._update_folder_hint()

    def _update_folder_hint(self) -> None:
        """在标题上提示"正在文件夹里看"，并保持"返回上一层"按钮可用。

        路径用 :meth:`_folder_label` 转成 ``homework / 2.4 作业`` 这种写法 ——
        直接插 Path 会显示 Windows 的反斜杠（``homework\\2.4 作业``），
        和状态栏、拖拽提示里的说法不一致，用户看到两套写法会犯迷糊。
        """
        book = self.book()
        if book is None:
            return
        folder = self._current_folder
        if folder is None:
            self.set_title(book.title)
        else:
            self.set_title(f"{book.title} › {self._folder_label(folder)}")
        button = getattr(self, "btn_folder_up", None)
        if button is not None:
            button.setVisible(folder is not None)
        # 按钮的显示取决于"在不在子文件夹里"，所以这里必须跟着同步。
        # （enter_folder / leave_folder / refresh 都会走到这里，
        #   放在这一个地方就不会出现"进了作业文件夹还是显示创建作业"的问题。）
        self._sync_homework_buttons()

    def open_file(self, path: Path) -> None:
        """在软件内部打开一个文件。

        * Markdown / 纯文本：走内置文档视图；
        * **JSON：用 VSCode 打开**（找不到 VSCode 时退回内置文本查看器）；
        * 其它类型：交给系统默认程序（图片、PDF 等本来也不是文本）。
        """
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix in (".md", ".markdown", ".txt"):
            self.open_document.emit(path)
            return
        if suffix in (".json", ".jsonc", ".json5"):
            if self.open_in_vscode(path):
                return
            # 没有 VSCode：退回内置查看器，别弹外部程序
            self.open_text.emit(path)
            return
        if suffix in C.TEXT_EXTENSIONS:
            self.open_text.emit(path)
            return
        from gwp.services import file_ops

        file_ops.open_with_system(path)

    def open_in_vscode(self, path: Path) -> bool:
        """用 VSCode 打开文件。找不到 VSCode 返回 False（由调用方兜底）。"""
        from gwp.services import file_ops

        if not file_ops.open_in_vscode(path):
            return False
        self.status_message.emit(f"已用 VSCode 打开：{path.name}")
        return True

    def _on_blank_context(self, global_pos: QPoint) -> None:
        """在列表**空白处**右键时的菜单：只放"目录级"动作。

        为什么单独做一个：空白处点不到任何条目，所以这里能做的只有
        "往当前这一层放东西" —— 新建文件夹 / 新建 Markdown / 上传 / 粘贴。
        这跟资源管理器的习惯一致（用户报障："右键新建文件夹存在异常"，
        根因之一就是空白处右键原来**什么都不弹**）。
        """
        can_new = self._creation_dir() is not None
        hint = "" if can_new else "（当前栏目不支持）"
        actions: list = [
            (f"新建文件夹…{hint}",
             (lambda: self.create_folder()) if can_new else None,
             can_new),
            (f"新建 Markdown…{hint}",
             (lambda: self.create_markdown()) if can_new else None,
             can_new),
            ("上传文件到当前目录…",
             (lambda: self.upload_files()) if can_new else None,
             can_new),
        ]
        if not self.clipboard.is_empty:
            actions.append(("粘贴到当前目录", self.paste_files))
        else:
            actions.append(("粘贴到当前目录（剪贴板为空）", None, False))
        actions.extend([
            None,
            ("刷新", self.refresh),
        ])
        menu = common_menu(self, actions)
        menu.exec(global_pos)

    def _on_item_context(self, item: BookItem, global_pos: QPoint) -> None:
        if item is None:
            # **空白处右键**：菜单只提供"在这一层新建 / 粘贴"这类目录级动作。
            self._on_blank_context(global_pos)
            return
        actions: list = [("打开", lambda: self._on_item_double_clicked(item))]
        suffix = item.path.suffix.lower()
        if suffix in (".md", ".markdown", ".txt"):
            actions.append(("在编辑器中打开", lambda: self.open_document.emit(item.path)))
        elif suffix in C.JSON_EXTENSIONS or suffix in C.CODE_EXTENSIONS:
            # 文本/配置文件：软件内部看 + 用 VSCode 改
            actions.append(("在软件内查看", lambda: self._on_item_double_clicked(item)))
            actions.append(("用 VSCode 打开", lambda: self.open_in_vscode(item.path)))
        actions.extend(
            [
                ("用系统默认程序打开", lambda: file_ops.open_with_system(item.path)),
                ("在资源管理器中显示", lambda: file_ops.reveal_in_explorer(item.path)),
            ]
        )
        # 作业专属动作：只有带作业信息的文件夹才显示
        homework = (
            hw.load(item.path)
            if (item.is_dir and self._current_tab_key() == "homework")
            else None
        )
        if homework is not None:
            actions.append(None)
            actions.append(("编辑作业…", lambda: self.edit_homework(item)))
            actions.append(
                (
                    f"打开提交网址" if homework.submit_url else "打开提交网址（未填写）",
                    (lambda: self._on_submit_link(item.path)) if homework.submit_url else None,
                    bool(homework.submit_url),
                )
            )
            actions.append(
                (
                    "复制提交网址",
                    (lambda: self._copy_submit_url(homework.submit_url))
                    if homework.submit_url
                    else None,
                    bool(homework.submit_url),
                )
            )
        # 软件自己的内部文件（如作业的 homework.json）：列出但不许动。
        # 改它的名字或删掉它，会让这条作业丢掉 DDL 与提交网址，
        # 而用户完全不会意识到这两者有关联 —— 所以直接不给这些入口。
        if item.is_meta:
            actions.extend(
                [
                    None,
                    ("查看内容（只读）", lambda: self.open_file(item.path)),
                    ("在资源管理器中显示", lambda: file_ops.reveal_in_explorer(item.path)),
                    None,
                    (
                        "这是软件的作业信息文件，只读、不可改动",
                        None,
                        False,
                    ),
                ]
            )
            menu = common_menu(self, actions)
            menu.exec(global_pos)
            return

        # 新建动作的落点：右键文件夹时建在**该文件夹里面**（方便「其它文件」下分类），
        # 右键普通文件时建在它**旁边**（所以要把 item 也传进去）。
        #
        # 能不能建由 `_creation_dir` 判断；**不能建时菜单项直接禁用**，
        # 而不是让用户点了再吃一句"请先进入某个书目…"——
        # 用户明明就在书目里，那句话既没解释清楚也没给出下一步。
        _new_inside = item.path if item.is_dir else None
        _can_new = self._creation_dir(inside=_new_inside, item=item) is not None
        _new_hint = "" if _can_new else "（先进入一个书目）"
        actions.extend(
            [
                None,
                (f"新建文件夹…{_new_hint}",
                 lambda: self.create_folder(inside=item if item.is_dir else None,
                                            item=item),
                 _can_new),
                (f"新建 Markdown…{_new_hint}",
                 lambda: self.create_markdown(inside=item if item.is_dir else None,
                                              item=item),
                 _can_new),
                # 拖拽之外也给一个明确入口（有些人不习惯拖，或触控板不好拖）
                (f"上传文件到「{item.name}」…" if item.is_dir else "上传文件到当前目录…",
                 lambda: self.upload_files(inside=item.path if item.is_dir else None)),
                (f"提取「{item.name}」里的图片…" if item.is_dir
                 else "提取本目录图片为 Markdown…",
                 lambda: self.extract_images(inside=item.path if item.is_dir else None)),
                None,
                ("剪切", lambda: self.copy_selection(mode=CUT)),
                ("复制", lambda: self.copy_selection(mode=COPY)),
                ("粘贴到此处" if item.is_dir else "粘贴到当前目录", self.paste_files),
                None,
                # 作业的"重命名"和普通文件夹不同：它会一并同步
                # homework.json 里的名字与内容 Markdown 的文件名
                # （见 _rename_item 的说明）。菜单文案把这个区别说出来。
                (
                    "重命名作业…（同时改文件夹与作业信息）"
                    if hw.load(item.path) is not None else "重命名…",
                    lambda: self._rename_item(item),
                ),
                ("复制到…", lambda: self._copy_item(item)),
                None,
                ("删除…", lambda: self._delete_item(item)),
            ]
        )
        menu = common_menu(self, actions)
        menu.exec(global_pos)

    def _copy_submit_url(self, url: str) -> None:
        """把提交网址复制到系统剪贴板。"""
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(url)
        self.status_message.emit("提交网址已复制到剪贴板")

    # ==================================================================
    # 作业（校修课的「作业」栏目）
    # ==================================================================

    def create_homework(self) -> None:
        """新建作业：作业内容 + DDL + 提交方式。"""
        folder = self._homework_dir()
        book = self.book()
        if folder is None or book is None:
            return
        from gwp.ui.dialogs.homework_dialog import HomeworkDialog

        # 提交网址默认沿用这本书**上一份作业**的（需求："避免用户每次输入"）。
        # 取不到就留空，不编造。
        default_url = ""
        try:
            default_url = hw.last_submit_url(book.path)
        except Exception:  # noqa: BLE001 - 默认值失败不该挡住新建
            log.debug("读取上次提交网址失败", exc_info=True)
        dialog = HomeworkDialog(self, folder=folder / "（作业名）",
                                default_url=default_url)
        if not dialog.exec():
            return
        name = dialog.folder_name
        target = folder / name
        if target.exists():
            common.warn(
                self,
                f"「{name}」已经存在。\n\n如果是同一份作业，请用右键「编辑作业…」修改。",
                "无法新建作业",
            )
            return
        try:
            hw.create(
                target,
                content=dialog.content_text,
                due=dialog.due_text,
                submit_url=dialog.submit_url,
            )
        except OSError as exc:
            common.error(self, f"创建作业失败：{exc}", "创建作业")
            return
        self.refresh()
        self.status_message.emit(f"已创建作业：{name}")

    def edit_homework(self, item: BookItem) -> None:
        """编辑作业：**改名** + DDL / 提交方式 / 内容。

        改名要**先**做（用户报障："更改作业名称功能异常"）：
        之前的实现只保存了 DDL / 提交方式 / 内容，
        **完全没有读作业名** —— 即使对话框里能改，点保存也不会生效。

        先改名再写其余字段：改名会移动文件夹并回滚失败，
        摸清新位置之后再把其它字段写进去，路径不会错。
        """
        if item is None:
            return
        existing = hw.load(item.path)
        if existing is None:
            common.warn(self, "这个文件夹不是作业（没有作业信息文件）。", "无法编辑")
            return
        from gwp.ui.dialogs.homework_dialog import HomeworkDialog

        dialog = HomeworkDialog(self, homework=existing)
        if not dialog.exec():
            return

        renamed = False
        if dialog.name_changed:
            log.info("编辑作业：准备改名 %r -> %r（%s）",
                     existing.name, dialog.input_name.text(), existing.path)
            try:
                existing = hw.rename(existing, dialog.input_name.text())
                renamed = True
                log.info("编辑作业：改名完成 -> %s", existing.path)
            except DataError as exc:
                log.info("编辑作业：改名被拒（重名）：%s", exc)
                common.warn(self, str(exc), "无法改名")
                return
            except OSError as exc:
                log.exception("编辑作业：改名失败")
                common.error(self, f"重命名作业失败：{exc}", "编辑作业")
                return
        else:
            log.info("编辑作业：名称未变，只保存其它字段（%s）", existing.name)

        existing.content = dialog.content_text
        existing.due = dialog.due_text
        existing.submit_url = dialog.submit_url
        try:
            hw.save(existing)
            # 内容变了就同步到 Markdown（文件已存在则不动，避免覆盖用户后续编辑）
            hw.write_content(existing)
            log.info("编辑作业：已保存 %s（name=%s）", existing.path, existing.name)
        except OSError as exc:
            log.exception("编辑作业：保存失败")
            common.error(self, f"保存作业失败：{exc}", "编辑作业")
            return
        self.refresh()
        self.status_message.emit(
            f"已重命名并保存作业：{existing.name}" if renamed
            else f"已保存作业：{existing.name}"
        )

    def open_submit_url(self, folder: Path) -> None:
        """在系统浏览器里打开作业的提交网址。"""
        self._on_submit_link(folder, "")

    def _on_submit_link(self, folder: Path, url: str = "") -> None:
        """点「提交作业」按钮：**先弹框**显示作业文件夹路径，再让用户决定是否跳转。

        为什么不一键直达：提交网址在教务系统，一点就跳走；
        用户常要先确认"这份作业放在哪个文件夹、附件放齐了没有"。
        """
        folder = Path(folder)
        homework = hw.load(folder)
        target = url or (homework.submit_url if homework is not None else "")
        if not target and homework is None:
            common.info(
                self,
                f"这个文件夹不是作业（没有作业信息文件）：\n{folder}",
                "无法提交",
            )
            return

        from gwp.ui.dialogs.submit_dialog import SubmitHomeworkDialog

        dialog = SubmitHomeworkDialog(self, homework=homework, folder=folder, url=target)
        accepted = dialog.exec()
        choice = dialog.choice
        del accepted
        if choice != "submit" or not target:
            return
        from gwp.services import shell_ops

        if not shell_ops.open_url(target):
            common.warn(
                self,
                f"无法打开网址：\n{target}\n\n可以手动复制到浏览器。",
                "打开失败",
            )

    # ==================================================================
    # 新建：文件夹 / Markdown
    # ==================================================================

    def _creation_dir(self, inside: Path | None = None,
                      item: BookItem | None = None) -> Path | None:
        """决定"新建"动作的目标目录。

        优先级（**从最具体到最笼统**）：

        1. ``inside`` —— 右键点在某个**文件夹**上，就建在**那个文件夹里面**；
        2. ``_current_folder`` —— 正在浏览某个文件夹时，就建在**当前这一层**；
        3. ``item`` 所在的那一层 —— 右键点在普通文件上，就建在它**旁边**；
        4. 当前标签登记的目录（例如「笔记」-> ``notebook``）；
        5. 虚拟栏目（AI 总结 / 简介 / 全部条目）走兜底：``notebook``。

        第 2、3、5 条是**"右键新建文件夹存在异常"的修复**。原来这里只看第 4 条：

        * 进入 ``notebook/第一章`` 后在**空白处**右键 -> 落点算成 ``notebook``，
          也就是**上一级**，跟用户看到的"我明明在这一层"不符；
        * 标签是虚拟栏目时 ``_target_folder()`` 返回 ``None``，
          于是**连新建都做不了**，只弹一句
          "请先进入某个书目，并切到有对应目录的分类" ——
          可用户明明就在一个书目里，这句话完全帮不上忙。

        判据要和 :meth:`drop_target_folder` **一致**，
        否则"拖文件进来"和"新建文件夹"会落到不同地方。
        """
        book = self.book()
        if book is None:
            return None
        if inside is not None:
            return Path(inside)
        if self._current_folder is not None and self._current_folder.is_dir():
            return self._current_folder
        if item is not None:
            # 右键点在某个条目上：建在它**所在的那一层**（"和它并排"）。
            # 用 ``.parent`` 而不是条目本身 —— 新建是"建一个同级的新文件夹"，
            # 不是"进到它里面去"（"建到里面"要右键那个文件夹，走 inside 那条路）。
            parent = Path(item.path).parent
            if parent.is_dir():
                return parent
        folder = self._target_folder()
        if folder is None:
            # 虚拟栏目：新建出来的东西总得有地方放，而「笔记」是这一层
            # 最常用、也最不可能有副作用的位置。
            folder = book.path / C.NOTEBOOK_FOLDER
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            common.error(self, f"无法创建目录：{folder}\n{exc}", "新建失败")
            return None
        return folder

    def _can_create_here(self) -> bool:
        """当前这一层能不能新建东西（右键菜单据此禁用/启用）。"""
        return self._creation_dir() is not None

    def build_summary_from_sources(self, *, ask: bool = True) -> None:
        """**生成总结**：把书目的资料直接插进 summary（需求变更后的行为）。

        需求原话（变更后）：

        > summary中板块，不需要你补充内容了（或者你可以仅仅在文档末尾补充tips），
        > 按照用户上传的文件来，不要AI识别文字了，直接插入图片或文件
        > AIsummary中 AI可以根据自己的理解改变图片插入顺序，
        > 实现不同文件夹内容，的混排插入

        所以现在的流程是：

        1. 收集「简介 + 笔记 + 易错题」（含子文件夹）里的全部文件；
        2. 全部转成图片（PDF 每页一张；Word/PPT/Excel/文本排成图片）；
        3. **可选**：让 AI 只看每页开头一小段文字，决定页序（实现跨文件夹混排）；
        4. 把 summary **整个重写**成"标题 + 资料图片"，旧版先自动备份。

        **AI 不写正文**。它只在第 3 步出现，而且默认关闭 ——
        只有用户勾了才发请求。

        几件刻意做的事：

        * **旧内容会先备份**：重写前存一份，可以从「版本管理」退回去；
        * **重复执行不会越插越多**：summary 是重写的，不是追加的；
        * **单份失败不影响其它**：失败的那份在末尾列出原因，原文件不动；
        * **AI 混排失败不算错误**：退回原顺序继续，不因为锦上添花而让整件事失败。
        """
        book = self.book()
        if book is None:
            common.warn(self, "请先打开一个书目。", "无法生成总结")
            return
        from gwp.services import source_merge

        sources = source_merge.collect_sources(book)
        if not sources:
            common.info(
                self,
                "书目里没有可插入的资料。\n\n"
                f"收集的是「{C.NOTEBOOK_FOLDER}」与「{C.ERROR_FOLDER}」"
                "里的全部文件（含子文件夹）。先放些资料进去再试。",
                "没有资料",
            )
            return

        want_mix = False
        want_supplement = False
        if ask:
            default_mix = bool(self.context.config.get("summary.ai_mix", False))
            default_supplement = bool(
                self.context.config.get("summary.ai_supplement", True)
            )
            choice = common.ask_generate_summary(
                self,
                f"把当前书目的 {len(sources)} 份资料合并成一个 PDF？\n\n"
                "· 每份资料都转成**页面图片**再合并（版面与公式都在）；\n"
                "· 旧的 Markdown 总结会被删掉，上一版先自动备份；\n"
                "· 中间产生的临时文件全部清理，**不会动你的原始文件**。\n\n"
                "下面两项都是可选的，不勾就完全不调用 AI。",
                mix_label="让 AI 按主题重排页序（混排不同文件夹的内容）",
                mix_checked=default_mix,
                supplement_label=f"文末加入「{_supplement_label()}」"
                                 "（AI 补充知识点，每页左上角带标记）",
                supplement_checked=default_supplement,
            )
            if choice is None:
                return
            want_mix, want_supplement = choice
            try:
                self.context.config.set("summary.ai_mix", bool(want_mix))
                self.context.config.set("summary.ai_supplement",
                                        bool(want_supplement))
                self.context.config.save()
            except Exception:  # noqa: BLE001 - 记住偏好失败不该挡住生成
                log.debug("保存总结偏好失败", exc_info=True)

        self._build_summary(book, sources, want_mix=want_mix,
                            want_supplement=want_supplement)

    def _build_summary(self, book, sources, *, want_mix: bool,
                       want_supplement: bool = False) -> None:
        """``build_summary_from_sources`` 的执行部分（拆开便于测试直接调用）。

        技术路线（需求）：

        > AI总结实现方法：将所有待总结文件转化并合并为一个pdf文档，
        > 结束后删除中间可能产生的废弃文档和数据

        所以流程是：

        1. 先备份现有的总结（PDF 或旧的 md）；
        2. 把每一份资料转成**页面图片**，全部写进一个**临时 PDF**；
        3. 全部成功才原子替换目标（中途失败目标一个字节都不动）；
        4. 删掉旧的 Markdown 总结（需求："不再生成md文档，旧的md之间删掉"）；
        5. 中间物（页面图片、公式图片、临时 PDF）全部清掉 ——
           这一点由 :mod:`gwp.services.summary_pdf` 用"专用临时目录 +
           finally 清理"**结构上**保证，不是靠一份"记得删这些"的清单。
        """
        from gwp.services import summary_pdf

        target = summary_pdf.summary_pdf_path(book)
        # **最后一道保护：测试环境里绝不允许写真实数据目录。**
        # 我本人踩过一次（端到端验证把用户真实书目的总结覆盖掉了），
        # 所以这一步不能省。
        guard = _real_data_write_blocked(target)
        if guard:
            log.error("已阻止测试环境写入真实数据目录：%s（%s）", target, guard)
            common.error(
                self,
                f"出于安全考虑，本次没有写入：\n{target}\n\n{guard}",
                "已阻止写入",
            )
            return

        # 先备份：总结会被整个重写，改坏了要能退回去
        backup_path = None
        try:
            existing = book.summary_path
            if existing is not None and Path(existing).is_file():
                record = self.context.backups.save_previous(
                    self.subject_name, self.book_name, Path(existing),
                    note="重新生成总结前",
                )
                backup_path = (
                    getattr(record, "file", None) or getattr(record, "directory", None)
                ) if record else None
        except Exception:  # noqa: BLE001 - 备份失败不阻止生成，但要说明
            log.warning("生成总结前备份失败", exc_info=True)

        busy = common.BusyDialog(self, "正在生成总结", "准备中…")
        busy.show()

        def _on_progress(done: int, total: int, name: str) -> None:
            """按资料的进度（第几份 / 共几份）。"""
            busy.report(
                f"正在处理资料（{done}/{total}）",
                int(done * 100 / max(1, total)), name,
            )

        def _on_mix_progress(message: str, percent: int = -1,
                             detail: str = "") -> None:
            """混排阶段的进度。

            **签名必须和 BusyDialog.report 一致**（message, percent, detail）——
            混排模块是按这个签名回调的；早先我只写了 `lambda text: ...`，
            于是混排一被触发就 TypeError（实测）。
            """
            busy.report(message, percent, detail)

        try:
            result = summary_pdf.build_summary_pdf(
                book, sources,
                on_progress=_on_progress,
                mix_progress=_on_mix_progress,
                ai_manager=self.context.ai,
                want_mix=want_mix,
                want_supplement=want_supplement,
                theme=str(self.context.config.get("ui.theme", "light") or "light"),
            )
        except Exception as exc:  # noqa: BLE001 - 生成失败要给出可读原因
            log.exception("生成总结 PDF 失败")
            busy.close()
            common.error(self, f"生成失败：{exc}", "生成总结")
            return
        finally:
            busy.close()

        if not result.ok or result.pdf_path is None:
            failed = result.failed
            reason = failed[0].error if failed else "没有可用的资料"
            common.warn(
                self,
                f"没有生成 PDF：{reason}\n\n"
                "（原有的总结文件没有被改动。）",
                "生成失败",
            )
            return

        # 旧的 Markdown 总结删掉（需求："不再生成md文档，旧的md之间删掉"）
        removed = summary_pdf.remove_legacy_markdown_summary(book)

        # **让缓存失效再刷新**：刚写了新文件，缓存里的 Book 还不知道它
        self.context.library.invalidate()
        self.refresh()
        details = [
            f"已合并：{len([c for c in result.chapters if not c.error])} 份资料，"
            f"共 {result.page_count} 页",
            f"PDF：{result.pdf_path.name}"
            f"（{result.size_bytes / 1024 / 1024:.1f} MB）",
        ]
        if result.supplement_pages:
            details.append(
                f"文末「{_supplement_label()}」补充：{result.supplement_pages} 页"
            )
        elif result.supplement_message:
            details.append(f"知识点补充：{result.supplement_message}")
        if backup_path is not None:
            details.append(f"上一版已备份：{backup_path}")
        if removed:
            details.append(f"已删除旧的 Markdown 总结：{len(removed)} 个")
        if result.mix_message:
            details.append(f"页序：{result.mix_message}")
        if result.failed:
            details.append(f"未能合并：{len(result.failed)} 份")
        details.append("中间产生的临时文件已全部清理。")
        common.info(self, "\n".join(details), "生成完成")
        self.status_message.emit(
            f"已生成总结 PDF：{result.page_count} 页"
        )
        if bool(self.context.config.get("summary.auto_open_after_generate", True)):
            self.open_summary()

    def extract_images(self, inside: Path | None = None) -> None:
        """把图片用 AI 提取成一份 Markdown（需求：文件夹内多图片 AI 提取并合并为 md）。

        默认作用在**正在浏览的目录**（与拖拽/导入同一套落点规则），
        也可以由右键文件夹指定 ``inside``。
        """
        folder = Path(inside) if inside is not None else self.drop_target_folder()
        if folder is None:
            common.warn(self, "请先进入某个书目，并切到有对应目录的分类。",
                        "无法提取图片")
            return
        if not folder.is_dir():
            common.warn(self, f"文件夹不存在：\n{folder}", "无法提取图片")
            return
        from gwp.services import image_digest

        images = image_digest.collect_images(folder)
        if not images:
            common.info(
                self,
                f"这个文件夹里没有图片：\n{folder}\n\n"
                "把要识别的图片先放进来（拖拽或「导入文件」），再试一次。",
                "没有图片",
            )
            return
        from gwp.ui.dialogs.image_digest_dialog import ImageDigestDialog

        dialog = ImageDigestDialog(self.context, folder, parent=self)
        dialog.exec()
        if dialog.saved_path is not None:
            self.status_message.emit(f"已生成：{dialog.saved_path.name}")
            self.refresh()
            bus.emit(BOOK_CONTENT_CHANGED,
                     subject=self.subject_name, book=self.book_name)
            # 对话框里勾了"保存后打开"就会走到这里（accept 后 saved_path 有值）
            self.open_file(dialog.saved_path)

    def upload_files(self, inside: Path | None = None) -> None:
        """用文件选择框"上传"文件到指定文件夹（或当前浏览的目录）。

        拖拽上传之外再给一个明确入口：有些人不用拖拽，
        触控板拖文件也不方便。落点规则和拖拽**完全一致**
        （都走 :meth:`drop_target_folder` / ``inside``）。
        """
        target = Path(inside) if inside is not None else self.drop_target_folder()
        if target is None:
            common.warn(self, "请先进入某个书目，并切到有对应目录的分类。",
                        "无法上传")
            return
        paths = common.pick_files(self, "选择要上传的文件", multiple=True)
        if not paths:
            return
        self._do_import([Path(p) for p in paths], target)

    def create_folder(self, inside: Path | None = None,
                      item: BookItem | None = None) -> None:
        """在当前分类（或指定文件夹）里新建一个文件夹。

        「其它文件」栏目就是靠它来分门别类的；配合右键文件夹，
        还能继续建子文件夹。
        """
        target = self._creation_dir(inside, item)
        if target is None:
            common.warn(self, "请先进入某个书目，并切到有对应目录的分类。", "无法新建文件夹")
            return
        name = common.ask_text(
            self, "新建文件夹", "文件夹名称", "新建文件夹", ok_text="创建"
        )
        if name is None:
            return
        # 用 validate_name 给用户**真实**的错误提示（sanitize 会静默替换非法字符）
        error = validate_name(name)
        if error:
            common.warn(self, error, "无法新建文件夹")
            return
        clean = sanitize_name(name)
        candidate = target / clean
        if candidate.exists():
            common.warn(self, f"「{clean}」已经存在。", "无法新建文件夹")
            return
        try:
            candidate.mkdir(parents=True)
        except OSError as exc:
            common.error(self, f"创建失败：{exc}", "新建文件夹")
            return
        self.refresh()
        self.status_message.emit(f"已新建文件夹：{clean}")
        self._reveal_created(candidate)

    def create_markdown(self, inside: Path | None = None,
                        item: BookItem | None = None) -> None:
        """在当前分类（或指定文件夹）里新建一个 Markdown 文件。"""
        target = self._creation_dir(inside, item)
        if target is None:
            common.warn(self, "请先进入某个书目，并切到有对应目录的分类。", "无法新建 Markdown")
            return
        name = common.ask_text(
            self, "新建 Markdown", "文件名（不用写 .md）", "新建文档", ok_text="创建"
        )
        if name is None:
            return
        raw = name if name.lower().endswith((".md", ".markdown")) else f"{name}.md"
        error = validate_name(raw)
        if error:
            common.warn(self, error, "无法新建 Markdown")
            return
        clean = sanitize_name(raw)
        if not clean.lower().endswith((".md", ".markdown")):
            clean += ".md"
        candidate = target / clean
        if candidate.exists():
            common.warn(self, f"「{clean}」已经存在。", "无法新建 Markdown")
            return
        try:
            candidate.write_text(f"# {candidate.stem}\n\n", encoding="utf-8")
        except OSError as exc:
            common.error(self, f"创建失败：{exc}", "新建 Markdown")
            return
        self.refresh()
        self.status_message.emit(f"已新建：{clean}")
        self._reveal_created(candidate)

    def _reveal_created(self, path: Path) -> None:
        """尝试在当前分类的表里选中刚创建的东西，让用户一眼看到。"""
        try:
            table = self._active_table()
            for item in table._items:      # noqa: SLF001 - 同类内部使用
                if item.path == path:
                    table.select_name(item.name)
                    return
        except Exception:  # noqa: BLE001 - 选中失败不影响创建结果
            pass

    # ==================================================================
    # 剪贴板：剪切 / 复制 / 粘贴
    # ==================================================================

    def _active_table(self) -> FileTable:
        return self._current_table()

    def copy_selection(self, mode: str = COPY) -> None:
        """把当前选中的条目放进剪贴板（复制或剪切）。"""
        table = self._active_table()
        items = table.selected_items()
        if not items:
            current = table.current_item()
            items = [current] if current is not None else []
        if not items:
            self.status_message.emit("请先选中要" + ("剪切" if mode == CUT else "复制") + "的文件")
            return
        # 不允许把书目的结构目录（book/error-prone/notebook/homework）剪走，否则整本书就废了
        protected = {
            (self.book().path / key).resolve()
            for key in C.BOOK_TEMPLATE_DIRS
            if self.book() is not None
        }
        chosen: list[Path] = []
        blocked: list[str] = []
        for item in items:
            try:
                resolved = item.path.resolve()
            except OSError:
                resolved = item.path
            if resolved in protected:
                blocked.append(item.name)
                continue
            chosen.append(item.path)
        if blocked:
            common.warn(
                self,
                "以下目录是书目的固定结构，不能剪切或复制：\n" + "、".join(blocked),
                "无法操作",
            )
        if not chosen:
            return
        self.clipboard.set(chosen, mode=mode)
        self._update_clipboard_buttons()
        self.status_message.emit(self.clipboard.describe())

    def paste_files(self) -> None:
        """把剪贴板内容粘贴到当前分类目录（没有分类时粘到书目根目录）。"""
        book = self.book()
        if book is None:
            return
        if self.clipboard.is_empty:
            # 应用内剪贴板为空时，尝试读系统剪贴板（从资源管理器复制过来的）
            external = read_system_clipboard_files()
            external = [path for path in external if path.exists()]
            if external:
                self.clipboard.set(external, mode=COPY)
            else:
                self.status_message.emit("剪贴板为空：请先在这里或资源管理器里复制文件")
                return

        folder = self._target_folder() or book.path
        if self.clipboard.would_paste_into_itself(folder):
            common.warn(self, "不能把文件夹粘贴到它自己（或它的子目录）里面。", "无法粘贴")
            return
        # 防止粘到源文件所在目录时产生"自己复制自己"的一堆副本
        sources_in_target = [
            path for path in self.clipboard.paths if path.parent == folder
        ]
        if sources_in_target and not self.clipboard.is_cut:
            if not common.confirm(
                self,
                f"剪贴板里有 {len(sources_in_target)} 个项目本来就在「{folder.name}」中，"
                "继续会在同目录生成副本。要继续吗？",
                "粘贴",
            ):
                return

        was_cut = self.clipboard.is_cut
        results = self.clipboard.paste(folder)
        ok = [result for result in results if result.ok]
        failed = [result for result in results if not result.ok]
        renamed = [result for result in ok if result.status == "renamed"]

        self.refresh()
        bus.emit(BOOK_CONTENT_CHANGED, subject=self.subject_name, book=self.book_name)
        self._update_clipboard_buttons()

        action = "移动" if was_cut else "复制"
        message = f"已{action} {len(ok)} 个项目到「{folder.name}」"
        if renamed:
            message += f"（{len(renamed)} 个因同名自动改名）"
        self.status_message.emit(message)
        if failed:
            common.warn(
                self,
                "\n".join(f"{item.source.name}：{item.message}" for item in failed),
                "部分项目粘贴失败",
            )

    def clear_clipboard(self) -> None:
        self.clipboard.clear()
        self._update_clipboard_buttons()
        self.status_message.emit("已清空剪贴板")

    def _update_clipboard_buttons(self) -> None:
        """根据剪贴板状态与当前选中项，刷新工具条按钮可用性。"""
        if not hasattr(self, "btn_cut"):
            return
        has_selection = bool(self._active_table().selected_items())
        self.btn_cut.setEnabled(has_selection)
        self.btn_copy.setEnabled(has_selection)

        external = [path for path in read_system_clipboard_files() if path.exists()]
        self.btn_paste.setEnabled(not self.clipboard.is_empty or bool(external))
        self.btn_clear_clipboard.setVisible(not self.clipboard.is_empty)

        hint = self.clipboard.describe()
        if not self.clipboard.is_empty and external:
            hint += f"（另有系统剪贴板 {len(external)} 项）"
        for button in (self.btn_cut, self.btn_copy, self.btn_paste, self.btn_clear_clipboard):
            button.setToolTip(hint)
        if hasattr(self, "lbl_clipboard"):
            self.lbl_clipboard.setText(hint)

    def _rename_item(self, item: BookItem) -> None:
        """重命名条目。

        **作业文件夹要走作业专有逻辑**（`hw.rename`）：它除了移动文件夹，
        还要同步 `homework.json` 里的 name 与内容 Markdown 的文件名。
        只调 `file_ops.rename_path` 的话，文件夹改了名而元信息没改 ——
        下次扫描或编辑就会对不上（用户报障："作业文件夹名称未改变"）。
        """
        if item is None:
            return
        new_name = common.ask_text(self, "重命名", "新名称：", item.name)
        if not new_name or new_name == item.name:
            return
        log.info("重命名条目：%s -> %r（%s）", item.name, new_name, item.path)

        # 是作业吗？是的话交给作业自己的改名（含回滚与元信息同步）
        if item.is_dir:
            existing = hw.load(item.path)
            if existing is not None:
                try:
                    moved = hw.rename(existing, new_name)
                    log.info("重命名作业完成 -> %s", moved.path)
                except DataError as exc:
                    log.info("重命名作业被拒（重名）：%s", exc)
                    common.warn(self, str(exc), "无法改名")
                    return
                except OSError as exc:
                    log.exception("重命名作业失败")
                    common.error(self, f"重命名失败：{exc}", "重命名")
                    return
                self.refresh()
                self.status_message.emit(f"已重命名为：{moved.name}")
                return

        try:
            file_ops.rename_path(item.path, new_name)
        except OSError as exc:
            log.exception("重命名失败")
            common.error(self, str(exc), "重命名失败")
            return
        self.refresh()
        self.status_message.emit(f"已重命名为：{new_name}")

    def _copy_item(self, item: BookItem) -> None:
        directory = common.pick_directory(self, "选择目标文件夹", item.path.parent)
        if not directory:
            return
        results = file_ops.import_files([item.path], directory, overwrite=False)
        ok = sum(1 for result in results if result.ok)
        self.status_message.emit(f"已复制 {ok} 个文件到 {directory}")

    def _delete_item(self, item: BookItem) -> None:
        if not common.confirm(self, f"确定删除「{item.name}」吗？将移入回收站。", "删除"):
            return
        try:
            file_ops.delete_path(item.path, to_recycle=True)
        except OSError as exc:
            common.error(self, str(exc), "删除失败")
            return
        self.refresh()
        self.status_message.emit(f"已删除：{item.name}")

    # ==================================================================
    # 导入
    # ==================================================================

    def _import_tooltip(self) -> str:
        """「导入文件」的悬浮提示：说清会导入到哪个位置。

        导入目标随"你在看哪一层"变化（笔记 / 练习 / 作业 / 某个子文件夹…），
        在"简介、AI 总结、全部条目"这些没有对应目录的标签下会弹窗让人选，
        因此提示要跟着变，避免用户以为文件会落在他看不见的地方。
        """
        if self._current_folder is not None:
            return f"导入文件到当前位置：{self._folder_label(self._current_folder)}"
        key = self._current_tab_key()
        title = next((t for k, t, _f in self._tab_defs if k == key), "")
        folder = self._target_folder()
        if folder is not None and title:
            return f"导入文件到当前位置：{title}（{folder.name}）"
        if title:
            return f"导入文件到当前位置；「{title}」没有对应目录，导入时会让你选择分类"
        return "导入文件到当前位置"

    def _update_import_tooltip(self) -> None:
        button = getattr(self, "btn_import", None)
        if button is not None:
            button.setToolTip(self._import_tooltip())

    def import_files(self) -> None:
        book = self.book()
        if book is None:
            return
        # 用 drop_target_folder()（= 拖拽的落点规则），**不是** _target_folder()：
        # 后者只看标签登记，进了子文件夹再点「导入文件」会导到上一级。
        # 两处必须同一套规则，否则"拖"和"点按钮"会落到不同地方。
        folder = self.drop_target_folder()
        if self._target_folder() is None and self._current_folder is None:
            # 在"简介/总结/全部"这些没有对应目录的标签下，让用户选一个分类
            options = {
                f"笔记（{C.NOTEBOOK_FOLDER}）": book.path / C.NOTEBOOK_FOLDER,
                f"作业（{C.HOMEWORK_FOLDER}，不参与总结）": book.path / C.HOMEWORK_FOLDER,
                f"易错题（{C.ERROR_FOLDER}）": book.path / C.ERROR_FOLDER,
                f"教材（{C.BOOK_FOLDER}，不参与总结）": book.path / C.BOOK_FOLDER,
                "书目根目录": book.path,
            }
            from PyQt6.QtWidgets import QInputDialog

            names = list(options)
            choice, ok = QInputDialog.getItem(self, "选择导入位置", "把文件放到：", names, 0, False)
            if not ok:
                return
            folder = options[choice]

        filters = (
            "所有支持的文件 (*.md *.markdown *.txt *.pdf *.docx *.pptx *.xlsx *.csv *.png *.jpg *.jpeg);;"
            "Markdown (*.md *.markdown);;PDF (*.pdf);;"
            "Word (*.docx);;PowerPoint (*.pptx);;Excel (*.xlsx *.csv);;"
            "图片 (*.png *.jpg *.jpeg);;所有文件 (*.*)"
        )
        paths = common.pick_open_files(self, "选择要导入的文件", filters)
        if not paths:
            return
        self._do_import(paths, folder)

    def _do_import(self, paths: list[Path], folder: Path) -> None:
        overwrite = False
        if bool(self.context.config.get("import.ask_before_overwrite", True)):
            conflicts = [path.name for path in paths if (folder / path.name).exists()]
            if conflicts:
                box = QMessageBox(self)
                box.setWindowTitle("文件已存在")
                box.setText(f"以下文件在目标文件夹中已存在：\n\n{', '.join(conflicts[:8])}")
                box.setInformativeText("要覆盖它们吗？选择「否」则自动改名导入。")
                box.setIcon(QMessageBox.Icon.Question)
                overwrite = bool(box.exec() == QMessageBox.StandardButton.Yes)

        results = file_ops.import_files(
            paths,
            folder,
            overwrite=overwrite,
            copy=bool(self.context.config.get("import.copy_files", True)),
            suffix_style=str(self.context.config.get("import.suffix_on_conflict", "_1") or "_1"),
        )
        ok = [result for result in results if result.ok]
        failed = [result for result in results if not result.ok]
        self.refresh()
        bus.emit(BOOK_CONTENT_CHANGED, subject=self.subject_name, book=self.book_name)
        # 状态栏里给出**相对书目的完整路径**，而不是只给文件夹名 ——
        # 用户反馈过一次"传到上一目录"，只显示 "第一章" 根本看不出落点在哪一级。
        message = f"已导入 {len(ok)} 个文件到 {self._folder_label(folder)}"
        if failed:
            message += f"，{len(failed)} 个失败：{failed[0].message}"
        self.status_message.emit(message)
        if failed:
            common.warn(self, "\n".join(f"{item.source.name}：{item.message}" for item in failed), "部分文件导入失败")

    def _folder_label(self, folder: Path) -> str:
        """给用户看的目录名：相对书目的路径（例如 ``others / 第一章``）。"""
        book = self.book()
        if book is not None:
            try:
                relative = Path(folder).relative_to(book.path)
                return " / ".join(relative.parts)
            except ValueError:
                pass
        return Path(folder).name

    # -- 拖拽上传 -------------------------------------------------------
    #
    # 需求："作业以及其它文件夹都要支持拖拽上传，目前会传到上一目录"。
    #
    # 原来的实现有三个问题，一起修掉：
    #
    # 1. **落点算错**：用的是 ``_target_folder()``，它只看标签登记，
    #    完全不管你浏览到哪一层。于是进了 ``others/第一章`` 再拖文件，
    #    文件被丢到 ``others``（**上一级目录**）—— 用户反馈的正是这个。
    #    现在用 :meth:`drop_target_folder`：**浏览到哪就传进哪**。
    # 2. **表格不接受拖拽**：``FileTable`` 没开 ``acceptDrops``，
    #    事件靠 Qt 冒泡到 BookView 才生效；一旦以后给表格加拖拽排序，
    #    导入就会被吃掉。现在表格自己也处理（见 ``file_table.py``）。
    # 3. **没有任何视觉反馈**：用户不知道会传到哪。现在拖进来会高亮落点，
    #    并在状态栏写明目标目录。

    def _drop_paths(self, mime) -> list[Path]:
        if not mime.hasUrls():
            return []
        return [
            Path(url.toLocalFile())
            for url in mime.urls()
            if url.isLocalFile() and url.toLocalFile()
        ]

    def handle_file_drop(self, pos, mime) -> bool:
        """处理一次外部文件拖入。返回是否消费了这次拖拽。

        由 ``BookView`` 和 ``FileTable`` 共用 —— 表格上的拖拽先走这里，
        没消费掉才冒泡到视图，两条路径的落点规则完全一致。
        """
        paths = self._drop_paths(mime)
        if not paths:
            return False
        folder = self._row_folder_at(pos) or self.drop_target_folder()
        if folder is None:
            common.warn(self, "当前栏目没有对应的文件夹，无法导入。", "无法导入")
            return True
        self._do_import(paths, folder)
        return True

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if self._drop_paths(event.mimeData()):
            event.acceptProposedAction()
            self._set_drop_hint(self.drop_target_folder())
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:  # noqa: N802
        self._set_drop_hint(None)
        super().dragLeaveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        self._set_drop_hint(None)
        if self.handle_file_drop(event.position(), event.mimeData()):
            event.acceptProposedAction()

    def _set_drop_hint(self, folder: Path | None) -> None:
        """拖拽过程中显示"会传到哪"（以前完全没有反馈，这是那个
        "传到上一目录"的 bug 一直没被发现的原因之一）。

        文案复用 :meth:`_folder_label`（``others / 第一章``），
        和导入完成后状态栏里的说法一致 —— 两处一样，
        用户才能把"拖的时候看到的"和"传完之后看到的"对上。
        """
        if folder is None or self.book() is None:
            self.lbl_drop_hint.setVisible(False)
            return
        self.lbl_drop_hint.setText(f"拖到这里 → {self._folder_label(folder)}")
        self.lbl_drop_hint.setVisible(True)

    # ==================================================================
    # 总结
    # ==================================================================

    def preview_materials(self) -> None:
        """「预览将生成的资料」：只列清单，**不调用 AI**。

        以前这个入口会显示"发送给 AI 的内容"并允许填额外要求，
        然后走 AI 写正文那条路。需求变更后 AI 不再写正文，
        所以它改成**如实列出会被插入的文件**，让用户先看清会得到什么。
        """
        book = self.book()
        if book is None:
            return
        from gwp.services import source_merge
        from gwp.ui.dialogs.materials_dialog import SummarySourcesDialog

        sources = source_merge.collect_sources(book)
        if not sources:
            common.info(
                self,
                "书目里没有可插入的资料。\n\n"
                f"收集的是「{C.NOTEBOOK_FOLDER}」与「{C.ERROR_FOLDER}」"
                "里的全部文件（含子文件夹）。",
                "没有资料",
            )
            return
        dialog = SummarySourcesDialog(book.title, sources, self)
        if dialog.exec():
            self.build_summary_from_sources()

    def generate_summary(self) -> None:
        """顶栏「生成总结 PDF」：把资料合并成一个 PDF。

        会用两个复选框问两件可选的事：AI 混排页序、文末「长庚知道」补充。
        **资料正文不由 AI 写** —— 只有「长庚知道」那几页是 AI 的文字，
        而且明确标注、放在最后（需求："可以在文档最后加入一些关于知识点的
        你的补充"）。
        """
        book = self.book()
        if book is None:
            return
        self.build_summary_from_sources()

    # -- 日记类型的两套生成 ---------------------------------------------

    def generate_diary_thought(self) -> None:
        """「AI 思想总结」：读 my diary 归纳思想。"""
        self._start_diary_generation("thought")

    def generate_diary_book(self) -> None:
        """「AI 日记」：把 my diary 整合成一篇格式统一的日记册。"""
        self._start_diary_generation("book")

    def _start_diary_generation(self, mode: str) -> None:
        book = self.book()
        if book is None:
            return
        if self._ai_worker is not None and self._ai_worker.isRunning():
            common.warn(self, "正在生成中，请稍候或取消。")
            return

        adapter = self.context.ai.active()
        if adapter is not None:
            ok, reason = adapter.is_configured()
            if not ok:
                proceed = common.confirm(
                    self,
                    f"当前 AI 不可用：{reason}\n\n要尝试用兜底 AI 继续吗？",
                    "AI 不可用",
                )
                if not proceed:
                    return

        title = "生成思想总结" if mode == "thought" else "生成日记"
        dialog = SummaryProgressDialog(f"{title}：{book.title}", self)
        self._progress = dialog
        dialog.show()

        def task(**helpers):
            return self.context.summarizer.generate_diary(
                book,
                mode=mode,
                adapter=None,
                on_progress=lambda event: helpers["on_progress"](
                    event.message, event.percent, event.detail
                ),
                on_chunk=helpers["on_chunk"],
                question_handler=helpers["on_question"],
                should_cancel=helpers["should_cancel"],
            )

        worker = AIWorker(task, parent=self, label=title)
        worker.progress.connect(self._on_summary_progress)
        worker.chunk.connect(self._on_summary_chunk)
        worker.question.connect(self._on_summary_question)
        worker.finished_ok.connect(self._on_summary_finished)
        worker.failed.connect(self._on_summary_failed)
        worker.cancelled.connect(self._on_summary_cancelled)
        self._ai_worker = worker
        worker.start()

    def apply_subject_type(self, subject_type: str) -> None:
        """按科目类型切换标签与按钮。

        * 普通科目：显示「生成总结」，隐藏两个日记按钮；
        * **日记**：只显示「生成思想总结」与「生成日记」，没有普通的总结按钮。
        """
        self.subject_type = subject_type or C.DEFAULT_SUBJECT_TYPE
        is_diary = self.subject_type == C.SUBJECT_DIARY
        self.btn_summary.setVisible(not is_diary)
        self.btn_diary_thought.setVisible(is_diary)
        self.btn_diary_book.setVisible(is_diary)
        self._apply_tabs(C.tabs_for_type(self.subject_type))

    # 说明：这里原来有一个 `_start_generation()`，负责"让 AI 写 summary 正文"。
    # 需求变更后「生成总结」不再调用 AI 写正文（改成直接插入资料图片），
    # 它就变成了**没有任何调用方的死代码** —— 而留着的风险是：
    # 以后有人顺手用它，就又绕过新行为了。所以删掉。
    #
    # 日记科目的两套生成（思想总结 / 整理日记）走的是 _start_diary_generation，
    # 与这里无关，仍然保留。

    def _on_summary_progress(self, message: str, percent: int, detail: str) -> None:
        if self._progress is not None:
            self._progress.set_stage(message, percent, detail)

    def _on_summary_chunk(self, text: str) -> None:
        if self._progress is not None:
            self._progress.append_chunk(text)

    def _on_summary_question(self, question, holder) -> None:
        from gwp.ui.dialogs.question_dialog import AiQuestionDialog

        dialog = AiQuestionDialog(question, self._progress or self)
        dialog.exec()
        if self._ai_worker is not None:
            self._ai_worker.answer_question(dialog.answer())

    def _on_summary_finished(self, result) -> None:
        self._close_progress()
        # **先让缓存失效再刷新**。
        #
        # `Library.subjects()` 会缓存扫描结果，而 `book()` 是从缓存里取的 ——
        # summary 文件此时刚写进磁盘，但缓存里的 Book 对象**还不知道**
        # （它的 summary_path 是旧的、甚至是 None）。
        # 只调 refresh() 的话，AI 总结标签页会一直是空的，
        # 直到下次启动重新扫描才出现（用户报障："生成的AI总结在AI总结位置未显示"）。
        self.context.library.invalidate()
        self.refresh()
        if result is None or not getattr(result, "ok", False):
            message = getattr(result, "error", "未知错误")
            common.error(self, message, "生成失败")
            self.status_message.emit("生成失败")
            return
        bus.emit(SUMMARY_UPDATED, subject=self.subject_name, book=self.book_name)
        details = [
            f"资料：{result.material_count} 份（约 {result.char_count} 字符）",
            f"AI：{result.provider or '默认'}",
            f"耗时：{result.elapsed:.1f} 秒",
        ]
        if result.backup_path:
            details.append(f"上一版已备份到：{result.backup_path}")
        if result.skipped:
            details.append(f"跳过 {len(result.skipped)} 个空文件")
        common.info(self, "总结已生成。\n\n" + "\n".join(details), "生成完成")
        self.status_message.emit("总结已生成")
        if bool(self.context.config.get("summary.auto_open_after_generate", True)) and result.summary_path:
            self.open_document.emit(Path(result.summary_path))

    def _on_summary_failed(self, message: str) -> None:
        self._close_progress()
        self.refresh()
        common.error(self, message, "生成失败")

    def _on_summary_cancelled(self) -> None:
        self._close_progress()
        self.status_message.emit("已取消生成")

    def _close_progress(self) -> None:
        if self._progress is not None:
            self._progress.close()
            self._progress.deleteLater()
            self._progress = None

    def open_summary(self) -> None:
        book = self.book()
        if book is None or not book.has_summary or book.summary_path is None:
            common.warn(self, "还没有生成总结。")
            return
        self.open_document.emit(book.summary_path)

    def open_backups(self) -> None:
        book = self.book()
        if book is None:
            return
        summary_path = book.summary_path or (book.path / f"{book.name}{C.SUMMARY_SUFFIX}")
        dialog = BackupDialog(self.context, self.subject_name, self.book_name, summary_path, self)
        dialog.exec()
        self.refresh()

    def restore_latest_backup(self) -> None:
        book = self.book()
        if book is None:
            return
        backup = self.context.backups.latest(self.subject_name, self.book_name)
        if backup is None:
            common.warn(self, "没有可恢复的历史版本。")
            return
        if not common.confirm(
            self,
            f"确定恢复历史版本（{backup.created_label}）吗？\n当前总结会先被另存一份。",
            "恢复上一版",
        ):
            return
        summary_path = book.summary_path or (book.path / f"{book.name}{C.SUMMARY_SUFFIX}")
        ok = self.context.backups.restore(self.subject_name, self.book_name, summary_path, backup)
        if ok:
            bus.emit(SUMMARY_UPDATED, subject=self.subject_name, book=self.book_name)
            common.info(self, "已恢复。", "恢复完成")
            self.refresh()
        else:
            common.warn(self, "恢复失败：找不到备份内容。")

    # ==================================================================
    # 导出
    # ==================================================================

    def export_pdf(self) -> None:
        """导出 PDF。

        取哪份文件的优先级（曾经是"只要有总结就导出总结"，容易误导出）：
        1. 当前标签页里**选中的**文件（目录会被跳过，取其中第一个文件）；
        2. 没选中时：有总结就用总结；
        3. 再没有就提示用户先选文件或先生成总结。
        """
        book = self.book()
        if book is None:
            return
        source = self._resolve_export_source(book)
        if source is None:
            common.warn(
                self,
                "没有可导出的 Markdown 内容。\n\n"
                "请先在列表里选中一个 Markdown 文件，或先生成学习总结。",
                "导出 PDF",
            )
            return
        self.export_markdown(source)

    def _resolve_export_source(self, book: Book) -> Path | None:
        """按上面的优先级找出要导出的文件。"""
        table = self._current_table()
        for item in table.selected_items():
            if not item.is_dir:
                return item.path
            nested = self._first_markdown_inside(item.path)
            if nested is not None:
                return nested
        current = table.current_item()
        if current is not None and not current.is_dir:
            return current.path
        if book.has_summary and book.summary_path is not None:
            return book.summary_path
        return None

    @staticmethod
    def _first_markdown_inside(folder: Path) -> Path | None:
        """选中的是文件夹时，取其中第一个可导出的文本文件。"""
        try:
            candidates = sorted(
                path for path in folder.rglob("*")
                if path.is_file()
                and path.suffix.lower() in (".md", ".markdown", ".txt")
                and not path.name.startswith(".")
            )
        except OSError:
            return None
        return candidates[0] if candidates else None

    def export_markdown(self, source: Path) -> None:
        """导出指定 Markdown 为 PDF（书目页与文档窗口共用）。"""
        from gwp.ui.dialogs.export_dialog import ExportPdfDialog

        dialog = ExportPdfDialog(self.context, source, self)
        if dialog.exec():
            self.status_message.emit(
                f"已导出 PDF：{dialog.output_path}"
                if dialog.output_path
                else "已导出 PDF"
            )

    def _current_table(self) -> FileTable:
        return self._tables.get(self._current_tab_key(), self._tables["root"])

    def reveal_book(self) -> None:
        book = self.book()
        if book is not None:
            file_ops.reveal_in_explorer(book.path)


def common_menu(parent: QWidget, actions: list):
    from gwp.ui.widgets.cards import build_context_menu

    return build_context_menu(parent, actions)


__all__ = ["TABS", "BookView"]
