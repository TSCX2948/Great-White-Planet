"""文档合并：把一个书目的全部资料插入 AI 总结里。

需求原话：

> 更主要的功能是文档合并，你要把 pdf 以及其他文档插入到 summary 文档中
> 要求 AI 总结的全部文件，如果插入困难，便以图片插入，
> 图片本地可以专门找一个新位置存储

所以这里的定位是：**AI 总结是"一份完整的复习文档"的主干，
用户放在书目里的其它文件（PDF 教材、讲义、课件、图片……）也要成为它的一部分。**

统一的处理策略
--------------
把每一份资料都变成**图片**，再按小节插进 summary 的末尾：

| 来源 | 处理方式 |
| --- | --- |
| PDF | **每页**渲染成图片（需求明确要求"每页当图片插入"） |
| 图片（png/jpg/…） | 直接复制/登记 |
| Word / PPT / Excel / 纯文本 | 先用 :mod:`gwp.services.document_reader` 抽成 Markdown，再用 **PyMuPDF Story** 把这份 Markdown 渲染成图片 |

为什么连"能抽文字"的 Word 也走图片：需求说"插入困难便以图片插入"，
而 Word/PPT 的**版面**（表格、公式图片、图表）在纯文本里会丢。
抽成 Markdown 是为了"内容不丢"，渲染成图片是为了"版面不丢" ——
两者结合才既完整又能看。

图片存哪
--------
``<data>/else data/merged/<书目>/`` —— 需求要求"专门找一个新位置存储"。
放在 **else data**（软件数据侧）而不是书目里：它是**生成物**，
不该混进用户的资料目录；集中存放也便于清理。

这个模块**不依赖 Qt**，可以单独测试。
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF

from gwp.core import constants as C
from gwp.services import document_reader
from gwp.services import markdown_renderer as md_render
from gwp.services import math_render

log = logging.getLogger(__name__)

#: 合并出来的图片放在哪里（相对 else data）
MERGED_DIR_NAME = "merged"

#: PDF / 文档渲染成图片时的分辨率
PAGE_DPI = 110

#: 一页渲染出来的图片超过这个像素高度就切分（避免单张图过大导致 PDF 导出很慢）
MAX_PAGE_PIXELS = 4000

#: 这些后缀直接当图片插入
_IMAGE_SUFFIXES = set(C.IMAGE_EXTENSIONS)

#: 这些后缀**不做**合并：软件自己的数据文件
_SKIP_NAMES = {C.BOOK_META, C.SUBJECT_META, C.HOMEWORK_META, C.INTRO_FILE}

#: 插入小节用的标题
MERGE_HEADING = "附：原始资料（合并）"

#: 每份资料的插入方式（决定"插图片"还是"插文字"）
#:
#: 需求（用户明确规定的分流）：
#:
#: > 图片型pdf/表格/ppt/pptx 按照图片插入；文字形pdf、doc/docx 仍然插入文字
#: > （公式部分插入图片）；md 文档直接融合进去
#:
#: 所以这里**不是"能抽文字就不插图片"**，而是按类型明确分派 ——
#: 表格与 PPT 的**版面**才是内容主体（表格线、幻灯片排版），
#: 转成文字会把它们压扁成一行行字，所以一律走图片。
HANDLE_IMAGES = "images"      # 直接转成图片插入
HANDLE_TEXT = "text"          # 抽成文字插入（公式变图片）
HANDLE_MERGE = "merge"        # 文字直接融合进 summary

#: 后缀 -> 插入方式。没列到的走需要询问的策略（见 describe_unknown）。
_SUFFIX_HANDLING: dict[str, str] = {
    # 表格与幻灯片：版面即内容 -> 图片
    ".pptx": HANDLE_IMAGES,
    ".ppt": HANDLE_IMAGES,
    ".xlsx": HANDLE_IMAGES,
    ".xls": HANDLE_IMAGES,
    # 文档：文字为主 -> 文字（公式另处理成图片）
    ".doc": HANDLE_TEXT,
    ".docx": HANDLE_TEXT,
    ".txt": HANDLE_TEXT,
    ".rtf": HANDLE_TEXT,
    # Markdown：本来就是 Markdown -> 直接融合
    ".md": HANDLE_MERGE,
    ".markdown": HANDLE_MERGE,
}

#: 重复生成时，这两个标记**之间**的内容会被整段重写。
#:
#: 用一对标记而不是"从标记到文件末尾"：因为"使用提示"要固定在**文档最末尾**
#: （需求："可以在文档末尾补充tips"），如果只用一个起始标记，
#: 重写就会把末尾的提示一起吃掉。
MERGE_MARKER = "<!-- GWP:MERGED-SOURCES -->"
MERGE_END_MARKER = "<!-- GWP:MERGED-SOURCES-END -->"

#: summary 末尾的"使用提示"。
#:
#: 需求："summary中板块，不需要你补充内容了（**或者你可以仅仅在文档末尾补充tips**）"。
#: 所以 AI 的"补充"只剩这一处 —— 而且是**固定文字**，不是每次让模型现编：
#: 固定文字才能保证同一句话在任何一次生成里都一致、可预期。
TIPS_SECTION = """## 使用提示

