"""Windows 虚拟桌面（Win11 多桌面）检测。

为什么需要
----------
Win11 的"多桌面"其实是**一个桌面命名空间**，不是独立会话。用户在桌面 1 开着软件，
切到桌面 2 再双击快捷方式，任务栏不会有任何变化（窗口在桌面 1），
用户会以为"点了没反应"。需求是：这种情况要**弹窗明确告知**，并只保留一个实例。

怎么判断
--------
Windows 提供 ``IVirtualDesktopManager`` 接口，其中
``IsWindowOnCurrentVirtualDesktop(hwnd)`` 会告诉我们"这个窗口是不是在当前桌面上"。
思路：

1. 第一个实例把自己的**窗口句柄（HWND）**写进 ``instance.lock``；
2. 第二个实例拿到那个 HWND，问系统"它在当前桌面吗"；
3. 不在 -> 说明已有实例开在**另一个虚拟桌面**上，弹窗提示并退出。

另外，我们会给主窗口设置 ``Qt::WA_X11DoNotAcceptFocus`` 之外更关键的一项：
Windows 上窗口默认**跟随所有虚拟桌面**显示（``pin``），
所以必须显式关闭，否则软件会在每个桌面上都出现。

这个模块完全用 ctypes 调 Win32，不依赖 pywin32；任何一步失败都退化为
"不做跨桌面检查"，绝不因为检测失败而让软件打不开。
"""

from __future__ import annotations

import ctypes
import logging
import sys
from ctypes import wintypes

log = logging.getLogger(__name__)

#: IVirtualDesktopManager 的 IID 与 CLSID（Windows 10 起稳定，Win11 沿用）
CLSID_VirtualDesktopManager = "{AA509086-5CA9-4C25-8F95-589D3C07B48A}"
IID_IVirtualDesktopManager = "{A5CD92FF-29BE-454C-8D04-D82879FB3F1B}"

CLSCTX_ALL = 0x17
COINIT_APARTMENTTHREADED = 0x2
RPC_E_CHANGED_MODE = -2147417850  # 0x80010106
S_OK = 0
S_FALSE = 1  # CoInitializeEx 返回它表示"本线程已经初始化过"，同样是成功


class VirtualDesktopUnavailable(RuntimeError):
    """当前系统拿不到虚拟桌面信息（非 Windows / 接口不可用）。"""


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_ubyte * 8),
    ]

    @classmethod
    def from_string(cls, text: str) -> "_GUID":
        cleaned = text.strip().strip("{}")
        parts = cleaned.split("-")
        if len(parts) != 5:
            raise ValueError(f"GUID 格式不对：{text}")
        data4 = bytes.fromhex(parts[3] + parts[4])
        return cls(
            int(parts[0], 16),
            int(parts[1], 16),
            int(parts[2], 16),
            (ctypes.c_ubyte * 8)(*data4),
        )


def is_supported() -> bool:
    """当前系统是否支持虚拟桌面检测。"""
    return sys.platform.startswith("win")


def _ensure_com() -> bool:
    """确保当前线程初始化了 COM（公寓模型）。

    返回 True 表示可以继续使用 COM。注意三种"都能用"的返回：
    ``S_OK``（刚初始化）、``S_FALSE``（本线程此前已初始化）、
    ``RPC_E_CHANGED_MODE``（已被初始化成别的公寓模型，Qt 常见）。
    """
    try:
        ole32 = ctypes.WinDLL("ole32", use_last_error=True)
        ole32.CoInitializeEx.restype = ctypes.c_long
        ole32.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        result = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        if result in (S_OK, S_FALSE, RPC_E_CHANGED_MODE):
            return True
        log.debug("CoInitializeEx 返回 0x%08X", result & 0xFFFFFFFF)
        return False
    except OSError:
        log.debug("无法加载 ole32", exc_info=True)
        return False


def _create_manager():
    """创建 IVirtualDesktopManager 实例，失败抛 VirtualDesktopUnavailable。"""
    if not is_supported():
        raise VirtualDesktopUnavailable("非 Windows 系统，不做虚拟桌面检查")

    if not _ensure_com():
        raise VirtualDesktopUnavailable("COM 初始化失败")

    ole32 = ctypes.WinDLL("ole32", use_last_error=True)
    ole32.CoCreateInstance.restype = ctypes.c_long
    ole32.CoCreateInstance.argtypes = [
        ctypes.POINTER(_GUID),
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.POINTER(_GUID),
        ctypes.POINTER(ctypes.c_void_p),
    ]

    clsid = _GUID.from_string(CLSID_VirtualDesktopManager)
    iid = _GUID.from_string(IID_IVirtualDesktopManager)
    pointer = ctypes.c_void_p()
    result = ole32.CoCreateInstance(
        ctypes.byref(clsid), None, CLSCTX_ALL, ctypes.byref(iid), ctypes.byref(pointer)
    )
    if result != S_OK or not pointer:
        raise VirtualDesktopUnavailable(
            f"CoCreateInstance(IVirtualDesktopManager) 失败：0x{result & 0xFFFFFFFF:08X}"
        )
    return pointer


