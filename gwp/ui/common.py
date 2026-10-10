"""界面通用工具：消息框、忙碌指示、图标等。

把这些零碎功能集中起来，各个视图就不用重复实现。
"""

from __future__ import annotations

import logging
from pathlib import Path
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

log = logging.getLogger(__name__)

#: 消息框默认按钮文字（中文化）
YES = QMessageBox.StandardButton.Yes
NO = QMessageBox.StandardButton.No


# --------------------------------------------------------------------------
# 消息框
# --------------------------------------------------------------------------

def info(parent: QWidget | None, text: str, title: str = "提示") -> None:
    QMessageBox.information(parent, title, text)


def warn(parent: QWidget | None, text: str, title: str = "注意") -> None:
    QMessageBox.warning(parent, title, text)


def error(parent: QWidget | None, text: str, title: str = "出错了") -> None:
    QMessageBox.critical(parent, title, text)


def confirm(
    parent: QWidget | None,
    text: str,
    title: str = "请确认",
    *,
    dangerous: bool = False,
    detail: str = "",
) -> bool:
    """二选一确认框，返回用户是否点了「确定」。

    ``dangerous=True`` 用于**删除**这类不可逆或代价高的操作，区别有三点：

    * 图标用「警告」而不是「问号」；
    * **默认按钮是「取消」** —— 直接按回车不会误删（原先默认「确定」，
      手快按到回车就把数据删了）；
    * 确定按钮排在右侧、文案是「删除」，需要有意去点。

    ``detail`` 会显示在详细信息区（可折叠），用来放路径、内容清单这类
    用户需要但不该占据主视线的东西。
    """
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    if detail:
        box.setDetailedText(detail)

    if not dangerous:
        box.setIcon(QMessageBox.Icon.Question)
        yes = box.addButton("确定", QMessageBox.ButtonRole.AcceptRole)
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(yes)
        box.exec()
        return box.clickedButton() is yes

    box.setIcon(QMessageBox.Icon.Warning)
    # 注意按钮顺序：先加「取消」，后加「删除」，删除就会落在右侧
    cancel = box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
    confirm_button = box.addButton("删除", QMessageBox.ButtonRole.DestructiveRole)
    box.setDefaultButton(cancel)          # ← 回车 = 取消，防误触
    box.setEscapeButton(cancel)
    box.exec()
    return box.clickedButton() is confirm_button


