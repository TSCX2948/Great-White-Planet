"""日志：控制台 + 文件（``else data/logs``，按天切分并自动清理）。"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import threading
import time
import traceback
from pathlib import Path

_initialized = False


def setup_logging(log_dir: Path, level: str = "INFO", keep_days: int = 14) -> Path:
    """初始化根日志。可重复调用，只会生效一次。返回日志文件路径。"""
    global _initialized
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "gwp.log"

    root = logging.getLogger()
    root.setLevel(getattr(logging, str(level).upper(), logging.INFO))
    if _initialized:
        return log_file

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.handlers.TimedRotatingFileHandler(
        log_file, when="midnight", backupCount=max(1, int(keep_days)), encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # 控制台：pythonw 启动时没有 stderr，需要保护
    if sys.stderr is not None:
        stream = logging.StreamHandler(sys.stderr)
        stream.setFormatter(fmt)
        root.addHandler(stream)

    _initialized = True
    install_exception_hooks()
    logging.getLogger(__name__).info("日志已启动 -> %s", log_file)
    return log_file


# --------------------------------------------------------------------------
# 未捕获异常也要留下证据
# --------------------------------------------------------------------------

#: 是否已经装过钩子（避免重复包装，重复包装会把原始钩子套娃）
_hooks_installed = False


def install_exception_hooks() -> None:
    """让**未捕获的异常**写进日志，而不是让进程静默消失。

    为什么必须装：软件是用 ``pythonw.exe`` 启动的 —— **它没有 stderr**。
    于是任何没被 catch 的异常都不会打印到任何地方，进程直接退出，
    用户看到的就是"**闪退**"，而日志里一个字都没有。

    现实中就吃过这个亏：用户报"改作业名会闪退"，
    而 ``gwp.log`` 里连一条改名记录都没有 —— 因为改名根本没执行到，
    而真正的原因（异常）被丢进了不存在的 stderr。

    装两个钩子：

    * ``sys.excepthook`` 管主线程；
    * ``threading.excepthook`` 管后台线程（AI 请求、天气、唤回都在线程里）。

    注意：这只能捕获 **Python 异常**。真正的硬崩溃
    （0xC0000005 访问越界 / 0xC0000409 栈溢出，通常是 Qt 对象被用后释放）
    不会经过这里 —— 那种情况 Windows 事件日志里才有记录。
    """
    global _hooks_installed
    if _hooks_installed:
        return
    _hooks_installed = True
    log = logging.getLogger("gwp.crash")

    def _main_hook(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        log.critical(
            "未捕获的异常（主线程），进程即将退出：\n%s",
            "".join(traceback.format_exception(exc_type, exc_value, exc_tb)),
        )

    def _thread_hook(args) -> None:
        if issubclass(args.exc_type, SystemExit):
            return
        log.critical(
            "未捕获的异常（线程 %s）：\n%s",
            getattr(args.thread, "name", "?"),
            "".join(
                traceback.format_exception(
                    args.exc_type, args.exc_value, args.exc_traceback
                )
            ),
        )

    sys.excepthook = _main_hook
    threading.excepthook = _thread_hook


def cleanup_old_logs(log_dir: Path, keep_days: int) -> int:
    """删除超过 keep_days 天的历史日志，返回删除数量。"""
    if keep_days <= 0 or not log_dir.exists():
        return 0
    cutoff = time.time() - keep_days * 86400
    removed = 0
    for item in log_dir.glob("gwp.log.*"):
        try:
            if item.stat().st_mtime < cutoff:
                item.unlink()
                removed += 1
        except OSError:
            continue
    return removed