def _vtable_method(pointer: ctypes.c_void_p, index: int, restype, argtypes):
    """取出 COM 接口第 index 个虚函数（0=QueryInterface,1=AddRef,2=Release）。"""
    vtable = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p)).contents.value
    entries = ctypes.cast(vtable, ctypes.POINTER(ctypes.c_void_p))
    address = entries[index]
    prototype = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return prototype(address)


def window_is_on_current_desktop(hwnd: int) -> bool | None:
    """判断某个窗口是否在当前虚拟桌面上。

    返回 ``True`` / ``False``；无法判断时返回 ``None``（调用方应当当作"同桌面"处理，
    宁可少拦一次，也不要误拦导致软件打不开）。
    """
    if not hwnd or not is_supported():
        return None
    manager = None
    try:
        manager = _create_manager()
        BOOL = ctypes.c_int
        # IVirtualDesktopManager 的方法顺序：
        #   0 QueryInterface  1 AddRef  2 Release
        #   3 IsWindowOnCurrentVirtualDesktop  4 GetWindowDesktopId  5 IsWindowOnCurrentVirtualDesktopByApp
        method = _vtable_method(
            manager, 3, ctypes.c_long, [wintypes.HWND, ctypes.POINTER(BOOL)]
        )
        on_current = BOOL(0)
        result = method(manager, wintypes.HWND(hwnd), ctypes.byref(on_current))
        if result != S_OK:
            log.info(
                "IsWindowOnCurrentVirtualDesktop(0x%X) 失败：0x%08X（按同桌面处理）",
                hwnd,
                result & 0xFFFFFFFF,
            )
            return None
        return bool(on_current.value)
    except VirtualDesktopUnavailable as exc:
        log.debug("虚拟桌面接口不可用：%s", exc)
        return None
    except Exception:  # noqa: BLE001 - 检测失败不应影响启动
        log.debug("虚拟桌面检测异常", exc_info=True)
        return None
    finally:
        if manager:
            try:
                release = _vtable_method(manager, 2, ctypes.c_ulong, [])
                release(manager)
            except Exception:  # noqa: BLE001
                pass


def window_is_on_other_desktop(hwnd: int) -> bool:
    """窗口是否开在**另一个**虚拟桌面上（无法判断时返回 False）。"""
    return window_is_on_current_desktop(hwnd) is False


def window_desktop_id(hwnd: int) -> str | None:
    """取窗口所在虚拟桌面的 GUID（失败返回 None）。"""
    if not hwnd or not is_supported():
        return None
    manager = None
    try:
        manager = _create_manager()
        # 0 QueryInterface  1 AddRef  2 Release
        # 3 IsWindowOnCurrentVirtualDesktop  4 GetWindowDesktopId
        method = _vtable_method(
            manager, 4, ctypes.c_long, [wintypes.HWND, ctypes.POINTER(_GUID)]
        )
        desktop = _GUID()
        result = method(manager, wintypes.HWND(hwnd), ctypes.byref(desktop))
        if result != S_OK:
            log.debug("GetWindowDesktopId 返回 0x%08X", result & 0xFFFFFFFF)
            return None
        return str(desktop)
    except VirtualDesktopUnavailable as exc:
        log.debug("虚拟桌面接口不可用：%s", exc)
        return None
    except Exception:  # noqa: BLE001
        log.debug("读取桌面 ID 异常", exc_info=True)
        return None
    finally:
        if manager:
            try:
                _vtable_method(manager, 2, ctypes.c_ulong, [])(manager)
            except Exception:  # noqa: BLE001
                pass


def _switch_desktop_to(hwnd: int) -> bool:
    """把当前桌面切换到 ``hwnd`` 所在的虚拟桌面（失败返回 False）。"""
    manager = None
    try:
        manager = _create_manager()
        # 0..4 同上，5 = IsWindowOnCurrentVirtualDesktopByApp
        get_id = _vtable_method(
            manager, 4, ctypes.c_long, [wintypes.HWND, ctypes.POINTER(_GUID)]
        )
        desktop = _GUID()
        if get_id(manager, wintypes.HWND(hwnd), ctypes.byref(desktop)) != S_OK:
            return False
        switch = _vtable_method(manager, 6, ctypes.c_long, [ctypes.c_void_p])
        result = switch(manager, ctypes.byref(desktop))
        if result != S_OK:
            log.info("SwitchDesktop 返回 0x%08X（系统可能不允许程序切换桌面）", result & 0xFFFFFFFF)
            return False
        return True
    except VirtualDesktopUnavailable as exc:
        log.debug("无法切换桌面：%s", exc)
        return False
    except Exception:  # noqa: BLE001
        log.debug("切换桌面异常", exc_info=True)
        return False
    finally:
        if manager:
            try:
                _vtable_method(manager, 2, ctypes.c_ulong, [])(manager)
            except Exception:  # noqa: BLE001
                pass