* 本文件的内容是**原始资料的图片**，未经过 AI 改写；要看原文请点开对应文件。
* 图片集中存放在数据目录的 `else data/merged/<书目>/` 与 `else data/equations/` 下。
* 想调整页序：重新点「生成总结」并勾选「让 AI 按主题重排页序」。
* 想知道某次改写之前长什么样：「版本管理」里有每一版的备份。"""


@dataclass
class MergedItem:
    """一份要合并的资料的处理结果。

    一份资料**要么是图片型、要么是文字型**（见 :func:`merge_source`）：

    * 图片型：内容在 ``images`` 里，写 summary 时按 ``![](...)`` 引用；
    * 文字型：内容在 ``text`` 里，**原样写进 summary**（公式在最终渲染时变图片）。

    ``text`` 与 ``images`` 互斥使用，但都保留字段 —— 这样"判成文字型却抽不出字"
    时可以退回图片，不用换一个对象。
    """

    source: Path
    label: str                                   # 在总结里显示的小标题
    images: list[Path] = field(default_factory=list)
    kind: str = "text"
    error: str = ""
    note: str = ""
    #: 每张图片对应的**原文开头若干字符**（与 ``images`` 一一对应）。
    #: 只用于"AI 混排"时判断这一页讲什么；**不会**写进总结。
    page_texts: list[str] = field(default_factory=list)
    #: 文字型资料的内容（Markdown）。与 ``images`` 二选一。
    text: str = ""
    #: 是否"没有插入内容"（未规定处理方式的类型）。这类不算失败，也不会被删。
    skipped: bool = False

    @property
    def ok(self) -> bool:
        if self.error or self.skipped:
            return False
        return bool(self.images) or bool((self.text or "").strip())

    @property
    def is_text(self) -> bool:
        return bool((self.text or "").strip()) and not self.images

    @property
    def rel_label(self) -> str:
        return self.label

    def preview_of(self, index: int, limit: int = 120) -> str:
        """第 ``index`` 页的内容开头（取不到就返回空串）。"""
        if 0 <= index < len(self.page_texts):
            text = re.sub(r"\s+", " ", self.page_texts[index] or "").strip()
            return text[:limit]
        return ""


@dataclass
class MergeReport:
    """一次合并的总体结果。"""

    items: list[MergedItem] = field(default_factory=list)
    output_dir: Path | None = None
    #: 是否做过 AI 混排。混排之后"每份资料一个 ### 小节"的写法就表达不了
    #: 穿插了 —— 会被打散的资料要连续输出，标题只在第一次出现时写一次。
    mixed: bool = False
    #: 混排后的整体页序（仅当 ``mixed`` 为真时有意义）
    ordered_pages: list["Page"] = field(default_factory=list)

    @property
    def image_count(self) -> int:
        return sum(len(item.images) for item in self.items)

    @property
    def ok_items(self) -> list[MergedItem]:
        return [item for item in self.items if item.ok]

    @property
    def failed(self) -> list[MergedItem]:
        return [item for item in self.items if not item.ok]


# --------------------------------------------------------------------------
# 目录
# --------------------------------------------------------------------------

def merge_dir(else_data: Path, book_name: str) -> Path:
    """合并图片的存放目录（每个书目一个子目录，便于清理）。"""
    safe = re.sub(r'[\\/:*?"<>|]', "_", (book_name or "未命名").strip()) or "未命名"
    return Path(else_data) / MERGED_DIR_NAME / safe


# --------------------------------------------------------------------------
# 收集来源
# --------------------------------------------------------------------------

def collect_sources(book, extra_dirs: list[Path] | None = None) -> list[tuple[str, Path]]:
    """收集要合并的资料：简介 + 笔记 + 易错题（+ 额外目录）里的全部文件。

    **跳过软件自己的数据文件**（``book.json`` / ``homework.json`` / ``简介``）——
    把它们当资料插进总结里没有意义。

    ``extra_dirs`` 用于把"教材"或"其它文件"也一起合并进来（由界面选择）。
    """
    roots = [book.path / C.NOTEBOOK_FOLDER, book.path / C.ERROR_FOLDER]
    roots.extend(extra_dirs or [])
    if book.intro_path is not None and Path(book.intro_path).is_file():
        roots.insert(0, Path(book.intro_path))

    found: list[tuple[str, Path]] = []
    seen: set[Path] = set()
    #: 收集到的**文件**的名字（用来识别"某个 PDF 的抽图目录"）
    collected_files: set[str] = set()
    for root in roots:
        root = Path(root)
        if root.is_file():
            if root not in seen:
                seen.add(root)
                collected_files.add(root.name)
                found.append(("简介", root))
            continue
        if not root.is_dir():
            continue
        label = {
            C.NOTEBOOK_FOLDER: "笔记",
            C.ERROR_FOLDER: "易错题",
            C.BOOK_FOLDER: "教材",
            C.OTHERS_FOLDER: "其它文件",
        }.get(root.name, root.name)
        try:
            entries = sorted(root.rglob("*"), key=lambda p: str(p).lower())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_file():
                continue
            if entry.name in _SKIP_NAMES or entry.name.startswith("."):
                continue
            if entry in seen:
                continue
            seen.add(entry)
            # 用相对书目的路径当标题，避免同名文件分不清
            try:
                rel = entry.relative_to(book.path)
            except ValueError:
                rel = Path(entry.name)
            found.append((f"{label} · {rel.as_posix()}", entry))
            collected_files.add(entry.name)

    # ---- 去掉"某个 PDF 的抽图目录"里的重复图片 ----
    #
    # ``document_reader`` 在把图片型 PDF 转成页面图片时，会在**原文件旁边**
    # 建一个 ``<名字>_pages/`` 放那些 png。如果原 PDF 也在收集范围内，
    # 那些 png 就成了"同一个 PDF 的第二份内容" —— 实测每个 PDF 都被插入了
    # 两次（一次整份、一次逐页）。
    #
    # 规则：``X_pages/`` 里的文件，当且仅当同一目录下有 ``X.*`` 这个源文件时跳过。
    def _is_extracted_pages(rel_or_name: str) -> bool:
        return "_pages/" in rel_or_name.replace("\\", "/")

    kept: list[tuple[str, Path]] = []
    for label, path in found:
        try:
            rel = path.relative_to(book.path).as_posix()
        except ValueError:
            rel = path.name
        if _is_extracted_pages(rel):
            folder_name = Path(rel).parent.name
            owner = folder_name[: -len("_pages")]
            # 原文件在收集列表里 -> 跳过这些抽出来的图
            if any(Path(name).stem == owner for name in collected_files):
                continue
        kept.append((label, path))
    return kept


# --------------------------------------------------------------------------
# 渲染
# --------------------------------------------------------------------------

def render_pdf_pages(source: Path, target_dir: Path, prefix: str) -> MergedItem:
    """PDF → 每页一张图片（需求："每页当图片插入"）。"""
    item = MergedItem(source=source, label=source.name, kind="pdf")
    try:
        document = fitz.open(str(source))
    except Exception as exc:  # noqa: BLE001 - 单个文件失败不该中断整批
        item.error = f"打不开 PDF：{exc}"
        return item
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        for index in range(document.page_count):
            page = document.load_page(index)
            pixmap = page.get_pixmap(dpi=PAGE_DPI)
            image_path = target_dir / f"{prefix}_p{index + 1:03d}.png"
            try:
                pixmap.save(str(image_path))
            except Exception as exc:  # noqa: BLE001
                item.error = f"第 {index + 1} 页渲染失败：{exc}"
                break
            item.images.append(image_path)
            # 顺手记下这一页的文字开头 —— 只给"AI 混排"判断用，不写进总结。
            # 扫描件取不到文字也没关系（那就是空串，AI 只能按顺序对待它）。
            try:
                item.page_texts.append(page.get_text() or "")
            except Exception:  # noqa: BLE001
                item.page_texts.append("")
        if not item.images and not item.error:
            item.error = "PDF 没有可渲染的页面"
    finally:
        document.close()
    return item


def render_markdown_as_images(
    markdown_text: str, source: Path, target_dir: Path, prefix: str, *,
    equation_dir: Path | None = None, max_pages: int = 60,
) -> MergedItem:
    """把一段 Markdown 渲染成图片（用于 Word/PPT/Excel/文本）。

    做法：Markdown → HTML（复用 :mod:`gwp.services.markdown_renderer`）
    → PyMuPDF ``Story`` 排版成 PDF → 每页栅格化成 PNG。
    这样**版面**（表格、标题层级、代码块）能保留下来，
    而直接插纯文本会把表格与图表压扁成一行行字。

    ``equation_dir`` 给定时，**公式会先被渲染成图片**再排版 ——
    因为 PyMuPDF 的 Story 同样不认识 LaTeX，不处理就又是一堆 ``$\\varepsilon$``
    源码（实测确认过）。

    排版失败时**退回"把这段文字直接画成图片"** ——
    需求是"插入困难也要以图片插入"，不能因为排版器挑食就把这份资料丢掉。
    """
    item = MergedItem(source=source, label=source.name, kind="doc")
    text = (markdown_text or "").strip()
    if not text:
        item.error = "没有可合并的内容"
        return item

    try:
        html = md_render.render_document(
            text,
            md_render.RenderOptions(
                base_dir=source.parent, inline_theme=False, body_only=True,
                title=source.name, equation_dir=equation_dir,
                # **必须把图片内嵌成 data URI**：PyMuPDF 的 Story 不加载
                # file:// 引用的图片，只会显示 [image] 占位符（实测三种
                # archive 变体都不行）。data URI 是直接嵌进 HTML 的内容，
                # 不依赖文件访问，实测能正常画出来。
                resolve_images=True, inline_images=True,
            ),
        )
        css = md_render.themes.markdown_css(theme="light", for_pdf=True)
        story = fitz.Story(
            html=html, user_css=css, archive=fitz.Archive(str(source.parent))
        )
        mediabox = fitz.paper_rect("a4")
        where = mediabox + (36, 36, -36, -36)

        def _rect(rect_num, filled):        # noqa: ARG001 - PyMuPDF 约定
            # 每一页都用同一版心；返回 (媒介框, 版心, 变换)
            # 注意这个回调会收到两个参数（页码, 是否填充），
            # 少写参数会 TypeError（我第一版就是这样，导致每份文档都退回纯文本）。
            return mediabox, where, None

        # write_with_links(rectfn) 会**直接返回一个 fitz.Document**
        # （不是 PDF 字节 —— 我第一版当成字节又 fitz.open 了一次，
        # 于是每份文档都报 "bad stream" 并退回纯文本）。
        document = story.write_with_links(_rect)
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            page_count = min(document.page_count, max_pages)
            for index in range(page_count):
                page = document.load_page(index)
                pixmap = page.get_pixmap(dpi=PAGE_DPI)
                image_path = target_dir / f"{prefix}_p{index + 1:03d}.png"
                pixmap.save(str(image_path))
                item.images.append(image_path)
                # 同样的道理：记下这一页的文字，供"AI 混排"判断
                try:
                    item.page_texts.append(page.get_text() or "")
                except Exception:  # noqa: BLE001
                    item.page_texts.append("")
            if document.page_count > max_pages:
                item.note = f"（内容较长，只合并了前 {max_pages} 页）"
        finally:
            document.close()
    except Exception as exc:  # noqa: BLE001
        log.warning("Markdown 排版失败，退回纯文本渲染：%s", source, exc_info=True)
        item.error = ""
        item.note = f"（排版器不支持其中部分格式，已按纯文本合并）"
        item.images = []

    if item.images:
        return item

    # ---- 兜底：把纯文本直接画成图片（分块，避免单张过高） ----
    try:
        from PIL import Image, ImageDraw

        from gwp.services import math_render
        font = math_render._font(20)         # noqa: SLF001 - 复用同一套字体策略
        lines: list[str] = []
        for raw_line in text.splitlines():
            lines.extend(raw_line[i:i + 78] for i in range(0, max(1, len(raw_line)), 78))
            if not raw_line:
                lines.append("")
        probe = ImageDraw.Draw(Image.new("L", (1, 1)))
        line_height = 30
        per_image = 46
        target_dir.mkdir(parents=True, exist_ok=True)
        for chunk_index in range(0, len(lines), per_image):
            chunk = lines[chunk_index:chunk_index + per_image] or [""]
            width = max(
                int(probe.textlength(line, font=font)) for line in chunk
            ) + 24
            height = line_height * len(chunk) + 24
            canvas = Image.new("RGB", (max(320, width), height), (255, 255, 255))
            draw = ImageDraw.Draw(canvas)
            y = 12
            for line in chunk:
                draw.text((12, y), line, font=font, fill=(0, 0, 0))
                y += line_height
            image_path = target_dir / (
                f"{prefix}_t{chunk_index // per_image + 1:03d}.png"
            )
            canvas.save(image_path, format="PNG")
            item.images.append(image_path)
            # 这一块画的就是这些行，正好当它的"文字内容"
            item.page_texts.append("\n".join(chunk))
        if not item.images:
            item.error = "渲染后没有任何内容"
    except Exception as exc:  # noqa: BLE001
        log.warning("纯文本兜底渲染也失败：%s", source, exc_info=True)
        item.error = f"渲染失败：{exc}"
    return item


def copy_image(source: Path, target_dir: Path, prefix: str) -> MergedItem:
    """图片直接复制到合并目录（保持原样，不重新编码）。"""
    item = MergedItem(source=source, label=source.name, kind="image")
    target = target_dir / f"{prefix}{source.suffix.lower()}"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        if not target.is_file():
            target.write_bytes(source.read_bytes())
        item.images.append(target)
        # 图片没有"文字内容"；文件名本身就是给 AI 的唯一线索
        item.page_texts.append(source.stem.replace("_", " "))
    except OSError as exc:
        item.error = f"复制图片失败：{exc}"
    return item


def _prefix_for(source: Path, index: int) -> str:
    """给合并出来的图片起前缀。

    中文文件名（我们这边全是）用 ASCII 过滤后会变成一串下划线，
    所以**只保留 ASCII、并压掉连续下划线**，最后附一个短哈希，
    保证"不同文件不会撞名"且"文件名还能看"。
    """
    import hashlib

    ascii_stem = re.sub(r"[^0-9A-Za-z]+", "_", source.stem).strip("_")[:32]
    if not ascii_stem:
        ascii_stem = "doc"
    digest = hashlib.sha1(source.name.encode("utf-8")).hexdigest()[:6]
    return f"{index:03d}_{ascii_stem}_{digest}"


def equation_dir_for(else_data: Path) -> Path:
    """公式图片目录。"""
    return Path(else_data) / math_render.EQUATION_DIR_NAME


def is_text_pdf(source: Path) -> tuple[bool, str]:
    """判断一个 PDF 是"文字型"还是"图片型"。返回 ``(是文字型, 原因)``。

    依据是 :mod:`gwp.services.document_reader` 的判断（它按"每页平均字符数"
    和文字层是否可用下结论）。**不去猜**：拿不到结论时按"图片型"处理 ——
    宁可插入完整页面图片（内容一定不丢），也不要插进一堆乱码文字。
    """
    try:
        got = document_reader.extract(source)
    except Exception as exc:  # noqa: BLE001 - 判不出来就当图片型（更安全）
        return False, f"无法判断文字层（{type(exc).__name__}），按图片型处理"
    if got.kind != "pdf":
        return False, f"读取结果不是 PDF（{got.kind}），按图片型处理"
    if got.reliable and (got.markdown or "").strip():
        return True, "文字层可用"
    note = "；".join(got.notes) or "文字层不可用"
    return False, note


def merge_markdown_source(source: Path, item: MergedItem) -> MergedItem:
    """``.md`` 直接融合：把原文当文字插进去（不转图片）。

    需求："md 文档直接融合进去"。

    图片路径会被改写成**绝对路径**：summary 保存在书目目录下，
    而笔记里的图片可能是 ``./assets/x.png`` 这种相对写法 ——
    不改写的话融合之后就找不到图了。
    """
    try:
        text = source.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        item.error = f"读取失败：{exc}"
        return item
    if not text.strip():
        item.error = "文件是空的"
        return item
    item.kind = "md"
    item.images = []
    item.page_texts = []
    item.text = _rewrite_relative_images(text, source.parent)
    return item


def _rewrite_relative_images(text: str, base_dir: Path) -> str:
    """把 Markdown 里的**相对**图片路径换成绝对路径（绝对/网络的不动）。"""
    pattern = re.compile(r"(!\[[^\]]*\]\()([^)\s]+)(\))")

    def _replace(match: re.Match) -> str:
        prefix, src, suffix = match.group(1), match.group(2), match.group(3)
        if src.startswith(("http://", "https://", "data:", "file:", "/", "\\")):
            return match.group(0)
        if re.match(r"^[A-Za-z]:[\\/]", src):        # Windows 绝对路径
            return match.group(0)
        candidate = (base_dir / src)
        try:
            if candidate.is_file():
                return f"{prefix}{candidate.resolve().as_posix()}{suffix}"
        except OSError:
            return match.group(0)
        return match.group(0)

    return pattern.sub(_replace, text)


def merge_source(source: Path, target_dir: Path, *, index: int = 1,
                 equation_dir: Path | None = None) -> MergedItem:
    """合并**一份**资料：**按类型分派**插入方式。

    规则（用户明确规定）：

    ====================  ==========  ==========================================
    文件类型              插入方式    说明
    ====================  ==========  ==========================================
    图片型 PDF            图片        **每页**转成图片
    文字型 PDF            文字        文字直接插入，公式变图片
    表格 xls/xlsx         图片        版面即内容
    幻灯 ppt/pptx         图片        版面即内容
    doc/docx              文字        文字插入，公式变图片
    txt/rtf               文字        同上
    md/markdown           直接融合    本来就是 Markdown
    图片 png/jpg/...      图片        原样复制
    ====================  ==========  ==========================================

    没列到的后缀**不擅自决定** —— 交给调用方询问用户（见 :func:`describe_unknown`）。
    """
    source = Path(source)
    prefix = _prefix_for(source, index)
    suffix = source.suffix.lower()
    item_base = MergedItem(source=source, label=source.name)

    if not source.is_file():
        item_base.error = "文件不存在"
        return item_base
    if suffix in _IMAGE_SUFFIXES:
        return copy_image(source, target_dir, prefix)

    # ---- PDF：先分"文字型 / 图片型" ----
    if suffix == ".pdf":
        text_type, reason = is_text_pdf(source)
        if not text_type:
            item = render_pdf_pages(source, target_dir, prefix)
            item.note = reason
            return item
        # 文字型：插文字（公式会在最终渲染时变成图片）
        try:
            extracted = document_reader.extract(source)
        except Exception as exc:  # noqa: BLE001
            item_base.error = f"读取失败：{exc}"
            return item_base
        item_base.kind = "pdf-text"
        item_base.text = extracted.markdown or ""
        item_base.note = "文字型 PDF，已插入文字（公式显示为图片）"
        if not item_base.text.strip():
            # 判成文字型却抽不出字：退回图片，别让这份资料消失
            item = render_pdf_pages(source, target_dir, prefix)
            item.note = "文字层读出为空，已改为插入页面图片"
            return item
        return item_base

    handling = _SUFFIX_HANDLING.get(suffix)

    # ---- Markdown：直接融合 ----
    if handling == HANDLE_MERGE:
        return merge_markdown_source(source, item_base)

    # ---- 图片型（表格 / 幻灯）：转成图片 ----
    if handling == HANDLE_IMAGES:
        try:
            extracted = document_reader.extract(source)
        except Exception as exc:  # noqa: BLE001
            item_base.error = f"读取失败：{exc}"
            return item_base
        if extracted.is_empty:
            item_base.error = extracted.error or "没有可提取的内容"
            return item_base
        item = render_markdown_as_images(
            extracted.markdown, source, target_dir, prefix,
            equation_dir=equation_dir,
        )
        if extracted.notes:
            item.note = "；".join(extracted.notes)[:200]
        return item

    # ---- 文字型（doc/docx/txt）：插文字 ----
    if handling == HANDLE_TEXT:
        try:
            extracted = document_reader.extract(source)
        except Exception as exc:  # noqa: BLE001
            item_base.error = f"读取失败：{exc}"
            return item_base
        if extracted.is_empty:
            item_base.error = extracted.error or "没有可提取的内容"
            return item_base
        item_base.kind = "doc-text"
        item_base.text = extracted.markdown or ""
        # docx 里的插图要一起带过来（否则讲义里的图会消失）
        item_base.images = []
        if extracted.image_files:
            for extra in extracted.image_files:
                item_base.images.append(extra)
        item_base.note = "；".join(extracted.notes)[:200] if extracted.notes else ""
        item_base.images = []          # 内嵌图片已写在 text 的 Markdown 里
        return item_base

    # ---- 没规定的类型：不擅自决定 ----
    item_base.kind = "unknown"
    item_base.text = ""
    item_base.note = (
        f"未规定 {suffix or '无后缀'} 这类文件的处理方式，"
        "已在末尾列出、未插入内容"
    )
    item_base.skipped = True
    return item_base


#: 需要用户决定处理方式的类型（在确认框里列出来问）
def describe_unknown(sources: list[tuple[str, Path]]) -> list[str]:
    """列出"没规定处理方式"的文件后缀，供界面询问用户。"""
    known = set(_SUFFIX_HANDLING) | _IMAGE_SUFFIXES | {".pdf"}
    unknown: list[str] = []
    for _label, path in sources:
        suffix = Path(path).suffix.lower()
        if suffix not in known and suffix not in unknown:
            unknown.append(suffix or "（无后缀）")
    return unknown


def run_merge(book, else_data: Path, sources: list[tuple[str, Path]],
              *, on_progress=None) -> MergeReport:
    """把 ``sources`` 全部合并到图片目录。返回报告。

    ``on_progress(当前序号, 总数, 文件说明)`` 用于显示进度。
    """
    target_dir = merge_dir(else_data, book.name)
    equations = equation_dir_for(else_data)
    report = MergeReport(output_dir=target_dir)
    total = len(sources)
    for position, (label, path) in enumerate(sources, start=1):
        if on_progress is not None:
            try:
                on_progress(position, total, path.name)
            except Exception:  # noqa: BLE001 - 进度回调出错不该中断
                log.debug("合并进度回调失败", exc_info=True)
        item = merge_source(path, target_dir, index=position,
                            equation_dir=equations)
        item.label = label
        report.items.append(item)
    return report


# --------------------------------------------------------------------------
# 写入总结
# --------------------------------------------------------------------------

# --------------------------------------------------------------------------
# AI 混排：让模型决定图片的插入顺序
# --------------------------------------------------------------------------

#: 混排时给 AI 看的"这一页讲什么"取多少字符。
#:
#: 只取开头：目的是**判断主题**，不是理解全文。取得太多会让请求变贵变慢，
#: 而对"这页属于哪一节"的判断几乎没有帮助。
PAGE_PREVIEW_CHARS = 160

#: 一次混排最多让 AI 重排多少页（超过就只按原顺序，避免超出上下文）
MAX_MIX_PAGES = 600

MIX_SYSTEM_PROMPT = """你是「长庚」，正在帮助整理一份学习资料合集的**页序**。

