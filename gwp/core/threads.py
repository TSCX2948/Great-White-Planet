"""线程登记处：保证"还有线程在跑"时不会把 QThread 析构掉。

为什么必须有这个模块
--------------------
Qt 有一条**会直接中止进程**的检查：如果一个 ``QThread`` 对象被析构时它还在运行，
Qt 会调用 ``qFatal`` 打印

    QThread: Destroyed while thread '' is still running

然后立刻终止进程（退出码 ``0xC0000409``）。它**不抛 Python 异常**，
所以日志里一个字都没有，用户看到的就是"**闪退**"。

现实中就撞上了：用户报"改作业名会闪退"，而 Windows 事件日志里是

    出错应用程序名称： pythonw.exe
    出错模块名称： Qt6Core.dll
    异常代码： 0xc0000409

我们自己也复现了同样的退出码 —— 只要在预扫描线程还在跑的时候结束进程就会崩。

原来的做法是在 ``MainWindow.closeEvent`` 里对 ``StartupWorker``
``wait(3000)``。问题是**预扫描 7 个科目要 20 多秒**：3 秒一到就放弃，
窗口照常销毁，线程还在跑 —— 于是崩。

这里的做法
----------
不再"在某一个地方记得等某一个线程"（那种写法每加一个线程就要补一次，
漏一个就是随机闪退），而是：

* 每个后台线程创建时**登记**自己；
* 结束时**注销**；
* 退出时统一等待所有还活着的线程 —— 而且等得**久一点、分两轮**：
  先给一个正常预算，没结束就再给一个更长的兜底预算。

这一个模块把"随机闪退"变成"最多退出慢几秒"。
"""

from __future__ import annotations

import logging
import threading
from typing import Any

log = logging.getLogger(__name__)

#: 还活着的线程（弱引用没有意义 —— 我们要的正是"别让它被回收"）
_live: dict[int, Any] = {}
_lock = threading.Lock()

#: 正常退出时每轮等待的毫秒数。第一轮短（大多数线程这时已经停了），
#: 第二轮长（预扫描这种慢活需要时间）。
GRACE_MS = 2000
FINAL_MS = 20000


def register(thread: Any) -> None:
    """登记一个后台线程。"""
    with _lock:
        _live[id(thread)] = thread


def unregister(thread: Any) -> None:
    """注销（线程正常结束时调用）。"""
    with _lock:
        _live.pop(id(thread), None)


def live_count() -> int:
    """还登记着的线程数（测试用）。"""
    with _lock:
        return len(_live)


def _is_running(thread: Any) -> bool:
    try:
        from PyQt6.QtCore import QThread

        if isinstance(thread, QThread):
            return bool(thread.isRunning())
    except Exception:  # noqa: BLE001 - 拿不到 Qt 就当作"在跑"，保守等待
        return True
    return False


def detach_all() -> int:
    """把所有登记着的线程**从父对象上摘下来**，返回处理数量。

    这一步是必须的，而且顺序很关键。

    本项目的后台线程几乎都带父对象（``AIWorker(task, parent=self)`` 这类），
    这是好习惯 —— 父窗口一销毁，Qt 就会连带销毁它。但在**退出**时它变成了坑：

    * 窗口 ``deleteLater()`` -> Qt 销毁它的子 ``QThread`` -> 线程还在跑
      -> ``qFatal`` -> **进程被中止**（0xC0000409，用户看到"闪退"）；
    * 这时候我们**还没机会**去 ``wait()``，因为销毁发生在 Qt 内部。

    所以退出时必须**先脱钩、再等待**，顺序反了就没用（都实测过）：

        detach_all()      # 先 setParent(None)：Qt 不再连带销毁它
        stop_all()        # 再 quit() + wait()：等它自己收工

    脱钩之后线程对象仍被本模块的登记表持有，所以不会被 Python 垃圾回收 ——
    这也正是登记表要保存强引用而不只是弱引用的原因。
    """
    with _lock:
        threads = list(_live.values())
    count = 0
    for thread in threads:
        try:
            thread.setParent(None)
            count += 1
        except Exception:  # noqa: BLE001 - 不是 QObject 之类，跳过
            continue
    if count:
        log.info("退出前已把 %d 个后台线程从父对象上摘下来", count)
    return count


def stop_all(*, grace_ms: int = GRACE_MS, final_ms: int = FINAL_MS) -> int:
    """等所有登记着的线程结束。返回**最终仍在运行**的线程数。

    分两轮等：第一轮给正常预算，还没结束就再给一个更长的兜底预算。
    等不完也不抛异常 —— 但会把情况记进日志，这样下次能查到是哪个线程。
    """
    with _lock:
        threads = list(_live.values())
    if not threads:
        return 0

    remaining = [t for t in threads if _is_running(t)]
    if not remaining:
        return 0
    log.info("退出前还有 %d 个后台线程在跑，等待它们结束……", len(remaining))

    for round_ms in (max(0, grace_ms), max(0, final_ms)):
        for thread in remaining:
            if not _is_running(thread):
                continue
            # 先请它自己退出（QThread 的 quit 会让事件循环收工）
            try:
                thread.quit()
            except Exception:  # noqa: BLE001
                pass
            try:
                thread.wait(round_ms)
            except Exception:  # noqa: BLE001 - 等不到不该让退出失败
                log.debug("等待线程结束失败", exc_info=True)
        remaining = [t for t in remaining if _is_running(t)]
        if not remaining:
            return 0

    log.warning(
        "退出时仍有 %d 个线程在运行：%s",
        len(remaining),
        [type(t).__name__ for t in remaining],
    )
    return len(remaining)


def shutdown(*, grace_ms: int = GRACE_MS, final_ms: int = FINAL_MS) -> int:
    """退出时的**唯一入口**：先脱钩，再等待。返回仍在运行的线程数。

    调用方只要调这一个函数 —— 顺序不会记错（分成两个函数调就一定会有人
    只调其中一个，然后随机闪退）。

    调用之后**清空登记表**：退出是终结性的，留着那些引用只会让
    ``live_count()`` 报出"其实已经停了"的线程（而且长时间运行的进程
    会攒下每一个创建过的 worker）。
    """
    try:
        detach_all()
        still = stop_all(grace_ms=grace_ms, final_ms=final_ms)
    finally:
        with _lock:
            _live.clear()
    return still


__all__ = [
    "FINAL_MS",
    "GRACE_MS",
    "detach_all",
    "live_count",
    "register",
    "shutdown",
    "stop_all",
    "unregister",
]
