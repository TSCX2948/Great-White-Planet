"""依赖自检：告诉用户缺什么、怎么装。

需求文档第十一节要求软件支持后续扩展；第十二节列出未来要支持的格式。
本模块把这些扩展所需的库集中登记，缺库时只影响对应功能，不会让软件无法启动。
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass


@dataclass
class Dependency:
    module: str            # import 名
    package: str           # pip 名
    purpose: str
    required: bool = False   # 核心功能（缺了软件基本不可用）


DEPENDENCIES: tuple[Dependency, ...] = (
    Dependency("PyQt6.QtWidgets", "PyQt6", "界面框架（必需）", required=True),
    Dependency("markdown", "markdown", "Markdown 渲染与导出"),
    Dependency("pygments", "pygments", "代码块语法高亮"),
    Dependency("pymupdf", "pymupdf", "PDF 解析、页面转图片、PDF 导出"),
    Dependency("docx", "python-docx", "docx 教材/笔记解析"),
    Dependency("pptx", "python-pptx", "pptx 解析（需求文档第十二节的扩展规划）"),
    Dependency("openpyxl", "openpyxl", "xlsx 解析（需求文档第十二节的扩展规划）"),
    Dependency("PIL", "pillow", "图片缩放与格式转换"),
)


def check() -> list[tuple[Dependency, bool, str]]:
    """返回 [(依赖, 是否可用, 错误信息)]。"""
    results = []
    for dependency in DEPENDENCIES:
        try:
            importlib.import_module(dependency.module)
            results.append((dependency, True, ""))
        except Exception as exc:  # noqa: BLE001 - 任何导入问题都算缺失
            results.append((dependency, False, str(exc)))
    return results


def missing() -> list[Dependency]:
    return [dependency for dependency, ok, _ in check() if not ok]


def missing_required() -> list[Dependency]:
    return [dependency for dependency in missing() if dependency.required]


def install_command() -> str:
    packages = " ".join(sorted({dependency.package for dependency in missing()}))
    return f"pip install {packages}" if packages else ""


def summary() -> str:
    rows = []
    for dependency, ok, error in check():
        mark = "OK" if ok else "缺失"
        rows.append(f"[{mark}] {dependency.package:<14} {dependency.purpose}")
        if not ok and error:
            rows.append(f"        {error}")
    return "\n".join(rows)


__all__ = [
    "DEPENDENCIES",
    "Dependency",
    "check",
    "install_command",
    "missing",
    "missing_required",
    "summary",
]
