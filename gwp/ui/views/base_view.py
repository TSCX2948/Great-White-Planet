"""视图基类：统一的标题栏（面包屑 + 操作区 + 搜索）。"""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gwp.bootstrap import AppContext


class BaseView(QWidget):
    """所有页面视图的公共骨架。"""

    status_message = pyqtSignal(str)
    data_changed = pyqtSignal()

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.context = context
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(18, 16, 18, 14)
        self._root.setSpacing(12)

        self.header = QHBoxLayout()
        self.header.setSpacing(8)

        self.lbl_title = QLabel("")
        self.lbl_title.setObjectName("Title")
        # 标题是这里唯一"可以被压缩"的东西：空间不够时它省略，
        # 按钮保持完整 —— 用户需要看懂的是按钮文字，书名看一半也认得出。
        self.lbl_title.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.lbl_title.setMinimumWidth(80)
        self.lbl_title.setToolTip("")          # 被省略时用悬浮提示补全书名
        self.header.addWidget(self.lbl_title)

        self.lbl_subtitle = QLabel("")
        self.lbl_subtitle.setObjectName("Muted")
        self.lbl_subtitle.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.header.addWidget(self.lbl_subtitle)

        self.lbl_breadcrumb = QLabel("")
        self.lbl_breadcrumb.setObjectName("Muted")
        self.lbl_breadcrumb.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        self.header.addWidget(self.lbl_breadcrumb)

        # 搜索框可伸缩，让它吸收多余空间；没有多余空间时它会缩到最小，
        # 而不是把按钮挤扁。
        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索…")
        self.search.setMinimumWidth(90)
        self.search.setMaximumWidth(240)
        self.search.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.search.setVisible(False)
        self.search.textChanged.connect(self._on_search)
        self.header.addWidget(self.search, 1)

        self.actions = QHBoxLayout()
        self.actions.setSpacing(6)
        self.header.addLayout(self.actions)

        # 标题栏包一层容器：设置背景图时它会有一层半透明底色，
        # 这样"我的科目 / 搜索框"这些文字压在壁纸上也不会看不清。
        self.header_bar = QWidget()
        self.header_bar.setObjectName("HeaderBar")
        self.header_bar.setLayout(self.header)
        self.header.setContentsMargins(10, 6, 10, 6)
        self._root.addWidget(self.header_bar)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        self._root.addLayout(self.body, 1)

    # ------------------------------------------------------------------

    def set_title(self, title: str, subtitle: str = "", breadcrumb: str = "") -> None:
        self.lbl_title.setText(title)
        # 标题在窄窗口下会被省略，悬浮提示给出完整内容
        self.lbl_title.setToolTip(title)
        self.lbl_subtitle.setText(subtitle)
        self.lbl_breadcrumb.setText(breadcrumb)
        # 副标题与面包屑是"补充信息"：按钮放不下时它们先整个让位（宽度缩到 0），
        # 而不是把按钮挤到文字显示不全。
        for label in (self.lbl_subtitle, self.lbl_breadcrumb):
            has_text = bool(label.text())
            label.setVisible(has_text)
            label.setSizePolicy(
                QSizePolicy.Policy.Ignored if has_text else QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Preferred,
            )

    def add_action(
        self,
        text: str,
        callback,
        accent: bool = False,
        tooltip: str = "",
        checkable: bool = False,
    ) -> QPushButton:
        """在标题栏右侧添加一个操作按钮。

        所有按钮都用 QPushButton，保证大小、圆角、字号与其它按钮完全一致；
        ``checkable=True`` 时按钮会有勾选态（用于"显示/隐藏某面板"这类开关）。

        **按钮不可压缩**：尺寸策略设为 Fixed，最小宽度 = 内容所需宽度。
        这样窗口变窄时被牺牲的是标题（它会省略号截断，并保留完整书名在
        悬浮提示里），而不是按钮文字 —— 按钮看半截等于不知道点下去会干什么。
        """
        button = QPushButton(text)
        button.setProperty("accent", accent)
        if tooltip:
            button.setToolTip(tooltip)
        button.setCheckable(checkable)
        if checkable:
            button.clicked.connect(callback)
        else:
            button.clicked.connect(lambda _checked=False: callback())
        # 先加进布局（此时样式尚未应用），应用后再锁定宽度
        self.actions.addWidget(button)
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        return button

    def lock_action_widths(self) -> None:
        """把每个按钮的最小宽度锁定为"完整显示文字所需宽度"。

        必须在**样式表生效之后**调用（字体、内边距都会影响所需宽度），
        因此在窗口显示后由主窗口触发一次即可。
        """
        for index in range(self.actions.count()):
            item = self.actions.itemAt(index)
            widget = item.widget() if item is not None else None
            if not isinstance(widget, QPushButton):
                continue
            hint = widget.sizeHint().width()
            widget.setMinimumWidth(hint)
            widget.setMaximumWidth(hint)

    def enable_search(self, placeholder: str = "搜索…") -> None:
        self.search.setPlaceholderText(placeholder)
        self.search.setVisible(True)

    def _on_search(self, _text: str) -> None:
        """子类覆盖以过滤内容。"""

    def on_shown(self) -> None:
        """视图被切换到前台时调用（用来刷新数据）。"""

    def refresh(self) -> None:
        """子类覆盖以重新加载数据。"""


__all__ = ["BaseView"]