用户会给你一份「页清单」：每一页有一个编号、来自哪个文件夹/文件、以及该页开头的文字。

你的任务：**重新排列这些页的先后顺序**，让同一知识点的内容聚在一起，
使这份合集读起来是一条连贯的学习主线。

规则：
1. 目标是**混排**：不要把同一个文件的页全部堆在一起，
   除非它们的主题确实连续。同一知识点下，不同文件夹的页应当相邻。
2. **不能增删、不能重复、不能改编号** —— 你只输出顺序。
3. 每页都必须出现在结果里，一次且仅一次。
4. 如果没有足够信息判断（例如整页没有文字），就把它们按原相对顺序放在最后。

**只输出 JSON**，不要任何解释、不要代码块围栏。格式：

{"order": [3, 1, 2, 7, ...]}

其中数字是页编号，按你建议的阅读顺序排列。"""


@dataclass
class Page:
    """混排的最小单位：一张要插入的图片。"""

    index: int                                  # 全局编号（从 1 开始，给 AI 看的）
    item_i: int                                 # 属于第几份资料
    page_i: int                                 # 是那份资料的第几页
    label: str = ""
    preview: str = ""

    @property
    def image_key(self) -> tuple[int, int]:
        return (self.item_i, self.page_i)


def flatten_pages(report: MergeReport) -> list[Page]:
    """把所有资料的所有页摊平成一个线性清单（按当前顺序编号）。"""
    pages: list[Page] = []
    number = 0
    for item_i, item in enumerate(report.items):
        if not item.ok:
            continue
        item.page_texts = list(item.page_texts) + [""] * (
            len(item.images) - len(item.page_texts)
        )
        for page_i in range(len(item.images)):
            number += 1
            pages.append(Page(
                index=number, item_i=item_i, page_i=page_i,
                label=item.label,
                preview=item.preview_of(page_i, PAGE_PREVIEW_CHARS),
            ))
    return pages


def catalog_for_ai(pages: list[Page]) -> str:
    """把页清单写成给 AI 看的紧凑文本。"""
    lines = [f"共 {len(pages)} 页。", ""]
    for page in pages:
        preview = page.preview or "（这一页没有可提取的文字）"
        lines.append(f"{page.index}. [{page.label}] {preview}")
    return "\n".join(lines)


def parse_order(reply: str, pages: list[Page]) -> tuple[list[Page] | None, str]:
    """从 AI 的回复里解析出重排顺序。

    返回 ``(有序页清单, 错误说明)``。**校验很严**：编号必须不多不少、
    不重不漏 —— 因为输出错一份就会丢页或重复页，那比不混排严重得多。
    校验不过就返回 ``(None, 原因)``，调用方退回原顺序。
    """
    from gwp.data_manager.wordbook import extract_json

    data = extract_json(reply or "")
    if not isinstance(data, dict):
        return None, "AI 没有返回可解析的 JSON"
    order = data.get("order")
    if not isinstance(order, list):
        return None, "AI 返回的 JSON 里没有 order 列表"

    valid = {page.index for page in pages}
    seen: list[int] = []
    for value in order:
        try:
            number = int(value)
        except (TypeError, ValueError):
            continue
        seen.append(number)

    missing = valid - set(seen)
    unknown = set(seen) - valid
    if unknown:
        return None, f"AI 给出了不存在的页编号：{sorted(unknown)[:5]}"
    if missing:
        return None, f"AI 漏掉了 {len(missing)} 页（例如 {sorted(missing)[:5]}）"
    if len(seen) != len(valid):
        return None, "AI 返回的页编号有重复"

    by_index = {page.index: page for page in pages}
    return [by_index[number] for number in seen], ""


def apply_order(report: MergeReport, ordered: list[Page]) -> MergeReport:
    """按混排结果重排 ``report`` 里每份资料的图片顺序。

    **不改变图片文件，也不改变哪些页被插入** —— 只是把顺序换掉。
    某份资料的页在整体里是"穿插"出现的，所以重排之后它自己的图片列表
    也会变成那个穿插后的相对顺序，写 summary 时按新顺序输出即可。
    """
    buckets: dict[int, list[Path]] = {i: [] for i in range(len(report.items))}
    for page in ordered:
        item = report.items[page.item_i]
        if page.page_i < len(item.images):
            buckets[page.item_i].append(item.images[page.page_i])
    for item_i, images in buckets.items():
        if images:
            report.items[item_i].images = images
    # 混排之后"每份资料一个标题"的写法已经表达不了穿插，
    # 所以记下真正的整体顺序，交给 build_section 用。
    report.mixed = True
    report.ordered_pages = ordered
    return report


def mix_pages(ai_manager, report: MergeReport, *, on_progress=None,
              should_cancel=None) -> tuple[bool, str]:
    """让 AI 决定页序。返回 ``(是否成功, 说明)``。

    失败**不算错误**：退回原顺序继续合并即可 —— 混排是锦上添花，
    不能因为它没成就让整个总结生成失败。
    """
    pages = flatten_pages(report)
    if len(pages) < 2:
        return False, "只有一页，不需要混排"
    if len(pages) > MAX_MIX_PAGES:
        return False, f"页数太多（{len(pages)} 页 > {MAX_MIX_PAGES}），已按原顺序"

    from gwp.ai.base import ChatMessage

    if on_progress is not None:
        on_progress(f"正在让 AI 安排 {len(pages)} 页的顺序……")
    messages = [
        ChatMessage(role="system", content=MIX_SYSTEM_PROMPT),
        ChatMessage(role="user", content=catalog_for_ai(pages)),
    ]
    try:
        reply, provider = ai_manager.chat_with_fallback(
            messages, None, None, None, should_cancel
        )
    except Exception as exc:  # noqa: BLE001 - 混排失败不影响合并
        log.warning("AI 混排请求失败", exc_info=True)
        return False, f"AI 不可用（{type(exc).__name__}），已按原顺序"

    ordered, reason = parse_order(reply, pages)
    if ordered is None:
        log.info("AI 混排结果没通过校验：%s", reason)
        return False, f"{reason}，已按原顺序"
    apply_order(report, ordered)
    return True, f"AI（{provider}）已重排 {len(pages)} 页"


def build_section(report: MergeReport, else_data: Path, *, note: str = "") -> str:
    """把合并结果拼成一段 Markdown（要追加到 summary 末尾的内容）。

    ``report.mixed`` 为真时改用**混排写法**：资料被打散了，
    所以不能再"一份资料一个小节"，而是按混排后的整体页序逐页输出，
    在来源发生变化时才插入一行小标题说明这一页来自哪里。
    """
    lines: list[str] = [MERGE_MARKER, "", f"## {MERGE_HEADING}", ""]
    if note:
        lines += [note, ""]
    lines += [
        f"本节的图片存放在：`{_rel(report.output_dir, else_data)}`"
        "（相对 `else data` 目录）。",
        "",
    ]
    ok_items = report.ok_items
    if not ok_items:
        lines += ["> 没有任何资料被合并进来。", ""]
        return _with_failed(lines, report)

    if report.mixed and report.ordered_pages:
        return _with_failed(_mixed_lines(report, lines), report)

    for item in ok_items:
        lines.append(f"### {item.label}")
        lines.append("")
        if item.is_text:
            # 文字型：原样插入文字。公式会在最终渲染时变成图片
            # （见 markdown_renderer.substitute_equations）。
            meta = [f"文字 {len(item.text)} 字符"]
            if item.note:
                meta.append(item.note)
            lines += [f"*（{'；'.join(meta)}）*", ""]
            lines.append(item.text.strip())
            lines += ["", ""]
            continue
        meta = [f"共 {len(item.images)} 页/张"]
        if item.note:
            meta.append(item.note)
        lines += [f"*（{'；'.join(meta)}）*", ""]
        # **连续图片之间不留空行**：每张图之间插空行的话，
        # Markdown 会把它们拆成多个独立段落，渲染时每段各有上下外边距，
        # 于是图与图之间出现明显缝隙（需求："图片之间不要有间隙"）。
        # 连着写就让它们落在同一个段落里，由 CSS 再去掉内部间距。
        for image in item.images:
            # 用**绝对路径**引用：summary 在书目下，而图片在 else data 下，
            # 相对路径会算不准（且移动书目后就失效）。
            lines.append(f"![{item.label}]({image.as_posix()})")
        lines += ["", ""]
    return _with_failed(lines, report)


def _mixed_lines(report: MergeReport, lines: list[str]) -> list[str]:
    """混排后的正文：**图片按新页序、文字型资料按原位置**。

    为什么要分成两段来处理：混排排的是"页"，而文字型资料（文字 PDF / docx /
    Markdown）**没有页**。早先的写法是"只要有文字型资料就整个放弃混排" ——
    那等于让最常见的组合（md 笔记 + 扫描讲义）永远用不上这个功能。

    现在的做法：先把**文字型资料**完整贴着（它们的顺序不动，也不需要动），
    再把**图片**按 AI 给的页序输出。两边内容都不丢。
    """
    text_items = [item for item in report.items if item.ok and item.is_text]
    if text_items:
        for item in text_items:
            lines.append(f"### {item.label}")
            lines.append("")
            lines.append(f"*（文字 {len(item.text)} 字符）*")
            lines.append("")
            lines.append(item.text.strip())
            lines += ["", ""]
        lines.append("> 以上是文字型资料；**以下图片由 AI 按主题重排过页序**，"
                     "所以同一个文件的内容可能分散在几处。")
        lines.append("")
    else:
        lines.append("> 本节由 AI 按内容主题重排过页序，"
                     "所以同一个文件的内容可能分散在几处。")
        lines.append("")

    current_label = ""
    for page in report.ordered_pages:
        item = report.items[page.item_i]
        if page.page_i >= len(item.images):
            continue
        if page.label != current_label:
            if current_label:
                lines.append("")
            lines.append(f"### {page.label}")
            lines.append("")
            current_label = page.label
        image = item.images[page.page_i]
        lines.append(f"![{page.label}]({image.as_posix()})")
    if report.ordered_pages:
        lines.append("")
    return lines


def _with_failed(lines: list[str], report: MergeReport) -> str:
    # 注意：**这里不加结束标记**。资料段由 ``compose_summary`` /
    # ``append_to_summary`` 统一收尾 —— 三处都加就会写出两个结束标记
    # （实测把"重复生成"的断言弄炸了）。
    failed = report.failed
    if failed:
        lines += ["### 未能插入的资料（保留原文件）", ""]
        for item in failed:
            reason = item.error or item.note or "未知原因"
            tag = "未规定处理方式" if item.skipped else "失败"
            lines.append(f"- `{item.label}`（{tag}）：{reason}")
        lines += [""]
    return "\n".join(lines)


def compose_summary(head_lines: list[str], section: str,
                    tail: str = "") -> str:
    """拼出完整 summary：**前言 + 资料 + 末尾提示**。

    ``tail`` 固定放在文件最末尾（需求："可以在文档末尾补充tips"）。
    资料段的结束标记由这里补上 —— 调用方只管给 ``section`` 正文。
    """
    parts = [line for line in head_lines if line is not None]
    text = "\n".join(parts).rstrip() + "\n\n"
    text += section.strip() + "\n\n" + MERGE_END_MARKER + "\n"
    if tail:
        text += "\n" + tail.strip() + "\n"
    return text


def _rel(path: Path | None, base: Path) -> str:
    if path is None:
        return "（未知）"
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def append_to_summary(summary_text: str, section: str) -> str:
    """把资料小节替换进已有 summary（保留末尾的提示）。

    **重复生成不会越插越多**：上一次生成的那一段（两个标记之间）会被替换掉，
    而标记之后的"使用提示"保持不动。
    """
    text = summary_text or ""
    start = text.find(MERGE_MARKER)
    end = text.find(MERGE_END_MARKER)
    body = section.strip()
    if MERGE_END_MARKER not in body:
        body += "\n\n" + MERGE_END_MARKER
    if start >= 0 and end > start:
        tail = text[end + len(MERGE_END_MARKER):].lstrip("\n")
        result = text[:start] + body + "\n\n" + tail
    else:
        # 没有标记（老文件或第一次）：整段追加到末尾。
        # 注意这里补的换行数要和上面那条分支**完全一致** ——
        # 否则"第一次"和"第二次"产出的文件会差一个字符，
        # 幂等断言就会挂（实测差 1 个字符）。
        result = text.rstrip() + "\n\n" + body + "\n\n"
    return result.rstrip() + "\n"


__all__ = [
    "MERGE_HEADING",
    "MERGE_MARKER",
    "MERGED_DIR_NAME",
    "MergeReport",
    "MergedItem",
    "append_to_summary",
    "build_section",
    "collect_sources",
    "merge_dir",
    "merge_source",
    "render_markdown_as_images",
    "render_pdf_pages",
    "run_merge",
]
