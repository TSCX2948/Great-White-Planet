"""元数据读写：科目/书目的 ``subject.json`` / ``book.json``。

元数据文件是可选的：不存在时按目录名推导默认值，因此用户可以手工往
``data/user data/subjects`` 里丢文件夹，软件一样能识别（需求文档：软件自动扫描文件夹生成界面）。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from gwp.core import constants as C

log = logging.getLogger(__name__)


def read_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default or {})
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("元数据损坏，已忽略: %s (%s)", path, exc)
        return dict(default or {})


def write_json(path: Path, data: dict[str, Any]) -> None:
    """原子写入，避免写一半崩溃导致元数据损坏。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    os.replace(tmp, path)


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def pick_color(name: str, palette: tuple[str, ...] = C.DEFAULT_CARD_COLORS) -> str:
    """按名称稳定地挑一个卡片颜色（同名永远同色，用户没设过颜色时使用）。"""
    if not palette:
        return "#4F7CFF"
    total = sum(ord(ch) for ch in name) if name else 0
    return palette[total % len(palette)]


# --------------------------------------------------------------------------
# 科目
# --------------------------------------------------------------------------

SUBJECT_META_DEFAULTS: dict[str, Any] = {
    "type": "subject",        # 文件种类标记（历史字段，勿改）
    "subject_type": C.DEFAULT_SUBJECT_TYPE,   # 科目类型：日记 / 校修课 / 自学课
    "display_name": "",
    "description": "",
    "cover": "",              # 相对于科目目录或资产目录的文件名
    "color": "",
    "order": 0,               # 首页排序权重，越小越靠前
    "pinned": False,
    "created_at": "",
    "updated_at": "",
}


def load_subject_meta(subject_dir: Path) -> dict[str, Any]:
    meta = dict(SUBJECT_META_DEFAULTS)
    meta.update(read_json(subject_dir / C.SUBJECT_META, {}))
    if not meta.get("display_name"):
        meta["display_name"] = subject_dir.name
    if not meta.get("color"):
        meta["color"] = pick_color(subject_dir.name)
    return meta


def save_subject_meta(subject_dir: Path, meta: dict[str, Any]) -> None:
    meta = dict(meta)
    meta["type"] = "subject"
    meta["updated_at"] = now_iso()
    meta.setdefault("created_at", meta["updated_at"])
    write_json(subject_dir / C.SUBJECT_META, meta)


# --------------------------------------------------------------------------
# 书目
# --------------------------------------------------------------------------

BOOK_META_DEFAULTS: dict[str, Any] = {
    "type": "book",
    "display_name": "",
    "description": "",
    "author": "",
    "tags": [],
    "cover": "",
    "color": "",
    "order": 0,
    "pinned": False,
    "created_at": "",
    "updated_at": "",
    "summary_note": "",        # 最近一次生成 summary 的说明/模型名
}


def load_book_meta(book_dir: Path) -> dict[str, Any]:
    meta = dict(BOOK_META_DEFAULTS)
    meta.update(read_json(book_dir / C.BOOK_META, {}))
    if not meta.get("display_name"):
        meta["display_name"] = book_dir.name
    return meta


def save_book_meta(book_dir: Path, meta: dict[str, Any]) -> None:
    meta = dict(meta)
    meta["type"] = "book"
    meta["updated_at"] = now_iso()
    meta.setdefault("created_at", meta["updated_at"])
    write_json(book_dir / C.BOOK_META, meta)