def ask_choice(
    parent: QWidget | None,
    text: str,
    title: str = "请选择",
    *,
    checkbox: str = "",
    checked: bool = False,
    ok_text: str = "确定",
    cancel_text: str = "取消",
) -> bool | None:
    """「确定 / 取消」+ 一个可选复选框的对话框。

    返回：

    * ``None`` —— 用户取消了（调用方应当**中止**，而不是当 False 处理）；
    * ``bool`` —— 用户点了确定，值是复选框是否被勾选。

    为什么需要它：有些操作带一个**可选附加步骤**（比如「生成总结」里的
    "让 AI 重排页序"）。用两次弹窗问会很啰嗦，用 `confirm` 又表达不了
    "选确定时顺便选要不要附加功能"。返回三态是刻意的 ——
    "取消"和"确定且不勾选"是两件不同的事，混在一个 bool 里必然出错。
    """
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(QMessageBox.Icon.Question)
    yes = box.addButton(ok_text, QMessageBox.ButtonRole.AcceptRole)
    box.addButton(cancel_text, QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(yes)
    option = None
    if checkbox:
        option = QCheckBox(checkbox)
        option.setChecked(bool(checked))
        box.setCheckBox(option)
        box.setEscapeButton(box.buttons()[1])
    box.exec()
    if box.clickedButton() is not yes:
        return None
    return bool(option.isChecked()) if option is not None else True


def ask_generate_summary(
    parent: QWidget | None,
    text: str,
    *,
    mix_label: str,
    mix_checked: bool,
    supplement_label: str,
    supplement_checked: bool,
    title: str = "生成总结",
) -> tuple[bool, bool] | None:
    """「生成总结」的确认框：带**两个**独立复选框。

    返回 ``(混排, 长庚知道补充)``；用户取消时返回 ``None``。

    为什么不用 :func:`ask_choice` 问两次：那样要弹两次窗，很啰嗦；
    而 ``QMessageBox`` 只有一个复选框位（`setCheckBox` 会被后一次覆盖，
    实测第二个复选框根本不显示）。所以这里自己拼一个 QDialog ——
    两个选项互相独立，勾哪个都不影响另一个。
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    layout = QVBoxLayout(dialog)
    body = QLabel(text)
    body.setWordWrap(True)
    body.setTextFormat(Qt.TextFormat.MarkdownText)
    layout.addWidget(body)

    mix_box = QCheckBox(mix_label)
    mix_box.setChecked(bool(mix_checked))
    layout.addWidget(mix_box)
    supplement_box = QCheckBox(supplement_label)
    supplement_box.setChecked(bool(supplement_checked))
    layout.addWidget(supplement_box)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok
        | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return bool(mix_box.isChecked()), bool(supplement_box.isChecked())


def ask_text(
    parent: QWidget | None,
    title: str,
    label: str,
    default: str = "",
    ok_text: str = "确定",
) -> str | None:
    """输入框对话框。返回 None 表示取消。"""
    from PyQt6.QtWidgets import QInputDialog

    text, ok = QInputDialog.getText(parent, title, label, text=default)
    if not ok:
        return None
    return text


# --------------------------------------------------------------------------
# 日期 / 时间输入
# --------------------------------------------------------------------------

def make_datetime_edit(moment=None, *, minutes_only: bool = True) -> "QDateTimeEdit":
    """做一个"用鼠标选 / 滚轮调"的日期时间输入框（不用手打数字）。

    需求原文："数字看不清 修改  后面几点几分也弄成这种选择/滚轮，而非手动填写"。

    具体做了四件事：

    1. **日期用日历弹窗选**（``setCalendarPopup(True)``）——
       不用手打年月日；
    2. **时分用上下按钮 / 滚轮调**：``setDisplayFormat`` 带明确的间隔符
       （``yyyy-MM-dd HH:mm``），Qt 会把每一段做成可单独点选、可滚轮的区段；
       再显式允许键盘跟踪，方向上/下键与鼠标滚轮都能加减；
    3. **日历弹窗加大字号、加宽**（QSS 在 themes.py）——数字看得清；
    4. **不做手打校验**：这几段只能从合法范围里调，用户写不出非法日期。

    ``minutes_only=False`` 时精确到秒（暂时没用到，留着以备需求）。
    """
    from PyQt6.QtCore import QDateTime
    from PyQt6.QtWidgets import QDateTimeEdit

    edit = QDateTimeEdit()
    edit.setCalendarPopup(True)
    # 显式给出秒的可选性：默认只到分钟，避免用户被"秒"这一段干扰
    edit.setDisplayFormat("yyyy-MM-dd HH:mm" if minutes_only else "yyyy-MM-dd HH:mm:ss")
    edit.setDateTime(
        QDateTime(moment) if moment is not None else QDateTime.currentDateTime()
    )
    # 键盘跟踪：光标停在某一段上时，上下键 / 滚轮直接调这一段
    edit.setKeyboardTracking(True)
    edit.setWrapping(True)              # 59 分再加到 0 分，符合"滚轮"直觉
    # 日历弹窗要有足够宽度，否则数字挤在一起（需求："数字看不清"）
    calendar = edit.calendarWidget()
    if calendar is not None:
        calendar.setMinimumWidth(360)
        calendar.setGridVisible(True)
        # 让"周"从周一开始，符合国内习惯
        calendar.setFirstDayOfWeek(Qt.DayOfWeek.Monday)
    return edit


# --------------------------------------------------------------------------
# 文件/目录选择
# --------------------------------------------------------------------------

def pick_directory(parent: QWidget | None, title: str, start: Path | str | None = None) -> Path | None:
    directory = QFileDialog.getExistingDirectory(
        parent, title, str(start) if start else ""
    )
    return Path(directory) if directory else None


def pick_files(
    parent: QWidget | None,
    title: str = "选择文件",
    start: Path | str | None = None,
    *,
    multiple: bool = True,
    name_filter: str = "所有文件 (*.*)",
) -> list[Path]:
    """选一个或多个文件（"上传"用它）。取消返回空列表。

    和 :func:`pick_directory` 放在一起，界面上所有"选文件/选目录"都走这两个函数，
    便于以后统一加"最近使用目录"之类的行为。
    """
    if multiple:
        chosen, _selected = QFileDialog.getOpenFileNames(
            parent, title, str(start) if start else "", name_filter
        )
        return [Path(item) for item in chosen]
    single, _selected = QFileDialog.getOpenFileName(
        parent, title, str(start) if start else "", name_filter
    )
    return [Path(single)] if single else []


def pick_save_file(
    parent: QWidget | None,
    title: str,
    default_name: str = "",
    filters: str = "所有文件 (*.*)",
    start: Path | str | None = None,
) -> Path | None:
    path, _ = QFileDialog.getSaveFileName(
        parent,
        title,
        str(Path(start) / default_name) if start else default_name,
        filters,
    )
    return Path(path) if path else None


def pick_open_image(parent: QWidget | None, title: str = "选择图片") -> Path | None:
    """选择 jpg/png 图片。"""
    path, _selected_filter = QFileDialog.getOpenFileName(
        parent, title, "", "图片 (*.jpg *.jpeg *.png);;所有文件 (*.*)"
    )
    return Path(path) if path else None


def ask_multiline(
    parent: QWidget | None,
    title: str,
    label: str,
    default: str = "",
    *,
    readonly: bool = False,
    height: int = 320,
) -> str | None:
    """多行文本对话框。确定返回文本（可能是空串），取消返回 ``None``。

    为什么需要它：项目里原来的 ``ask_text`` 走 ``QInputDialog.getText``，
    **只有单行** —— 用来编辑 Markdown 正文、粘贴长提示词都不够用
    （AI 提问框 ``AiQuestionDialog`` 同样只有 ``QLineEdit``）。

    返回 ``None`` 和空串的区别很重要：前者是"用户取消了"，
    后者是"用户确定要清空"。调用方据此决定要不要覆盖原内容。
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(720, height)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(10)

    if label:
        caption = QLabel(label)
        caption.setWordWrap(True)
        layout.addWidget(caption)

    box = QPlainTextEdit(default)
    box.setReadOnly(readonly)
    layout.addWidget(box, 1)

    if readonly:
        hint = QLabel("这段内容可以直接选中复制。")
        hint.setObjectName("Muted")
        layout.addWidget(hint)

    buttons = QHBoxLayout()
    buttons.addStretch(1)
    btn_cancel = QPushButton("取消" if not readonly else "关闭")
    buttons.addWidget(btn_cancel)
    btn_ok = None
    if not readonly:
        btn_ok = QPushButton("确定")
        btn_ok.setProperty("accent", True)
        buttons.addWidget(btn_ok)
    layout.addLayout(buttons)

    btn_cancel.clicked.connect(dialog.reject)
    if btn_ok is not None:
        btn_ok.clicked.connect(dialog.accept)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return box.toPlainText()


def ask_paste_reply(    parent: QWidget | None,
    *,
    title: str = "网页版 AI",
    prompt: str = "",
    hint: str = "",
    height: int = 240,
) -> str:
    """弹一个"把网页版的回答粘回来"的对话框，返回用户粘贴的文本（取消返回空串）。

    这是网页版桥接的通用接收端（``web_bridge.send_to_ai`` 用的就是它）。
    设计要点：

    * 上面显示**提示**（图片/提示词是不是已经进了剪贴板、打开了哪个网址）；
    * 中间放原文提示词，**只读**但可选中复制 —— 万一剪贴板被别的程序占了，
      用户还能手动复制；
    * 下面是粘贴框，**打开对话框时如果剪贴板里已经有文字就自动填进去**
      （用户刚在网页里 Ctrl+C 过，能省一步）；
    * 明确写出"可以留空，留空就表示这张识别不了，会直接插图" ——
      让用户知道**跳过是受支持的操作**，不用硬凑内容。
    """
    dialog = QDialog(parent)
    dialog.setWindowTitle(title)
    dialog.resize(680, 460)
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(10)

    if hint:
        label = QLabel(hint)
        label.setObjectName("Muted")
        label.setWordWrap(True)
        layout.addWidget(label)

    if prompt:
        layout.addWidget(QLabel("发给 AI 的内容（想手动复制就从这里选）："))
        source = QPlainTextEdit(prompt)
        source.setReadOnly(True)
        source.setMaximumHeight(120)
        layout.addWidget(source)

    layout.addWidget(QLabel("把 AI 的回答粘贴到这里（Ctrl+V）："))
    box = QPlainTextEdit()
    clipboard = QApplication.clipboard()
    if clipboard is not None:
        existing = clipboard.text() or ""
        # 只自动填"看起来像回答"的内容，避免把上一次复制的提示词又粘一遍
        if existing.strip() and existing.strip() != prompt.strip():
            box.setPlainText(existing)
    layout.addWidget(box, 1)

    tip = QLabel("识别不了可以直接留空 —— 留空的图片会**原样插入到结果里**，不会编内容。")
    tip.setObjectName("Muted")
    tip.setWordWrap(True)
    layout.addWidget(tip)

    buttons = QHBoxLayout()
    buttons.addStretch(1)
    btn_cancel = QPushButton("跳过这一张")
    btn_ok = QPushButton("确定")
    btn_ok.setProperty("accent", True)
    buttons.addWidget(btn_cancel)
    buttons.addWidget(btn_ok)
    layout.addLayout(buttons)

    result = {"text": ""}
    btn_cancel.clicked.connect(dialog.reject)

    def accept() -> None:
        result["text"] = box.toPlainText().strip()
        dialog.accept()

    btn_ok.clicked.connect(accept)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return result["text"]
    return ""


def pick_open_files(
    parent: QWidget | None,
    title: str = "选择文件",
    filters: str = "所有文件 (*.*)",
) -> list[Path]:
    paths, _ = QFileDialog.getOpenFileNames(parent, title, "", filters)
    return [Path(path) for path in paths]


def pick_open_file(
    parent: QWidget | None,
    title: str = "选择文件",
    filters: str = "所有文件 (*.*)",
) -> Path | None:
    path, _ = QFileDialog.getOpenFileName(parent, title, "", filters)
    return Path(path) if path else None


# --------------------------------------------------------------------------
# 忙碌对话框
# --------------------------------------------------------------------------

class BusyDialog(QProgressDialog):
    """模态进度对话框，支持"取消"。"""

    def __init__(
        self,
        parent: QWidget | None,
        title: str = "请稍候",
        message: str = "正在处理……",
        cancel_text: str = "取消",
    ) -> None:
        super().__init__(message, cancel_text, 0, 100, parent)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumWidth(420)
        self.setAutoClose(False)
        self.setAutoReset(False)
        self.setValue(0)

    def report(self, message: str, percent: int = -1, detail: str = "") -> None:
        text = message if not detail else f"{message}\n{detail}"
        self.setLabelText(text)
        if percent is None or percent < 0:
            self.setRange(0, 0)
        else:
            if self.maximum() == 0:
                self.setRange(0, 100)
            self.setValue(max(0, min(100, int(percent))))
        QApplication.processEvents()


class Toast(QLabel):
    """短暂的状态提示（贴在状态栏上方的浮层）。"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            "background: rgba(31,39,51,0.92); color: #FFFFFF; padding: 8px 16px;"
            "border-radius: 10px; font-size: 10pt;"
        )
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def show_message(self, text: str, msec: int = 2600) -> None:
        self.setText(text)
        self.adjustSize()
        parent = self.parentWidget()
        if parent is not None:
            x = max(12, (parent.width() - self.width()) // 2)
            y = max(12, parent.height() - self.height() - 48)
            self.move(x, y)
        self.raise_()
        self.show()
        self._timer.start(msec)


# --------------------------------------------------------------------------
# 图标（用文字/图形绘制，避免额外资源文件）
# --------------------------------------------------------------------------

def color_swatch(color: str, size: int = 16, radius: int = 4) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, radius, radius)
    painter.end()
    return pixmap


def app_icon(color: str = "#4F7CFF", size: int = 256, config=None) -> QIcon:
    """程序图标（"太白金星"）。

    实际取图规则见 :mod:`gwp.resources.app_icon`：优先使用
    ``gwp/resources/icons/planet.ico``（可用 ``python -m gwp.cli icon`` 替换），
    没有资源文件时用代码绘制。``color`` 只在内置绘制失败时作为最后的兜底色。
    """
    from gwp.resources import app_icon as icon_module

    return icon_module.app_icon(config=config, color=color, size=size)


def app_pixmap(size: int = 64, config=None) -> QPixmap:
    """程序图标的位图版本（对话框里显示用）。"""
    from gwp.resources import app_icon as icon_module

    return icon_module.pixmap(config=config, size=size)


def file_icon(path: Path, size: int = 20) -> QIcon:
    """按文件类型给一个彩色小图标（比系统图标更统一）。"""
    colors = {
        ".md": "#4F7CFF",
        ".markdown": "#4F7CFF",
        ".txt": "#6E7B8B",
        ".pdf": "#D9534F",
        ".docx": "#2F7FA8",
        ".doc": "#2F7FA8",
        ".pptx": "#F2814B",
        ".ppt": "#F2814B",
        ".xlsx": "#3E9E5F",
        ".xls": "#3E9E5F",
        ".csv": "#3E9E5F",
        ".png": "#8E63CE",
        ".jpg": "#8E63CE",
        ".jpeg": "#8E63CE",
    }
    color = colors.get(path.suffix.lower(), "#9BA6B5")
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, int(size * 0.82), 4, 4)
    painter.setBrush(QColor("#FFFFFF"))
    painter.drawRoundedRect(int(size * 0.2), int(size * 0.4), int(size * 0.6), 2, 1, 1)
    painter.drawRoundedRect(int(size * 0.2), int(size * 0.58), int(size * 0.45), 2, 1, 1)
    painter.end()
    return QIcon(pixmap)


def folder_icon(color: str = "#F2B54B", size: int = 20) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, int(size * 0.28), size, int(size * 0.66), 3, 3)
    painter.drawRoundedRect(int(size * 0.08), int(size * 0.16), int(size * 0.36), int(size * 0.24), 2, 2)
    painter.end()
    return QIcon(pixmap)


def elide(text: str, limit: int = 42) -> str:
    text = (text or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def html_escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


__all__ = [
    "BusyDialog",
    "Toast",
    "app_icon",
    "app_pixmap",
    "ask_text",
    "color_swatch",
    "confirm",
    "elide",
    "error",
    "file_icon",
    "folder_icon",
    "html_escape",
    "info",
    "pick_directory",
    "pick_open_file",
    "pick_open_files",
    "pick_open_image",
    "pick_save_file",
    "warn",
]
