"""首页：以彩色长方体卡片展示所有科目与收纳箱。

需求文档第三节：
* 首页图形化显示，默认是彩色长方体卡片；
* 支持新建 / 删除 / 改名 / 更换图片，全部通过右键菜单；
* 科目完全来自扫描 ``data/user data/subjects``，代码里不写死任何课程名。

收纳箱（后加的需求）：
* 可以把若干科目收进一个箱子里，箱子卡片**样式与科目卡片一致，只多一圈边框**；
* 箱子只做分组，不搬动任何文件；删除箱子只是把科目放回最外层；
* 双击箱子进入"箱内视图"，只显示箱内科目，顶部显示返回按钮。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from gwp.bootstrap import AppContext
from gwp.core import constants as C
from gwp.core.eventbus import BOOK_CONTENT_CHANGED, SUBJECTS_CHANGED, bus
from gwp.data_manager.models import Subject
from gwp.data_manager import homework as hw
from gwp.data_manager import schedule as sch
from gwp.ui import common
from gwp.ui.dialogs.schedule_dialog import ScheduleDialog
from gwp.ui.dialogs.subject_dialog import SubjectDialog
from gwp.ui.views.base_view import BaseView
from gwp.ui.widgets.clock_bar import ClockWeatherBar
from gwp.ui.widgets.cards import (
    BOX_MIME,
    SUBJECT_MIME,
    BoxCard,
    CardGrid,
    SubjectCard,
    build_context_menu,
)
from gwp.ui.widgets.schedule_panel import SchedulePanel, collect_entries

log = logging.getLogger(__name__)


class ReportingSplitter(QSplitter):
    """会在"分配完尺寸"之后发信号的 QSplitter。

    为什么需要它：``QSplitter`` 重新分配子控件宽度时，
    **不会**让子控件（比如 QScrollArea 的 viewport）收到 Resize 事件。
    于是"科目区现在有多宽"这个信息没有可靠的获取时机 ——
    实测结果是网格一直用着几十秒前的旧宽度，列数不变、卡片被裁掉。

    所以在 ``resizeEvent``（窗口变了）和 ``moveSplitter``（用户拖了，
    虽然现在已禁用）之后各发一次信号，由外面去重新计算列数。
    """

    sizes_applied = pyqtSignal()

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        super().resizeEvent(event)
        self.sizes_applied.emit()

    def moveSplitter(self, pos: int, index: int) -> None:  # noqa: N802
        super().moveSplitter(pos, index)
        self.sizes_applied.emit()


class HomeView(BaseView):
    """科目总览页（含收纳箱）。"""

    subject_opened = pyqtSignal(str)          # 科目名
    box_opened = pyqtSignal(str)              # 收纳箱 id
    #: 请求在软件内打开某本书目的作业栏目：科目名, 书目名, 作业文件夹路径
    homework_opened = pyqtSignal(str, str, str)

    #: 科目区的最小宽度：一张卡片（约 190px）+ 内边距 + 一点余量。
    #: 日程栏展开时**不会**把科目区压到比这更窄 ——
    #: 否则一列卡片都显示不全（用户报障："日程栏打开会遮挡 Subject"）。
    SUBJECT_MIN_WIDTH = 260

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self.set_title("我的科目", "双击进入科目；拖动卡片可调整顺序；右键卡片可以重命名、换图、删除")
        self.btn_new_subject = self.add_action(
            "＋ 新建科目", self.create_subject, accent=True, tooltip="新建一个科目文件夹"
        )
        self.btn_new_box = self.add_action(
            "＋ 新建收纳箱", self.create_box, tooltip="新建一个箱子，用来把若干科目收在一起"
        )
        # 关闭收纳箱：**唯一的退出入口**（需求：取消「返回全部」，由它完成）
        self.btn_close_box = self.add_action(
            "✕ 关闭收纳箱", self.leave_box, accent=True,
            tooltip="收起这个收纳箱，回到「我的科目」总览（不会删除任何科目）",
        )
        self.btn_close_box.setVisible(False)
        self.add_action("刷新", self.refresh, tooltip="重新扫描 user data/subjects")

        # 键盘退出收纳箱 + 把选中的科目移出箱子。
        # 单击卡片就会展开箱子（需求如此），因此右键不一定好按，键盘是稳妥的退路。
        self._install_box_shortcuts()

        self.enable_search("搜索科目…")

        #: 当前进入了哪个收纳箱（None = 最外层）
        self.current_box_id: str | None = None

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(12)

        self.grid = CardGrid()
        self.grid.card_opened.connect(self._open_card)
        # 收纳箱单击即展开（需求：点击收纳箱后展开，不需要双击）；
        # 科目仍然是双击进入，避免单击就跳走。
        self.grid.card_activated.connect(self._on_card_activated)
        self.grid.card_context.connect(self._card_menu)
        container_layout.addWidget(self.grid)

        # 科目区宽度变化时，把**真实可用宽度**告诉网格。
        #
        # 为什么必须这么做：网格原来是按自己的宽度算列数的，而它的宽度
        # 又受"所有卡片排成一行的最小宽度"约束 —— 两者互相依赖，
        # 于是窗口变窄、或者展开右侧日程栏时，网格不肯变窄，
        # 第三列被滚动区裁掉，看起来就像"被日程栏遮住了"。
        # 让滚动区自己上报视口宽度，列数就跟着可见宽度走。
        self.scroll.viewport().installEventFilter(self)
        self.empty_hint = QLabel(
            "还没有科目。\n\n点击右上角「＋ 新建科目」创建第一个，"
            "或者直接把文件夹放进 data\\user data\\subjects 里再点刷新。"
        )
        self.empty_hint.setObjectName("EmptyHint")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setWordWrap(True)
        container_layout.addWidget(self.empty_hint)
        container_layout.addStretch(1)

        self.scroll.setWidget(container)

        # 右侧：日期 / 时间 / 天气 + 日程栏
        clock_visible = bool(self.context.config.get("ui.show_clock_bar", True))
        weather_enabled = bool(self.context.config.get("ui.weather_enabled", True))
        self.clock_bar = ClockWeatherBar(auto_fetch=weather_enabled)
        self.clock_bar.setVisible(clock_visible)
        self.schedule_panel = SchedulePanel(config=self.context.config)
        self.schedule_panel.btn_new.clicked.connect(self.create_schedule)
        self.schedule_panel.completion_changed.connect(self._on_schedule_completion)
        self.schedule_panel.homework_opened.connect(self._on_schedule_open_homework)
        self.schedule_panel.collapse_toggled.connect(self.toggle_schedule_panel)
        self.schedule_panel.submit_requested.connect(self._on_schedule_submit)
        self.schedule_panel.schedule_edit_requested.connect(self.edit_schedule)
        self.schedule_panel.schedule_delete_requested.connect(self.delete_schedule)

        side = QWidget()
        side_layout = QVBoxLayout(side)
        # 右列不留内边距：日程栏折叠后要**贴着窗口右缘**，
        # 留一点边距都会在竖条右边露出一条空白（用户报的就是这个）。
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)
        # 时钟条塞进日程栏面板内部（由 panel 负责显隐），
        # 这样折叠时两者一起收起来，右列才会真的只剩 48px 宽。
        self.schedule_panel.set_clock_bar(self.clock_bar)
        side_layout.addWidget(self.schedule_panel)
        # 日程栏宽度**固定**，所以这一列不许被内容撑宽/压窄
        side.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.side_column = side

        self.splitter = ReportingSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.scroll)
        self.splitter.addWidget(side)
        # 分隔条重新分配宽度之后，把新的可用宽度告诉网格。
        #
        # **为什么必须在 splitter 上报、而不是靠视口的 Resize 事件**：
        # `QSplitter` 给子控件分配尺寸时**不会**走它们的 resize 请求路径，
        # 视口往往收不到 Resize 事件（实测：改尺寸后网格一直用着旧宽度，
        # 于是列数不变、卡片被裁掉 —— 这正是用户看到的"被日程栏遮住"）。
        self.splitter.sizes_applied.connect(self._sync_grid_width)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)      # 右侧不参与拉伸
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)    # 折叠由按钮控制，不靠拖到 0
        # 需求："调节日程栏宽度固定，只有全部折叠和完全展开 不能调整宽度"
        #
        # 所以**禁用分隔条的拖动**（原来可以连续拖，宽度是个滑动的量）。
        # 关掉 childrenCollapsible 之外，还要把 handle 的宽度设为 0 并
        # 把它的鼠标交互关掉，否则用户仍能把分隔条拖走。
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(0)
        for _index in range(1, self.splitter.count()):
            _handle = self.splitter.handle(_index)
            if _handle is not None:
                _handle.setEnabled(False)
                _handle.setCursor(Qt.CursorShape.ArrowCursor)
        self._apply_schedule_width()
        self.body.addWidget(self.splitter, 1)

        bus.subscribe(SUBJECTS_CHANGED, lambda **_: self.refresh())
        # 书目里新建 / 删除 / 改动作业后，首页日程栏要跟着变
        bus.subscribe(BOOK_CONTENT_CHANGED, lambda **_: self.refresh_schedule())
        self.refresh()

    # ==================================================================

    def refresh(self) -> None:
        library = self.context.library
        keyword = self.search.text().strip().lower()

        # 当前如果在一个已不存在的箱子里（被删除/手工改了 boxes.json），自动回到最外层
        if self.current_box_id is not None and library.boxes.get(self.current_box_id) is None:
            self.current_box_id = None

        width = int(self.context.config.get("ui.card.width", 196) or 196)
        height = int(self.context.config.get("ui.card.height", 124) or 124)
        radius = int(self.context.config.get("ui.card.radius", 14) or 14)

        cards: list = []
        if self.current_box_id is not None:
            cards, shown = self._build_box_cards(keyword, width, height, radius)
        else:
            cards, shown = self._build_top_level_cards(keyword, width, height, radius)

        self.grid.set_cards(cards)
        self._update_header(shown, keyword)
        self.refresh_schedule()

    # ------------------------------------------------------------------
    # 右侧日程栏
    # ------------------------------------------------------------------

    def refresh_schedule(self) -> None:
        """重新收集作业与其它日程，填进右侧栏。"""
        panel = getattr(self, "schedule_panel", None)
        if panel is None:
            return
        store = getattr(self.context, "schedule", None)
        entries = collect_entries(self.context.library, store)
        panel.set_entries(entries)

    def create_schedule(self) -> None:
        """新建一条其它日程。"""
        dialog = ScheduleDialog(self)
        if not dialog.exec():
            return
        try:
            item = self.context.schedule.add(
                dialog.title_text, due=dialog.due_text, note=dialog.note_text
            )
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "新建日程失败")
            return
        self.refresh_schedule()
        self.status_message.emit(f"已新建日程：{item.title}")

    def edit_schedule(self, item_id: str) -> None:
        store = self.context.schedule
        item = store.get(item_id)
        if item is None:
            common.warn(self, "这条日程已经不存在了（可能被删除或手工改过文件）。", "无法编辑")
            self.refresh_schedule()
            return
        dialog = ScheduleDialog(self, item=item)
        if not dialog.exec():
            return
        try:
            store.update(
                item_id,
                title=dialog.title_text,
                due=dialog.due_text,
                note=dialog.note_text,
            )
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "保存日程失败")
            return
        self.refresh_schedule()
        self.status_message.emit(f"已保存日程：{dialog.title_text}")

    def delete_schedule(self, item_id: str) -> None:
        store = self.context.schedule
        item = store.get(item_id)
        if item is None:
            self.refresh_schedule()
            return
        if not common.confirm(
            self,
            f"删除日程「{item.title}」？\n\n"
            "只删这一条日程记录，不会碰任何科目、书目或文件。",
            "删除日程",
            dangerous=True,
        ):
            return
        store.remove(item_id)
        self.refresh_schedule()
        self.status_message.emit(f"已删除日程：{item.title}")

    def _on_schedule_completion(self, kind: str, key: str, done: bool) -> None:
        """日程栏里的完成/取消完成。"""
        try:
            if kind == "homework":
                hw.set_done(Path(key), done)
                book = self._book_of_homework(Path(key))
                if book is not None:
                    bus.emit(
                        "book_content_changed", subject=book[0], book=book[1]
                    )
            else:
                self.context.schedule.set_done(key, done)
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "更新完成状态失败")
            return
        self.refresh_schedule()
        self.status_message.emit("已标记为完成" if done else "已标记为未完成")

    def _book_of_homework(self, folder: Path) -> tuple[str, str] | None:
        """反查一个作业文件夹属于哪个科目的哪本书（用于广播刷新）。"""
        try:
            for subject in self.context.library.subjects():
                for book in subject.books:
                    if book.path in folder.parents:
                        return subject.name, book.name
        except Exception:  # noqa: BLE001
            log.exception("反查作业所属书目失败")
        return None

    def _on_schedule_open_homework(self, entry) -> None:
        """日程栏里的「打开」：**在软件内部**打开那个作业。

        需求："日程栏打开按键点击后在软件内打开对应 Book 的 homework 栏目，
        不是打开本地文件夹"。

        所以这里不再调资源管理器，而是发一个信号给主窗口，
        由它切到「科目 → 书目 → 作业栏目」，并定位到那条作业。
        """
        if entry is None:
            return
        # 兼容两种入参：AgendaEntry（新）和直接给一个路径（旧调用方/测试）
        folder = getattr(entry, "folder", None)
        if folder is None:
            folder = entry
        self.homework_opened.emit(
            str(getattr(entry, "subject", "") or ""),
            str(getattr(entry, "book", "") or ""),
            str(folder) if folder is not None else "",
        )

    def auto_collapse_for_room(self) -> bool:
        """空间不够时自动把日程栏折叠起来。返回是否发生了折叠。

        需求背景（用户报障）："当页面大小调整后 日程栏目打开会遮挡 Subject"。

        根因有两层，都修了：

        1. 科目卡的网格**不肯变窄**（它的最小宽度是"所有卡片排一行"），
           于是网格比可见区域宽，右边的列被裁掉 —— 看起来就像被日程栏遮住；
        2. 即使网格会换行，**窗口太窄时 380px 的日程栏本身就该让位** ——
           科目卡片是主内容，日程栏是辅助信息。

        这一条处理第 2 层：放不下一列卡片 + 日程栏时，把日程栏折起来
        （折叠后只占 48px，空间立刻回来）。用户想展开时点一下就行，
         而且一旦空间够了它也不会自己弹回来（免得来回跳）。
        """
        panel = getattr(self, "schedule_panel", None)
        if panel is None or panel.collapsed:
            return False
        total = self.splitter.width()
        # 还没有真实宽度（启动早期、或当前不是首页）时不要动 ——
        # 否则布局尚未完成就会被判成"空间不够"，日程栏会莫名其妙地折起来。
        if total <= 0 or not self.isVisible():
            return False
        # 能同时放下"一列卡片 + 展开的日程栏"吗？
        if total - panel.EXPANDED_WIDTH >= self.SUBJECT_MIN_WIDTH:
            return False
        panel.set_collapsed(True)
        self._apply_schedule_width()
        self.status_message.emit("空间不够，日程栏已自动折叠（点 ‹ 可展开）")
        log.info("窗口太窄（splitter=%s），自动折叠日程栏", total)
        return True

    # ==================================================================
    # 日程栏宽度（需求：固定，只有折叠/展开两态）
    # ==================================================================

    def _sync_grid_width(self) -> None:
        """把科目区**视口的真实宽度**告诉网格，让它重新决定排几列。"""
        grid = getattr(self, "grid", None)
        scroll = getattr(self, "scroll", None)
        if grid is None or scroll is None:
            return
        try:
            width = int(scroll.viewport().width())
        except Exception:  # noqa: BLE001
            return
        if width > 0:
            grid.set_available_width(width)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt 接口
        """盯住滚动区视口的尺寸变化（科目区能有多宽由它决定）。"""
        try:
            if obj is self.scroll.viewport() and event.type() in (
                QEvent.Type.Resize, QEvent.Type.Show
            ):
                self._sync_grid_width()
        except Exception:  # noqa: BLE001 - 事件过滤器里不能抛
            pass
        return super().eventFilter(obj, event)

    def _apply_schedule_width(self) -> None:
        """把分隔条设成"左侧自适应、右侧固定"。

        **为什么要设两次**（第二次用 ``QTimer.singleShot(0, …)``）：
        ``setSizes()`` 是按"当时的控件约束"来分配的，而我们在折叠时刚刚
        改了 ``minimum/maximumWidth``，Qt 还没来得及重新布局 ——
        于是第一次调用会被它按**旧约束**算出来（实测折叠后右侧仍是 329px
        而不是 48px）。等一个事件循环、约束生效后再设一次才准。
        """
        panel = getattr(self, "schedule_panel", None)
        if panel is None:
            return
        self._do_apply_schedule_width()
        QTimer.singleShot(0, self._do_apply_schedule_width)

    def _do_apply_schedule_width(self) -> None:
        panel = getattr(self, "schedule_panel", None)
        if panel is None:
            return
        # 空间实在不够时，先把日程栏折起来再分配
        self.auto_collapse_for_room()
        width = (panel.COLLAPSED_WIDTH if panel.collapsed
                 else panel.EXPANDED_WIDTH)
        total = max(self.splitter.width(), 600)
        left = total - width
        # 科目区至少要放得下一列卡片 + 一点余量。
        # 否则窗口很窄时右边那 380px 会把科目区压到不足一列宽，
        # 卡片一列都显示不全（用户报障："日程栏打开会遮挡 Subject"）。
        floor = self.SUBJECT_MIN_WIDTH
        if left < floor:
            left = floor
        self.splitter.setSizes([left, width])
        self._sync_grid_width()

    def toggle_schedule_panel(self) -> None:
        """折叠 / 展开日程栏（点面板上的 » 或折叠条上的 ‹）。"""
        panel = getattr(self, "schedule_panel", None)
        if panel is None:
            return
        panel.toggle_collapsed()
        self._apply_schedule_width()
        self.status_message.emit(
            "日程栏已折叠" if panel.collapsed else "日程栏已展开"
        )

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt 接口
        """窗口尺寸变了就重新分配宽度（拖动窗口不能把固定宽度带歪）。"""
        super().resizeEvent(event)
        self._apply_schedule_width()

    def _on_schedule_submit(self, folder, url: str) -> None:
        """日程栏里的「提交」：复用书目页那套确认框。"""
        from gwp.ui.dialogs.submit_dialog import SubmitHomeworkDialog
        from gwp.services import shell_ops

        path = Path(folder) if folder is not None else None
        item = hw.load(path) if path is not None else None
        dialog = SubmitHomeworkDialog(self, homework=item, folder=path, url=url)
        dialog.exec()
        if dialog.choice != "submit" or not url:
            return
        if not shell_ops.open_url(url):
            common.warn(self, f"无法打开网址：\n{url}", "打开失败")

    # -- 卡片构建 -------------------------------------------------------

    def _box_card(self, box, members: list[Subject], width: int, height: int, radius: int):
        # 边框颜色用箱子主色：和卡片渐变色同源，但因为是描边所以一眼能区分
        card = BoxCard(
            box,
            members,
            cover=box.cover_path(self.context.paths.subjects_dir),
            width=width,
            height=height,
            radius=radius,
            border_color=box.color or "#4F7CFF",
        )
        card.subjects_dropped.connect(self._on_subjects_dropped)
        card.card_dropped.connect(
            lambda mime, payload, c=card: self._on_card_dropped(
                mime, payload, c, bool(getattr(c, "_drop_before", True))
            )
        )
        return card

    def _subject_card(self, subject: Subject, width: int, height: int, radius: int):
        card = SubjectCard(
            subject,
            cover=self.context.library.subject_cover_path(subject),
            width=width,
            height=height,
            radius=radius,
        )
        card.card_dropped.connect(
            lambda mime, payload, c=card: self._on_card_dropped(
                mime, payload, c, bool(getattr(c, "_drop_before", True))
            )
        )
        return card

    def _on_subjects_dropped(self, box_id: str, subject_names: list) -> None:
        """把拖到箱子上的科目收进去。"""
        self._move_into_box(box_id, [str(name) for name in subject_names])

    def _on_card_dropped(self, mime: str, payload: str, target, before: bool = True) -> None:
        """把拖过来的卡片放到 ``target`` 卡片的位置上（调整显示顺序）。

        ``before`` 表示落点在目标卡片的左半边（True）还是右半边（False），
        与拖动时显示的黄色竖条一致。

        规则：

        * 科目拖到**同类**科目上（都不在箱里）-> 调整科目顺序；
        * 科目拖到**同箱**科目上 -> **调整箱内顺序**；
        * 科目拖到**别的箱子**的科目上 -> 搬进那个箱子，并插到目标位置；
        * **收纳箱拖到科目上 / 科目拖到收纳箱卡片上（在最外层）-> 混排**：
          箱子与科目可以交替排列，顺序由同一套 order 决定；
        * 收纳箱拖到收纳箱上 -> 调整收纳箱顺序；
        * 科目拖到收纳箱上仍表示"收进箱子"（由 ``BoxCard`` 处理，不走这里）。
        """
        if mime == BOX_MIME:
            moved = payload
            if isinstance(target, BoxCard):
                if moved == target.box.id:
                    return
                self.context.library.boxes.move_before(moved, target.box.id)
                self.refresh()
                self.status_message.emit("已调整收纳箱顺序")
                return
            # 拖到科目上：箱子与科目混排，按落点在左/右决定插到前面还是后面
            target_subject = getattr(target, "subject", None)
            if target_subject is None:
                return
            library = self.context.library
            if before:
                library.box_before_subject(moved, target_subject.name)
            else:
                library.box_after_subject(moved, target_subject.name)
            self.refresh()
            self.status_message.emit(
                f"已把收纳箱排到「{target_subject.title}」"
                f"{'前面' if before else '后面'}"
            )
            return

        if mime == SUBJECT_MIME:
            moved = payload
            target_subject = getattr(target, "subject", None)
            if target_subject is None:
                return
            if moved == target_subject.name:
                return

            boxes = self.context.library.boxes
            target_box = boxes.box_of(target_subject.name)
            moved_box = boxes.box_of(moved)

            if target_box is None and moved_box is None:
                # 都在最外层：调整科目顺序（落点在右半边时插到目标后面）
                library = self.context.library
                if before:
                    library.move_subject_before(moved, target_subject.name)
                else:
                    library.subject_after(moved, target_subject.name)
                self.refresh()
                self.status_message.emit("已调整科目顺序")
                return

            if target_box is None:
                # 目标是未收纳的科目：把拖过来的科目移出箱子，再排到它旁边
                boxes.remove_subjects([moved])
                library = self.context.library
                if before:
                    library.move_subject_before(moved, target_subject.name)
                else:
                    library.subject_after(moved, target_subject.name)
                self.refresh()
                self.status_message.emit("已把科目移出收纳箱并排到目标位置")
                return

            # 目标在某个箱子里
            if moved_box is not None and moved_box.id == target_box.id:
                # 同一个箱子内拖动 = 箱内排序
                self._reorder_inside_box(
                    target_box.id, moved, target_subject.name, before
                )
                self.status_message.emit("已调整箱内顺序")
                return

            # 从别处（另一个箱子或最外层）拖进来：放进目标箱子并插到目标位置
            if moved_box is not None:
                boxes.remove_subjects([moved])
            boxes.move_subjects(target_box.id, [moved])
            self._reorder_inside_box(target_box.id, moved, target_subject.name, before)
            self.refresh()
            self.status_message.emit(f"已把「{moved}」移入「{target_box.title}」")

    def _reorder_inside_box(
        self, box_id: str, name: str, anchor: str, before: bool = True
    ) -> None:
        """把箱内 ``name`` 移到 ``anchor`` 之前/之后（箱内拖拽排序）。"""
        box = self.context.library.boxes.get(box_id)
        if box is None:
            return
        members = list(box.members)
        if name not in members or anchor not in members:
            return
        members.remove(name)
        index = members.index(anchor)
        members.insert(index if before else index + 1, name)
        self.context.library.boxes.reorder(box_id, members)
        self.refresh()

    def _build_top_level_cards(
        self, keyword: str, width: int, height: int, radius: int
    ) -> tuple[list, list[Subject]]:
        """最外层：收纳箱与未收纳的科目**混在一起**，按各自的 order 交替排列。

        箱子和科目的 order 是同一个坐标系（都由 ``set_home_order`` 维护），
        因此这里把它们合成一张列表统一排序，拖拽就能让箱子排到科目前面。
        """
        library = self.context.library
        pairs = library.boxes_with_members(refresh=False)

        # (order, 序号, 卡片, 成员) —— 序号用于同 order 时保持稳定
        entries: list[tuple[int, int, object, list[Subject]]] = []
        shown_subjects: list[Subject] = []
        counter = 0

        for box, members in pairs:
            if keyword:
                visible = [
                    member for member in members
                    if keyword in member.title.lower() or keyword in member.name.lower()
                ]
                # 箱子本身名命中，或箱内有匹配的科目，都保留这个箱子
                if keyword not in box.title.lower() and not visible:
                    continue
                members_to_show = visible or members
            else:
                members_to_show = members
            card = self._box_card(box, members_to_show, width, height, radius)
            entries.append((int(box.order or 0), counter, card, members))
            shown_subjects.extend(members)
            counter += 1

        for subject in library.unboxed_subjects():
            if keyword and not (
                keyword in subject.title.lower()
                or keyword in subject.description.lower()
                or keyword in subject.name.lower()
            ):
                continue
            card = self._subject_card(subject, width, height, radius)
            entries.append((int(subject.order or 0), counter, card, []))
            shown_subjects.append(subject)
            counter += 1

        entries.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in entries], shown_subjects

    def _build_box_cards(
        self, keyword: str, width: int, height: int, radius: int
    ) -> tuple[list, list[Subject]]:
        """箱内视图：只显示这个箱子里的科目。"""
        library = self.context.library
        members: list[Subject] = []
        for box, box_members in library.boxes_with_members(refresh=False):
            if box.id == self.current_box_id:
                members = box_members
                break
        if keyword:
            members = [
                member for member in members
                if keyword in member.title.lower()
                or keyword in member.description.lower()
                or keyword in member.name.lower()
            ]
        cards = [self._subject_card(subject, width, height, radius) for subject in members]
        return cards, members

    def _update_header(self, shown: list[Subject], keyword: str) -> None:
        total_books = sum(subject.book_count for subject in shown)
        # 需求：**日记单独计数，不算在科目里**。
        # 日记是"按天记录"的东西，和"上什么课"不是一回事，
        # 混在科目数里会让人以为多了一门课。
        diary_count = sum(
            1 for subject in shown if subject.subject_type == C.SUBJECT_DIARY
        )
        subject_count = len(shown) - diary_count
        parts = [f"{subject_count} 个科目"]
        if diary_count:
            parts.append(f"{diary_count} 个日记")
        counts_text = " · ".join(parts)

        in_box = self.current_box_id is not None
        box = self.context.library.boxes.get(self.current_box_id) if in_box else None

        # 箱内只留「✕ 关闭收纳箱」作为退出入口；最外层显示两个新建按钮
        self.btn_close_box.setVisible(in_box)
        self.btn_new_box.setVisible(not in_box)
        self.btn_new_subject.setVisible(not in_box)

        if in_box and box is not None:
            self.set_title(
                f"收纳箱：{box.title}",
                f"{counts_text} · {total_books} 本书目"
                if shown
                else "这个收纳箱还是空的",
                "我的科目 / 收纳箱　（点「✕ 关闭收纳箱」回到总览）",
            )
        else:
            box_count = len(self.context.library.boxes.load())
            self.set_title(
                "我的科目",
                f"共 {counts_text} · {total_books} 本书目"
                + (f" · {box_count} 个收纳箱" if box_count else "")
                if shown
                else "双击进入科目；右键卡片可以重命名、换图、删除",
            )

        self.empty_hint.setVisible(not shown)
        if keyword:
            self.empty_hint.setText("没有匹配的科目。")
        elif in_box:
            self.empty_hint.setText(
                "这个收纳箱还是空的。\n\n在最外层把科目拖到箱子上，"
                "或在科目的右键菜单里选「移入收纳箱…」。"
            )
        else:
            self.empty_hint.setText(
                "还没有科目。\n\n点击右上角「＋ 新建科目」创建第一个，"
                "或者直接把文件夹放进 data\\user data\\subjects 里再点刷新。"
            )

    def _on_search(self, _text: str) -> None:
        self.refresh()

    def on_shown(self) -> None:
        self.refresh()

    def refresh_settings(self) -> None:
        """设置改动后立即生效（不用重启）。"""
        clock = getattr(self, "clock_bar", None)
        if clock is not None:
            clock.setVisible(bool(self.context.config.get("ui.show_clock_bar", True)))
            clock.set_weather_enabled(
                bool(self.context.config.get("ui.weather_enabled", True))
            )
        self.refresh()

    # ==================================================================
    # 操作
    # ==================================================================

    def create_subject(self) -> None:
        dialog = SubjectDialog(self)
        if not dialog.exec():
            return
        values = dialog.values()
        try:
            subject = self.context.library.create_subject(
                values["name"],
                values["description"],
                values["color"],
                subject_type=values.get("subject_type", ""),
            )
        except Exception as exc:  # noqa: BLE001 - DataError / OSError 都要提示
            common.error(self, str(exc), "新建科目失败")
            return
        source: Path | None = values.get("cover_source")
        if source is not None and str(source) and source.is_file():
            try:
                self.context.library.set_subject_cover(subject.name, source)
            except Exception as exc:  # noqa: BLE001
                common.warn(self, f"科目已创建，但设置图片失败：{exc}")
        self.refresh()
        self.status_message.emit(
            f"已创建{C.type_label(subject.subject_type)}：{subject.title}"
        )

    def _open_subject(self, subject: Subject) -> None:
        if subject is not None:
            self.subject_opened.emit(subject.name)

    def _on_card_activated(self, card) -> None:
        """单击卡片：收纳箱立刻展开，科目只选中（双击才进入）。

        信号统一派发**卡片本身**，因此这里可以安全地按卡片类型分派。
        """
        if isinstance(card, BoxCard):
            self.enter_box(card.box.id)

    def _open_card(self, card) -> None:
        """双击卡片：科目进科目页，收纳箱进入箱内视图。"""
        if isinstance(card, BoxCard):
            self.enter_box(card.box.id)
            return
        subject = getattr(card, "subject", None)
        if subject is not None:
            self._open_subject(subject)

    def _card_menu(self, card, global_pos: QPoint) -> None:
        """右键卡片：按类型分发到科目菜单或收纳箱菜单。

        同时兼容**卡片**和**数据模型**（``Subject``/``Box``）：信号统一派发卡片本身，
        但历史调用方可能传模型。方法自己两种都认，避免再次出现
        "收到模型却按卡片判断 → 静默什么都不做"的右键失灵。
        """
        if isinstance(card, BoxCard):
            self._box_menu(card, global_pos)
            return
        # 卡片：直接取 .subject；模型（Subject）：本身就是科目
        subject = getattr(card, "subject", None)
        if subject is None and getattr(card, "name", ""):
            subject = card
        if subject is not None:
            self._subject_menu(subject, global_pos)
            return
        # 可能是 Box 模型（没有 subject 也不是卡片）
        box = getattr(card, "members", None)
        if box is not None:
            card_obj = BoxCard(card)
            self._box_menu(card_obj, global_pos)

    def _subject_menu_entries(self, subject: Subject) -> list:
        """科目的右键菜单项。

        拆成独立方法，既方便维护也便于测试直接检查菜单结构
        （不必真的弹出菜单）。

        收纳箱相关的两项**按数据事实出现**，不按"当前在哪个视图"：

        * 科目**真的在某个箱子里** -> 出现「移出收纳箱：<箱名> → 最外层」；
        * 科目没在任何箱子里 -> 出现「移入收纳箱 …」。

        这样即使在总览里也不会找不到"怎么拿出来"，同时两者互斥、不会混淆。
        """
        if subject is None:
            return []
        library = self.context.library
        current_box = library.boxes.box_of(subject.name)

        entries: list = [
            ("打开", lambda: self.subject_opened.emit(subject.name)),
            ("在新窗口打开", lambda: self._open_in_new_window(subject)),
            None,
        ]

        if current_box is not None:
            # 已经在箱子里：首要操作是"拿出来"
            entries.append(
                (
                    f"移出收纳箱：{current_box.title} → 最外层",
                    lambda: self._remove_from_box([subject.name]),
                )
            )
            others = [
                box for box in library.boxes.load() if box.id != current_box.id
            ]
            if others:
                entries.append(
                    (
                        "移动到其它收纳箱 …",
                        [
                            (
                                f"{box.title}（{box.member_count}）",
                                lambda _checked=False, bid=box.id: self._move_into_box(
                                    bid, [subject.name]
                                ),
                            )
                            for box in others
                        ],
                    )
                )
        else:
            boxes = library.boxes.load()
            submenu: list = [
                ("＋ 新建收纳箱并放入…", lambda: self._move_into_new_box([subject.name]))
            ]
            if boxes:
                submenu.append(None)
                for box in boxes:
                    submenu.append(
                        (
                            f"{box.title}（{box.member_count}）",
                            lambda _checked=False, bid=box.id: self._move_into_box(
                                bid, [subject.name]
                            ),
                        )
                    )
            else:
                submenu.append(("（还没有收纳箱）", None, False))
            entries.append(("移入收纳箱 …", submenu))

        entries.extend(
            [
                None,
                ("编辑名称/类型…", lambda: self._rename_subject(subject)),
                self._subject_type_entry(subject),
                ("更换卡片图片…", lambda: self._set_cover(subject)),
                ("移除卡片图片", lambda: self._clear_cover(subject)),
                ("修改说明…", lambda: self._edit_description(subject)),
                ("更换颜色…", lambda: self._change_color(subject)),
                None,
                ("置顶/取消置顶", lambda: self._toggle_pin(subject)),
                ("在资源管理器中打开", lambda: self._reveal(subject)),
                None,
                ("删除科目…", lambda: self._delete_subject(subject)),
            ]
        )
        return entries

    def _subject_type_entry(self, subject: Subject) -> tuple:
        """菜单里的"修改类型"项。

        日记类型的目录结构与普通科目完全不同，无法直接转换 ——
        这种情况给一个**禁用项**并写明原因，而不是让它消失
        （消失了用户只会困惑"为什么没有"）。
        """
        if subject.subject_type == C.SUBJECT_DIARY:
            return ("修改类型（日记不可转换）", None, False)
        return (
            f"修改类型…（当前：{subject.type_label}）",
            lambda: self._change_subject_type(subject),
        )

    def _subject_menu(self, subject: Subject, global_pos: QPoint) -> None:
        entries = self._subject_menu_entries(subject)
        if not entries:
            return
        menu = build_context_menu(self, entries)
        menu.exec(global_pos)

    def _install_box_shortcuts(self) -> None:
        """箱内快捷键：Esc 关闭收纳箱，Shift+Delete 把选中科目移出箱子。"""
        from PyQt6.QtGui import QKeySequence, QShortcut

        escape = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        escape.activated.connect(self.leave_box)

        remove = QShortcut(QKeySequence("Shift+Delete"), self)
        remove.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        remove.activated.connect(self.remove_selected_from_box)

    def remove_selected_from_box(self) -> None:
        """把当前选中的卡片对应的科目移出收纳箱（供快捷键与按钮调用）。"""
        selected = getattr(self.grid, "_selected", None)
        subject = getattr(selected, "subject", None)
        if subject is None:
            self.status_message.emit("请先单击选中要移出的科目")
            return
        if self.context.library.boxes.box_of(subject.name) is None:
            self.status_message.emit(f"「{subject.title}」不在任何收纳箱里")
            return
        self._remove_from_box([subject.name])

    def _box_menu(self, card: BoxCard, global_pos: QPoint) -> None:
        box = card.box
        entries: list = [
            ("打开收纳箱", lambda: self.enter_box(box.id)),
            None,
            ("重命名…", lambda: self._rename_box(box)),
            ("更换边框颜色…", lambda: self._change_box_color(box)),
            ("更换卡片图片…", lambda: self._set_box_cover(box)),
            ("移除卡片图片", lambda: self._clear_box_cover(box)),
            None,
            ("把箱内科目全部移出", lambda: self._empty_box(box)),
            None,
            (
                f"删除收纳箱（{box.member_count} 个科目会回到最外层）…",
                lambda: self._delete_box(box),
            ),
        ]
        menu = build_context_menu(self, entries)
        menu.exec(global_pos)

    # ==================================================================
    # 收纳箱
    # ==================================================================

    def enter_box(self, box_id: str) -> None:
        self.current_box_id = box_id
        self.search.clear()
        self.refresh()
        box = self.context.library.boxes.get(box_id)
        if box is not None:
            self.status_message.emit(f"已进入收纳箱：{box.title}")

    def leave_box(self) -> None:
        self.current_box_id = None
        self.search.clear()
        self.refresh()

    def create_box(self) -> None:
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, "新建收纳箱", "收纳箱名称（例如：数学基础）："
        )
        if not ok or not name.strip():
            return
        try:
            box = self.context.library.boxes.create(name.strip())
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "新建收纳箱失败")
            return
        self.refresh()
        self.status_message.emit(f"已创建收纳箱：{box.title}（右键科目可以放进去）")

    def _move_into_box(self, box_id: str, subject_names: list[str]) -> None:
        moved = self.context.library.boxes.move_subjects(box_id, subject_names)
        box = self.context.library.boxes.get(box_id)
        title = box.title if box is not None else box_id
        self.refresh()
        self.status_message.emit(f"已把 {moved} 个科目放入「{title}」")

    def _move_into_new_box(self, subject_names: list[str]) -> None:
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, "移入新收纳箱", "收纳箱名称（例如：数学基础）："
        )
        if not ok or not name.strip():
            return
        try:
            box = self.context.library.boxes.create(name.strip())
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "新建收纳箱失败")
            return
        self._move_into_box(box.id, subject_names)

    def _remove_from_box(self, subject_names: list[str]) -> None:
        count = self.context.library.boxes.remove_subjects(subject_names)
        self.refresh()
        if count:
            self.status_message.emit(f"已把 {count} 个科目移出收纳箱")

    def _rename_box(self, box) -> None:
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "重命名收纳箱", "新名称：", text=box.title)
        if not ok or not name.strip():
            return
        self.context.library.boxes.rename(box.id, name.strip())
        self.refresh()
        self.status_message.emit(f"收纳箱已重命名为：{name.strip()}")

    def _change_box_color(self, box) -> None:
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QColorDialog

        color = QColorDialog.getColor(
            QColor(box.color or "#4F7CFF"), self, "选择收纳箱边框颜色"
        )
        if not color.isValid():
            return
        self.context.library.boxes.set_color(box.id, color.name())
        self.refresh()

    def _set_box_cover(self, box) -> None:
        path = common.pick_open_image(self, "选择收纳箱卡片图片")
        if not path:
            return
        try:
            self.context.library.boxes.set_cover(box.id, Path(path))
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "设置图片失败")
            return
        self.refresh()

    def _clear_box_cover(self, box) -> None:
        self.context.library.boxes.set_cover(box.id, None)
        self.refresh()

    def _empty_box(self, box) -> None:
        if not box.members:
            common.info(self, "这个收纳箱已经是空的。")
            return
        if not common.confirm(
            self,
            f"把「{box.title}」里的 {box.member_count} 个科目全部移出？\n\n"
            "科目本身不会被删除，只是回到最外层。",
            "清空收纳箱",
        ):
            return
        self.context.library.boxes.remove_subjects(list(box.members))
        self.refresh()
        self.status_message.emit(f"已清空收纳箱：{box.title}")

    def _delete_box(self, box) -> None:
        if not common.confirm(
            self,
            f"删除收纳箱「{box.title}」？\n\n"
            f"箱内的 {box.member_count} 个科目会回到最外层，"
            "**科目和文件都不会被删除**。",
            "删除收纳箱",
        ):
            return
        released = self.context.library.boxes.delete(box.id)
        if self.current_box_id == box.id:
            self.current_box_id = None
        self.refresh()
        self.status_message.emit(
            f"已删除收纳箱「{box.title}」，{len(released)} 个科目回到最外层"
        )

    # -- 具体操作 -------------------------------------------------------

    def _open_in_new_window(self, subject: Subject) -> None:
        window = self.window()
        if hasattr(window, "open_subject_window"):
            window.open_subject_window(subject.name)
        else:
            self.status_message.emit("当前窗口不支持多窗口打开")

    def _rename_subject(self, subject: Subject) -> None:
        """编辑科目（名称 / 类型 / 说明 / 颜色 / 图片）。"""
        dialog = SubjectDialog(self, subject=subject)
        if not dialog.exec():
            return
        values = dialog.values()
        new_name = values["name"]
        new_type = values.get("subject_type", "")
        try:
            if new_name != subject.name:
                renamed = self.context.library.rename_subject(subject.name, new_name)
                target = renamed.name
            else:
                target = subject.name
            self.context.library.update_subject(
                target,
                description=values["description"],
                color=values["color"],
            )
            # 类型变了就一并应用（自学课 <-> 校修课；日记会被数据层拒绝）
            type_changed = bool(new_type) and new_type != subject.subject_type
            if type_changed:
                self.context.library.change_subject_type(target, new_type)
            source = values.get("cover_source")
            if source is not None:
                if str(source):
                    self.context.library.set_subject_cover(target, source)
                else:
                    self._remove_cover_file(target)
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "保存失败")
            return
        self.refresh()
        if type_changed:
            self.status_message.emit(
                f"已把「{new_name}」改为{C.type_label(new_type)}"
            )
        else:
            self.status_message.emit(f"已保存科目：{new_name}")

    def _change_subject_type(self, subject: Subject) -> None:
        """专门的"修改类型"入口：只改类型，不动别的字段。

        自学课与校修课目录结构相同，切换**不会移动或删除任何文件**。
        """
        if subject.subject_type == C.SUBJECT_DIARY:
            common.warn(
                self,
                "日记类型的目录结构（AI summary / AI diary / my diary / else diary）"
                "与普通科目完全不同，不能直接转换。\n\n"
                "如果需要，请新建一个目标类型的科目，再把文件手工搬过去。",
                "无法修改类型",
            )
            return

        options = [
            kind for kind in C.SUBJECT_TYPES
            if kind != C.SUBJECT_DIARY and kind != subject.subject_type
        ]
        if not options:
            common.info(self, "当前已经是唯一的可选类型。", "修改类型")
            return

        current_label = subject.type_label
        target_kind = options[0]
        target_label = C.type_label(target_kind)
        if not common.confirm(
            self,
            f"把「{subject.title}」从「{current_label}」改为「{target_label}」？\n\n"
            f"两者的目录结构完全相同，**不会移动或删除任何文件** ——\n"
            f"只是「{C.HOMEWORK_FOLDER}」这个栏目在界面上"
            f"从「{'练习' if subject.subject_type == C.SUBJECT_SELF_STUDY else '作业'}」"
            f"变成「{'练习' if target_kind == C.SUBJECT_SELF_STUDY else '作业'}」。",
            "修改科目类型",
        ):
            return
        try:
            self.context.library.change_subject_type(subject.name, target_kind)
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "修改类型失败")
            return
        self.refresh()
        self.status_message.emit(
            f"已把「{subject.title}」改为{target_label}"
        )

    def _set_cover(self, subject: Subject) -> None:
        path = common.pick_open_image(self, "选择科目卡片图片")
        if not path:
            return
        try:
            self.context.library.set_subject_cover(subject.name, path)
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "设置图片失败")
            return
        self.refresh()
        self.status_message.emit("卡片图片已更新")

    def _clear_cover(self, subject: Subject) -> None:
        self._remove_cover_file(subject.name)
        self.refresh()
        self.status_message.emit("已移除卡片图片")

    def _remove_cover_file(self, subject_name: str) -> None:
        asset_dir = self.context.paths.subject_asset_dir(subject_name)
        if asset_dir.exists():
            for file in asset_dir.glob("*"):
                try:
                    if file.is_file():
                        file.unlink()
                except OSError:
                    continue
        try:
            self.context.library.update_subject(subject_name, cover="")
        except Exception:  # noqa: BLE001
            log.exception("清除卡片图片记录失败")

    def _edit_description(self, subject: Subject) -> None:
        dialog = SubjectDialog(self, subject=subject)
        if dialog.exec():
            self._rename_subject(subject)

    def _change_color(self, subject: Subject) -> None:
        from PyQt6.QtGui import QColor
        from PyQt6.QtWidgets import QColorDialog

        color = QColorDialog.getColor(QColor(subject.color or "#4F7CFF"), self, "选择卡片颜色")
        if not color.isValid():
            return
        self.context.library.update_subject(subject.name, color=color.name())
        self.refresh()

    def _toggle_pin(self, subject: Subject) -> None:
        self.context.library.update_subject(subject.name, pinned=not subject.pinned)
        self.refresh()

    def _reveal(self, subject: Subject) -> None:
        from gwp.services import file_ops

        file_ops.reveal_in_explorer(subject.path)

    def _subject_delete_warning(self, subject: Subject) -> tuple[str, str, bool]:
        """拼出删除科目的警告文案。

        返回 ``(主文案, 详细信息, 是否非空)``。

        要点：**文案必须与实际行为一致** —— 能进回收站才说"可还原"，
        否则明确警告"永久删除"，不能让用户在以为能还原的情况下丢掉数据。
        """
        from gwp.services import shell_ops

        book_count = len(getattr(subject, "books", []) or [])
        file_count = sum(
            sum(book.item_counts.values()) for book in (subject.books or [])
        ) + int(getattr(subject, "file_count", 0) or 0)
        has_content = bool(book_count or file_count)

        recyclable = shell_ops.can_use_recycle_bin()
        if recyclable:
            outcome = "删除后会移入系统回收站，可从回收站还原。"
        else:
            outcome = "⚠ 当前**无法使用回收站**，删除后将**永久丢失、无法还原**。"

        title = f"确定要删除科目「{subject.title}」吗？"
        lines = [
            title,
            "",
            f"类型：{subject.type_label}",
            f"包含书目：{book_count} 本",
            f"其中文件：约 {file_count} 个",
            "",
            outcome,
        ]
        if has_content:
            lines += ["", "这个科目里有内容，请再确认一次。"]
        detail = "\n".join(
            [
                f"科目目录：{subject.path}",
                f"类型：{subject.type_label}",
                f"书目列表：{'、'.join(b.title for b in (subject.books or [])) or '（无）'}",
            ]
        )
        return "\n".join(lines), detail, has_content

    def _delete_subject(self, subject: Subject) -> None:
        if bool(self.context.config.get("ui.confirm_on_delete", True)):
            message, detail, has_content = self._subject_delete_warning(subject)
            # dangerous=True：默认按钮是「取消」，直接回车不会误删
            if not common.confirm(
                self, message, "删除科目", dangerous=True, detail=detail
            ):
                return
            if has_content:
                # 非空科目再确认一次：删除会连带丢掉里面所有书目
                if not common.confirm(
                    self,
                    f"「{subject.title}」里有 {len(subject.books or [])} 本书目，"
                    "删除后它们会一起消失。\n\n真的要删除吗？",
                    "再次确认删除",
                    dangerous=True,
                ):
                    return
        try:
            self.context.library.delete_subject(subject.name, to_recycle=True)
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "删除失败")
            return
        self.refresh()
        self.status_message.emit(f"已删除科目：{subject.title}")


__all__ = ["HomeView"]
