"""应用入口：创建 QApplication、装配运行时、显示主窗口。

``create_application`` 与 ``run`` 分离，方便测试脚本在无界面模式下复用。
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from gwp import __app_name__, __version__
from gwp.bootstrap import (
    bootstrap,
    check_single_instance,
    cleanup_on_exit,
    last_instance_conflict,
    publish_instance_window,
    release_single_instance,
)

log = logging.getLogger(__name__)


def _enable_high_dpi() -> None:
    """高 DPI 支持（PyQt6 默认开启缩放，这里只做舍入策略设置）。"""
    from PyQt6.QtCore import Qt

    try:
        from PyQt6.QtGui import QGuiApplication

        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except Exception:  # noqa: BLE001
        log.debug("设置高 DPI 策略失败", exc_info=True)


def create_application(argv: list[str]):
    """创建并配置 QApplication（不显示任何窗口）。"""
    from PyQt6.QtWidgets import QApplication

    # **必须在建窗口之前**设应用标识：
    # 不设的话 Windows 会把窗口归到 pythonw.exe 名下，
    # 任务栏显示的是 Python 解释器的图标（需求："将任务栏的图标改成
    # 快捷方式现在的图标"）。设了之后任务栏改用窗口自己的 planet.ico。
    from gwp.core.app_identity import set_app_user_model_id

    set_app_user_model_id()

    _enable_high_dpi()
    app = QApplication.instance()
    if app is None:
        app = QApplication(list(argv) if argv else [__app_name__])
    app.setApplicationName(__app_name__)
    app.setApplicationDisplayName(__app_name__)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(__app_name__)
    # **绝不允许"最后一个窗口关闭就退出"**。
    # 原因：主窗口关闭时会隐藏到后台（需求），如果 Qt 在这里自动退出，
    # 进程会立刻死掉，"后台驻留"就完全失效 —— 而且表现为
    # "点了关闭软件就没了"，看起来就像隐藏功能没实现。
    # 放在 create_application 而不是 run() 里，是为了让测试也走同一条路径。
    # 真正的退出统一走 MainWindow.quit_completely()。
    app.setQuitOnLastWindowClosed(False)
    return app


def _pin_window_to_current_desktop(window) -> int:
    """让主窗口只出现在当前的 Win11 虚拟桌面上，并返回它的窗口句柄。

    Windows 默认把窗口"钉"在所有虚拟桌面上，所以不显式关闭的话，
    用户开了一个软件会在每个桌面都看到它——这既不符合需求，
    也让"已经在运行"的判断失去意义。
    """
    hwnd = 0
    try:
        hwnd = int(window.winId())
    except Exception:  # noqa: BLE001
        log.debug("拿不到窗口句柄", exc_info=True)

    if sys.platform.startswith("win") and hwnd:
        try:
            import ctypes

            VK_NONE = 0
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            # 记录"窗口只在当前桌面显示"的扩展样式位（Win10 1803+）
            WS_EX_VD_SAME_DESKTOP = 0x00020000

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
            user32.GetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int]
            user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
            user32.SetWindowLongPtrW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t]

            current = user32.GetWindowLongPtrW(ctypes.c_void_p(hwnd), GWL_EXSTYLE)
            updated = (current | WS_EX_VD_SAME_DESKTOP) & ~WS_EX_TOOLWINDOW
            if updated != current:
                user32.SetWindowLongPtrW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, updated)
                log.debug("已设置窗口只在当前虚拟桌面显示（hwnd=%s）", hwnd)
        except Exception:  # noqa: BLE001 - 失败也不该影响启动
            log.debug("设置虚拟桌面固定失败", exc_info=True)
    return hwnd


def run(argv: list[str] | None = None) -> int:
    """正常启动软件，返回退出码。

    同一台机器上同一个数据目录只允许一个主窗口。已有实例在跑时：

    * 若它**在后台运行**（"关闭到后台"留下的状态）-> **直接把窗口唤回**，
      不弹任何提示框，也不需要建界面；
    * 若它开在**当前桌面**上 -> 提示"已经在运行"，退出（退出码 2）；
    * 若它开在**另一个虚拟桌面**上（Win11 多桌面）-> 弹窗明确告知，
      并说明怎么切过去，同样退出，不会在第二个桌面再开一个。
    """
    argv = list(argv if argv is not None else sys.argv[1:])
    app = create_application([sys.argv[0], *argv])

    context = bootstrap(argv)

    # ---- 先抢实例锁并处理"已有实例"，再决定要不要建界面 ----
    #
    # **顺序很重要**（这里踩过一个回归）：原来先建 MainWindow、再检查单实例，
    # 于是"已有实例在后台、用户双击快捷方式想唤回窗口"这条路上，
    # 第二个进程会白白把整个界面建一遍（实测 8 秒）才走到"唤回"。
    #
    # 但**不能只是"读一下锁"**（那样等于没抢）：必须真的走
    # ``check_single_instance`` 把锁拿到手，否则两个进程可能同时判定
    # "没人占" —— 结果是**两个主窗口都建出来**，比慢一点严重得多。
    already_running = check_single_instance(context, hwnd=0)
    if already_running is not None:
        conflict = last_instance_conflict(context)
        _report_already_running(
            context,
            on_other_desktop=bool(conflict is not None and conflict.on_other_desktop),
            other_pid=int(getattr(conflict, "pid", 0) or 0),
            other_hwnd=int(getattr(conflict, "hwnd", 0) or 0),
        )
        return already_running

    from gwp.ui import common
    from gwp.ui.main_window import MainWindow

    app.setWindowIcon(common.app_icon(config=context.config))

    window = MainWindow(context)

    # 窗口建好了，把句柄补进锁文件，供下一个实例判断虚拟桌面 / 是否隐藏
    hwnd = _pin_window_to_current_desktop(window)
    publish_instance_window(context, hwnd)

    # 命令行参数：支持直接打开某个文件
    for argument in argv:
        if argument.startswith("-"):
            continue
        candidate = Path(argument)
        if candidate.exists() and candidate.is_file():
            window.open_document_window(candidate)
    window.show()

    # 退出时先释放实例锁，再做数据清理
    app.aboutToQuit.connect(lambda: release_single_instance(context))
    app.aboutToQuit.connect(lambda: cleanup_on_exit(context))

    # **兜底一等**：任何后台线程还在跑就等它结束。
    #
    # 这一步必须是"最后一道保险"，不能只依赖 MainWindow.closeEvent ——
    # 因为窗口可能根本没走 closeEvent（进程被结束、异常退出），
    # 而 Qt 在"QThread 还在跑时被析构"这条路上会 qFatal **直接中止进程**
    # （0xC0000409，用户看到"闪退"、日志里什么都没有）。
    # 注册成 atexit：它在解释器收尾、Qt 析构之前跑。
    import atexit

    def _final_thread_guard() -> None:
        from gwp.core import threads as _threads

        _threads.shutdown()

    atexit.register(_final_thread_guard)
    # aboutToQuit 也跟着等一次：那时窗口还在，等起来更干净
    app.aboutToQuit.connect(_final_thread_guard)
    return app.exec()


def _report_already_running(
    context,
    on_other_desktop: bool = False,
    other_pid: int = 0,
    other_hwnd: int = 0,
) -> None:
    """已有实例在跑时的处理。

    **分两种情况，行为完全不同**：

    1. 已有实例只是**藏在后台**（"关闭到后台"功能留下的状态）——
       这时用户双击快捷方式的意图非常明确：**我要用软件**。
       所以直接把窗口显示出来就完事，**不弹任何提示框**
       （弹框才是打扰：用户会看到"软件已经在运行"却仍然没有窗口）。
    2. 已有实例开着，只是用户没找到（或在另一个虚拟桌面）——
       保留原来的提示框，说清怎么找回来。

    设置环境变量 ``GWP_NO_PROMPT=1`` 可跳过弹窗（自动化/脚本启动时用，
    避免在没有真实桌面的环境里卡在模态对话框上）。
    """
    lock_file = context.paths.else_data / "instance.lock"
    log.warning(
        "检测到已有实例在运行（另一个桌面=%s，PID=%s，窗口=%s），本次启动退出；锁文件=%s",
        on_other_desktop,
        other_pid or "未知",
        other_hwnd or "无",
        lock_file,
    )

    # ---- 情况 1：窗口就在当前桌面上、只是被隐藏了 -> 请求唤回，不打扰 ----
    #
    # 注意这里**不强依赖窗口句柄**：句柄可能还没被写进锁文件
    # （前一个实例刚启动、或锁是旧版本格式），但"写唤回请求"这条路
    # 不需要句柄 —— 那个进程自己在轮询这个文件。
    if not on_other_desktop:
        hidden = False
        if other_hwnd:
            try:
                from gwp.core.desktops import window_is_visible

                hidden = window_is_visible(other_hwnd) is False
            except Exception:  # noqa: BLE001
                hidden = False
        else:
            # 没有句柄可用：保守地认为"可能是藏在后台"，
            # 请求一次没有副作用（窗口本来就可见时，show() 只是幂等操作）。
            hidden = True
        if hidden:
            # **请求那个进程自己显示窗口，而不是我们替它显示。**
            # 从外部 ShowWindow 会让原生窗口变可见、但 Qt 不重绘 ->
            # 用户看到**全黑窗口**（见 core/wakeup.py 的记录）。
            try:
                from gwp.core.wakeup import request_wake

                if request_wake(context.paths.else_data):
                    log.info("已有实例在后台运行，已请求它把窗口唤回（未弹提示框）")
                    return
            except Exception:  # noqa: BLE001
                log.debug("请求唤回后台窗口失败，退回提示用户", exc_info=True)

    if os.environ.get("GWP_NO_PROMPT"):
        log.info("已设置 GWP_NO_PROMPT，跳过提示框")
        return

    if on_other_desktop:
        title = "软件已在另一个桌面上运行"
        message = (
            "Great White Planet 已经打开了，而且开在**另一个虚拟桌面**上，"
            "所以当前桌面看不到它。\n\n"
            "同一时间只允许打开一个主窗口，本次启动不会新建窗口。\n\n"
            "要切过去看它，可以任选一种：\n"
            "  · 按  Win + Ctrl + ←/→  在两/多个桌面之间切换\n"
            "  · 按  Win + Tab  打开任务视图，点那个桌面上的软件窗口\n"
            "  · 点击下面的「切到那个桌面」按钮\n\n"
            f"（如果确实找不到窗口，可以删除这个文件后重新启动：\n{lock_file}）"
        )
    else:
        title = "Great White Planet 已在运行"
        message = (
            "Great White Planet 已经在运行了。\n\n"
            "同一时间只允许打开一个主窗口，请切换到已经打开的窗口"
            "（在任务栏上找它的图标）。\n\n"
            "**如果它其实关掉了、只是还在后台运行**："
            "双击右下角托盘里的星球图标，或者再双击一次桌面快捷方式，"
            "就能把窗口叫回来。\n\n"
            "如果确实没看到窗口，可以删除下面这个文件后重新启动：\n"
            f"{lock_file}"
        )

    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox

        if QApplication.instance() is None:
            return
        box = QMessageBox()
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(message)
        switch_button = None
        if on_other_desktop:
            switch_button = box.addButton("切到那个桌面", QMessageBox.ButtonRole.ActionRole)
        box.addButton("知道了", QMessageBox.ButtonRole.AcceptRole)
        box.exec()
        if switch_button is not None and box.clickedButton() is switch_button:
            from gwp.core.desktops import activate_window

            if activate_window(other_hwnd):
                log.info("已切换到已有实例所在的虚拟桌面")
            else:
                log.info("无法自动切换桌面，已提示用户手动切换")
    except Exception:  # noqa: BLE001 - 无界面环境下不该崩
        log.debug("无法弹出提示框", exc_info=True)


__all__ = ["create_application", "run"]
