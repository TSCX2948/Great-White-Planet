"""文件表格控件：展示书目内的条目（简介、总结、文件夹内容）。"""

from __future__ import annotations

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from gwp.data_manager import homework as hw
from gwp.data_manager.models import BookItem
from gwp.ui import common

#: 作业栏目专属列追加在通用列之后
_DUE_COLUMN_TITLE = "DDL"
_SUBMIT_COLUMN_TITLE = "提交方式"

#: 提交列里那个按钮的文字与高度（网址本身太长，只做按钮）
_SUBMIT_BUTTON_TEXT = "提交作业"
_SUBMIT_BUTTON_HEIGHT = 24
#: 提交列的固定宽度：容得下按钮 + 少量留白，不被长网址撑开
_SUBMIT_COLUMN_WIDTH = 92

#: 作业完成状态的字色（需求："已完成的作业取消颜色标记 用绿色字体标已完成
#: 未完成的作业用红色字体标未完成"）
_DONE_COLOR = QBrush(QColor("#1E8E3E"))      # 已完成：绿
_UNDONE_COLOR = QBrush(QColor("#C5221F"))    # 未完成：红
_DONE_TEXT = "已完成"
_UNDONE_TEXT = "未完成"

#: 逾期 / 即将截止的行色（浅色底 + 深色字，深浅主题下都可读）
_OVERDUE_TEXT_COLOR = QColor("#B3261E")
_SOON_TEXT_COLOR = QColor("#8A6100")

#: 未完成且临近/超过 DDL 时的**整行底色**。
#:
#: 需求："已完成的作业取消颜色标记 用绿色字体标已完成
#: 未完成的作业用红色字体标未完成" + "但是未完成 快到DDL的还是要染色"。
#:
#: 两句话合起来就是一条规则：**只有"未完成"才染色**。
#: 已经交了的作业不该再被"快到截止了"追着跑 —— 底色的作用是催办，
#: 交完就不需要催了。
_OVERDUE_BRUSH = QBrush(QColor("#FFE1E1"))
_SOON_BRUSH = QBrush(QColor("#FFF4D6"))


