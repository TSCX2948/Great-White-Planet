"""作业：作业内容 + DDL + 提交方式。

数据形态
--------

每个作业是 ``<书目>/homework/<作业名>/`` 一个**子文件夹**，里面：

* :data:`gwp.core.constants.HOMEWORK_META` （``homework.json``）—— 记录 DDL 与提交方式；
* 其余文件由用户自己放（作业内容、附件……）。

为什么不塞进一个文件里：一个作业常常要交好几样东西（报告 + 代码 + 截图），
子文件夹最直观，也符合软件"资料就是普通文件"的一贯设计 ——
在资源管理器里直接就能看懂、能整个拷走。

时间与链接
----------

* ``due_at`` 存 ISO 8601 本地时间字符串（``2026-10-15T23:59``），**可以为空**；
* ``submit_url`` 只接受 http/https，避免把随便一段文字变成可点的链接。

本模块**不依赖 Qt**，方便单测。
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from gwp.core import constants as C

log = logging.getLogger(__name__)

#: "即将到期"的判定阈值：距离 DDL 还剩不到这个时长就标黄/标红提醒。
#:
#: 需求（用户反馈）：原来是 24 小时，太紧 —— 用户看到"距现在 48 小时"的作业
#: 还是普通颜色，以为没到提醒范围。改成 48 小时，
#: 与"提前两天开始留意作业"这个实际习惯对齐。
#:
#: 作业与日程**共用**这一个常量（`schedule.py` 与日程栏都从这里取），
#: 所以改一处两边一起变 —— 不要在两处各写一个阈值，那样迟早不一致。
DUE_SOON = timedelta(hours=48)

_TIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
    "%Y/%m/%d %H:%M",
    "%Y/%m/%d",
)


def is_valid_url(text: str) -> bool:
    """只接受 http/https，并要有主机名。"""
    raw = (text or "").strip()
    if not raw:
        return True                      # 允许留空
    try:
        parsed = urlparse(raw)
    except ValueError:
        return False
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def normalize_url(text: str) -> str:
    """补全用户常漏的 ``https://`` 前缀；已经合法就原样返回。"""
    raw = (text or "").strip()
    if not raw:
        return ""
    if is_valid_url(raw):
        return raw
    if "://" not in raw and "." in raw.split("/")[0]:
        candidate = f"https://{raw}"
        if is_valid_url(candidate):
            return candidate
    return raw


def parse_due(text: str) -> datetime | None:
    """把用户输入的时间解析成 ``datetime``；空或无法识别返回 None。"""
    raw = (text or "").strip()
    if not raw:
        return None
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:                                  # 兜底：ISO 8601（含时区）
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def format_due(moment: datetime | None) -> str:
    """把时间写回 ISO 字符串。含时分就带上时分，否则只写日期。"""
    if moment is None:
        return ""
    if (moment.hour, moment.minute, moment.second) == (0, 0, 0):
        return moment.strftime("%Y-%m-%d")
    if moment.second == 0:
        return moment.strftime("%Y-%m-%dT%H:%M")
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


@dataclass
class Homework:
    """一个作业的元信息。"""

    name: str
    path: Path
    #: 作业内容（正文）。用户在对话框里填，同时也会写进 README.md
    content: str = ""
    #: 截止时间（ISO 字符串，可为空 = 没设 DDL）
    due: str = ""
    #: 提交方式：一个网址（可为空）
    submit_url: str = ""
    #: 是否已完成（用户在首页日程栏点「完成作业」）
    done: bool = False
    created_at: str = ""
    updated_at: str = ""

    # -- 派生信息 ------------------------------------------------------

    @property
    def due_at(self) -> datetime | None:
        return parse_due(self.due)

    @property
    def due_label(self) -> str:
        moment = self.due_at
        if moment is None:
            return "未设 DDL"
        return moment.strftime("%Y-%m-%d %H:%M").replace(" 00:00", "")

    def state(self, now: datetime | None = None) -> str:
        """返回 ``overdue`` / ``soon`` / ``ok`` / ``none``（无 DDL）。"""
        moment = self.due_at
        if moment is None:
            return "none"
        reference = now or datetime.now()
        if moment < reference:
            return "overdue"
        if moment - reference <= DUE_SOON:
            return "soon"
        return "ok"

    @property
    def submit_label(self) -> str:
        return self.submit_url or "未填写"

    @property
    def file_count(self) -> int:
        """作业文件夹里除元信息文件外的条目数。"""
        if not self.path.is_dir():
            return 0
        return sum(
            1 for item in self.path.iterdir()
            if item.name != C.HOMEWORK_META
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "content": self.content,
            "due": self.due,
            "submit_url": self.submit_url,
            "done": bool(self.done),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, folder: Path, data: dict) -> "Homework":
        content = str(data.get("content") or "")
        due = str(data.get("due") or "")
        url = str(data.get("submit_url") or "")
        return cls(
            name=folder.name,
            path=folder,
            content=content,
            # 兼容用户手工写的日期格式
            due=format_due(parse_due(due)) if parse_due(due) else due,
            submit_url=url,
            done=bool(data.get("done", False)),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
        )


