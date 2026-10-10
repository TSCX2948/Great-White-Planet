"""收纳箱：把若干科目分组的容器。

设计要点
--------
* **收纳箱只做分组，不搬动文件**。科目仍然是 ``user data/subjects/<科目>``
  下的普通文件夹；收纳箱只是"哪些科目显示在同一个盒子里"这一层信息。
  因此：

  - 删掉收纳箱**不会删除任何科目或文件**，成员只是回到最外层；
  - 手工移动/重命名科目文件夹后，收纳箱里失效的成员会被自动忽略（不报错）；
  - 一个科目最多属于一个收纳箱（移动即改归属）。

* 存储位置：数据根目录下的 ``boxes.json``（与 ``user data`` / ``else data`` 平级），
  这样它属于"用户的数据组织方式"，不会被当成软件缓存清掉，
  备份 ``user data`` 时也能一并带走（如果想连分组一起备份，把本文件一起复制即可）。

* 文件内容形如::

      {
        "version": 1,
        "boxes": [
          {
            "id": "数学基础",
            "name": "数学基础",
            "color": "#4F7CFF",
            "cover": "",
            "order": 0,
            "members": ["高等代数", "数学分析"]
          }
        ]
      }
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gwp.core import constants as C
from gwp.data_manager import metadata as meta_io

log = logging.getLogger(__name__)

#: 收纳箱元数据文件名（位于数据根目录）
BOXES_FILE = "boxes.json"

#: 收纳箱默认颜色（用户可改；新建时按已有数量轮换）
DEFAULT_BOX_COLORS = C.DEFAULT_CARD_COLORS


@dataclass
class Box:
    """一个收纳箱。

    ``eq=False`` 保持默认的"按标识比较"，因此仍然是可哈希的
    （需求：箱子的身份就是它的 ``id``，不需要按内容比较）。
    """

    id: str
    name: str = ""
    color: str = ""
    cover: str = ""
    order: int = 0
    members: list[str] = field(default_factory=list)   # 科目目录名

    def __hash__(self) -> int:
        return hash(self.id)

    @property
    def title(self) -> str:
        return self.name or self.id

    @property
    def member_count(self) -> int:
        return len(self.members)

    def cover_path(self, subjects_dir: Path) -> Path | None:
        """收纳箱自己的图片：存在科目目录下的一个隐藏目录里。"""
        if not self.cover:
            return None
        candidate = Path(self.cover)
        if candidate.is_absolute():
            return candidate if candidate.exists() else None
        resolved = Path(subjects_dir) / _BOX_ASSET_DIR / candidate
        return resolved if resolved.exists() else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "color": self.color,
            "cover": self.cover,
            "order": int(self.order),
            "members": list(self.members),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Box":
        box_id = str(data.get("id") or "").strip()
        if not box_id:
            box_id = uuid.uuid4().hex[:8]
        members: list[str] = []
        for item in data.get("members") or []:
            name = str(item).strip()
            # 去重并保持顺序
            if name and name not in members:
                members.append(name)
        try:
            order = int(data.get("order") or 0)
        except (TypeError, ValueError):
            order = 0
        return cls(
            id=box_id,
            name=str(data.get("name") or box_id),
            color=str(data.get("color") or ""),
            cover=str(data.get("cover") or ""),
            order=order,
            members=members,
        )


#: 收纳箱图片存放在科目目录下的这个隐藏子目录里（避免被当成一个"科目"）
_BOX_ASSET_DIR = ".boxes"

#: 全局版本号：任何一次写盘都会 +1，让**所有** BoxStore 实例的缓存失效。
#: 因为 Library 与调用方可能各持一个实例，只靠实例内的缓存标志会读到旧数据。
_WRITE_GENERATION = 0


def _bump_generation() -> None:
    global _WRITE_GENERATION
    _WRITE_GENERATION += 1


class BoxStore:
    """``boxes.json`` 的读写与增删改。

    所有写操作都是"读-改-原子写"，因此手工编辑该文件、软件再改动它也不会
    互相破坏（见 :func:`gwp.data_manager.metadata.write_json`）。
    """

    def __init__(self, subjects_dir: Path) -> None:
        self.subjects_dir = Path(subjects_dir)
        self._boxes: list[Box] | None = None
        self._generation = -1

    # ------------------------------------------------------------------
    # 位置
    # ------------------------------------------------------------------

    @property
    def path(self) -> Path:
        # subjects 的上一级是 user data，再上一级是数据根目录
        return self.subjects_dir.parent.parent / BOXES_FILE

    @property
    def asset_dir(self) -> Path:
        return self.subjects_dir / _BOX_ASSET_DIR

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------

    def load(self, refresh: bool = False) -> list[Box]:
        """返回收纳箱列表。

        **返回的是深拷贝**：调用方（包括本类的写方法）可以随意修改，
        不会污染内部缓存。这一点很关键——早期版本返回的是共享对象，
        写方法就地改 `members` 会把缓存改坏，从而出现
        "文件里已删除的箱子、缓存里还存在"这类矛盾状态。
        """
        if self._boxes is not None and not refresh and self._generation == _WRITE_GENERATION:
            return [self._copy(box) for box in self._boxes]
        data = meta_io.read_json(self.path, {"version": 1, "boxes": []})
        raw = data.get("boxes")
        boxes: list[Box] = []
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict):
                    boxes.append(Box.from_dict(item))
        boxes.sort(key=lambda box: (box.order, box.title.lower()))
        self._boxes = boxes
        self._generation = _WRITE_GENERATION
        return [self._copy(box) for box in boxes]

    def invalidate(self) -> None:
        self._boxes = None
        self._generation = -1

    @staticmethod
    def _copy(box: Box) -> Box:
        """复制一个 Box（含 members 列表），用于隔离缓存与调用方。"""
        return Box(
            id=box.id,
            name=box.name,
            color=box.color,
            cover=box.cover,
            order=box.order,
            members=list(box.members),
        )

    def get(self, box_id: str) -> Box | None:
        for box in self.load():
            if box.id == box_id:
                return box
        return None

    def box_of(self, subject_name: str) -> Box | None:
        """某个科目属于哪个收纳箱（不属于任何箱子时返回 None）。"""
        for box in self.load():
            if subject_name in box.members:
                return box
        return None

    def move_subject(self, box_id: str, name: str, index: int) -> None:
        """把箱内某个科目移动到指定下标（箱内拖拽排序用）。

        下标会被夹到合法区间；科目不在箱内、或下标没变化时什么都不做，
        因此界面重复触发也不会产生多余的写盘。
        """
        box = self.get(box_id)
        if box is None:
            raise ValueError(f"收纳箱不存在：{box_id}")
        members = list(box.members)
        if name not in members:
            return
        current = members.index(name)
        target = max(0, min(len(members) - 1, int(index)))
        if target == current:
            return
        members.pop(current)
        members.insert(target, name)
        box.members = members
        self._save([b if b.id != box.id else box for b in self.load()])

    def reorder(self, box_id: str, ordered_names: list[str]) -> None:
        """按给定顺序重写箱内成员（只认箱内已有的科目，不会丢成员）。"""
        box = self.get(box_id)
        if box is None:
            return
        members = list(box.members)
        wanted = [
            str(name) for name in (ordered_names or []) if str(name) in members
        ]
        # 去重且保持稳定
        seen: list[str] = []
        for name in wanted:
            if name not in seen:
                seen.append(name)
        # 列表里没提到的成员保持在后面，绝不丢
        box.members = seen + [name for name in members if name not in seen]
        self._save([b if b.id != box.id else box for b in self.load()])

    def set_order(
        self,
        box_ids: list[str],
        absolute: bool = False,
        positions: dict[str, int] | None = None,
    ) -> None:
        """按给定顺序重写 order 字段（拖拽排序用）。

        传入的是**期望的完整顺序**；只认识列表里出现的 id，其余保持原相对位置
        （排在最后），因此即使界面漏传了一个箱子也不会把它弄丢。

        ``positions`` 给出每个箱子的**绝对 order**（首页混排时用混合序列下标）；
        缺省时按 ``box_ids`` 里的下标。

        ``absolute=True`` 时**不重新编号**，而是原样写 ``positions``/下标。
        首页的箱子/科目混排需要跨两个列表比较 order，重新压成 ``0..n-1``
        会让"单个箱子"永远是 0，从而表达不出"箱子排到科目前面"。
        """
        wanted = [str(box_id) for box_id in (box_ids or [])]
        if not wanted and not positions:
            return
        boxes = self.load(refresh=True)
        explicit = {str(k): int(v) for k, v in (positions or {}).items()}
        position = (
            explicit
            if explicit
            else {box_id: index for index, box_id in enumerate(wanted)}
        )
        for box in boxes:
            box.order = position.get(box.id, len(wanted))
        if not absolute:
            # 只按箱子自身排序时，order 保持紧凑的 0..n-1
            boxes.sort(key=lambda box: (box.order, box.title.lower()))
            for index, box in enumerate(boxes):
                box.order = index
        self._save(boxes)

    def move_before(self, box_id: str, target_id: str) -> None:
        """把某个收纳箱移到另一个之前（拖到卡片上时调用）。"""
        boxes = self.load()
        order = [box.id for box in boxes]
        if box_id not in order or target_id not in order or box_id == target_id:
            return
        order.remove(box_id)
        order.insert(order.index(target_id), box_id)
        self.set_order(order)

    def _save(self, boxes: list[Box]) -> None:
        """写盘并让缓存失效。

        写方法拿到的都是 ``load(refresh=True)`` 的副本，改完后统一在这里落盘；
        缓存置空后下一次 ``load()`` 会从文件重建，因此永远和磁盘一致。
        """
        meta_io.write_json(
            self.path,
            {"version": 1, "boxes": [box.to_dict() for box in boxes]},
        )
        _bump_generation()          # 让所有实例（含 Library 持有的那个）的缓存失效
        self._boxes = None

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def create(self, name: str, color: str = "", members: list[str] | None = None) -> Box:
        """新建收纳箱。

        同名时自动加序号（``数学`` → ``数学 2``），避免用户看到两个一样的盒子。
        """
        clean = (name or "").strip() or "收纳箱"
        boxes = self.load(refresh=True)
        existing = {box.title for box in boxes}
        title = clean
        index = 2
        while title in existing:
            title = f"{clean} {index}"
            index += 1

        box = Box(
            id=self._unique_id(boxes, title),
            name=title,
            color=color or DEFAULT_BOX_COLORS[len(boxes) % len(DEFAULT_BOX_COLORS)],
            order=self._next_order(boxes),
            members=[],
        )
        if members:
            box = self._cleaned(box, members, boxes)
        boxes.append(box)
        self._save(boxes)
        return box

    def rename(self, box_id: str, name: str) -> Box | None:
        boxes = self.load(refresh=True)
        target = None
        for box in boxes:
            if box.id == box_id:
                box.name = (name or "").strip() or box.name
                target = box
                break
        if target is not None:
            self._save(boxes)
        return target

    def set_color(self, box_id: str, color: str) -> Box | None:
        boxes = self.load(refresh=True)
        target = None
        for box in boxes:
            if box.id == box_id:
                box.color = color
                target = box
                break
        if target is not None:
            self._save(boxes)
        return target

    def set_cover(self, box_id: str, source: Path | None) -> Box | None:
        """设置收纳箱背景图（复制到 ``subjects/.boxes``，不占用科目目录名）。"""
        boxes = self.load(refresh=True)
        target = next((box for box in boxes if box.id == box_id), None)
        if target is None:
            return None

        if source is None:
            target.cover = ""
        else:
            source = Path(source)
            if not source.is_file():
                raise FileNotFoundError(f"图片不存在：{source}")
            self.asset_dir.mkdir(parents=True, exist_ok=True)
            suffix = source.suffix.lower() or ".png"
            destination = self.asset_dir / f"{target.id}{suffix}"
            import shutil

            shutil.copy2(source, destination)
            target.cover = destination.name
        self._save(boxes)
        return target

    def delete(self, box_id: str) -> list[str]:
        """删除收纳箱，**只删分组**，返回被释放的科目名列表。"""
        boxes = self.load(refresh=True)
        released: list[str] = []
        kept: list[Box] = []
        for box in boxes:
            if box.id == box_id:
                released = list(box.members)
                continue
            kept.append(box)
        if released or len(kept) != len(boxes):
            self._save(kept)
        return released

    def move_subjects(self, box_id: str, subject_names: list[str]) -> int:
        """把若干科目放入某个收纳箱（会自动从原箱子移出）。返回实际移动的数量。"""
        targets = [name for name in (subject_names or []) if name]
        if not targets:
            return 0
        boxes = self.load(refresh=True)
        destination = next((box for box in boxes if box.id == box_id), None)
        if destination is None:
            return 0

        moved = 0
        for box in boxes:
            if box is destination:
                continue
            before = len(box.members)
            box.members = [name for name in box.members if name not in targets]
            moved += before - len(box.members)

        for name in targets:
            if name not in destination.members:
                destination.members.append(name)
                moved += 1
        self._save(boxes)
        return moved

    def remove_subjects(self, subject_names: list[str]) -> int:
        """把科目从它所在的收纳箱移出（回到最外层）。"""
        targets = {name for name in (subject_names or []) if name}
        if not targets:
            return 0
        boxes = self.load(refresh=True)
        moved = 0
        for box in boxes:
            before = len(box.members)
            box.members = [name for name in box.members if name not in targets]
            moved += before - len(box.members)
        if moved:
            self._save(boxes)
        return moved

    def prune(self, valid_subject_names: set[str]) -> list[str]:
        """清理指向已不存在科目的成员记录，返回被清掉的科目名。

        这样用户直接在资源管理器里删掉/改名科目目录后，收纳箱不会留下幽灵成员。
        """
        boxes = self.load(refresh=True)
        removed: list[str] = []
        changed = False
        for box in boxes:
            kept = []
            for name in box.members:
                if name in valid_subject_names:
                    kept.append(name)
                else:
                    removed.append(name)
                    changed = True
            box.members = kept
        if changed:
            self._save(boxes)
        return removed

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------

    def _unique_id(self, boxes: list[Box], title: str) -> str:
        used = {box.id for box in boxes}
        base = title.strip() or "box"
        if base not in used:
            return base
        index = 2
        while f"{base}-{index}" in used:
            index += 1
        return f"{base}-{index}"

    def _next_order(self, boxes: list[Box]) -> int:
        return max((box.order for box in boxes), default=-1) + 1

    def _cleaned(self, box: Box, members: list[str], boxes: list[Box]) -> Box:
        """过滤掉已属于别的箱子的成员，避免一个科目出现在两个盒子里。"""
        taken = {name for other in boxes for name in other.members}
        box.members = [name for name in members if name and name not in taken]
        return box


__all__ = [
    "BOXES_FILE",
    "DEFAULT_BOX_COLORS",
    "Box",
    "BoxStore",
]