class FileTable(QTableWidget):
    """条目列表：名称 / 类型 / 大小 / 修改时间。

    ``set_homework_mode(True)`` 后会追加两列 —— 「DDL」与「提交方式」，
    并按截止情况给整行上色（逾期浅红、24 小时内浅黄）。
    """

    open_requested = pyqtSignal(object)          # BookItem
    context_requested = pyqtSignal(object, QPoint)
    double_clicked_item = pyqtSignal(object)
    #: 点击「提交方式」列里的链接：(作业文件夹, 网址)
    submit_link_clicked = pyqtSignal(object, str)
    #: 外部文件被拖到表格上：(落点坐标（视口坐标系）, mimeData)
    #: 由 BookView 负责真正导入 —— 落点规则只写一处，避免两边不一致。
    #:
    #: 第一个参数用 ``object`` 而不是 ``QPoint``：``PyQt6.QtCore.QPoint``
    #: 不是默认注册的信号参数类型，用 ``QPoint`` 声明时 emit 会被**静默丢弃**
    #: （不报错、槽不执行 —— 实测踩过，很难查）。``object`` 收什么都行。
    files_dropped = pyqtSignal(object, object)

    COLUMNS = ("名称", "类型", "大小", "修改时间")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(0, len(self.COLUMNS), parent)
        self.setHorizontalHeaderLabels(list(self.COLUMNS))
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(False)
        self.setShowGrid(False)
        self.setSortingEnabled(False)
        self.setWordWrap(False)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context)
        self.doubleClicked.connect(self._on_double_click)
        self.cellClicked.connect(self._on_cell_clicked)
        self.verticalHeader().setDefaultSectionSize(30)

        # 接受**外部文件**拖入（从资源管理器拖文件进来 = 上传）。
        # 不开的话事件全靠 Qt 冒泡到 BookView，一旦这里将来做行内拖拽排序，
        # 导入就会被吃掉；而且拖到表格上时用户看不到任何落点反馈。
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)

        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for index in range(1, len(self.COLUMNS)):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)

        self._items: list[BookItem] = []
        self._homework: dict[str, hw.Homework] = {}     # 路径字符串 -> 作业
        self._homework_mode = False

    # ------------------------------------------------------------------

    def set_homework_mode(self, enabled: bool) -> None:
        """切换成"作业栏目"模式：多两列，并按 DDL 上色。"""
        enabled = bool(enabled)
        if enabled == self._homework_mode:
            return
        self._homework_mode = enabled
        titles = list(self.COLUMNS)
        if enabled:
            titles += [_DUE_COLUMN_TITLE, _SUBMIT_COLUMN_TITLE]
        self.setColumnCount(len(titles))
        self.setHorizontalHeaderLabels(titles)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for index in range(1, len(titles)):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)
        if enabled:
            # 「提交方式」列固定宽度：里面只有一个按钮，
            # 不能让（很长的）网址把列撑开。
            submit_column = self.column_of(_SUBMIT_COLUMN_TITLE)
            if submit_column >= 0:
                header.setSectionResizeMode(
                    submit_column, QHeaderView.ResizeMode.Fixed
                )
                self.setColumnWidth(submit_column, _SUBMIT_COLUMN_WIDTH)
        if not enabled:
            self._homework.clear()

    def set_homework_map(self, mapping: dict[str, hw.Homework]) -> None:
        """给出"文件夹路径 -> 作业"的映射，用于渲染 DDL 与提交方式。"""
        self._homework = dict(mapping or {})

    def homework_for(self, item: BookItem) -> hw.Homework | None:
        if not self._homework_mode or item is None:
            return None
        return self._homework.get(str(item.path))

    def column_of(self, title: str) -> int:
        """按标题找列号；不存在返回 -1。"""
        for index in range(self.columnCount()):
            header = self.horizontalHeaderItem(index)
            if header is not None and header.text() == title:
                return index
        return -1

    # ------------------------------------------------------------------

    def set_items(self, items: list[BookItem]) -> None:
        self._items = list(items)
        self.setRowCount(len(items))
        for row, item in enumerate(items):
            name_item = QTableWidgetItem(item.name)
            name_item.setIcon(common.folder_icon() if item.is_dir else common.file_icon(item.path))
            name_item.setData(Qt.ItemDataRole.UserRole, row)
            if item.is_summary or item.is_intro:
                font = name_item.font()
                font.setBold(True)
                name_item.setFont(font)
            if item.is_meta:
                # 软件自己的内部文件（如作业的 homework.json）：
                # **必须列出来**（用户要能看到作业文件夹里的东西），
                # 但置灰表示"这不是你的内容，别动它"。
                name_item.setForeground(QBrush(QColor("#8A8F98")))
                name_item.setToolTip(
                    "这是软件用来记录这条信息的文件（DDL、提交网址等），"
                    "不是你的作业内容，请勿删除或改写。"
                )
            self.setItem(row, 0, name_item)
            self.setItem(row, 1, QTableWidgetItem(item.kind_label))
            self.setItem(row, 2, QTableWidgetItem(item.size_label))
            self.setItem(row, 3, QTableWidgetItem(item.mtime_label))

            homework = self.homework_for(item)
            if homework is not None:
                due_column = self.column_of(_DUE_COLUMN_TITLE)
                submit_column = self.column_of(_SUBMIT_COLUMN_TITLE)

                # ---- 完成状态：**用字体颜色标**，不用整行底色 ----
                #
                # 需求（用户原话）："已完成的作业取消颜色标记 用绿色字体标已完成
                # 未完成的作业用红色字体标未完成"。
                #
                # 所以：已完成 -> 绿色「已完成」；未完成 -> 红色「未完成」。
                # 状态字跟名字放在同一格（名字后面加括号），因为它说的就是
                # "这条作业的状态"，单独占一列反而把表格拉宽。
                is_done = bool(getattr(homework, "done", False))
                status_item = self.item(row, 0)
                if status_item is not None:
                    status_item.setText(
                        f"{item.name}（{_DONE_TEXT if is_done else _UNDONE_TEXT}）"
                    )
                    status_item.setForeground(
                        _DONE_COLOR if is_done else _UNDONE_COLOR
                    )
                    status_item.setToolTip(
                        f"作业「{item.name}」\n"
                        f"状态：{_DONE_TEXT if is_done else _UNDONE_TEXT}"
                        f"（在首页日程栏点「完成作业」，或用右键菜单）"
                    )
                    # 已完成的加删除线？**不加**。用户要的是"用绿色字体标"，
                    # 删除线会让名字更难读，而颜色已经把状态说清了。
                    # 加粗只留给 summary / intro（见上面），这里不掺进去。

                state = homework.state()
                due_text = homework.due_label
                if state == "overdue":
                    due_text += "（已过期）"
                elif state == "soon":
                    due_text += "（即将截止）"
                if due_column >= 0:
                    due_cell = QTableWidgetItem(due_text)
                    # 逾期仍然用红色 —— 它和"未完成"是两件事：
                    # 未完成说的是"你还没交"，逾期说的是"期限已经过了"。
                    # 两者都要能一眼看到，所以颜色可以重合。
                    if state == "overdue":
                        due_cell.setForeground(QBrush(_OVERDUE_TEXT_COLOR))
                    elif state == "soon":
                        due_cell.setForeground(QBrush(_SOON_TEXT_COLOR))
                    self.setItem(row, due_column, due_cell)

                # ---- 未完成且临近/逾期 DDL：整行染色 ----
                #
                # **只有未完成才染**（需求："未完成 快到DDL的还是要染色"，
                # 而"已完成的作业取消颜色标记"）。理由很实际：
                # 底色的唯一作用是催办，交完就不需要催了；
                # 已完成的作业还留着浅红底，会让人以为"这条还没处理"。
                #
                # 字色和底色不冲突：名称格是深绿/深红（对比度足够），
                # DDL 格是深棕/深红，压在浅色底上都清楚。
                if not is_done:
                    brush = None
                    if state == "overdue":
                        brush = _OVERDUE_BRUSH
                    elif state == "soon":
                        brush = _SOON_BRUSH
                    if brush is not None:
                        for column in range(self.columnCount()):
                            cell = self.item(row, column)
                            if cell is not None:
                                cell.setBackground(brush)
                if submit_column >= 0:
                    if homework.submit_url:
                        # 提交网址往往很长（教务系统那种上百字符），
                        # 直接显示会把表格撑得没法看 —— 换成一个「提交作业」按钮，
                        # 完整网址放在悬浮提示里，需要复制时用右键菜单。
                        button = QPushButton(_SUBMIT_BUTTON_TEXT)
                        button.setObjectName("SubmitHomework")
                        button.setToolTip(f"打开提交网址：\n{homework.submit_url}")
                        button.setCursor(Qt.CursorShape.PointingHandCursor)
                        button.setFixedHeight(_SUBMIT_BUTTON_HEIGHT)
                        button.clicked.connect(
                            lambda _checked=False, folder=homework.path,
                            url=homework.submit_url: self.submit_link_clicked.emit(
                                folder, url
                            )
                        )
                        holder = QWidget()
                        holder_layout = QHBoxLayout(holder)
                        holder_layout.setContentsMargins(2, 0, 2, 0)
                        holder_layout.addWidget(button)
                        holder_layout.addStretch(1)
                        self.setCellWidget(row, submit_column, holder)
                    else:
                        # 没填提交方式：不摆一个点了没反应的按钮，直接说明
                        empty_cell = QTableWidgetItem("未填写")
                        empty_cell.setForeground(QBrush(QColor("#8A8F98")))
                        empty_cell.setToolTip("右键作业 →「编辑作业…」可以补上提交网址")
                        self.setItem(row, submit_column, empty_cell)

                # 底色的染色规则见上面那段：**只有未完成才染**。
                # 已完成的作业一律没有底色（需求："已完成的作业取消颜色标记"）。
        self.resizeRowsToContents()

    def current_item(self) -> BookItem | None:
        row = self.currentRow()
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def item_at(self, row: int) -> BookItem | None:
        """按行号取条目（拖拽落点判定、右键菜单都要用）。"""
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def row_at(self, pos) -> int:
        """某个坐标（视口坐标系）在哪一行上；不在任何行上返回 -1。

        接受 ``QPoint`` 或 ``QPointF`` —— 拖拽事件给的是 ``QPointF``，
        而 ``indexAt`` 只认 ``QPoint``，必须显式取整。
        """
        if hasattr(pos, "toPoint"):
            pos = pos.toPoint()
        index = self.indexAt(pos)
        return index.row() if index is not None and index.isValid() else -1

    def selected_items(self) -> list[BookItem]:
        rows = sorted({index.row() for index in self.selectedIndexes()})
        return [self._items[row] for row in rows if 0 <= row < len(self._items)]

    def select_name(self, name: str) -> None:
        for row, item in enumerate(self._items):
            if item.name == name:
                self.selectRow(row)
                return

    # ------------------------------------------------------------------

    def _on_double_click(self, index) -> None:
        row = index.row()
        if 0 <= row < len(self._items):
            self.double_clicked_item.emit(self._items[row])

    def _on_cell_clicked(self, row: int, column: int) -> None:
        """点「提交方式」列 = 打开发网址（其他列不响应单击）。"""
        if not self._homework_mode or not (0 <= row < len(self._items)):
            return
        if column != self.column_of(_SUBMIT_COLUMN_TITLE):
            return
        homework = self.homework_for(self._items[row])
        if homework is not None and homework.submit_url:
            self.submit_link_clicked.emit(homework.path, homework.submit_url)

    def _on_context(self, pos: QPoint) -> None:
        """右键。

        **右键在空白处也要出菜单**（用户报障："右键新建文件夹存在异常"）。

        原来是 `item is None` 就直接 return —— 于是在列表下方的空白区域右键
        什么都不会发生，而"新建文件夹"只藏在**条目**的右键菜单里。
        用户的直觉是"在空白处右键 -> 新建"（资源管理器就是这样），
        所以这里补一条通路：空白处右键就把菜单请求发出去，
        ``item`` 传 ``None``，由 BookView 决定"建在当前这一层"。
        """
        item = self.current_item()
        if item is None:
            # 顺便清掉选中，免得菜单动作作用在一个"看不见的选中项"上
            self.clearSelection()
            self.setCurrentCell(-1, -1)
        self.context_requested.emit(item, self.viewport().mapToGlobal(pos))

    # -- 外部文件拖入（上传）--------------------------------------------
    #
    # 只处理"从资源管理器拖进来的文件"（mimeData 里有 urls）。
    # 表格内部的拖拽（如果有）不带 urls，不会走到这里。

    @staticmethod
    def _has_local_files(mime) -> bool:
        return bool(mime is not None and mime.hasUrls()
                    and any(url.isLocalFile() for url in mime.urls()))

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if self._has_local_files(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802
        if self._has_local_files(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802
        if self._has_local_files(event.mimeData()):
            event.acceptProposedAction()
            # 落点用**视口坐标**交给 BookView，它据此判断是否落在某个文件夹行上
            self.files_dropped.emit(
                event.position().toPoint(), event.mimeData()
            )
            return
        super().dropEvent(event)


__all__ = ["FileTable"]
