"""gwp.resources：随软件分发的资源与图标生成。

图标相关的两个模块刻意不依赖 Qt（``planet_icon`` 只用 Pillow/numpy），
只有 ``app_icon`` 因为要返回 QIcon 才用到 Qt。

``planet_icon`` 采用**惰性导入**（PEP 562）：它需要 numpy，而 numpy 只在
"没有现成图标文件、必须现场绘制"时才会用到。随包已经带了 ``icons/planet.ico``，
所以正常启动完全不需要 numpy —— 打包时也就能把 numpy 排除掉，安装包小很多。

注意：``__getattr__`` 里必须用 :func:`importlib.import_module`，
不能写 ``from gwp.resources import planet_icon`` —— 后者会再次触发本函数的
``__getattr__``，造成无限递归。
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ["planet_icon"]


def __getattr__(name: str) -> Any:
    if name == "planet_icon":
        return importlib.import_module("gwp.resources.planet_icon")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
