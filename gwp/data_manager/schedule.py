"""其它日程：不属于任何作业的待办（考试、报名截止、要交的材料……）。

为什么单独存一个文件
--------------------

作业天生属于"某个科目的某本书"，所以元信息跟着作业文件夹走（``homework.json``）。
"其它日程"不一样 —— 它可能跟哪门课都不沾边（"周三交学费"、"报名截止"），
硬塞进某个科目反而别扭。因此存在**数据根目录**下，与 ``boxes.json`` 同级:

```
data/
├── boxes.json        收纳箱
├── schedule.json     其它日程   <- 这个文件
└── user data/
    └── subjects/...
```

为什么不做成"书目下的一个文件夹"
--------------------------------

日程是**跨科目**的视图：首页右侧那一栏要同时列出来自不同科目、不同书目的作业
和这些自定义日程。如果日程散落在各书目里，首页就得扫描整棵树才能凑齐一栏。

数据形态
--------

```json
{
  "version": 1,
  "items": [
    {"id": "…", "title": "交学费", "due": "2026-10-20T18:00", "done": false,
     "note": "在教务系统里交", "created_at": "…"}
  ]
}
```

本模块**不依赖 Qt**，方便单测。
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from gwp.data_manager.homework import DUE_SOON, format_due, parse_due

log = logging.getLogger(__name__)

#: 其它日程的存储文件名（位于数据根目录，与 boxes.json 同级）
SCHEDULE_FILE = "schedule.json"


@dataclass
class ScheduleItem:
    """一条自定义日程。"""

    id: str
    title: str
    due: str = ""
    done: bool = False
    note: str = ""
    created_at: str = ""

    # -- 派生信息（与 Homework 保持同一套语义，便于首页统一排序）----

    @property
    def due_at(self) -> datetime | None:
        return parse_due(self.due)

    @property
    def due_label(self) -> str:
        moment = self.due_at
        if moment is None:
            return "未设时间"
        return moment.strftime("%Y-%m-%d %H:%M").replace(" 00:00", "")

    def state(self, now: datetime | None = None) -> str:
        """``overdue`` / ``soon`` / ``ok`` / ``none``。"""
        if self.done:
            return "done"
        moment = self.due_at
        if moment is None:
            return "none"
        reference = now or datetime.now()
        if moment < reference:
            return "overdue"
        if moment - reference <= DUE_SOON:
            return "soon"
        return "ok"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "due": self.due,
            "done": bool(self.done),
            "note": self.note,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScheduleItem":
        due = str(data.get("due") or "")
        return cls(
            id=str(data.get("id") or uuid.uuid4().hex),
            title=str(data.get("title") or ""),
            due=format_due(parse_due(due)) if parse_due(due) else due,
            done=bool(data.get("done", False)),
            note=str(data.get("note") or ""),
            created_at=str(data.get("created_at") or ""),
        )


class ScheduleStore:
    """其它日程的读写（读-改-原子写，可安全手工编辑该文件）。"""

    def __init__(self, data_root: Path) -> None:
        self.data_root = Path(data_root)
        self._items: list[ScheduleItem] | None = None

    @property
    def path(self) -> Path:
        return self.data_root / SCHEDULE_FILE

    # ------------------------------------------------------------------

    def invalidate(self) -> None:
        self._items = None

    def load(self, refresh: bool = False) -> list[ScheduleItem]:
        """返回全部日程（**按 DDL 排序，未完成的在前**）。"""
        if self._items is not None and not refresh:
            return [self._copy(item) for item in self._items]
        items: list[ScheduleItem] = []
        if self.path.is_file():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                log.warning("日程文件读取失败：%s", self.path, exc_info=True)
                data = {}
            raw = data.get("items") if isinstance(data, dict) else None
            if isinstance(raw, list):
                for entry in raw:
                    if isinstance(entry, dict) and str(entry.get("title") or "").strip():
                        items.append(ScheduleItem.from_dict(entry))
        items = sort_items(items)
        self._items = items
        return [self._copy(item) for item in items]

    @staticmethod
    def _copy(item: ScheduleItem) -> ScheduleItem:
        return ScheduleItem(
            id=item.id, title=item.title, due=item.due,
            done=item.done, note=item.note, created_at=item.created_at,
        )

    def get(self, item_id: str) -> ScheduleItem | None:
        for item in self.load():
            if item.id == item_id:
                return item
        return None

    # ------------------------------------------------------------------

    def add(
        self,
        title: str,
        due: str = "",
        note: str = "",
    ) -> ScheduleItem:
        """新建一条日程。"""
        clean = (title or "").strip()
        if not clean:
            raise ValueError("日程名称不能为空")
        items = self.load(refresh=True)
        item = ScheduleItem(
            id=uuid.uuid4().hex,
            title=clean,
            due=format_due(parse_due(due)) if parse_due(due) else (due or ""),
            note=(note or "").strip(),
            created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
        items.append(item)
        self._save(items)
        return item

    def update(
        self,
        item_id: str,
        title: str | None = None,
        due: str | None = None,
        note: str | None = None,
    ) -> ScheduleItem | None:
        items = self.load(refresh=True)
        for item in items:
            if item.id != item_id:
                continue
            if title is not None:
                clean = title.strip()
                if not clean:
                    raise ValueError("日程名称不能为空")
                item.title = clean
            if due is not None:
                item.due = format_due(parse_due(due)) if parse_due(due) else due
            if note is not None:
                item.note = note.strip()
            self._save(items)
            return self._copy(item)
        return None

    def set_done(self, item_id: str, done: bool = True) -> bool:
        items = self.load(refresh=True)
        for item in items:
            if item.id == item_id:
                item.done = bool(done)
                self._save(items)
                return True
        return False

    def remove(self, item_id: str) -> bool:
        items = self.load(refresh=True)
        kept = [item for item in items if item.id != item_id]
        if len(kept) == len(items):
            return False
        self._save(kept)
        return True

    # ------------------------------------------------------------------

    def _save(self, items: list[ScheduleItem]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 1,
            "items": [item.to_dict() for item in sort_items(items)],
        }
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(self.path)
        # 重读一次，保证缓存与磁盘一致（并让排序生效）
        self._items = None
        self.load(refresh=True)


# --------------------------------------------------------------------------
# 排序
# --------------------------------------------------------------------------

def sort_key(done: bool, due_at: datetime | None, title: str):
    """统一排序键：**未完成在前 → DDL 早的在前 → 没 DDL 的排最后 → 名称**。

    没设 DDL 的排在有 DDL 的后面（而不是当成"很早"），
    否则一堆没时间的日程会顶到最前面，把真正临近截止的挤下去。
    """
    return (
        1 if done else 0,
        0 if due_at is not None else 1,
        due_at or datetime.max,
        (title or "").lower(),
    )


def sort_items(items: list[ScheduleItem]) -> list[ScheduleItem]:
    """按 :func:`sort_key` 排序日程。"""
    return sorted(
        items,
        key=lambda item: sort_key(item.done, item.due_at, item.title),
    )


__all__ = ["SCHEDULE_FILE", "ScheduleItem", "ScheduleStore", "sort_items", "sort_key"]
