"""数据模型：Subject / Book / BookItem。

模型只描述“磁盘上有什么”，不负责增删改（那是 store.py 的职责），
也不认识 Qt（那是 ui 层的事）。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from gwp.core import constants as C


def _fmt_time(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except (OSError, OverflowError, ValueError):
        return "-"


@dataclass
class BookItem:
    """书目里的一个条目（文件或文件夹）。"""

    name: str
    path: Path
    is_dir: bool
    size: int = 0
    mtime: float = 0.0
    is_summary: bool = False
    is_intro: bool = False
    is_image: bool = False
    #: 软件自己的内部文件（例如作业的 ``homework.json``）。
    #: 这些文件**必须能列出来**（用户打开作业文件夹时要看到里面的东西），
    #: 但它们是元数据、不是用户内容，界面应置灰并禁止改名/删除，
    #: 计数也不该把它们算成条目。
    is_meta: bool = False

    @property
    def suffix(self) -> str:
        return self.path.suffix.lower()

    @property
    def kind_label(self) -> str:
        if self.is_meta:
            return "作业信息"
        if self.is_summary:
            return "AI总结"
        if self.is_intro:
            return "简介"
        if self.is_dir:
            return "文件夹"
        return self.suffix.lstrip(".").upper() or "文件"

    @property
    def size_label(self) -> str:
        if self.is_dir:
            return "-"
        size = float(self.size)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"

    @property
    def mtime_label(self) -> str:
        return _fmt_time(self.mtime)


@dataclass
class Book:
    """一个书目。目录结构固定为 Introduct.md / <书名>_summary.md / book / error-prone / notebook。"""

    name: str                       # 目录名（磁盘上的真实名字，重命名会变）
    path: Path
    subject_name: str
    display_name: str = ""
    description: str = ""
    color: str = ""
    cover: str = ""
    tags: list[str] = field(default_factory=list)
    order: int = 0
    pinned: bool = False
    created_at: str = ""
    updated_at: str = ""
    summary_note: str = ""
    intro_path: Path | None = None
    summary_path: Path | None = None
    summary_mtime: float = 0.0
    intro_mtime: float = 0.0
    item_counts: dict[str, int] = field(default_factory=dict)
    extra: dict = field(default_factory=dict)

    @property
    def title(self) -> str:
        return self.display_name or self.name

    @property
    def has_summary(self) -> bool:
        return self.summary_path is not None and self.summary_path.exists()

    @property
    def summary_name(self) -> str:
        return self.summary_path.name if self.summary_path else f"{self.name}{C.SUMMARY_SUFFIX}"

    def folder(self, key: str) -> Path:
        """取 book / error-prone / notebook 子目录路径（存在性不保证）。"""
        return self.path / key

    @property
    def summary_source_count(self) -> int:
        """参与总结的条目数（不含 book 目录）。"""
        return sum(
            self.item_counts.get(key, 0)
            for key in C.SUMMARY_SOURCE_DIRS
        )

    @property
    def updated_label(self) -> str:
        return self.updated_at.replace("T", " ")[:16] if self.updated_at else "-"

    @property
    def summary_label(self) -> str:
        return _fmt_time(self.summary_mtime) if self.summary_mtime else "未生成"


@dataclass
class Subject:
    """一个科目：包含若干书目。"""

    name: str                       # 目录名
    path: Path
    display_name: str = ""
    description: str = ""
    color: str = ""
    cover: str = ""
    order: int = 0
    pinned: bool = False
    created_at: str = ""
    updated_at: str = ""
    #: 科目类型：日记 / 校修课 / 自学课（见 constants.SUBJECT_TYPES）
    subject_type: str = C.DEFAULT_SUBJECT_TYPE
    books: list[Book] = field(default_factory=list)
    book_count: int = 0
    file_count: int = 0
    total_size: int = 0
    missing_dirs: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    @property
    def title(self) -> str:
        return self.display_name or self.name

    @property
    def type_label(self) -> str:
        """类型的中文名（用于卡片角标与提示）。"""
        return C.type_label(self.subject_type)

    @property
    def is_diary(self) -> bool:
        return self.subject_type == C.SUBJECT_DIARY

    @property
    def cover_path(self) -> Path | None:
        if not self.cover:
            return None
        candidate = Path(self.cover)
        if candidate.is_absolute():
            return candidate if candidate.exists() else None
        return (self.path / candidate) if (self.path / candidate).exists() else None

    @property
    def has_cover(self) -> bool:
        return self.cover_path is not None

    @property
    def created_label(self) -> str:
        return self.created_at.replace("T", " ")[:16] if self.created_at else "-"

    @property
    def size_label(self) -> str:
        size = float(self.total_size)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} GB"
