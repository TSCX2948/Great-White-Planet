"""gwp.ui：PyQt6 界面层。

使用惰性导入，这样 ``from gwp.ui import common`` 不会连带把主窗口和所有视图都加载进来，
既加快启动速度，也避免模块之间互相导入。
"""

from __future__ import annotations

import importlib
from typing import Any

_SUBMODULES = (
    "common",
    "help_content",
    "main_window",
    "startup_tasks",
    "dialogs",
    "views",
    "widgets",
    "windows",
)

__all__ = list(_SUBMODULES)


def __getattr__(name: str) -> Any:  # PEP 562
    if name in _SUBMODULES:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_SUBMODULES))
