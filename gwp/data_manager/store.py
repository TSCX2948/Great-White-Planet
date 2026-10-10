"""Library 数据管理器：扫描、创建、重命名、删除科目与书目。

设计要点
--------
* **不写死任何科目名/书目名**：界面完全由 `data/user data/subjects` 的扫描结果生成。
* 目录不存在时自动补齐（Introduct.md、book、error-prone、notebook）。
* 所有会改变磁盘的操作都在这里收口，界面层只调用这些方法。
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import threading
from pathlib import Path

from gwp.core import constants as C
from gwp.core.config import Config
from gwp.core.eventbus import BOOKS_CHANGED, SUBJECTS_CHANGED, bus
from gwp.core.paths import DataPaths, current as current_paths
from gwp.data_manager import metadata as meta_io
from gwp.data_manager.models import Book, BookItem, Subject

log = logging.getLogger(__name__)

#: Windows 非法路径字符
_INVALID_CHARS = r'<>:"/\|?*'
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}

#: 摘要文件历史遗留命名（兼容手工创建/旧版本）
_SUMMARY_ALIASES = ("Summary.md", "summary.md", "Book_summary.md")

#: 科目目录中属于软件自身的子目录，不当作书目
_SUBJECT_INTERNAL_DIRS = {"book", "error-prone", "notebook", "assets", ".gwp"}


class DataError(Exception):
    """数据层可预期的错误（名称非法、已存在等），界面可以直接把消息展示给用户。"""


# --------------------------------------------------------------------------
# 名称处理
# --------------------------------------------------------------------------

def sanitize_name(raw: str, fallback: str = "未命名") -> str:
    """把用户输入变成合法的文件夹名。不合法字符替换为下划线。"""
    name = (raw or "").strip()
    name = re.sub(r"[\x00-\x1f]", "", name)
    for ch in _INVALID_CHARS:
        name = name.replace(ch, "_")
    name = name.strip().rstrip(".")          # Windows 不允许以点/空格结尾
    if not name:
        name = fallback
    if name.upper() in _RESERVED_NAMES:
        name = f"_{name}"
    return name[:120]


def validate_name(raw: str) -> str | None:
    """返回错误信息；None 表示合法。"""
    name = (raw or "").strip()
    if not name:
        return "名称不能为空"
    if any(ch in name for ch in _INVALID_CHARS):
        return f"名称不能包含以下字符：{' '.join(_INVALID_CHARS)}"
    if name != name.rstrip(". "):
        return "名称不能以点或空格结尾"
    if name.upper() in _RESERVED_NAMES:
        return f"“{name}”是系统保留名，请换一个"
    return None


def summary_filename(book_name: str) -> str:
    """书目**旧版** summary 的文件名：``<书名>_summary.md``。

    新的总结是 PDF（见 :func:`summary_pdf_filename`），这个函数只为
    兼容已有数据保留。
    """
    return f"{book_name}{C.SUMMARY_SUFFIX}"


def summary_pdf_filename(book_name: str) -> str:
    """书目总结（PDF）的文件名：``<书名>_summary.pdf``。"""
    return f"{book_name}{C.SUMMARY_PDF_SUFFIX}"


def canonical_summary_path(book_dir: Path, book_name: str) -> Path:
    """总结该写到哪个文件：**优先 PDF**（新路线），其次旧的 md。"""
    pdf = Path(book_dir) / summary_pdf_filename(book_name)
    if pdf.is_file():
        return pdf
    legacy = Path(book_dir) / summary_filename(book_name)
    if legacy.is_file():
        return legacy
    return pdf          # 都没有：新路线就写 PDF


# --------------------------------------------------------------------------

class Library:
    """对 ``data/user data/subjects`` 的一站式访问入口。"""

    def __init__(self, config: Config | None = None, paths: DataPaths | None = None) -> None:
        self.config = config or Config.load()
        self.paths = paths or current_paths()
        self._lock = threading.RLock()
        self._subjects: list[Subject] | None = None
        self._boxes = None                 # BoxStore，惰性创建（见 boxes 属性）

    # ------------------------------------------------------------------
    # 扫描
    # ------------------------------------------------------------------

    def ensure_layout(self) -> None:
        """确保数据根目录结构存在。"""
        self.paths.ensure()

    def invalidate(self) -> None:
        with self._lock:
            self._subjects = None
        # 科目列表变了，收纳箱里的失效成员也要重新核对
        self._boxes = None

    # ------------------------------------------------------------------
    # 收纳箱（只做分组，不搬动文件）
    # ------------------------------------------------------------------

    @property
    def boxes(self) -> "BoxStore":
        """收纳箱存储（``<数据根目录>/boxes.json``）。"""
        store = getattr(self, "_boxes", None)
        if store is None:
            from gwp.data_manager.boxes import BoxStore

            store = BoxStore(self.paths.subjects_dir)
            self._boxes = store
        return store

    def boxes_with_members(self, refresh: bool = True) -> list[tuple["Box", list[Subject]]]:
        """返回 [(收纳箱, 成员科目)]，成员按**箱内自己的顺序**排列。

        * 自动过滤掉指向已不存在科目的成员（用户手工删了文件夹也不会报错）；
        * 顺序取自 ``box.members``（可由箱内拖拽排序调整），
          不能再按科目全局顺序重排 —— 那样会把箱内排序覆盖掉，
          表现就是"拖了没反应"。
        """
        subjects = self.subjects(refresh=refresh)
        by_name = {subject.name: subject for subject in subjects}
        store = self.boxes

        # 清理幽灵成员：只在真的有失效项时才写盘
        valid = set(by_name)
        store.prune(valid)

        result: list[tuple[Box, list[Subject]]] = []
        for box in store.load():
            members: list[Subject] = []
            for name in box.members:
                subject = by_name.get(name)
                if subject is not None and subject not in members:
                    members.append(subject)
            result.append((box, members))
        return result

    def unboxed_subjects(self, refresh: bool = False) -> list[Subject]:
        """不属于任何收纳箱的科目。"""
        subjects = self.subjects(refresh=refresh)
        in_box: set[str] = set()
        for box in self.boxes.load():
            in_box.update(box.members)
        return [subject for subject in subjects if subject.name not in in_box]

    def subjects(self, refresh: bool = False, with_books: bool = True) -> list[Subject]:
        """扫描并返回全部科目。结果会被缓存，磁盘变化时用 refresh=True。"""
        with self._lock:
            if self._subjects is None or refresh:
                self._subjects = self._scan_subjects(with_books=with_books)
            elif with_books and any(not s.books for s in self._subjects):
                # 之前只做了轻量扫描，这里补全书目
                self._subjects = self._scan_subjects(with_books=True)
            return list(self._subjects)

    def subject(self, name: str) -> Subject | None:
        for subject in self.subjects():
            if subject.name == name:
                return subject
        return None

    def book(self, subject_name: str, book_name: str) -> Book | None:
        subject = self.subject(subject_name)
        if subject is None:
            return None
        for book in subject.books:
            if book.name == book_name:
                return book
        return None

    def _scan_subjects(self, with_books: bool = True) -> list[Subject]:
        root = self.paths.subjects_dir
        subjects: list[Subject] = []
        if not root.exists():
            try:
                root.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                log.error("无法创建科目根目录 %s: %s", root, exc)
            return subjects

        try:
            entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
        except OSError as exc:
            log.error("读取科目根目录失败 %s: %s", root, exc)
            return subjects

        for entry in entries:
            if not entry.is_dir() or entry.name.startswith("."):
                continue
            try:
                subjects.append(self._load_subject(entry, with_books=with_books))
            except Exception:  # noqa: BLE001 - 单个科目异常不应影响其它科目
                log.exception("加载科目失败: %s", entry)

        subjects.sort(key=lambda s: (not s.pinned, s.order, s.title.lower()))
        return subjects

    def _load_subject(self, subject_dir: Path, with_books: bool = True) -> Subject:
        meta = meta_io.load_subject_meta(subject_dir)
        subject = Subject(
            name=subject_dir.name,
            path=subject_dir,
            display_name=meta.get("display_name") or subject_dir.name,
            description=meta.get("description", ""),
            color=meta.get("color", ""),
            cover=meta.get("cover", ""),
            order=int(meta.get("order", 0) or 0),
            pinned=bool(meta.get("pinned", False)),
            created_at=meta.get("created_at", ""),
            updated_at=meta.get("updated_at", ""),
            subject_type=str(meta.get("subject_type") or C.DEFAULT_SUBJECT_TYPE),
            extra=meta,
        )
        if not with_books:
            return subject

        books: list[Book] = []
        total_size = 0
        file_count = 0
        try:
            children = sorted(subject_dir.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            children = []

        for child in children:
            if not child.is_dir() or child.name.startswith("."):
                continue
            if child.name in _SUBJECT_INTERNAL_DIRS:
                continue
            try:
                book = self._load_book(child, subject.name)
                books.append(book)
                total_size += self._dir_size(child)
                file_count += sum(book.item_counts.values())
            except Exception:  # noqa: BLE001
                log.exception("加载书目失败: %s", child)

        books.sort(key=lambda b: (not b.pinned, b.order, b.title.lower()))
        subject.books = books
        subject.book_count = len(books)
        subject.file_count = file_count
        subject.total_size = total_size
        subject.missing_dirs = [
            key for key in C.BOOK_TEMPLATE_DIRS if not (subject_dir / key).exists()
        ] if not books else []
        return subject

    # ------------------------------------------------------------------
    # 书目扫描
    # ------------------------------------------------------------------

    def _load_book(self, book_dir: Path, subject_name: str) -> Book:
        meta = meta_io.load_book_meta(book_dir)
        book = Book(
            name=book_dir.name,
            path=book_dir,
            subject_name=subject_name,
            display_name=meta.get("display_name") or book_dir.name,
            description=meta.get("description", ""),
            color=meta.get("color", "") or meta_io.pick_color(book_dir.name),
            cover=meta.get("cover", ""),
            tags=list(meta.get("tags") or []),
            order=int(meta.get("order", 0) or 0),
            pinned=bool(meta.get("pinned", False)),
            created_at=meta.get("created_at", ""),
            updated_at=meta.get("updated_at", ""),
            summary_note=meta.get("summary_note", ""),
            extra=meta,
        )
        intro_names = (C.INTRO_FILE, "Introduce.md", "introduction.md", "Intro.md")
        for name in intro_names:
            candidate = book_dir / name
            if candidate.exists():
                book.intro_path = candidate
                book.intro_mtime = candidate.stat().st_mtime
                break

        summary = self.find_summary(book_dir, book_dir.name)
        if summary is not None:
            book.summary_path = summary
            book.summary_mtime = summary.stat().st_mtime

        for key in (
            C.BOOK_FOLDER,
            C.ERROR_FOLDER,
            C.NOTEBOOK_FOLDER,
            C.HOMEWORK_FOLDER,
            C.OTHERS_FOLDER,
        ):
            folder = book_dir / key
            if folder.is_dir():
                try:
                    if key == C.HOMEWORK_FOLDER:
                        # 作业栏目**单独处理**：一个作业 = 一个子目录 = 一行，
                        # 所以只数顶层条目。
                        # 这里曾经用 rglob 递归数文件，于是"2.4 作业"目录里的
                        # homework.json + 作业内容文件被算成 2，而表格只显示 1 行
                        # —— 标签上的数字和点进去看到的内容对不上（用户报障）。
                        # 规则：**标签上的数字永远等于点进去能看到几行。**
                        book.item_counts[key] = sum(
                            1 for p in folder.iterdir()
                            if not p.name.startswith(".")
                        )
                    else:
                        book.item_counts[key] = sum(
                            1 for p in folder.rglob("*") if p.is_file()
                        )
                except OSError:
                    book.item_counts[key] = 0
            else:
                book.item_counts[key] = 0

        # 顶层散落的文件也算内容（用户可能直接丢在书目根目录）
        try:
            loose = [
                p for p in book_dir.iterdir()
                if p.is_file() and p.name not in (C.INTRO_FILE, C.BOOK_META)
                and not p.name.endswith(C.SUMMARY_SUFFIX)
                and not p.name.endswith(C.SUMMARY_PDF_SUFFIX)
            ]
            if loose:
                book.item_counts["_root"] = len(loose)
        except OSError:
            pass
        return book

    @staticmethod
    def find_summary(book_dir: Path, book_name: str) -> Path | None:
        """定位总结文件。

        优先级：

        1. ``<书名>_summary.pdf`` —— **新路线**的产物（合并 PDF）；
        2. ``<书名>_summary.md`` —— 旧的 Markdown（读旧数据用）；
        3. 几个历史别名。

        PDF 优先是有意的：同一本书以前生成过 md、现在生成成 PDF 时，
        界面应当显示**新**的那个。
        """
        pdf = book_dir / summary_pdf_filename(book_name)
        if pdf.is_file():
            return pdf
        canonical = book_dir / summary_filename(book_name)
        if canonical.exists():
            return canonical
        for alias in _SUMMARY_ALIASES:
            candidate = book_dir / alias
            if candidate.exists():
                return candidate
        try:
            matches = sorted(book_dir.glob(f"*{C.SUMMARY_SUFFIX}"))
        except OSError:
            matches = []
        return matches[0] if matches else None

    def list_items(self, book: Book) -> list[BookItem]:
        """列出书目的顶层条目：简介、AI总结在最前，然后是各文件夹。"""
        items: list[BookItem] = []

        def _item(path: Path) -> BookItem:
            stat = path.stat()
            is_dir = path.is_dir()
            return BookItem(
                name=path.name,
                path=path,
                is_dir=is_dir,
                size=0 if is_dir else stat.st_size,
                mtime=stat.st_mtime,
                is_summary=bool(book.summary_path and path == book.summary_path),
                is_intro=bool(book.intro_path and path == book.intro_path),
                is_image=path.suffix.lower() in C.IMAGE_EXTENSIONS,
            )

        special: list[BookItem] = []
        for path in (book.summary_path, book.intro_path):
            if path is not None and path.exists():
                special.append(_item(path))

        try:
            children = sorted(book.path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            children = []

        seen = {item.path for item in special}
        others: list[BookItem] = []
        for child in children:
            if child in seen or child.name == C.BOOK_META:
                continue
            others.append(_item(child))

        # 文件夹（book/error-prone/notebook/homework）按固定顺序放在前面
        order = {
            C.ERROR_FOLDER: 0,
            C.NOTEBOOK_FOLDER: 1,
            C.HOMEWORK_FOLDER: 2,
            C.BOOK_FOLDER: 3,
        }
        others.sort(key=lambda it: (0 if it.is_dir else order.get(it.name, 9) + 1, it.name.lower()))
        return special + others

    def list_folder(
        self, folder: Path, *, recursive: bool = False
    ) -> list[BookItem]:
        """列出某个子目录（book / error-prone / notebook / 任意文件夹）内的内容。

        默认**只列这一层**：文件夹就是文件夹，里面的东西**双击进去**才看。

        为什么默认改成只列一层（用户报障）：
        "在本地建立文件夹后，文件夹里面的内容在软件里会和文件夹平行显示"。
        原来的实现会把每个子目录里的文件**也铺出来**，名字做成
        ``第二章/2.1 极限.md``，于是表格里同时出现：

        ```
        第二章
        第二章/2.1 极限.md     <- 和文件夹平行，看着像多出来的条目
        ```

        这不只是难看：那个 `第二章/2.1 极限.md` 行是**假的层级**
        （它不在这一层），右键删它删的是子文件夹里的文件、
        拖拽排序也排不动它，用户会以为软件把目录结构搞乱了。

        ``recursive=True`` 保留原来的"铺平"行为，给
        **「最近」列表**用 —— 它要的正是"所有文件按修改时间排"，
        不关心它们在哪一层。只有那一个调用点需要它。

        ``homework.json`` 之类的**内部文件**会被标成 ``is_meta``：
        它们必须能列出来（用户打开作业文件夹时要看到里面的东西），
        但界面会置灰、禁止改名删除，也不计入条目数。
        """
        if not folder.is_dir():
            return []
        result: list[BookItem] = []
        try:
            entries = sorted(folder.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return []
        for entry in entries:
            if entry.name.startswith("."):
                continue
            try:
                stat = entry.stat()
            except OSError:
                continue
            result.append(
                BookItem(
                    name=entry.name,
                    path=entry,
                    is_dir=entry.is_dir(),
                    size=0 if entry.is_dir() else stat.st_size,
                    mtime=stat.st_mtime,
                    is_image=entry.suffix.lower() in C.IMAGE_EXTENSIONS,
                    is_meta=entry.name == C.HOMEWORK_META,
                )
            )
            if recursive and entry.is_dir():
                try:
                    for sub in sorted(entry.iterdir(), key=lambda p: p.name.lower()):
                        if sub.is_dir():
                            continue
                        sstat = sub.stat()
                        result.append(
                            BookItem(
                                name=f"{entry.name}/{sub.name}",
                                path=sub,
                                is_dir=False,
                                size=sstat.st_size,
                                mtime=sstat.st_mtime,
                                is_image=sub.suffix.lower() in C.IMAGE_EXTENSIONS,
                                is_meta=sub.name == C.HOMEWORK_META,
                            )
                        )
                except OSError:
                    continue
        return result

    def list_homework_items(self, book: Book) -> list[BookItem]:
        """列出作业栏目的条目：**一个作业一行**。

        ``list_folder`` 默认只列一层；即使传 ``recursive=True`` 把它铺平，
        作业栏目也不能用：每个作业内部有 ``homework.json`` 和作业内容文件，
        全铺出来会变成一长串 ``第一次作业/homework.json`` 这种噪音。
        """
        folder = book.path / C.HOMEWORK_FOLDER
        if not folder.is_dir():
            return []
        items: list[BookItem] = []
        try:
            entries = sorted(
                folder.iterdir(),
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except OSError:
            return []
        for entry in entries:
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                # 子目录 = 一个作业（也可能只是用户自己丢进来的文件夹）
                size = 0
                mtime = 0.0
                try:
                    stat = entry.stat()
                    mtime = stat.st_mtime
                    size = sum(
                        p.stat().st_size
                        for p in entry.rglob("*")
                        if p.is_file()
                    )
                except OSError:
                    pass
                items.append(
                    BookItem(
                        name=entry.name, path=entry, is_dir=True,
                        size=size, mtime=mtime,
                    )
                )
            else:
                # 直接丢在作业目录下的散文件也列出来，别让用户找不到
                try:
                    stat = entry.stat()
                except OSError:
                    continue
                items.append(
                    BookItem(
                        name=entry.name, path=entry, is_dir=False,
                        size=stat.st_size, mtime=stat.st_mtime,
                        is_image=entry.suffix.lower() in C.IMAGE_EXTENSIONS,
                    )
                )
        return items

    # ------------------------------------------------------------------
    # 科目增删改
    # ------------------------------------------------------------------

    def _next_home_order(self) -> int:
        """给"要排到最后"的新顶层项算一个 order。

        首页最外层是**箱子与未收纳科目混排**、共用一套 order，
        所以取现有全部顶层项 order 的最大值 +1（空的时候是 0）。
        """
        orders = [int(box.order or 0) for box in self.boxes.load()]
        orders.extend(
            int(subject.order or 0) for subject in self.unboxed_subjects(refresh=True)
        )
        return (max(orders) + 1) if orders else 0

    def _next_book_order(self, subject_name: str) -> int:
        """给新书目算一个"排在最后"的 order。"""
        orders: list[int] = []
        subject_dir = self.paths.subjects_dir / subject_name
        if subject_dir.is_dir():
            for child in subject_dir.iterdir():
                if not child.is_dir() or child.name.startswith("."):
                    continue
                meta = meta_io.load_book_meta(child)
                orders.append(int(meta.get("order", 0) or 0))
        return (max(orders) + 1) if orders else 0

    def create_subject(
        self,
        name: str,
        description: str = "",
        color: str = "",
        cover: str = "",
        subject_type: str = C.DEFAULT_SUBJECT_TYPE,
    ) -> Subject:
        error = validate_name(name)
        if error:
            raise DataError(error)
        clean = sanitize_name(name)
        target = self.paths.subjects_dir / clean
        if target.exists():
            raise DataError(f"科目“{clean}”已经存在")

        kind = subject_type if subject_type in C.SUBJECT_TYPES else C.DEFAULT_SUBJECT_TYPE
        target.mkdir(parents=True, exist_ok=True)
        # 科目下**不能**预建 book/error-prone/notebook/homework：
        # 扫描时"科目下的每个子目录算一本书"，预建这些目录会被当成 4 本空书。
        # 子目录由 create_book / ensure_book_layout 在书目里创建。
        meta = {
            "display_name": clean,
            "description": description,
            "color": color or meta_io.pick_color(clean),
            "cover": cover,
            "subject_type": kind,
            # 需求：**新建的排在最后**。以前一律写 0，而排序是
            # (pinned, order, 标题)，结果新科目插到了最前面。
            # 首页是"箱子 + 未收纳科目"混排、共用一套 order，
            # 所以取比现有最大 order 更大的值。
            "order": self._next_home_order(),
            "created_at": meta_io.now_iso(),
            "updated_at": meta_io.now_iso(),
        }
        meta_io.save_subject_meta(target, meta)
        self.invalidate()
        bus.emit(SUBJECTS_CHANGED, action="create", name=clean)
        log.info("新建科目: %s（类型=%s）", clean, kind)

        # 日记类型：自动建一个默认书目（MyBook），用户打开就能直接写
        if kind == C.SUBJECT_DIARY:
            try:
                self.create_book(clean, C.DIARY_DEFAULT_BOOK, subject_type=kind)
            except Exception:  # noqa: BLE001 - 建默认书目失败不该让新建科目失败
                log.warning("为日记科目创建默认书目失败：%s", clean, exc_info=True)

        return self.subject(clean) or Subject(name=clean, path=target, subject_type=kind)

    def change_subject_type(self, name: str, subject_type: str) -> Subject:
        """修改科目类型。返回更新后的科目。

        **只在"同类结构"之间允许切换** —— 也就是 **自学课 <-> 校修课**：
        两者目录完全一样（``book`` / ``error-prone`` / ``notebook`` / ``homework`` /
        ``others``），区别只有 ``homework`` 在界面上叫「练习」还是「作业」，
        因此切换**不动任何文件、不会丢数据**。

        **日记类型不参与切换**：它的目录结构（``AI summary`` / ``AI diary`` /
        ``my diary`` / ``else diary``）与普通科目完全不同，硬换要么丢内容、
        要么留下一堆用途不明的目录。要换就得手工搬文件，所以这里直接拒绝并说明原因。
        """
        if subject_type not in C.SUBJECT_TYPES:
            raise DataError(f"未知的科目类型：{subject_type}")

        subject = self.subject(name)
        if subject is None:
            raise DataError(f"科目“{name}”不存在")

        current = subject.subject_type or C.DEFAULT_SUBJECT_TYPE
        if current == subject_type:
            return subject

        if C.SUBJECT_DIARY in (current, subject_type):
            raise DataError(
                "日记类型的目录结构（AI summary / AI diary / my diary / else diary）"
                "与普通科目完全不同，不能直接转换。\n\n"
                "如果需要，请新建一个目标类型的科目，再把文件手工搬过去。"
            )

        subject_dir = self.paths.subjects_dir / name
        meta = meta_io.load_subject_meta(subject_dir)
        meta["subject_type"] = subject_type
        meta["updated_at"] = meta_io.now_iso()
        meta_io.save_subject_meta(subject_dir, meta)

        self.invalidate()
        bus.emit(SUBJECTS_CHANGED, action="type", name=name)
        log.info(
            "修改科目类型: %s（%s -> %s）", name, C.type_label(current),
            C.type_label(subject_type),
        )
        return self.subject(name) or subject  # type: ignore[return-value]

    def rename_subject(self, old_name: str, new_name: str) -> Subject:
        error = validate_name(new_name)
        if error:
            raise DataError(error)
        source = self.paths.subjects_dir / old_name
        if not source.is_dir():
            raise DataError(f"科目“{old_name}”不存在")
        clean = sanitize_name(new_name)
        target = self.paths.subjects_dir / clean
        if target.exists() and clean != old_name:
            raise DataError(f"科目“{clean}”已经存在")
        if clean == old_name:
            return self.subject(old_name)  # type: ignore[return-value]

        self._move_dir(source, target)
        meta = meta_io.load_subject_meta(target)
        meta["display_name"] = clean
        meta_io.save_subject_meta(target, meta)

        # 卡片图片属于非用户数据，放在 else data/assets 下，目录名同步
        old_assets = self.paths.subject_asset_dir(old_name)
        new_assets = self.paths.subject_asset_dir(clean)
        if old_assets.exists():
            new_assets.parent.mkdir(parents=True, exist_ok=True)
            self._move_dir(old_assets, new_assets)
            current_cover = meta.get("cover", "")
            if current_cover:
                # cover 可能指向资产目录里的文件名，同步过去
                pass
        self.invalidate()
        bus.emit(SUBJECTS_CHANGED, action="rename", name=clean, old=old_name)
        log.info("重命名科目: %s -> %s", old_name, clean)
        return self.subject(clean)  # type: ignore[return-value]

    def update_subject(self, name: str, **fields) -> Subject:
        subject_dir = self.paths.subjects_dir / name
        if not subject_dir.is_dir():
            raise DataError(f"科目“{name}”不存在")
        meta = meta_io.load_subject_meta(subject_dir)
        for key in ("display_name", "description", "color", "cover", "order", "pinned"):
            if key in fields and fields[key] is not None:
                meta[key] = fields[key]
        meta_io.save_subject_meta(subject_dir, meta)
        self.invalidate()
        bus.emit(SUBJECTS_CHANGED, action="update", name=name)
        return self.subject(name)  # type: ignore[return-value]

    def set_subject_order(
        self,
        names: list[str],
        absolute: bool = False,
        positions: dict[str, int] | None = None,
    ) -> None:
        """按给定顺序重写科目的 order 字段（首页拖拽排序用）。

        传入期望的完整顺序；未出现在列表里的科目排到后面，
        保证任何情况下都不会弄丢科目。

        ``positions`` 给出每个科目的**绝对 order**（首页混排时用混合序列下标）。

        ``absolute=True`` 时把 ``positions``/下标直接当作 order 写入，而**不**重编号成
        ``0..n-1`` —— 首页的箱子/科目混排需要跨两个列表比较 order。
        """
        wanted = [str(name) for name in (names or [])]
        if not wanted and not positions:
            return
        existing = [subject.name for subject in self.subjects(refresh=True)]
        position = {name: index for index, name in enumerate(wanted)}
        ordered: list[str] = []
        for name in wanted:
            if name in existing and name not in ordered:
                ordered.append(name)
        for name in existing:
            if name not in position:
                ordered.append(name)
        if positions:
            # 显式给了绝对 order：以它为准（首页混排）
            position = {str(k): int(v) for k, v in positions.items()}
        elif not absolute:
            # 只排科目时，order 保持紧凑的 0..n-1
            position = {name: index for index, name in enumerate(ordered)}
        for name in ordered:
            directory = self.paths.subjects_dir / name
            if not directory.is_dir():
                continue
            meta = meta_io.load_subject_meta(directory)
            meta["order"] = position.get(name, 0)
            meta_io.save_subject_meta(directory, meta)
        self.invalidate()
        bus.emit(SUBJECTS_CHANGED, action="reorder")

    def move_subject_before(self, name: str, target_name: str) -> None:
        """把某个科目移到另一个科目之前（拖到卡片上时调用）。"""
        names = [subject.name for subject in self.subjects()]
        if name not in names or target_name not in names or name == target_name:
            return
        names.remove(name)
        names.insert(names.index(target_name), name)
        self.set_subject_order(names)

    def subject_after(self, name: str, target_name: str) -> None:
        """把某个科目移到另一个科目**之后**（落点在卡片右半边时调用）。"""
        names = [subject.name for subject in self.subjects()]
        if name not in names or target_name not in names or name == target_name:
            return
        names.remove(name)
        names.insert(names.index(target_name) + 1, name)
        self.set_subject_order(names)

    # ------------------------------------------------------------------
    # 箱子与科目的混排（首页最外层）
    # ------------------------------------------------------------------

    def set_home_order(self, items: list[tuple[str, str]]) -> None:
        """按给定顺序重写首页最外层的混排顺序。

        ``items`` 是 ``[(kind, key)]``，``kind`` 为 ``"box"`` 或 ``"subject"``，
        ``key`` 分别是箱子 id / 科目目录名。

        这是首页顺序的**唯一权威**：箱子和科目共用一套 0..N-1 编号，
        因此可以表达任意交错顺序。

        关键点：**两个列表各自单独编号会互相碰撞** —— 箱子编成 0..n-1、
        科目也编成 0..m-1，于是"箱子排到科目前面"根本表达不出来。
        所以这里统一用混合序列的下标，并据此推导出各自列表内部的相对顺序。
        """
        cleaned: list[tuple[str, str]] = []
        for kind, key in items:
            if kind not in ("box", "subject"):
                continue
            if (kind, key) not in cleaned:
                cleaned.append((kind, key))

        boxes_now = [box.id for box, _members in self.boxes_with_members(refresh=True)]
        subjects_now = [subject.name for subject in self.subjects(refresh=True)]
        # 只有"顶层项"参与混排编号：箱子 + 未收纳的科目。
        # 箱内科目不写 order，避免它们的 order 和顶层项碰撞（撞了就排出怪顺序）。
        unboxed_now = [
            subject.name for subject in self.unboxed_subjects(refresh=True)
        ]

        # 没出现在列表里的项补在后面，保证不丢失
        for box_id in boxes_now:
            if ("box", box_id) not in cleaned:
                cleaned.append(("box", box_id))
        for name in unboxed_now:
            if ("subject", name) not in cleaned:
                cleaned.append(("subject", name))

        # 箱内科目不是顶层项，直接剔除（无论调用方有没有传进来）
        in_box: set[str] = set()
        for box in self.boxes.load():
            in_box.update(box.members)
        cleaned = [
            item for item in cleaned
            if not (item[0] == "subject" and item[1] in in_box)
        ]

        if not cleaned:
            return

        # 统一编号：混合序列下标就是 order。
        order_of = {item: index for index, item in enumerate(cleaned)}
        # 注意 absolute=True + positions —— 箱子的 order 必须取**混合序列下标**，
        # 不能取"箱子列表内的下标"（那样单个箱子永远拿到 0，
        # 于是又跑到科目前面，混排结果被抹掉）。
        self.boxes.set_order(
            [key for kind, key in cleaned if kind == "box"],
            absolute=True,
            positions={
                key: order_of[("box", key)]
                for kind, key in cleaned
                if kind == "box"
            },
        )
        # 科目只写**未收纳**的那些（顶层项）
        self.set_subject_order(
            [key for kind, key in cleaned if kind == "subject"],
            absolute=True,
            positions={
                key: order_of[("subject", key)]
                for kind, key in cleaned
                if kind == "subject"
            },
        )
        self.invalidate()
        bus.emit(SUBJECTS_CHANGED, action="reorder")

    def home_sequence(self, refresh: bool = True) -> list[tuple[str, str]]:
        """首页最外层的当前混排序列 ``[(kind, key)]``（按 order 排好）。

        只包含**真正的顶层项**：所有收纳箱 + **未收纳**的科目。
        在箱子里的科目不属于顶层（它们显示在箱内），如果算进来，
        拖拽时会按错误的相对位置计算，箱子就会移错地方。
        """
        items: list[tuple[int, int, tuple[str, str]]] = []
        counter = 0
        for box, _members in self.boxes_with_members(refresh=refresh):
            items.append((int(box.order or 0), counter, ("box", box.id)))
            counter += 1
        for subject in self.unboxed_subjects(refresh=refresh):
            items.append((int(subject.order or 0), counter, ("subject", subject.name)))
            counter += 1
        items.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in items]

    def box_before_subject(self, box_id: str, subject_name: str) -> None:
        """把收纳箱排到某个科目所在的位置（首页混排用）。

        插到目标**前面还是后面**由 :meth:`box_after_subject` 区分；
        这里统一处理"以目标为参照"的移动。
        """
        self._move_home_item(("box", box_id), ("subject", subject_name), before=True)

    def box_after_subject(self, box_id: str, subject_name: str) -> None:
        """把收纳箱排到某个科目**后面**（首页混排用）。"""
        self._move_home_item(("box", box_id), ("subject", subject_name), before=False)

    def subject_before_box(self, subject_name: str, box_id: str) -> None:
        """把科目排到某个收纳箱**前面**（首页混排用）。"""
        self._move_home_item(("subject", subject_name), ("box", box_id), before=True)

    def subject_after_box(self, subject_name: str, box_id: str) -> None:
        """把科目排到某个收纳箱**后面**（首页混排用）。"""
        self._move_home_item(("subject", subject_name), ("box", box_id), before=False)

    def _move_home_item(
        self, moved: tuple[str, str], anchor: tuple[str, str], before: bool
    ) -> None:
        """首页混排的通用移动：把 ``moved`` 放到 ``anchor`` 之前或之后。"""
        items = self.home_sequence(refresh=False)
        if moved not in items or anchor not in items or moved == anchor:
            return
        items = [item for item in items if item != moved]
        index = items.index(anchor)
        items.insert(index if before else index + 1, moved)
        # 关键：先把被移动的箱子写成**绝对 order**。
        # 否则后续 set_home_order 里 boxes.set_order 的重编号会把这次移动抹掉
        # （单个箱子永远拿回 0，于是又跑到最前面）。
        if moved[0] == "box":
            self.boxes.set_order(
                [key for kind, key in items if kind == "box"], absolute=True
            )
        self.set_home_order(items)

    def move_box_to_home_index(self, box_id: str, index: int) -> None:
        """把收纳箱移动到首页混排序列的指定下标（越界会夹紧）。"""
        items = self.home_sequence(refresh=False)
        if ("box", box_id) not in items:
            return
        items = [item for item in items if item != ("box", box_id)]
        target = max(0, min(len(items), int(index)))
        items.insert(target, ("box", box_id))
        self.boxes.set_order(
            [key for kind, key in items if kind == "box"], absolute=True
        )
        self.set_home_order(items)

    def set_subject_cover(self, name: str, source_image: Path, copy: bool = True) -> Path:
        """更换科目卡片图片。图片复制到 ``else data/assets``，不污染用户数据。"""
        subject_dir = self.paths.subjects_dir / name
        if not subject_dir.is_dir():
            raise DataError(f"科目“{name}”不存在")
        if source_image.suffix.lower() not in C.COVER_EXTENSIONS:
            raise DataError("卡片图片仅支持 jpg / png 格式")
        if not source_image.is_file():
            raise DataError(f"图片不存在：{source_image}")

        asset_dir = self.paths.subject_asset_dir(name)
        asset_dir.mkdir(parents=True, exist_ok=True)
        target = asset_dir / f"cover{source_image.suffix.lower()}"
        for old in asset_dir.glob("cover.*"):
            if old != target:
                try:
                    old.unlink()
                except OSError:
                    pass
        if copy:
            shutil.copy2(source_image, target)
        else:
            self._move_dir(source_image, target)

        meta = meta_io.load_subject_meta(subject_dir)
        meta["cover"] = target.name          # 相对资产目录的文件名，便于整体迁移
        meta.pop("cover_asset", None)
        meta_io.save_subject_meta(subject_dir, meta)
        self.invalidate()
        bus.emit(SUBJECTS_CHANGED, action="cover", name=name)
        return target

    def subject_cover_path(self, subject: Subject) -> Path | None:
        """解析卡片图片的真实路径。

        查找顺序：``else data/assets/subjects/<科目>`` → 科目目录内 → 元数据里记录的绝对路径。
        """
        asset_dir = self.paths.subject_asset_dir(subject.name)

        # 1) 元数据里可能记录的是资产目录中的文件名
        if subject.cover:
            name = Path(subject.cover).name
            candidate = asset_dir / name
            if candidate.exists():
                return candidate
            # 2) 也可能直接放在科目目录里
            inside = subject.path / subject.cover
            if inside.exists():
                return inside
            # 3) 绝对路径
            absolute = Path(subject.cover)
            if absolute.is_absolute() and absolute.exists():
                return absolute

        # 4) 资产目录里的任何 cover.*
        if asset_dir.exists():
            for pattern in ("cover.*", "*.png", "*.jpg", "*.jpeg"):
                matches = sorted(asset_dir.glob(pattern))
                if matches:
                    return matches[0]

        # 5) 科目目录里的任何 cover.*
        for pattern in ("cover.*", "*.png", "*.jpg", "*.jpeg"):
            matches = sorted(subject.path.glob(pattern))
            if matches:
                return matches[0]
        return None

    def delete_subject(self, name: str, to_recycle: bool = False) -> None:
        """删除科目。默认永久删除；to_recycle=True 时移到回收站（若可用）。"""
        target = self.paths.subjects_dir / name
        if not target.is_dir():
            raise DataError(f"科目“{name}”不存在")
        self._delete_dir(target, to_recycle)
        asset_dir = self.paths.subject_asset_dir(name)
        if asset_dir.exists():
            self._delete_dir(asset_dir, to_recycle)
        backup_dir = self.paths.backup_dir / name
        if backup_dir.exists():
            self._delete_dir(backup_dir, False)
        self.invalidate()
        bus.emit(SUBJECTS_CHANGED, action="delete", name=name)
        log.info("删除科目: %s", name)

    # ------------------------------------------------------------------
    # 书目增删改
    # ------------------------------------------------------------------

    def create_book(
        self,
        subject_name: str,
        book_name: str,
        description: str = "",
        intro_text: str = "",
        subject_type: str = "",
    ) -> Book:
        error = validate_name(book_name)
        if error:
            raise DataError(error)
        subject_dir = self.paths.subjects_dir / subject_name
        if not subject_dir.is_dir():
            raise DataError(f"科目“{subject_name}”不存在")
        clean = sanitize_name(book_name)
        target = subject_dir / clean
        if target.exists():
            raise DataError(f"书目“{clean}”已经存在")

        # 类型决定目录结构：日记类型用 AI summary / AI diary / my diary / else diary
        kind = subject_type or self._subject_type(subject_name)
        target.mkdir(parents=True, exist_ok=True)
        for key in C.template_dirs_for_type(kind):
            (target / key).mkdir(exist_ok=True)

        intro = target / C.INTRO_FILE
        if not intro.exists():
            template = intro_text or self._intro_template(clean)
            intro.write_text(template, encoding="utf-8")

        meta_io.save_book_meta(
            target,
            {
                "display_name": clean,
                "description": description,
                "color": meta_io.pick_color(clean),
                # 需求：**新建的排在最后**（以前不写 order，默认 0 就排到最前）
                "order": self._next_book_order(subject_name),
                "created_at": meta_io.now_iso(),
                "updated_at": meta_io.now_iso(),
            },
        )
        self.invalidate()
        bus.emit(BOOKS_CHANGED, action="create", subject=subject_name, name=clean)
        log.info("新建书目: %s/%s", subject_name, clean)
        return self.book(subject_name, clean)  # type: ignore[return-value]

    def ensure_book_layout(self, subject_name: str, book_name: str) -> list[str]:
        """补齐书目缺失的标准目录/文件，返回本次补建的项目。

        目录清单按**科目类型**决定，因此日记科目只会补 AI summary / AI diary /
        my diary / else diary，而不会冒出来教材与易错题。
        """
        book_dir = self.paths.book_dir(subject_name, book_name)
        if not book_dir.is_dir():
            raise DataError(f"书目不存在：{subject_name}/{book_name}")
        kind = self._subject_type(subject_name)
        created: list[str] = []
        for key in C.template_dirs_for_type(kind):
            folder = book_dir / key
            if not folder.exists():
                folder.mkdir(parents=True, exist_ok=True)
                created.append(key)
        intro = book_dir / C.INTRO_FILE
        if not intro.exists():
            intro.write_text(self._intro_template(book_name), encoding="utf-8")
            created.append(C.INTRO_FILE)
        if created:
            self.invalidate()
            bus.emit(BOOKS_CHANGED, action="repair", subject=subject_name, name=book_name)
        return created

    def _subject_type(self, subject_name: str) -> str:
        """取科目类型；读不到时按默认类型（自学课）处理。"""
        meta = meta_io.load_subject_meta(self.paths.subjects_dir / subject_name)
        kind = str(meta.get("subject_type") or C.DEFAULT_SUBJECT_TYPE)
        return kind if kind in C.SUBJECT_TYPES else C.DEFAULT_SUBJECT_TYPE

    def rename_book(self, subject_name: str, old_name: str, new_name: str) -> Book:
        error = validate_name(new_name)
        if error:
            raise DataError(error)
        subject_dir = self.paths.subjects_dir / subject_name
        source = subject_dir / old_name
        if not source.is_dir():
            raise DataError(f"书目“{old_name}”不存在")
        clean = sanitize_name(new_name)
        target = subject_dir / clean
        if target.exists() and clean != old_name:
            raise DataError(f"书目“{clean}”已经存在")
        if clean == old_name:
            return self.book(subject_name, old_name)  # type: ignore[return-value]

        self._move_dir(source, target)
        meta = meta_io.load_book_meta(target)
        meta["display_name"] = clean
        meta_io.save_book_meta(target, meta)

        # summary 文件名跟随书名变化
        summary = self.find_summary(target, old_name)
        if summary is not None:
            # 新路线是 PDF、旧数据是 md：按**实际那个**改成对应的新名字。
            # 一律改成 md 的话，PDF 会变成"名字对不上"的孤儿文件 ——
            # 下次扫描就认不出它是这本书的总结了。
            suffix = (
                C.SUMMARY_PDF_SUFFIX
                if summary.name.endswith(C.SUMMARY_PDF_SUFFIX)
                else C.SUMMARY_SUFFIX
            )
            canonical = target / f"{clean}{suffix}"
            if summary != canonical:
                try:
                    self._move_dir(summary, canonical)
                except OSError:
                    log.exception("重命名 summary 文件失败: %s", summary)

        # 备份目录同步
        old_backup = self.paths.backup_book_dir(subject_name, old_name)
        if old_backup.exists():
            new_backup = self.paths.backup_book_dir(subject_name, clean)
            new_backup.parent.mkdir(parents=True, exist_ok=True)
            self._move_dir(old_backup, new_backup)

        self.invalidate()
        bus.emit(BOOKS_CHANGED, action="rename", subject=subject_name, name=clean, old=old_name)
        log.info("重命名书目: %s/%s -> %s", subject_name, old_name, clean)
        return self.book(subject_name, clean)  # type: ignore[return-value]

    def update_book(self, subject_name: str, book_name: str, **fields) -> Book:
        book_dir = self.paths.book_dir(subject_name, book_name)
        if not book_dir.is_dir():
            raise DataError(f"书目不存在：{subject_name}/{book_name}")
        meta = meta_io.load_book_meta(book_dir)
        for key in ("display_name", "description", "author", "tags", "cover", "color",
                    "order", "pinned", "summary_note"):
            if key in fields and fields[key] is not None:
                meta[key] = fields[key]
        meta_io.save_book_meta(book_dir, meta)
        self.invalidate()
        bus.emit(BOOKS_CHANGED, action="update", subject=subject_name, name=book_name)
        return self.book(subject_name, book_name)  # type: ignore[return-value]

    def delete_book(self, subject_name: str, book_name: str, to_recycle: bool = True) -> None:
        target = self.paths.book_dir(subject_name, book_name)
        if not target.is_dir():
            raise DataError(f"书目不存在：{subject_name}/{book_name}")
        self._delete_dir(target, to_recycle)
        backup = self.paths.backup_book_dir(subject_name, book_name)
        if backup.exists():
            self._delete_dir(backup, False)
        self.invalidate()
        bus.emit(BOOKS_CHANGED, action="delete", subject=subject_name, name=book_name)
        log.info("删除书目: %s/%s", subject_name, book_name)

    def move_book(self, subject_name: str, book_name: str, target_subject: str) -> Book:
        """把书目移动到另一个科目下。"""
        source = self.paths.book_dir(subject_name, book_name)
        if not source.is_dir():
            raise DataError(f"书目不存在：{subject_name}/{book_name}")
        if subject_name == target_subject:
            raise DataError("源科目与目标科目相同")
        target_dir = self.paths.subjects_dir / target_subject
        if not target_dir.is_dir():
            raise DataError(f"目标科目“{target_subject}”不存在")
        destination = target_dir / book_name
        if destination.exists():
            raise DataError(f"目标科目中已存在“{book_name}”")
        self._move_dir(source, destination)
        backup_src = self.paths.backup_book_dir(subject_name, book_name)
        if backup_src.exists():
            backup_dst = self.paths.backup_book_dir(target_subject, book_name)
            backup_dst.parent.mkdir(parents=True, exist_ok=True)
            self._move_dir(backup_src, backup_dst)
        self.invalidate()
        bus.emit(BOOKS_CHANGED, action="move", subject=target_subject, name=book_name, old=subject_name)
        return self.book(target_subject, book_name)  # type: ignore[return-value]

    def ensure_summary_file(self, subject_name: str, book_name: str, initial: str = "") -> Path:
        """确保 summary 文件存在（生成前先保证有落点）。"""
        book_dir = self.paths.book_dir(subject_name, book_name)
        if not book_dir.is_dir():
            raise DataError(f"书目不存在：{subject_name}/{book_name}")
        existing = self.find_summary(book_dir, book_name)
        if existing is not None:
            return existing
        target = book_dir / summary_filename(book_name)
        body = initial or self._summary_template(book_name)
        target.write_text(body, encoding="utf-8")
        self.invalidate()
        return target

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    def _intro_template(self, book_name: str) -> str:
        return (
            f"# {book_name} 简介\n\n"
            "## 学习目标\n\n"
            "- （在这里写下这本书的学习目标）\n\n"
            "## 内容范围\n\n"
            "- \n\n"
            "## 备注\n\n"
            "- 本文件由软件自动创建，可自由编辑；它会被 AI 纳入总结范围。\n"
        )

    def _summary_template(self, book_name: str) -> str:
        return (
            f"# {book_name}\n\n"
            "> 本文件由 Great White Planet 的 AI 整合 `Introduct.md`、`notebook`、`error-prone` 生成。\n"
            "> 你可以直接编辑它；再次生成时会自动保存上一版到 `else data/summary_backup`。\n\n"
            "## 待生成\n\n"
            "点击「工具 → 生成学习总结」开始整合资料。\n"
        )

    @staticmethod
    def _is_inside(child: Path, parent: Path) -> bool:
        try:
            child.resolve().relative_to(parent.resolve())
            return True
        except ValueError:
            return False

    def _dir_size(self, path: Path, limit_files: int = 4000) -> int:
        total = 0
        count = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
                    count += 1
                    if count >= limit_files:
                        break
        except OSError:
            pass
        return total

    @staticmethod
    def _move_dir(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.replace(source, target)
        except OSError:
            shutil.move(str(source), str(target))

    @staticmethod
    def _delete_dir(path: Path, to_recycle: bool) -> None:
        if not path.exists():
            return
        if to_recycle:
            try:
                from gwp.services import shell_ops

                if shell_ops.send_to_recycle_bin(path):
                    return
            except Exception:  # noqa: BLE001 - 回收站不可用时退回永久删除
                log.warning("移入回收站失败，改为永久删除: %s", path)
        shutil.rmtree(path, ignore_errors=False)
