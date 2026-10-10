"""首页右侧的日程栏：把所有作业与"其它日程"合并成一条按 DDL 排序的清单。

两件来源
--------

* **作业**：扫描所有科目 / 书目下的 ``homework/<作业名>/homework.json``；
* **其它日程**：数据根目录的 ``schedule.json``（见 :mod:`gwp.data_manager.schedule`）。

两者都用同一套排序规则（未完成在前 → DDL 早的在前 → 没 DDL 的排最后），
所以"下周三要交的作业"和"明天要办的杂事"会自然混在一起按时间排开。

每条都有一个**完成按键**：作业是「完成作业」，其它日程是「完成」。
完成后置底并划线，可以用顶部的开关隐藏起来。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from gwp.data_manager import homework as hw
from gwp.data_manager import schedule as sch
from gwp.ui import common

log = logging.getLogger(__name__)

#: 逾期 / 临期的强调色
_OVERDUE = "#B3261E"
_SOON = "#8A6100"
_MUTED = "#8A8F98"


@dataclass
class AgendaEntry:
    """日程栏里的一行（作业或其它日程的统一视图）。"""

    kind: str                 # "homework" | "schedule"
    title: str
    due: str = ""
    done: bool = False
    #: 作业专用
    folder: Path | None = None
    subject: str = ""
    book: str = ""
    submit_url: str = ""
    #: 其它日程专用
    item_id: str = ""
    note: str = ""

    @property
    def is_homework(self) -> bool:
        return self.kind == "homework"

    @property
    def due_at(self) -> datetime | None:
        return hw.parse_due(self.due)

    @property
    def due_label(self) -> str:
        moment = self.due_at
        if moment is None:
            return "未设 DDL" if self.is_homework else "未设时间"
        return moment.strftime("%Y-%m-%d %H:%M").replace(" 00:00", "")

    @property
    def due_label_short(self) -> str:
        """紧凑的截止时间：``10-11 18:20``。

        日程栏面板最窄只有 ~340px，而「2026-10-11 18:20」这种完整格式
        单独就占 260px（实测），会和来源、按钮一起把行撑破。
        当年的日期省略年份，省下约 40% 宽度。
        """
        moment = self.due_at
        if moment is None:
            return "未设 DDL" if self.is_homework else "未设时间"
        now = datetime.now()
        if moment.year == now.year:
            if (moment.hour, moment.minute) == (0, 0):
                return moment.strftime("%m-%d")
            return moment.strftime("%m-%d %H:%M")
        return moment.strftime("%Y-%m-%d")

    def state(self, now: datetime | None = None) -> str:
        if self.done:
            return "done"
        moment = self.due_at
        if moment is None:
            return "none"
        reference = now or datetime.now()
        if moment < reference:
            return "overdue"
        if moment - reference <= hw.DUE_SOON:
            return "soon"
        return "ok"

    @property
    def origin_label(self) -> str:
        if self.is_homework:
            if self.subject and self.book:
                return f"{self.subject} / {self.book}"
            return "作业"
        return "其它日程"

    def sort_key(self):
        return sch.sort_key(self.done, self.due_at, self.title)


class SchedulePanel(QFrame):
    """首页右侧的日程栏。"""

    #: 用户点了完成/取消完成：kind, 标识（作业是文件夹路径字符串，日程是 id）, 新状态
    completion_changed = pyqtSignal(str, str, bool)
    #: 请求在**软件内部**打开这个作业（参数是作业文件夹路径）
    homework_opened = pyqtSignal(object)
    #: 请求折叠 / 展开整个日程栏（宽度由 HomeView 管）
    collapse_toggled = pyqtSignal()
    #: 请求提交作业（folder, url）
    submit_requested = pyqtSignal(object, str)
    #: 请求编辑某条日程（id）
    schedule_edit_requested = pyqtSignal(str)
    #: 请求删除某条日程（id）
    schedule_delete_requested = pyqtSignal(str)

    #: 日程栏的**两个固定宽度**（像素）。
    #:
    #: 需求："调节日程栏宽度固定，只有全部折叠和完全展开 不能调整宽度"。
    #: 所以宽度只有这两个确定的值，由 :meth:`set_collapsed` 在两者之间切换；
    #: 分隔条不再允许拖动（原来宽度是连续的，用户明确不要这个自由度）。
    EXPANDED_WIDTH = 380
    COLLAPSED_WIDTH = 48

    def __init__(self, parent: QWidget | None = None, config=None) -> None:
        super().__init__(parent)
        #: 配置对象（可选）。用来读 ``ui.schedule_row_height`` 这类可调项。
        #: 传 None 时全部走默认值，方便单独测试这个控件。
        self._config = config
        self.setObjectName("Panel")
        #: 当前是否已折叠。折叠时只留一个竖排的「展开」窄条。
        self._collapsed = False

        # 折叠态和展开态用**同一套控件**，只是显隐 + 改宽度。
        # 换成两套控件会让"折叠时日程还在不在列表里"变得含糊，
        # 也会让测试和外部代码摸不到 schedule_panel 的成员。
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---- 折叠态：一条竖排窄条，点一下展开 ----
        #
        # 做成"竖向页签"的样子：顶部一个展开箭头、中间竖排的「日程」字样、
        # 底部未完成数量。这样折叠后**仍然一眼知道这一条是什么**，
        # 而不是只剩一个孤零零的箭头（用户看不出那是日程栏）。
        self.fold_bar = QFrame()
        self.fold_bar.setObjectName("ScheduleFoldBar")
        fold_layout = QVBoxLayout(self.fold_bar)
        fold_layout.setContentsMargins(2, 8, 2, 10)
        fold_layout.setSpacing(6)

        self.btn_unfold = QToolButton()
        self.btn_unfold.setObjectName("ScheduleUnfold")
        self.btn_unfold.setText("‹")
        self.btn_unfold.setToolTip("展开日程栏")
        self.btn_unfold.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_unfold.clicked.connect(self.collapse_toggled.emit)
        fold_layout.addWidget(self.btn_unfold, 0, Qt.AlignmentFlag.AlignHCenter)

        # 竖排文字：把「日程」两字上下排。用 QLabel + 换行最简单可靠
        # （QPainter 旋转文字在离屏渲染下不好验证，这个不需要）。
        self.lbl_fold_caption = QLabel("日\n程")
        self.lbl_fold_caption.setObjectName("ScheduleFoldCaption")
        self.lbl_fold_caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.lbl_fold_caption.setToolTip("日程栏（已折叠）")
        fold_layout.addWidget(self.lbl_fold_caption, 0,
                              Qt.AlignmentFlag.AlignHCenter)

        fold_layout.addStretch(1)

        self.lbl_fold_count = QLabel("")
        self.lbl_fold_count.setObjectName("ScheduleFoldCount")
        self.lbl_fold_count.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.lbl_fold_count.setToolTip("未完成的条数")
        fold_layout.addWidget(self.lbl_fold_count, 0,
                              Qt.AlignmentFlag.AlignHCenter)
        root.addWidget(self.fold_bar)

        # ---- 展开态：完整面板 ----
        self.expanded = QWidget()
        layout = QVBoxLayout(self.expanded)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(8)

        # 日期 / 时间 / 天气条挂在这里（由 HomeView 用 set_clock_bar 放进来）。
        #
        # **为什么把时钟条并进日程栏**：它原来是右列里独立的一行，
        # 最小宽度 329px。折叠日程栏时那一行仍然把整列撑在 329px，
        # 于是 48px 的窄条贴在列的左边、右边空出近 300px 的空白 ——
        # 用户看到的"白色竖条没靠右"就是这个空白。
        # 并进来之后两者一起显隐，整列就真的只有 48px 宽了。
        self.clock_holder = QWidget()
        clock_layout = QVBoxLayout(self.clock_holder)
        clock_layout.setContentsMargins(0, 0, 0, 0)
        clock_layout.setSpacing(0)
        layout.addWidget(self.clock_holder)

        # ---- 标题行 ----
        head = QHBoxLayout()
        head.setSpacing(8)
        self.lbl_title = QLabel("日程")
        self.lbl_title.setObjectName("Title")
        head.addWidget(self.lbl_title)
        self.lbl_count = QLabel("")
        self.lbl_count.setObjectName("Muted")
        head.addWidget(self.lbl_count)
        head.addStretch(1)

        self.btn_new = QPushButton("＋ 新建日程")
        self.btn_new.setProperty("accent", True)
        self.btn_new.setToolTip("新建一条与科目无关的日程（考试、报名截止、要办的事……）")
        head.addWidget(self.btn_new)

        # 「全部折叠」：唯一能把日程栏收起来的入口（需求只要折叠/展开两态）
        self.btn_fold = QToolButton()
        self.btn_fold.setObjectName("ScheduleFold")
        self.btn_fold.setText("»")
        self.btn_fold.setToolTip("折叠日程栏（只留一条窄边，点它再展开）")
        self.btn_fold.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.btn_fold.clicked.connect(self.collapse_toggled.emit)
        head.addWidget(self.btn_fold)
        layout.addLayout(head)

        # ---- 过滤器 ----
        filters = QHBoxLayout()
        filters.setSpacing(8)
        self.check_hide_done = QCheckBox("隐藏已完成")
        self.check_hide_done.setToolTip("只看还没做完的事情")
        filters.addWidget(self.check_hide_done)
        filters.addStretch(1)
        layout.addLayout(filters)

        # ---- 列表 ----
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")
        self.list_host = QWidget()
        self.list_layout = QVBoxLayout(self.list_host)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(6)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_host)
        layout.addWidget(self.scroll, 1)

        self.empty_hint = QLabel(
            "还没有日程。\n\n点「＋ 新建日程」加一条待办；\n"
            "校修课里创建的作业会自动出现在这里。"
        )
        self.empty_hint.setObjectName("EmptyHint")
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_hint.setWordWrap(True)
        layout.addWidget(self.empty_hint)

        # 展开态才是要被添加进 SchedulePanel 的那一半
        root.addWidget(self.expanded, 1)

        self._rows: list[QWidget] = []
        self.check_hide_done.toggled.connect(lambda _checked: self._restyle_done())
        self.set_collapsed(False)

    # ------------------------------------------------------------------
    # 折叠 / 展开（需求：只有这两态，宽度不可拖）
    # ------------------------------------------------------------------

    def set_clock_bar(self, bar: QWidget) -> None:
        """把"日期 / 时间 / 天气"条挂进展开态（见 ``clock_holder`` 的说明）。"""
        self.clock_bar = bar
        bar.setParent(self.clock_holder)
        holder_layout = self.clock_holder.layout()
        if holder_layout is not None:
            holder_layout.addWidget(bar)

    @property
    def collapsed(self) -> bool:
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        """切换到折叠或展开。

        折叠态**只保留一条窄边**（一个「‹」按钮 + 未完成数量），
        展开态是完整面板（含上面的时钟条）。两态宽度都是固定值，
        中间没有过渡 —— 这正是需求要的"只有全部折叠和完全展开，不能调整宽度"。
        """
        self._collapsed = bool(collapsed)
        self.fold_bar.setVisible(self._collapsed)
        self.expanded.setVisible(not self._collapsed)
        width = self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH
        self.setMinimumWidth(width)
        self.setMaximumWidth(width)
        self.updateGeometry()

    def toggle_collapsed(self) -> None:
        self.set_collapsed(not self._collapsed)

    def _update_fold_badge(self) -> None:
        """折叠窄条上的未完成数量（让折叠态也有一点点信息量）。"""
        label = getattr(self, "lbl_fold_count", None)
        if label is None:
            return
        try:
            pending = sum(
                1 for row in self._rows
                if getattr(row, "entry", None) is not None and not row.entry.done
            )
        except Exception:  # noqa: BLE001
            pending = 0
        label.setText(str(pending) if pending else "")
        label.setVisible(bool(pending))

    def _row_height(self) -> int:
        """单个任务行的**最小**高度。

        需求："可以加高单个任务的大小"。
        配置项 ``ui.schedule_row_height``（默认 88px），下限 44。

        注意这是 ``setMinimumHeight`` 而不是固定高度 —— 内容比这还多时
        （标题很长换行、有备注）行会**自动更高**，不会把文字裁掉。
        所以"空间不够"时不需要用户去改配置。
        """
        try:
            value = int(self._config.get("ui.schedule_row_height", 88) or 88)
        except (TypeError, ValueError, AttributeError):
            value = 88
        return max(44, value)

    def set_entries(self, entries: list[AgendaEntry]) -> None:
        """用新数据重建整个列表。"""
        for widget in self._rows:
            self.list_layout.removeWidget(widget)
            widget.setParent(None)
            widget.deleteLater()
        self._rows.clear()

        pending = [e for e in entries if not e.done]
        self.lbl_count.setText(f"（待办 {len(pending)} / 共 {len(entries)}）")

        shown = [
            entry for entry in entries
            if not (entry.done and self.check_hide_done.isChecked())
        ]
        for entry in shown:
            row = self._build_row(entry)
            # 把 entry 挂在行上：折叠窄条要统计未完成数量，测试也用它。
            row.entry = entry                      # type: ignore[attr-defined]
            # 插到末尾那个 stretch 之前
            self.list_layout.insertWidget(self.list_layout.count() - 1, row)
            self._rows.append(row)

        self.empty_hint.setVisible(not shown)
        self.scroll.setVisible(bool(shown))
        self._restyle_done()
        self._update_fold_badge()

    def _restyle_done(self) -> None:
        """已完成的条目划线、变灰，让"还剩什么"一眼可见。"""
        hide = self.check_hide_done.isChecked()
        for row in self._rows:
            done = bool(row.property("entryDone"))
            row.setVisible(not (done and hide))
            label = row.findChild(QLabel, "AgendaTitle")
            if label is None:
                continue
            font = label.font()
            font.setStrikeOut(done)
            label.setFont(font)
            label.setEnabled(not done)
            if not done:
                label.setStyleSheet("")

    # ------------------------------------------------------------------

    def _build_row(self, entry: AgendaEntry) -> QWidget:
        row = QFrame()
        row.setObjectName("AgendaRow")
        row.setProperty("entryDone", entry.done)
        row.setProperty("entryState", entry.state())

        # 行高：内容有三行（标题 / 来源+DDL / 备注），太矮会显得挤，
        # 也难点击。给一个下限，高度可在 config 的
        # ``ui.schedule_row_height`` 里调（默认 76px）。
        row.setMinimumHeight(self._row_height())

        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        # 完成勾选框（与下面的按钮是同一个动作，两种习惯都能用）
        check = QCheckBox()
        check.setChecked(entry.done)
        check.setToolTip("取消完成" if entry.done else "标记为完成")
        check.toggled.connect(
            lambda checked, e=entry: self._emit_completion(e, checked)
        )
        layout.addWidget(check, 0, Qt.AlignmentFlag.AlignTop)

        column = QVBoxLayout()
        column.setSpacing(2)

        state = entry.state()
        due_short = entry.due_label_short

        # ---- 文本区：标题 + 元信息（来源 · DDL）----
        #
        # 这里踩了两个坑，都记下来：
        #
        # 坑 1：把「来源 / DDL」和按钮塞在同一个 QHBoxLayout 里 ——
        #       按钮是 Fixed 策略、先把宽度拿走，剩给标签的是 0，
        #       DDL 完全看不见（用户截图反馈："这里要显示 DDL"）。
        #
        # 坑 2：把元信息拆成"独立一行 + 两个 QLabel"仍然不显示 ——
        #       当行宽恰好等于最小宽度时，QLabel 会被压成 0 宽；
        #       设成 Ignored 就永远 0 宽，设成 Fixed 又会把行撑到 583px
        #       反过来撑破 310px 的面板。两个极端都不对。
        #
        # 最终方案（第三版，也是稳定版）：
        #   * 标题 + 元信息合并成**一个富文本 QLabel**（自己就能换行）；
        #   * 这个标签**包一层容器**，容器设 Ignored 尺寸策略。
        #
        # 为什么必须包一层：直接把标签设成 Ignored，布局会把它的宽度压到
        # **0**（实测行宽 37px，只显示了开头几个字）；
        # 而设成 Preferred，标签的 sizeHint 又会驱动**行的最小宽度**，
        # 让行撑到 583px 反过来撑破 310px 的面板。
        #
        # 包一层之后职责就分开了：
        #   * 行宽由「勾选框 + 按钮 + 边距」决定（这是真正的最小值，约 220px）；
        #   * 容器把可用的列宽**全部给标签**，标签在内部正常换行、永远看得见。
        plain = QLabel()
        plain.setObjectName("AgendaText")
        plain.setTextFormat(Qt.TextFormat.RichText)
        plain.setWordWrap(True)
        plain.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        plain.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        plain.setMinimumWidth(0)
        plain.setProperty("entryTitle", entry.title)

        title_html = common.html_escape(entry.title)
        if state == "overdue" and not entry.done:
            title_html = f"<span style='color:{_OVERDUE};'>{title_html}</span>"
        origin_html = (
            f"<span style='color:{_MUTED};'>{common.html_escape(entry.origin_label)}</span>"
        )

        # DDL **单独一行 + 加粗**（需求）：
        # 之前 DDL 和"来源"挤在同一行，来源名字一长就把 DDL 顶到下一行
        # （用户截图：『高等代数 / 高等代数』换行后，DDL 被挤成孤零零一行，
        # 看起来像排版坏了）。分开之后两者互不影响，各自一行更清楚。
        if entry.done:
            due_html = f"<b><span style='color:{_MUTED};'>已完成</span></b>"
        elif state == "overdue":
            due_html = (
                f"<b><span style='color:{_OVERDUE};'>"
                f"DDL {due_short}（已过期）</span></b>"
            )
        elif state == "soon":
            due_html = (
                f"<b><span style='color:{_SOON};'>"
                f"DDL {due_short}（即将截止）</span></b>"
            )
        elif state == "none":
            due_html = (
                f"<b><span style='color:{_MUTED};'>"
                f"{'未设 DDL' if entry.is_homework else '未设时间'}</span></b>"
            )
        else:
            due_html = f"<b><span style='color:{_MUTED};'>DDL {due_short}</span></b>"

        lines = [f"<b>{title_html}</b>", origin_html, due_html]
        if entry.note:
            note_text = common.html_escape(entry.note.replace("\n", " ")[:60])
            lines.append(f"<span style='color:{_MUTED};'>{note_text}</span>")
        plain.setText("<br/>".join(lines))
        plain.setToolTip(
            f"{entry.title}\n来源：{entry.origin_label}\n截止：{entry.due_label}"
            + (f"\n备注：{entry.note}" if entry.note else "")
        )
        if entry.done:
            font = plain.font()
            font.setStrikeOut(True)
            plain.setFont(font)

        text_holder = QWidget()
        text_layout = QVBoxLayout(text_holder)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)
        text_layout.addWidget(plain)
        text_holder.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        column.addWidget(text_holder)

        layout.addLayout(column, 1)

        # ---- 按键区（横排，紧跟在元信息后面）----
        # 竖排会让每行的最小宽度被三个按钮撑到 500px 以上：面板一窄就把最右边的
        # 按钮裁掉（这是第一版实测出来的问题）。横排 + 短文案才是稳的。
        buttons = QHBoxLayout()
        buttons.setSpacing(4)
        buttons.setContentsMargins(0, 0, 0, 0)

        done_btn = QPushButton("已完成 ✓" if entry.done else "完成")
        done_btn.setToolTip(
            "取消完成标记"
            if entry.done
            else (
                "标记为完成（作业会同时记入 homework.json）"
                if entry.is_homework
                else "标记为完成"
            )
        )
        done_btn.setProperty("accent", not entry.done)
        done_btn.clicked.connect(
            lambda _checked=False, e=entry: self._emit_completion(e, not e.done)
        )
        buttons.addWidget(done_btn)

        if entry.is_homework:
            open_btn = QPushButton("打开")
            # 需求："日程栏打开按键点击后在软件内打开对应 Book 的 homework 栏目，
            #       不是打开本地文件夹"
            open_btn.setToolTip(
                f"在软件内打开「{entry.subject} / {entry.book}」的作业栏目"
                + (f"，定位到「{entry.title}」" if entry.title else "")
            )
            open_btn.clicked.connect(
                lambda _checked=False, e=entry: self.homework_opened.emit(e)
            )
            buttons.addWidget(open_btn)
            if entry.submit_url:
                submit_btn = QPushButton("提交")
                submit_btn.setToolTip(f"提交作业：\n{entry.submit_url}")
                submit_btn.clicked.connect(
                    lambda _checked=False, e=entry: self.submit_requested.emit(
                        e.folder, e.submit_url
                    )
                )
                buttons.addWidget(submit_btn)
        else:
            edit_btn = QPushButton("编辑")
            edit_btn.setToolTip("修改这条日程的名称 / 时间 / 备注")
            edit_btn.clicked.connect(
                lambda _checked=False, e=entry: self.schedule_edit_requested.emit(e.item_id)
            )
            buttons.addWidget(edit_btn)
            del_btn = QPushButton("删除")
            del_btn.setToolTip("删除这条日程")
            del_btn.clicked.connect(
                lambda _checked=False, e=entry: self.schedule_delete_requested.emit(
                    e.item_id
                )
            )
            buttons.addWidget(del_btn)

        # 按钮放在内容区**右边**（不在元信息行里，避免抢宽度把 DDL 压成 0）
        layout.addLayout(buttons)

        # 允许整行被压缩：否则行宽锁死在 sizeHint 上，面板再窄也不缩，右侧被裁掉
        row.setMinimumWidth(0)
        return row

    def _emit_completion(self, entry: AgendaEntry, done: bool) -> None:
        if done == entry.done:
            return
        if entry.is_homework:
            self.completion_changed.emit("homework", str(entry.folder), done)
        else:
            self.completion_changed.emit("schedule", entry.item_id, done)


# --------------------------------------------------------------------------
# 收集与排序
# --------------------------------------------------------------------------

def collect_entries(
    library,
    store: sch.ScheduleStore | None = None,
    now: datetime | None = None,
) -> list[AgendaEntry]:
    """把全部作业 + 全部其它日程收集成一个按 DDL 排好序的列表。"""
    entries: list[AgendaEntry] = []

    # 作业：走已有的科目 / 书目扫描，不在界面上自己遍历文件系统
    try:
        subjects = library.subjects(refresh=True)
    except Exception:  # noqa: BLE001 - 扫描失败不该让首页崩
        log.exception("收集作业失败")
        subjects = []
    for subject in subjects:
        for book in getattr(subject, "books", []):
            for item in hw.list_homework(book.path):
                entries.append(
                    AgendaEntry(
                        kind="homework",
                        title=item.name,
                        due=item.due,
                        done=item.done,
                        folder=item.path,
                        subject=subject.name,
                        book=book.name,
                        submit_url=item.submit_url,
                    )
                )

    if store is not None:
        try:
            for item in store.load():
                entries.append(
                    AgendaEntry(
                        kind="schedule",
                        title=item.title,
                        due=item.due,
                        done=item.done,
                        item_id=item.id,
                        note=item.note,
                    )
                )
        except Exception:  # noqa: BLE001
            log.exception("读取其它日程失败")

    entries.sort(key=lambda entry: entry.sort_key())
    return entries


__all__ = ["AgendaEntry", "SchedulePanel", "collect_entries"]
