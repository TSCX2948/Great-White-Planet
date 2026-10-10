"""单实例锁：同一个数据目录只允许一个主窗口运行。

为什么需要
----------
需求是"本软件在一个桌面只能打开一个主页面"。如果不拦，
双击两次快捷方式就会得到两个主窗口，两边各自维护扫描结果与聊天会话，
容易让人误操作（在 A 窗口删了科目，B 窗口还显示着）。

实现方式
--------
在 ``else data`` 下放一个 ``instance.lock``，里面写当前进程的 PID。
启动时：

1. 锁文件不存在 -> 直接写入自己的 PID，拿到锁；
2. 锁文件存在且里面的 PID **仍然存活** -> 说明已有实例在跑，本次启动应当退出；
3. 锁文件存在但 PID 已不存在（上次崩溃/被强杀）-> 视为陈旧锁，接管它。

用 PID 而不是"文件是否被占用"来判断，是因为 Windows 允许删除他人打开的文件，
单靠锁文件存在与否并不可靠；而 PID 存活检查在任务管理器里也解释得通。

这个模块不依赖 Qt，因此可以在无界面环境下单独测试。
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

#: 锁文件名（位于 else data 下）
LOCK_FILE_NAME = "instance.lock"

#: 陈旧锁的额外判定：文件超过这个秒数没更新，且 PID 无法确认存活时也接管
STALE_SECONDS = 24 * 3600


@dataclass
class LockInfo:
    """锁文件内容。"""

    pid: int = 0
    hwnd: int = 0                 # 主窗口句柄，用于判断它在哪个虚拟桌面
    executable: str = ""
    raw: str = ""

    @property
    def valid(self) -> bool:
        return self.pid > 0


@dataclass
class InstanceLock:
    """持有实例锁；进程退出时释放。"""

    path: Path
    pid: int
    acquired: bool = False
    hwnd: int = 0                 # 已有实例的主窗口句柄（未持锁时有意义）
    other_pid: int = 0            # 已有实例的 PID（未持锁时有意义）
    on_other_desktop: bool = False  # 已有实例是否开在另一个虚拟桌面上

    def release(self) -> None:
        """删除锁文件（仅当它确实属于自己时）。"""
        if not self.acquired:
            return
        try:
            existing = read_lock(self.path).pid
            if existing in (None, 0, self.pid) and self.path.exists():
                self.path.unlink()
                log.debug("已释放实例锁：%s", self.path)
        except OSError:
            log.debug("释放实例锁失败：%s", self.path, exc_info=True)
        finally:
            self.acquired = False

    def publish_window(self, hwnd: int) -> None:
        """把自己主窗口的句柄写进锁文件（供下一个实例判断虚拟桌面）。"""
        if not self.acquired:
            return
        self.hwnd = int(hwnd or 0)
        _write_lock(self.path, self.pid, self.hwnd)


def lock_path(data_dir: Path) -> Path:
    return Path(data_dir) / LOCK_FILE_NAME


def read_lock(path: Path) -> LockInfo:
    """读锁文件。

    兼容两种格式：

    * 新的 JSON：``{"pid": 123, "hwnd": 456, ...}``
    * 旧的两行文本：第一行 PID，第二行解释器路径
    """
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return LockInfo()
    if not text:
        return LockInfo()

    if text.startswith("{"):
        try:
            data = json.loads(text)
        except ValueError:
            return LockInfo(raw=text)
        if not isinstance(data, dict):
            return LockInfo(raw=text)
        try:
            pid = int(data.get("pid") or 0)
        except (TypeError, ValueError):
            pid = 0
        try:
            hwnd = int(data.get("hwnd") or 0)
        except (TypeError, ValueError):
            hwnd = 0
        return LockInfo(
            pid=pid, hwnd=hwnd, executable=str(data.get("exe") or ""), raw=text
        )

    # 旧格式
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return LockInfo(raw=text)
    first = lines[0].split()[0].split(",")[0]
    try:
        pid = int(first)
    except ValueError:
        return LockInfo(raw=text)
    return LockInfo(pid=pid, executable=lines[1] if len(lines) > 1 else "", raw=text)


def read_lock_pid(path: Path) -> int | None:
    """只取锁里的 PID；读不到返回 None。"""
    info = read_lock(path)
    return info.pid or None


def _write_lock(path: Path, pid: int, hwnd: int = 0) -> None:
    """原子写入锁文件。"""
    payload = {
        "pid": int(pid),
        "hwnd": int(hwnd or 0),
        "exe": os.path.abspath(sys.executable),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, path)


def is_process_alive(pid: int) -> bool:
    """判断某个 PID 是否仍然存在。

    只用于"同一台机器上的同一个用户"，因此不做权限猜测：
    权限不足时保守地当作"存活"，避免误抢别人的锁。
    """
    if pid <= 0:
        return False
    if pid == os.getpid():
        return True

    if sys.platform.startswith("win"):
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.OpenProcess.argtypes = [ctypes.c_uint, ctypes.c_int, ctypes.c_uint]
        kernel32.GetExitCodeProcess.restype = ctypes.c_int
        kernel32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint)]
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
        if not handle:
            error = ctypes.get_last_error()
            # 5 = 拒绝访问：进程存在但打不开 -> 当作存活
            if error == 5:
                return True
            return False
        try:
            code = ctypes.c_uint(0)
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)

    # 类 Unix：信号 0 只探测存在性
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def running_instance(data_dir: Path) -> LockInfo | None:
    """如果已有实例在运行，返回它的信息；否则返回 None。"""
    path = lock_path(data_dir)
    info = read_lock(path)
    if not info.valid:
        return None
    if info.pid == os.getpid():
        return None
    if is_process_alive(info.pid):
        return info
    log.info("发现陈旧实例锁（PID %s 已不存在），将接管：%s", info.pid, path)
    return None


def acquire(data_dir: Path, hwnd: int = 0) -> InstanceLock:
    """尝试获取实例锁。

    返回的 :class:`InstanceLock` 里 ``acquired`` 为 False 时，
    说明已有实例在运行，调用方应当退出；此时 ``pid`` / ``hwnd`` /
    ``on_other_desktop`` 描述那个实例的情况。
    """
    data_dir = Path(data_dir)
    path = lock_path(data_dir)
    existing = running_instance(data_dir)
    if existing is not None:
        # 那个实例的窗口是不是开在别的虚拟桌面上？
        on_other = False
        if existing.hwnd:
            from gwp.core import desktops

            verdict = desktops.window_is_on_current_desktop(existing.hwnd)
            on_other = verdict is False
            # 这一行是排错用的关键信息：用户报告的"没反应/重复开"都能靠它定位
            log.info(
                "已有实例：PID=%s 窗口=%s 桌面判定=%s（True=同桌面 False=另一个桌面 None=无法判断）",
                existing.pid,
                existing.hwnd,
                verdict,
            )
        else:
            log.info(
                "已有实例：PID=%s 但没有记录窗口句柄（旧版本锁），只做同窗口判断",
                existing.pid,
            )
        if on_other:
            log.warning(
                "已有实例（PID %s，窗口 %s）开在另一个虚拟桌面上",
                existing.pid,
                existing.hwnd,
            )
        return InstanceLock(
            path=path,
            pid=existing.pid,
            acquired=False,
            hwnd=existing.hwnd,
            other_pid=existing.pid,
            on_other_desktop=on_other,
        )

    try:
        _write_lock(path, os.getpid(), hwnd)
    except OSError:
        # 锁写不进去（例如只读目录）时不要让软件无法启动，只记日志
        log.warning("无法写入实例锁，跳过单实例检查：%s", path, exc_info=True)
        return InstanceLock(path=path, pid=os.getpid(), acquired=True)

    return InstanceLock(path=path, pid=os.getpid(), acquired=True, hwnd=hwnd)


__all__ = [
    "LOCK_FILE_NAME",
    "STALE_SECONDS",
    "InstanceLock",
    "LockInfo",
    "acquire",
    "is_process_alive",
    "lock_path",
    "read_lock",
    "read_lock_pid",
    "running_instance",
]
