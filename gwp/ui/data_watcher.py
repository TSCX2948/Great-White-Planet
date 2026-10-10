"""后台盯着 ``user data`` 的变化，有变动就通知界面刷新。

需求：

> 软件后台要不断扫描user data文件夹，更新文件变动，但不要耗费cpu太多性能

这需求里有一对**互相拉扯**的要求：既要"不断扫描"，又要"别耗 CPU"。
所以设计上做了三件事，每一件都是为了把代价压到可以忽略：

一、用 ``os.scandir`` 而不是 ``pathlib.rglob``
------------------------------------------------
实测（本机真实数据 + 5000 项假数据）：

===========  =========  ==========  ==================
方式          97 项      5100 项     每 5 秒占单核
===========  =========  ==========  ==================
rglob+stat    10.7 ms    **243 ms**  **4.86%**
os.scandir     3.3 ms    **10.4 ms**  **0.21%**
===========  =========  ==========  ==================

差 **23 倍**。原因是 Windows 的 ``DirEntry.stat()`` 直接复用目录项里已有的信息，
**不再发起系统调用**；而 ``Path.stat()`` 每次都要问一遍文件系统。
所以 5000 个文件下，rglob 方案每 5 秒要烧掉近 5% 的单核 —— 那是不可接受的；
scandir 方案 0.21%，可以长期开着。

二、只在"变了"的时候才做昂贵的事
--------------------------------
扫描只做一件最便宜的事：拿一份 ``路径 -> mtime`` 快照并与上一份**逐项比较**。
只有真的不同，才去让 ``Library`` 失效并重建界面 —— 那一步要 26 ms
（会重新解析每个书目的元信息），绝不能每个 tick 都做。

三、看不见的时候不扫
--------------------
窗口隐藏到后台（"关闭到后台"功能）或最小化时**完全停掉**定时器 ——
既然没人看，就没必要扫。窗口恢复时立刻补扫一次，
所以"后台改了文件、切回来"也能马上看到。

连续两次一样才算稳定
--------------------
本软件自己写文件（保存笔记、生成总结）也会改变 mtime。
如果一检测到不同就通知，可能正好抓到"写到一半"的中间状态，
界面会闪一下又变回来。所以要求**连续两次快照一致**才认账 ——
中间状态自然被过滤掉。

这个模块**依赖 Qt**（用 ``QTimer`` 和信号），所以放在 ``ui`` 这一层。
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

log = logging.getLogger(__name__)

#: 默认扫描间隔（毫秒）。
#:
#: 取值权衡（实测：本机数据 97 项 ≈ 3.3 ms，5000 项 ≈ 10.4 ms）：
#:
#: * ``2000`` —— 单核约 0.4%（5000 项规模），改动最多约
#:   ``interval * STABLE_TICKS``＋一次 tick ≈ **6 秒**可见；
#: * 想更省就调大（如 15000 -> 约 0.07%）；
#: * 最小 1000（再小就接近忙等，收益也很小）。
#:
#: 默认选 2 秒而不是 5 秒：要"看起来是实时的"就必须秒级，
#: 而靠"更便宜的单次扫描 + 固定观察窗口"完全扛得住这个频率。
DEFAULT_INTERVAL_MS = 2000

#: 间隔的上下限（防止把配置写成 0 或 1 而变成忙等）
MIN_INTERVAL_MS = 1000
MAX_INTERVAL_MS = 120_000

#: "观察窗口"是间隔的多少倍 —— 新状态稳定这么久之后才认账。
#:
#: 为什么不是"两次一致就够了"：一次 tick 太短，抓不住"写到一半"。
#: 用**固定的时间窗口**而不是"固定次数"，就能用更短的轮询间隔
#: 换取同样的稳妥：间隔 2 秒 + 窗口 4 秒 ≈ 最多 6 秒发现，
#: 而"两次一致"要 4 秒起、实测常到 10~14 秒。
STABLE_TICKS = 2.0


def snapshot(base: Path) -> dict[str, int]:
    """走一遍目录树，返回 ``{路径: mtime_ns}``。

    用 ``os.scandir`` 迭代式实现（不用递归，避免深目录爆栈）。
    读不到的条目**静默跳过** —— 扫描是尽力而为的后台行为，
    不该因为一个权限问题或"文件刚好被删掉"而中断整次扫描。

    **刻意不包含 ``base`` 自己**：目录的 mtime 会因为子项增删而变化，
    但我们要靠"两次快照完全一致"来判断"没有变化"。把 base 自己算进去，
    会让"新增一个文件再删掉"这种回到原状的操作永远判成"有变化"
    （实测就是这么挂的）。base 自己的变化必然伴随子项变化，
    所以不收录它不会漏掉任何真实改动。
    """
    result: dict[str, int] = {}
    stack = [str(base)]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        stat = entry.stat()
                    except OSError:
                        continue
                    result[entry.path] = stat.st_mtime_ns
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
                    except OSError:
                        continue
        except OSError:
            # 目录刚被删掉/无权限：跳过它，不要影响其它目录
            continue
    return result


def diff_snapshots(old: dict[str, int], new: dict[str, int]) -> tuple[list[str], list[str]]:
    """返回 ``(新增或改动的路径, 消失的路径)``。"""
    added = [path for path, mtime in new.items() if old.get(path) != mtime]
    removed = [path for path in old if path not in new]
    return added, removed


class DataWatcher(QObject):
    """定时比对 ``user data`` 的快照，有变化就发 ``changed`` 信号。"""

    #: 数据确实变了（参数是"新增/改动"与"消失"的路径列表）
    changed = pyqtSignal(list, list)

    def __init__(self, base: Path, parent: QObject | None = None,
                 *, interval_ms: int = DEFAULT_INTERVAL_MS,
                 stable_seconds: float | None = None) -> None:
        super().__init__(parent)
        self.base = Path(base)
        self._interval = max(MIN_INTERVAL_MS,
                             min(MAX_INTERVAL_MS, int(interval_ms or DEFAULT_INTERVAL_MS)))
        #: 观察窗口（秒）。默认按间隔推算；测试可以显式给小值 ——
        #: 否则"紧密循环调 check_now()"永远不会推进时间，
        #: 窗口永远等不到（我第一版就是这么把测试写挂的）。
        self._stable_seconds = (
            float(stable_seconds) if stable_seconds is not None
            else self._interval * STABLE_TICKS / 1000.0
        )
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval)
        self._timer.timeout.connect(self._tick)
        self._baseline: dict[str, int] | None = None
        self._pending: dict[str, int] | None = None
        #: 待确认状态是**什么时候**第一次看到的（用于"观察窗口"超时）
        self._pending_since = 0.0
        self._enabled = True
        #: 统计（给"工具 → 依赖自检"之类的地方看，也方便测试断言）
        self.scan_count = 0
        self.change_count = 0
        self.last_scan_ms = 0.0

    # -- 生命周期 -------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._timer.isActive()

    @property
    def interval_ms(self) -> int:
        return self._interval

    def start(self) -> None:
        """开始监听（先取一份基准快照，避免启动瞬间误报一次"全都变了"）。"""
        if self._timer.isActive():
            return
        self._baseline = snapshot(self.base)
        self._pending = None
        self.scan_count += 1
        self._timer.start()
        log.info("已开始监听数据目录变化（每 %d ms 一次）：%s",
                 self._interval, self.base)

    def stop(self) -> None:
        """停止监听（窗口隐藏时调用）。

        注意：**不清掉基准快照** —— 停掉期间发生的改动，
        恢复时会因为和旧基准不同而被发现，正是我们想要的。
        """
        if self._timer.isActive():
            self._timer.stop()
            log.debug("已暂停数据目录监听")

    def set_enabled(self, enabled: bool) -> None:
        """总开关（给"不要自动刷新"这种偏好留的口子）。"""
        self._enabled = bool(enabled)
        if not self._enabled:
            self.stop()

    def mark_current(self) -> None:
        """把当前状态记为基准（本软件自己改完文件后调用，避免自我误报）。"""
        self._baseline = snapshot(self.base)
        self._pending = None
        self.scan_count += 1

    # -- 一次扫描 -------------------------------------------------------

    def check_now(self) -> bool:
        """立刻扫一次。返回**本次是否确认了变化**（测试也用它）。"""
        return self._tick(force=True)

    def _tick(self, force: bool = False) -> bool:
        if not self._enabled and not force:
            return False
        started = time.perf_counter()
        now = time.time()
        current = snapshot(self.base)
        self.last_scan_ms = (time.perf_counter() - started) * 1000
        self.scan_count += 1

        if self._baseline is None:
            self._baseline = current
            return False
        if current == self._baseline:
            # 和"已认账的状态"一致 -> 没有变化
            self._pending = None
            return False
        if self._pending is None:
            # 第一次看到与基线不同：先记下来，等下一次确认
            self._pending = current
            self._pending_since = now
            return False
        if current != self._pending:
            # 又变了（还在写）：更新待确认值，继续等
            self._pending = current
            self._pending_since = now
            return False
        if (now - self._pending_since) < self._stable_seconds:
            # 新状态看起来稳定了，但还没等够"观察窗口"。
            #
            # 为什么要这个窗口而不是"两次一致就够了"：**一次 tick 太短**，
            # 抓不住"写到一半"。实测一个很小的改动也要 10~14 秒才被发现
            # （因为"两次一致"等于把间隔翻倍），体感偏慢。
            # 等一个明确的观察窗口，就能用**更短的轮询间隔**换取同样的稳妥。
            return False

        # 观察窗口内状态没再变 -> 认账。
        # 注意比较与采纳都用 `_pending`（上一次看到的那个稳定值），
        # 不用 `_baseline` —— 我第一版拿旧基线去比，
        # 结果"待确认值已经是最新"时仍判成"还在变"，一条通知都发不出来。
        added, removed = diff_snapshots(self._baseline, self._pending)
        self._baseline = self._pending
        self._pending = None
        self._pending_since = 0.0
        self.change_count += 1
        log.info("数据目录有变化：新增/改动 %d 项，消失 %d 项"
                 "（例如 %s）", len(added), len(removed),
                 ", ".join((added or removed)[:3]))
        self.changed.emit(added, removed)
        return True


__all__ = [
    "DEFAULT_INTERVAL_MS",
    "MAX_INTERVAL_MS",
    "MIN_INTERVAL_MS",
    "DataWatcher",
    "diff_snapshots",
    "snapshot",
]
