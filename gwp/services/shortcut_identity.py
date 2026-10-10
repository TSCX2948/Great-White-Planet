"""为 .lnk 快捷方式写 System.AppUserModel.ID（应用标识）。

为什么需要写它
--------------
从源码运行时进程是 ``pythonw.exe``。Windows 的任务栏按钮是按
**应用标识（AppUserModelID）** 分组的：

* 进程侧要在建窗口前调 ``SetCurrentProcessExplicitAppUserModelID``（见
  :mod:`gwp.core.app_identity`），否则任务栏把窗口归到 Python 名下、
  显示的是 **Python 解释器图标**（用户报障："将任务栏的图标改成快捷方式现在的图标"）；
* 快捷方式侧要写同一个标识，否则"从快捷方式启动"与"已在运行的实例"
  会被当成两个应用，任务栏出现两个图标，而且从快捷方式启动的那个
  用的还是解释器图标。

实现方式
--------
用 COM 的 ``SHGetPropertyStoreFromParsingName`` 拿到 ``IPropertyStore``
（读写模式），再 ``SetValue`` + ``Commit``。这是 Shell 提供的正规接口 ——
**不要试图用 ``WScript.Shell`` 或 ``Shell.Application`` 去写**：
``FolderItem.ExtendedProperty`` 是**只读**的，赋值会直接抛
"Could not find member"（实测如此）。

这个模块不依赖 Qt，可以用标准库 + ctypes 单独测试。
"""

from __future__ import annotations

import ctypes
import logging
import sys
import uuid
from pathlib import Path

log = logging.getLogger(__name__)

#: PKEY_AppUserModel_ID = {9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}, 5
_FMTID_APP_USER_MODEL = "9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"
_PID_APP_USER_MODEL_ID = 5

#: SHGetPropertyStoreFromParsingName 的 flags
GPS_READWRITE = 0x00000002
GPS_DEFAULT = 0x00000000

#: PROPVARIANT 里 VT_LPWSTR
_VT_LPWSTR = 31
_VT_EMPTY = 0


class _PropertyKey(ctypes.Structure):
    _fields_ = [("fmtid", ctypes.c_byte * 16), ("pid", ctypes.c_uint32)]


class _PropVariant(ctypes.Structure):
    """只用到 LPWSTR 那一种布局，别的一概不解释。"""

    _fields_ = [
        ("vt", ctypes.c_ushort),
        ("wReserved1", ctypes.c_ushort),
        ("wReserved2", ctypes.c_ushort),
        ("wReserved3", ctypes.c_ushort),
        ("pointer", ctypes.c_void_p),
    ]


def _guid_bytes(fmtid: str) -> bytes:
    return uuid.UUID(fmtid).bytes_le


def _make_pkey(fmtid: str, pid: int) -> _PropertyKey:
    key = _PropertyKey()
    raw = _guid_bytes(fmtid)
    for index in range(16):
        key.fmtid[index] = raw[index]
    key.pid = pid
    return key


def _vtable_call(pointer, index: int, restype, *argtypes):
    """按 vtable 下标取一个方法并设置签名。"""
    vtable = ctypes.cast(
        pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))
    )[0]
    prototype = ctypes.WINFUNCTYPE(restype, ctypes.c_void_p, *argtypes)
    return prototype(vtable[index])


def _release(pointer) -> None:
    if not pointer:
        return
    try:
        _vtable_call(pointer, 2, ctypes.c_ulong)(pointer)
    except Exception:  # noqa: BLE001
        log.debug("释放 COM 对象失败", exc_info=True)


def _get_store(path: Path, writable: bool):
    """拿到 ``IPropertyStore``。失败返回 None。"""
    ole32 = ctypes.WinDLL("ole32")
    ole32.CoInitialize.argtypes = [ctypes.c_void_p]
    ole32.CoInitialize(None)
    shell32 = ctypes.WinDLL("shell32")
    shell32.SHGetPropertyStoreFromParsingName.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.POINTER(ctypes.c_byte),
        ctypes.POINTER(ctypes.c_void_p),
    ]
    shell32.SHGetPropertyStoreFromParsingName.restype = ctypes.c_long
    iid = _guid_bytes("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99")
    iid_buffer = (ctypes.c_byte * 16)(*iid)
    store = ctypes.c_void_p()
    flags = GPS_READWRITE if writable else GPS_DEFAULT
    result = shell32.SHGetPropertyStoreFromParsingName(
        str(Path(path)), None, flags, iid_buffer, ctypes.byref(store)
    )
    if result != 0 or not store:
        log.debug("取属性存储失败：%s HRESULT=0x%08X", path, result & 0xFFFFFFFF)
        return None
    return store


def read_app_user_model_id(path: Path) -> str | None:
    """读快捷方式的 AppUserModelID。读不到返回 None（空值返回空串）。"""
    if not sys.platform.startswith("win"):
        return None
    store = _get_store(path, writable=False)
    if store is None:
        return None
    try:
        key = _make_pkey(_FMTID_APP_USER_MODEL, _PID_APP_USER_MODEL_ID)
        value = _PropVariant()
        get_value = _vtable_call(
            store, 5, ctypes.c_long,
            ctypes.POINTER(_PropertyKey), ctypes.POINTER(_PropVariant),
        )
        result = get_value(store, ctypes.byref(key), ctypes.byref(value))
        if result != 0:
            return None
        if value.vt == _VT_EMPTY:
            return ""
        if value.vt == _VT_LPWSTR and value.pointer:
            return ctypes.cast(value.pointer, ctypes.c_wchar_p).value or ""
        return None
    except Exception:  # noqa: BLE001
        log.debug("读应用标识失败：%s", path, exc_info=True)
        return None
    finally:
        _release(store)


def set_app_user_model_id(path: Path, app_id: str) -> bool:
    """给快捷方式写 AppUserModelID。成功返回 True。

    失败**不抛异常** —— 调用方（建快捷方式）不该因为这一步失败而整体失败：
    最坏情况只是"任务栏分组不理想"，而快捷方式本身是可用的。
    """
    if not sys.platform.startswith("win") or not app_id:
        return False
    target = Path(path)
    if not target.is_file():
        return False
    store = _get_store(target, writable=True)
    if store is None:
        return False
    try:
        key = _make_pkey(_FMTID_APP_USER_MODEL, _PID_APP_USER_MODEL_ID)
        value = _PropVariant()
        value.vt = _VT_LPWSTR
        # 让字符串活到 SetValue/Commit 之后
        buffer = ctypes.create_unicode_buffer(app_id)
        value.pointer = ctypes.cast(buffer, ctypes.c_void_p)

        set_value = _vtable_call(
            store, 6, ctypes.c_long,
            ctypes.POINTER(_PropertyKey), ctypes.POINTER(_PropVariant),
        )
        result = set_value(store, ctypes.byref(key), ctypes.byref(value))
        if result != 0:
            log.warning("写应用标识失败：%s HRESULT=0x%08X",
                        target, result & 0xFFFFFFFF)
            return False

        commit = _vtable_call(store, 7, ctypes.c_long)
        result = commit(store)
        if result != 0:
            log.warning("提交应用标识失败：%s HRESULT=0x%08X",
                        target, result & 0xFFFFFFFF)
            return False
        log.info("已给快捷方式写入应用标识：%s -> %s", target.name, app_id)
        return True
    except Exception:  # noqa: BLE001
        log.debug("写应用标识出错：%s", target, exc_info=True)
        return False
    finally:
        _release(store)


__all__ = ["read_app_user_model_id", "set_app_user_model_id"]
