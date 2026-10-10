"""跨进程"唤回主窗口"信号。

为什么需要它
------------
需求："当主界面关闭，软件在后台运行"。主窗口被 ``hide()`` 之后，
用户再双击一次桌面快捷方式就能唤回 —— 但**唤回的动作不能在第二个进程里做**。

第一个坑：外部 ShowWindow 会得到全黑窗口
----------------------------------------
最初的实现是：第二个进程发现"已有实例且窗口不可见"，
就直接调 Win32 的 ``ShowWindowAsync(hwnd, SW_SHOW)`` + ``SW_RESTORE``。

**它确实让原生窗口变可见了，但 Qt 完全不知道** ——
没有走到 Qt 的显示流程，就不会重新布局、也不会重绘，
于是用户看到的是一个**全黑的空窗口**。

> **一个控件的"可见性"有两个主人时（操作系统 + 框架），
> 只能让框架去改它。**

第二个坑：覆盖 QWidget.nativeEvent 在 PyQt6 6.11 上必崩
--------------------------------------------------------
自然的第二个想法是"给那个窗口发一条自定义 Windows 消息
（``RegisterWindowMessageW``），由第一个进程在 ``nativeEvent`` 里接住"。
消息 id 确实跨进程一致，但**覆盖 ``nativeEvent`` 本身就会崩溃**：

.. code-block:: text

    passthru  只调用 super().nativeEvent(...)   -> 退出码 -1073740771
    returnfn  直接 return False, None           -> 退出码 -1073740771
    readtype  读一下 event_type 的类型            -> 退出码 -1073740771

（三个最小复现都在 **PyQt6 6.11 + Qt 6.11** 上必崩，
连"什么都不做、只转发给父类"都崩，所以这不是我用错了返回值，
而是这条路在当前 PyQt6 上走不通。）

最终方案：一个"唤回标记"文件 + 定时器
--------------------------------------
不碰原生事件，改成**文件 + 轮询**：

1. 第二个进程启动时，发现"已有实例且窗口不可见"，
   就 ``touch`` 一下 ``else data/wake.request``（写入请求方的 PID 与时间），然后退出；
2. 第一个进程用一个 600ms 的 ``QTimer`` 看这个文件的修改时间有没有变新；
3. 变新了 —— 说明有用户双击了快捷方式 —— 就在**自己的 Qt 事件循环里**
   调 ``show()``，显示与重绘都走 Qt 自己的流程，不会出现黑窗口。

为什么可以接受"最多 600ms 的延迟"：用户刚双击完图标，
600ms 完全在"点击后就该有反应"的感知范围内；
而它换来的好处是**完全不用碰原生事件、也不依赖任何 Windows 消息机制**，
在离屏测试里也能直接验证（见 ``tests/smoke_core.py``）。

这个模块**不依赖 Qt**，只用标准库，可以单独测试。
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

log = logging.getLogger(__name__)

#: 唤回请求文件名（放在 else data 下）
WAKE_FILE_NAME = "wake.request"


def wake_path(data_dir: Path) -> Path:
    return Path(data_dir) / WAKE_FILE_NAME


def request_wake(data_dir: Path) -> bool:
    """请求"那个正在后台运行的实例"把主窗口唤回来。

    做法就是写一个标记文件：**内容不重要，修改时间才重要**
    （另一个进程靠 mtime 变化来判断"有新请求"）。
    写失败也无所谓 —— 那只是"唤不回来"，不该影响本次启动的退出。
    """
    target = wake_path(data_dir)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        # 写 pid 与时间，纯粹为了出问题时能看出来是谁在什么时候请求的
        target.write_text(
            f"{os.getpid()} {time.strftime('%Y-%m-%dT%H:%M:%S')}\n",
            encoding="utf-8",
        )
        log.info("已写入唤回请求：%s", target)
        return True
    except OSError:
        log.debug("写唤回请求失败：%s", target, exc_info=True)
        return False


class WakeWatcher:
    """盯着"唤回标记"文件，发现变化就回调。**不依赖 Qt 定时器**。

    刻意把"判断有没有新请求"（本类）和"隔多久看一次"（界面里的 QTimer）
    分开：这样文件比较逻辑可以在无界面环境下单独测试，
    而界面那边只需要一个定时器调 :meth:`poll`。
    """

    def __init__(self, data_dir: Path) -> None:
        self.path = wake_path(data_dir)
        #: 上次看到的修改时间（``None`` 表示"还没建立基准"）
        self._seen: float | None = None

    def mark_current(self) -> None:
        """把当前状态记为"已看过"（启动时调用，避免把自己写的当成新请求）。"""
        self._seen = self._mtime()

    def _mtime(self) -> float | None:
        try:
            return self.path.stat().st_mtime
        except OSError:
            return None

    def poll(self) -> bool:
        """有新请求返回 True，并把它标记为已处理。"""
        current = self._mtime()
        if current is None:
            # 文件被删了（或从来没有过）—— 更新基准，不算新请求
            self._seen = None
            return False
        if self._seen is None:
            # 第一次看到：说明这是启动后才出现的请求 -> 算新请求
            self._seen = current
            return True
        if current > self._seen:
            self._seen = current
            return True
        return False


__all__ = [
    "WAKE_FILE_NAME",
    "WakeWatcher",
    "request_wake",
    "wake_path",
]
