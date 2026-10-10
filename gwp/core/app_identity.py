"""应用身份（AppUserModelID）：让 Windows 认得出"这是我们自己"。

为什么需要它
------------
需求："将任务栏的图标改成快捷方式现在的图标"。

现象：从源码运行时进程是 ``venv\\Scripts\\pythonw.exe``，
而 Windows 的任务栏**按应用标识（AppUserModelID）分组**。
我们不设的话，窗口会被归到 Python 名下，任务栏按钮用的是
**Python 解释器的图标** —— 而不是我们通过 ``setWindowIcon()`` 设的那个星球。

设成一个我们自己的标识之后，Windows 就把它当成一个独立应用，
任务栏按钮转而使用窗口自己设的图标（``planet.ico``）。

另外，**快捷方式也用（或推导出）同一个标识**时，
"从桌面快捷方式启动"和"已经运行中的实例"会被认成同一个应用，
任务栏不会出现两个一模一样的图标。

这个模块**不依赖 Qt**，只用标准库 + ctypes，可以单独测试。
"""

from __future__ import annotations

import ctypes
import logging
import sys

log = logging.getLogger(__name__)

#: 应用标识。改动它等于换一个应用身份：
#: 任务栏会重新分组，而且**旧快捷方式与新进程可能不再被视为同一个应用**。
#: 所以要改就"进程 + 快捷方式 + 安装包"一起改。
APP_USER_MODEL_ID = "GreatWhitePlanet.LocalKnowledge"


def set_app_user_model_id(app_id: str = APP_USER_MODEL_ID) -> bool:
    """把当前进程的 AppUserModelID 设成 ``app_id``。成功返回 True。

    **必须在创建任何窗口之前调用** —— Windows 是在窗口出现时
    读取进程标识来决定分组的，那时候再改就已经晚了。

    非 Windows 或被策略禁止时返回 ``False``（只记日志，不影响启动）：
    任务栏图标退化成"显示解释器图标"，但软件功能完全正常。
    """
    if not sys.platform.startswith("win"):
        return False
    if not app_id:
        return False
    try:
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        # SetCurrentProcessExplicitAppUserModelID(PCWSTR)
        shell32.SetCurrentProcessExplicitAppUserModelID.argtypes = [ctypes.c_wchar_p]
        shell32.SetCurrentProcessExplicitAppUserModelID.restype = ctypes.c_long
        result = shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        if result == 0:
            log.info("已设置应用标识（任务栏图标用它分组）：%s", app_id)
            return True
        log.warning("设置应用标识失败：%s（HRESULT=%s）", app_id, result)
        return False
    except Exception:  # noqa: BLE001 - 设不了也不能影响启动
        log.debug("设置应用标识时出错", exc_info=True)
        return False


__all__ = ["APP_USER_MODEL_ID", "set_app_user_model_id"]
