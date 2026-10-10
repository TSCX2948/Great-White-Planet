"""Windows 系统集成：回收站、桌面快捷方式、开机自启。

全部使用标准库实现（不依赖 pywin32），便于在纯净环境里运行。
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

APP_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


# --------------------------------------------------------------------------
# 回收站
# --------------------------------------------------------------------------

def can_use_recycle_bin() -> bool:
    """粗略判断"删除能否进回收站"。

    用于**把警告文案说准**：能进回收站就可以告诉用户"可还原"，
    否则必须明确警告"将永久删除"。

    注意这只是探测：Windows 在单个文件超过回收站容量上限时仍可能直接永久删除，
    所以判定为"可用"时，文案里也要保留"若超出回收站容量则无法还原"的余地。
    """
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes

        # SHQueryRecycleBinW 返回 0 表示查询成功，说明回收站机制可用
        class SHQUERYRBINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("i64Size", ctypes.c_longlong),
                ("i64NumItems", ctypes.c_longlong),
            ]

        info = SHQUERYRBINFO()
        info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
        result = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(info))
        return result == 0
    except Exception:  # noqa: BLE001 - 探测失败按"不可用"处理，文案更保守
        return False

def send_to_recycle_bin(path: Path) -> bool:
    """把文件/文件夹移入回收站。成功返回 True。"""
    path = Path(path)
    if not path.exists():
        return False
    if not sys.platform.startswith("win"):
        return False
    try:
        import ctypes
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", ctypes.c_uint16),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", ctypes.c_void_p),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        FO_DELETE = 3
        FOF_SILENT = 0x0004
        FOF_NOCONFIRMATION = 0x0010
        FOF_ALLOWUNDO = 0x0040
        FOF_NOERRORUI = 0x0400

        operation = SHFILEOPSTRUCTW()
        operation.hwnd = None
        operation.wFunc = FO_DELETE
        # 路径必须以 \0\0 结尾
        operation.pFrom = str(path.resolve()) + "\0\0"
        operation.pTo = None
        operation.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))  # type: ignore[attr-defined]
        if result != 0:
            log.warning("SHFileOperationW 返回 %s（%s）", result, path)
            return False
        return not path.exists()
    except Exception:  # noqa: BLE001
        log.exception("移入回收站失败: %s", path)
        return False


# --------------------------------------------------------------------------
# 开机自启动
# --------------------------------------------------------------------------

def startup_command() -> str:
    """生成开机自启要执行的命令行（静默启动，不弹控制台）。"""
    root = Path(__file__).resolve().parents[2]     # code 目录
    pythonw = root / "venv" / "Scripts" / "pythonw.exe"
    launcher = root / "run.pyw"
    executable = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{executable}" "{launcher}" --startup'


def _reg_query() -> str:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, APP_RUN_KEY, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, "GreatWhitePlanet")
            return str(value)
    except FileNotFoundError:
        return ""
    except OSError:
        return ""


def is_autostart_enabled() -> bool:
    if not sys.platform.startswith("win"):
        return False
    try:
        return bool(_reg_query())
    except Exception:  # noqa: BLE001
        return False


def set_autostart(enabled: bool) -> tuple[bool, str]:
    """开启/关闭开机自启动。返回 (是否成功, 说明)。"""
    if not sys.platform.startswith("win"):
        return False, "当前系统不是 Windows，暂不支持开机自启"
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, APP_RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, "GreatWhitePlanet", 0, winreg.REG_SZ, startup_command())
            else:
                try:
                    winreg.DeleteValue(key, "GreatWhitePlanet")
                except FileNotFoundError:
                    pass
        return True, "已开启开机自动启动" if enabled else "已关闭开机自动启动"
    except OSError as exc:
        log.exception("设置开机自启失败")
        return False, f"设置失败：{exc}（可能需要管理员权限）"


# --------------------------------------------------------------------------
# 打开网址
# --------------------------------------------------------------------------

def open_url(url: str) -> bool:
    """用系统默认浏览器打开网址。成功返回 True。

    只放行 http / https —— 避免把 ``file://`` 或自定义协议交给系统，
    那等于给"点一下就执行本机东西"开了口子。
    """
    raw = (url or "").strip()
    if not raw:
        return False
    try:
        from urllib.parse import urlparse

        parsed = urlparse(raw)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        log.warning("拒绝打开非 http/https 链接：%s", raw)
        return False
    try:
        if sys.platform.startswith("win"):
            os.startfile(raw)  # type: ignore[attr-defined]  # noqa: S606 - 已限定协议
        else:
            opener = "open" if sys.platform == "darwin" else "xdg-open"
            subprocess.Popen(
                [opener, raw], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        return True
    except Exception:  # noqa: BLE001 - 打不开不该让界面崩
        log.exception("打开链接失败: %s", raw)
        return False


# --------------------------------------------------------------------------
# 桌面快捷方式
# --------------------------------------------------------------------------

def desktop_dir() -> Path:
    if sys.platform.startswith("win"):
        try:
            import ctypes

            buffer = ctypes.create_unicode_buffer(260)
            # CSIDL_DESKTOPDIRECTORY = 0x0010
            result = ctypes.windll.shell32.SHGetFolderPathW(  # type: ignore[attr-defined]
                None, 0x0010, None, 0, buffer
            )
            if result == 0 and buffer.value:
                return Path(buffer.value)

            # 备用方案：USERPROFILE\Desktop
            profile = os.environ.get("USERPROFILE", "")
            if profile:
                candidate = Path(profile) / "Desktop"
                if candidate.exists():
                    return candidate
        except Exception:  # noqa: BLE001
            log.exception("定位桌面目录失败")
    home = Path.home()
    for name in ("Desktop", "桌面"):
        candidate = home / name
        if candidate.exists():
            return candidate
    return home


def shortcut_target() -> tuple[Path, Path, Path]:
    """返回 (python可执行文件, 启动脚本, 工作目录)。"""
    code_dir = Path(__file__).resolve().parents[2]
    launcher = code_dir / "run.pyw"
    pythonw = code_dir / "venv" / "Scripts" / "pythonw.exe"
    executable = pythonw if pythonw.exists() else Path(sys.executable)
    return executable, launcher, code_dir


def create_desktop_shortcut(name: str = "Great White Planet") -> tuple[bool, str]:
    """在桌面创建快捷方式。使用 PowerShell 调用 WScript.Shell，无需第三方库。

    除了目标/参数/图标，还写两个属性：

    * ``IconLocation`` 显式带上索引 ``,0`` —— 图标文件里有多个尺寸时，
      不带索引会让 Windows 自己挑，结果不稳定；
    * ``System.AppUserModel.ID``（应用标识）与进程一致 ——
      这样"从快捷方式启动"和"已在运行的实例"会被 Windows 认成**同一个应用**，
      任务栏不会出现两个图标，而且任务栏用的是我们设的图标。
    """
    if not sys.platform.startswith("win"):
        return False, "当前系统不是 Windows，暂不支持创建快捷方式"

    executable, launcher, workdir = shortcut_target()
    if not launcher.exists():
        return False, f"找不到启动脚本：{launcher}"

    # 图标：优先用 resources/icons/planet.ico（"太白金星"），拿不到就退回解释器图标
    icon_location = f"{executable},0"
    try:
        from gwp.resources import app_icon as icon_module

        icon_file = icon_module.ensure_builtin_icon()
        if icon_file.is_file():
            icon_location = f"{icon_file},0"
    except Exception:  # noqa: BLE001 - 图标生成失败不应该导致建不了快捷方式
        log.exception("准备快捷方式图标失败，使用默认图标")

    desktop = desktop_dir()
    shortcut = desktop / f"{name}.lnk"
    script = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{shortcut}'); "
        f"$s.TargetPath = '{executable}'; "
        f"$s.Arguments = '\"{launcher}\"'; "
        f"$s.WorkingDirectory = '{workdir}'; "
        f"$s.IconLocation = '{icon_location}'; "
        f"$s.Description = 'Great White Planet 本地知识管理与 AI 辅助学习软件'; "
        "$s.Save()"
    )
    try:
        process = subprocess.run(  # noqa: S603
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"创建快捷方式失败：{exc}"

    if process.returncode != 0 or not shortcut.exists():
        detail = (process.stderr or process.stdout or "").strip()[:200]
        return False, f"创建快捷方式失败：{detail or '未知错误'}"

    # 应用标识要**另外**写：WScript.Shell 建快捷方式时没有这个属性，
    # 而且 Shell.Application 的 ExtendedProperty 是只读的（写它会抛
    # "Could not find member"）。所以用 COM 的 IPropertyStore 写。
    # 失败也不当成整体失败 —— 最坏只是任务栏分组不理想。
    applied = apply_shortcut_identity(shortcut)
    if not applied:
        log.warning("快捷方式已创建，但没能写入应用标识：%s", shortcut)
    return True, f"已在桌面创建快捷方式：{shortcut.name}"


def apply_shortcut_identity(shortcut) -> bool:
    """给一个已存在的快捷方式补上应用标识（任务栏分组用）。

    幂等：已经有**正确**的标识就直接返回 True，不重复写。
    """
    from gwp.core.app_identity import APP_USER_MODEL_ID
    from gwp.services import shortcut_identity

    target = Path(shortcut)
    if not target.is_file():
        return False
    try:
        current = shortcut_identity.read_app_user_model_id(target)
    except Exception:  # noqa: BLE001
        current = None
    if current == APP_USER_MODEL_ID:
        return True
    try:
        return shortcut_identity.set_app_user_model_id(target, APP_USER_MODEL_ID)
    except Exception:  # noqa: BLE001
        log.debug("写快捷方式应用标识失败：%s", target, exc_info=True)
        return False


def ensure_shortcut_identity(name: str = "Great White Planet") -> bool:
    """如果桌面上已经有快捷方式，但缺应用标识，就补上。

    为什么需要：用户桌面上那个快捷方式可能是**旧版本**创建的（没有标识）。
    不补的话，双击它启动的进程与快捷方式不是同一个任务栏分组，
    任务栏仍然可能显示解释器图标 —— 那正是用户报的问题。

    只在"快捷方式存在且标识不对"时才动手，正常情况下一行日志都不会多。

    **测试环境下直接跳过**：自动化测试会反复建主窗口，不该反复去
    改用户真实的桌面（那是测试的副作用，不是被测行为）。
    测试通过 ``GWP_ROOT`` 指向临时目录来表明"这是测试"。
    """
    if not sys.platform.startswith("win"):
        return False
    if os.environ.get("GWP_ROOT"):
        log.debug("检测到 GWP_ROOT（测试环境），跳过快捷方式整理")
        return False
    shortcut = desktop_dir() / f"{name}.lnk"
    if not shortcut.is_file():
        return False
    from gwp.core.app_identity import APP_USER_MODEL_ID
    from gwp.services import shortcut_identity

    try:
        current = shortcut_identity.read_app_user_model_id(shortcut)
    except Exception:  # noqa: BLE001
        return False
    if current == APP_USER_MODEL_ID:
        return False
    if apply_shortcut_identity(shortcut):
        log.info("已为已有的桌面快捷方式补上应用标识：%s", shortcut)
        return True
    return False


def remove_desktop_shortcut(name: str = "Great White Planet") -> bool:
    shortcut = desktop_dir() / f"{name}.lnk"
    try:
        if shortcut.exists():
            shortcut.unlink()
            return True
    except OSError:
        log.exception("删除快捷方式失败")
    return False


__all__ = [
    "can_use_recycle_bin",
    "create_desktop_shortcut",
    "desktop_dir",
    "is_autostart_enabled",
    "open_url",
    "remove_desktop_shortcut",
    "send_to_recycle_bin",
    "set_autostart",
    "startup_command",
]