def activate_window(hwnd: int) -> bool:
    """把已有实例所在桌面切过来，并让它的窗口获得焦点。

    这是"尽力而为"的操作：Windows 对程序主动切换虚拟桌面有限制，
    失败时返回 False，调用方只需提示用户手动用 ``Win+Ctrl+←/→`` 切换。
    """
    if not hwnd or not is_supported():
        return False

    switched = False
    if window_is_on_current_desktop(hwnd) is False:
        switched = _switch_desktop_to(hwnd)

    # 无论是否切换成功，都试着把窗口还原并置前
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.ShowWindowAsync.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        SW_RESTORE = 9
        user32.ShowWindowAsync(wintypes.HWND(hwnd), SW_RESTORE)
        user32.SetForegroundWindow(wintypes.HWND(hwnd))
    except Exception:  # noqa: BLE001
        log.debug("激活已有窗口失败", exc_info=True)

    return switched


def window_is_visible(hwnd: int) -> bool | None:
    """判断某个窗口当前是否可见。无法判断时返回 ``None``。

    用途：区分"已有实例只是藏在后台"和"已有实例开着但用户找不到"。
    前者应当**直接把窗口显示出来**，不该再弹"已经在运行"的提示框 ——
    用户其实是刚双击了快捷方式、期待看到窗口，而不是被教育一顿。
    """
    if not hwnd or not sys.platform.startswith("win"):
        return None
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.IsWindow.argtypes = [wintypes.HWND]
        user32.IsWindow.restype = wintypes.BOOL
        if not user32.IsWindow(wintypes.HWND(hwnd)):
            return None                     # 句柄已失效（窗口真的关了）
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL
        return bool(user32.IsWindowVisible(wintypes.HWND(hwnd)))
    except Exception:  # noqa: BLE001
        log.debug("查询窗口可见性失败：hwnd=%s", hwnd, exc_info=True)
        return None


def request_wake_window(hwnd: int) -> bool:
    """请 ``hwnd`` 所属进程**自己**把窗口显示出来。成功投递返回 True。

    **只做"请求"，不代替它显示窗口** —— 这一点是踩坑换来的：
    从外部调 ``ShowWindowAsync(SW_SHOW)`` 确实能让原生窗口变可见，
    但 Qt 不知道，于是不布局、不重绘，用户看到的是**全黑窗口**。

    所以这里只投递一条自定义消息（见 :mod:`gwp.core.wakeup`），
    显示动作由那个进程在 Qt 事件循环里完成。
    """
    if not hwnd:
        return False
    from gwp.core import wakeup

    return wakeup.send_wake(hwnd)


def bring_to_front(hwnd: int) -> bool:
    """把已经可见的窗口置前（不改变它的可见性）。尽力而为。

    与 :func:`request_wake_window` 的分工：

    * 窗口**不可见** -> 用 ``request_wake_window``，让对方自己显示；
    * 窗口**已可见但被别的窗口盖住** -> 用本函数置前即可。
    """
    if not hwnd or not sys.platform.startswith("win"):
        return False
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        user32.SetForegroundWindow(wintypes.HWND(hwnd))
        return True
    except Exception:  # noqa: BLE001 - 置前失败不影响功能
        log.debug("窗口置前失败：hwnd=%s", hwnd, exc_info=True)
        return False


def show_and_activate_window(hwnd: int) -> bool:
    """请对方进程唤回窗口，并对**已可见**的窗口做置前。成功返回 True。

    .. deprecated:: 已被 :func:`request_wake_window` + :func:`bring_to_front` 取代
       保留这个名字是因为它以前直接调 ``ShowWindowAsync``，
       而那正是"全黑窗口"的根因。现在它只投递请求 + 置前，不再强行改可见性。
    """
    if not hwnd:
        return False
    requested = request_wake_window(hwnd)
    if window_is_visible(hwnd):
        bring_to_front(hwnd)
    return requested


__all__ = [
    "CLSID_VirtualDesktopManager",
    "IID_IVirtualDesktopManager",
    "VirtualDesktopUnavailable",
    "activate_window",
    "bring_to_front",
    "is_supported",
    "request_wake_window",
    "show_and_activate_window",
    "window_desktop_id",
    "window_is_on_current_desktop",
    "window_is_on_other_desktop",
    "window_is_visible",
]
