"""gwp.services 服务层：文件、文档解析、渲染、导出、系统集成。

这里刻意使用**惰性导入**：``import gwp.services`` 不会连带加载 markdown /
pymupdf 等较重的库，只有真正用到某个子模块时才加载。
这样软件启动更快，模块之间也不会因为互相导入而出问题。
"""

from __future__ import annotations

import importlib
from typing import Any

_SUBMODULES = (
    "background",
    "dependencies",
    "document_reader",
    "file_clipboard",
    "file_ops",
    "markdown_renderer",
    "page_range",
    "pdf_exporter",
    "shell_ops",
    "themes",
)

__all__ = list(_SUBMODULES)


def __getattr__(name: str) -> Any:  # PEP 562：按需加载子模块
    if name in _SUBMODULES:
        module = importlib.import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_SUBMODULES))