# --------------------------------------------------------------------------
# 读写
# --------------------------------------------------------------------------

def meta_path(folder: Path) -> Path:
    return Path(folder) / C.HOMEWORK_META


def load(folder: Path) -> Homework | None:
    """读取一个作业文件夹的元信息。

    没有 ``homework.json`` 时返回 ``None``（说明只是普通文件夹，
    或者用户自己拷进来的东西）—— 界面上按普通文件夹展示，不做任何假设。
    """
    folder = Path(folder)
    file = meta_path(folder)
    if not file.is_file():
        return None
    try:
        data = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.warning("作业信息读取失败：%s", file, exc_info=True)
        return None
    if not isinstance(data, dict):
        return None
    return Homework.from_dict(folder, data)


def save(homework: Homework) -> Path:
    """写入 ``homework.json``（原子写）。"""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    if not homework.created_at:
        homework.created_at = now
    homework.updated_at = now
    homework.path.mkdir(parents=True, exist_ok=True)
    target = meta_path(homework.path)
    temporary = target.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(homework.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(target)
    return target


def rename(homework: Homework, new_name: str) -> Homework:
    """给作业改名：**移动文件夹** + 改 ``homework.json`` 里的名字。

    为什么要移动文件夹：作业的"名字"就是它的文件夹名 ——
    界面上显示的、日程栏里引用的、扫描时找到的，全都是它。
    只改 ``homework.json`` 里的 name 字段会让两者不一致
    （下次扫描又变回文件夹名），所以必须一起改。

    失败时**回滚**到原名，不留下"文件夹名和元信息不一致"的半成品。

    三处名字要一起改（都是"文件夹名"的副本）：

    1. 文件夹本身；
    2. ``homework.json`` 里的 ``name`` 字段；
    3. 内容 Markdown（默认与文件夹同名）—— **只在新名字当前没人用时**才移动，
       否则两份内容都在，宁可留下改名前的那份，也不覆盖任何东西。
    """
    folder = Path(homework.path)
    old_name = folder.name
    # 延迟导入：store 目前不依赖本模块，但**别把这条路堵死** ——
    # 名字清洗与 DataError 都住在 store 里，重复实现一份必然会漂移。
    from gwp.data_manager.store import DataError, sanitize_name

    clean = sanitize_name(new_name)
    if not clean or clean == old_name:
        return homework

    target = folder.parent / clean
    if target.exists():
        raise DataError(f"作业“{clean}”已经存在")

    # 改名前的 Markdown 文件名（用旧文件夹名算）。
    #
    # **注意这个路径只是用来取"文件名与旧名字是否一致"**：
    # 真正的文件已经被 os.replace 连同文件夹一起搬到新目录了，
    # 所以后面要用 `target / 旧文件名` 去操作它 ——
    # 直接用 `folder / 旧文件名` 会 FileNotFoundError
    # （这是我第二版踩到的坑：第一版是"移动后才判断存在"，
    # 永远为 False 所以 md 不改名；改成"移动前判断"之后又用错了路径）。
    old_markdown_name = content_file(folder).name
    old_markdown_at_new = target / old_markdown_name
    has_markdown = (folder / old_markdown_name).is_file()

    os.replace(folder, target)
    moved = Homework.from_dict(
        target,
        {
            "name": clean,
            "content": homework.content,
            "due": homework.due,
            "submit_url": homework.submit_url,
            "done": homework.done,
            "created_at": homework.created_at,
        },
    )
    try:
        save(moved)
    except OSError:
        # 元信息没写成 -> 把文件夹挪回去，别留下不一致的状态
        try:
            os.replace(target, folder)
        except OSError:
            log.exception("回滚作业改名失败：%s -> %s", target, folder)
        raise

    # 内容 Markdown 跟着改（可选步骤，失败不影响主体）
    new_markdown = content_file(target)
    if has_markdown and new_markdown.exists():
        log.info("改名后目标 Markdown 已存在，保留原文件：%s", old_markdown_name)
    elif has_markdown:
        try:
            os.replace(old_markdown_at_new, new_markdown)
        except OSError:
            log.warning("改名后 Markdown 未同步：%s", old_markdown_at_new,
                        exc_info=True)
    return moved


def content_file(folder: Path) -> Path:
    """作业内容的 Markdown 文件路径。"""
    return Path(folder) / f"{Path(folder).name}.md"


def write_content(homework: Homework) -> Path | None:
    """把作业内容写成 Markdown 文件。

    已经存在同名文件时**不覆盖** —— 用户可能已经在里面继续写了，
    这时只更新 ``homework.json`` 里的 content 字段，文件保持原样。
    """
    target = content_file(homework.path)
    if target.exists():
        return None
    try:
        target.write_text(
            f"# {homework.name}\n\n{homework.content.strip()}\n",
            encoding="utf-8",
        )
    except OSError:
        log.warning("写入作业内容失败：%s", target, exc_info=True)
        return None
    return target


def create(
    folder: Path,
    content: str = "",
    due: str = "",
    submit_url: str = "",
) -> Homework:
    """新建一个作业：建文件夹、写元信息、把内容落成 Markdown。"""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    homework = Homework(
        name=folder.name,
        path=folder,
        content=content,
        due=format_due(parse_due(due)) if parse_due(due) else due,
        submit_url=normalize_url(submit_url),
    )
    write_content(homework)
    save(homework)
    return homework


def set_done(folder: Path, done: bool = True) -> Homework | None:
    """把作业标记为已完成 / 未完成。"""
    homework = load(Path(folder))
    if homework is None:
        return None
    homework.done = bool(done)
    save(homework)
    return homework


def list_homework(book_path: Path) -> list[Homework]:
    """列出某个书目 ``homework`` 目录下的全部作业。"""
    folder = Path(book_path) / C.HOMEWORK_FOLDER
    if not folder.is_dir():
        return []
    found: list[Homework] = []
    for item in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
        if not item.is_dir():
            continue
        homework = load(item)
        if homework is not None:
            found.append(homework)
    return found


def looks_like_homework(folder: Path) -> bool:
    """这个文件夹是不是一个作业（有元信息文件）。"""
    return meta_path(folder).is_file()


def last_submit_url(book_path: Path) -> str:
    """取这本书**最近一份作业**用过的提交网址（没有就返回空串）。

    需求："新建作业的提交方式的网址默认为该book的作业之前的提交方式的网址，
    避免用户每次输入"。

    同一门课的作业提交入口通常是同一个（雨课堂 / 教务系统的同一页），
    所以这个默认值大概率正是用户要填的 —— 省掉每次重复粘贴。

    "最近"按 ``updated_at`` 排（刚改过的那份最可能是用户此刻在用的入口），
    ``updated_at`` 缺失或格式异常时退回 ``created_at``，再退回文件名。
    只认**合法网址**：某份作业把网址清空了，不该让默认值也变空 ——
    而是继续往前找还有网址的那一份。
    """
    candidates: list[tuple[str, str, str]] = []
    for homework in list_homework(book_path):
        url = normalize_url(homework.submit_url or "")
        if not url or not is_valid_url(url):
            continue
        candidates.append(
            (homework.updated_at or "", homework.created_at or "", url)
        )
    if not candidates:
        return ""
    # 时间戳是 ISO 文本，字典序即时间序；空串排最前面（会被最后选中）
    return max(candidates)[2]


__all__ = [
    "DUE_SOON",
    "Homework",
    "content_file",
    "create",
    "format_due",
    "is_valid_url",
    "last_submit_url",
    "list_homework",
    "load",
    "looks_like_homework",
    "meta_path",
    "normalize_url",
    "parse_due",
    "rename",
    "save",
    "set_done",
    "write_content",
]
