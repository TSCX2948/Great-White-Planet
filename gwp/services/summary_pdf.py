"""把一个书目的全部资料合并成**一个 PDF**。

这是"AI 总结"的新实现路线
--------------------------
需求：

> AI总结实现方法：将所有待总结文件转化并合并为一个pdf文档，
> 结束后删除中间可能产生的废弃文档和数据

所以「生成总结」现在的产物是 **``<书目>_summary.pdf``**（不再是 Markdown）。

每一份资料都变成**页面图片**再写进 PDF —— 包括文字型 PDF 与 Word。
为什么连"能抽文字"的也走图片：

* 需求要的就是"合并成一个 PDF"，让阅读体验统一；
* 文字型资料里的**公式**本来也得渲染成图片（LaTeX/Word 公式），
  一半文字一半图片拼出来的 PDF 反而更碎；
* 一条路径比两条路径少一半出错机会（这个项目已经因为"两条路"栽过几次）。

「不产生多余的中间数据」怎么保证
--------------------------------
方法不是"生成完再去删干净"（那样一定会漏），而是：

1. **全部内容先构建到一个临时 PDF**（``*.building.pdf``），
   中途失败就把它删掉 —— **目标文件一个字节都不会动**；
2. 只有全部成功，才用 ``os.replace`` 原子替换目标；
3. 构建期用到的页面图片、公式图片集中放在一个**本次专用**的临时目录里，
   结束时整个删掉。

这样"不留中间物"是**结构上的保证**，而不是靠一份"记得删这些"的清单。
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import fitz

from gwp.core import constants as C
from gwp.services import document_reader
from gwp.services import source_merge

log = logging.getLogger(__name__)

#: 构建中途用的临时文件后缀（成功后会消失）
BUILDING_SUFFIX = ".building.pdf"

#: 页面图片的渲染分辨率
PAGE_DPI = 110

#: 一个临时工作目录的前缀（整个目录结束时删除）
WORK_PREFIX = "gwp_summary_"

#: 给 AI 当"这份资料讲什么"的线索保留多少字符
HINT_CHARS = 1200


@dataclass
class ChapterPlan:
    """一份资料转成 PDF 页面的计划。"""

    label: str
    source: Path
    kind: str = "text"
    #: 该资料自己的页面图片（已经渲染好、落在工作目录里）
    images: list[Path] = field(default_factory=list)
    #: 失败原因（非空表示这份没进去）
    error: str = ""
    note: str = ""
    #: 提取到的正文（只留开头一小段就够）。
    #:
    #: **为什么要存下来**：转页面时已经读过一次正文，
    #: 生成「长庚知道」补充又要知道"这份资料讲什么"。
    #: 不存的话同一个 PDF 会被**提取两次** —— 扫描件还好，
    #: 几百页的文字版 PDF 就是白等一场。
    hint_text: str = ""


@dataclass
class BuildResult:
    """一次构建的结果。"""

    pdf_path: Path | None = None
    chapters: list[ChapterPlan] = field(default_factory=list)
    page_count: int = 0
    #: 其中"资料页"有多少、末尾"长庚知道"补充页有多少
    content_pages: int = 0
    supplement_pages: int = 0
    size_bytes: int = 0
    #: 混排是否成功，以及说明（未混排时为空串）
    mixed: bool = False
    mix_message: str = ""
    #: 「长庚知道」补充的说明（未做或失败时说明原因）
    supplement_message: str = ""

    @property
    def ok(self) -> bool:
        return self.pdf_path is not None and self.pdf_path.is_file()

    @property
    def failed(self) -> list[ChapterPlan]:
        return [c for c in self.chapters if c.error]

    @property
    def ok_chapters(self) -> list[ChapterPlan]:
        return [c for c in self.chapters if c.images and not c.error]


def summary_pdf_path(book) -> Path:
    """书目的 summary PDF 路径（``<书名>_summary.pdf``）。

    注意用 ``SUMMARY_PDF_SUFFIX`` 而不是 ``SUMMARY_SUFFIX + ".pdf"`` ——
    后者会拼出 ``<书名>_summary.md.pdf``（实测踩过）。
    """
    return Path(book.path) / f"{book.name}{C.SUMMARY_PDF_SUFFIX}"


def _render_pdf_source(source: Path, work_dir: Path, index: int) -> ChapterPlan:
    """PDF -> 逐页图片（图片型与文字型都走这条：统一版面、公式也在里面）。

    顺手把文字层的前一小段留下来当"这份资料讲什么"的线索 ——
    省掉后面为了写「长庚知道」补充而**再提取一次**的开销。
    """
    plan = ChapterPlan(label=source.name, source=source, kind="pdf")
    try:
        document = fitz.open(str(source))
    except Exception as exc:  # noqa: BLE001
        plan.error = f"打不开 PDF：{exc}"
        return plan
    try:
        # 文字层线索（扫描件取不到，就算了 —— 用文件名兜底）
        try:
            pieces: list[str] = []
            for page_index in range(min(document.page_count, 6)):
                pieces.append(document.load_page(page_index).get_text())
                if sum(len(p) for p in pieces) >= HINT_CHARS:
                    break
            plan.hint_text = " ".join(" ".join(pieces).split())[:HINT_CHARS]
        except Exception:  # noqa: BLE001 - 只是线索，失败不影响主体
            log.debug("取 PDF 文字线索失败：%s", source, exc_info=True)

        out = work_dir / f"{index:03d}_pdf"
        out.mkdir(parents=True, exist_ok=True)
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            target = out / f"p{page_index + 1:04d}.png"
            page.get_pixmap(dpi=PAGE_DPI).save(str(target))
            plan.images.append(target)
        if not plan.images:
            plan.error = "PDF 没有可渲染的页面"
    except Exception as exc:  # noqa: BLE001
        plan.error = f"渲染 PDF 失败：{exc}"
    finally:
        document.close()
    return plan


def _render_document_source(source: Path, work_dir: Path, index: int,
                            equation_dir: Path) -> ChapterPlan:
    """Word / PPT / Excel / 文本 -> 先抽成 Markdown，再排版成图片页面。"""
    plan = ChapterPlan(label=source.name, source=source)
    try:
        extracted = document_reader.extract(source)
    except Exception as exc:  # noqa: BLE001
        plan.error = f"读取失败：{exc}"
        return plan
    plan.kind = extracted.kind
    if extracted.is_empty:
        plan.error = extracted.error or "没有可提取的内容"
        return plan
    plan.hint_text = " ".join((extracted.markdown or "").split())[:HINT_CHARS]
    if extracted.notes:
        plan.note = "；".join(extracted.notes)[:200]

    out = work_dir / f"{index:03d}_doc"
    item = source_merge.render_markdown_as_images(
        extracted.markdown, source, out, f"{index:03d}",
        equation_dir=equation_dir,
    )
    if item.error:
        plan.error = item.error
        return plan
    plan.images = list(item.images)
    return plan


def _copy_image_source(source: Path, work_dir: Path, index: int) -> ChapterPlan:
    """图片 -> 原样复制（不重新编码）。"""
    plan = ChapterPlan(label=source.name, source=source, kind="image")
    out = work_dir / f"{index:03d}_img"
    try:
        out.mkdir(parents=True, exist_ok=True)
        target = out / source.name
        shutil.copy2(source, target)
        plan.images = [target]
    except OSError as exc:
        plan.error = f"复制图片失败：{exc}"
    return plan


def plan_chapter(label: str, source: Path, work_dir: Path, index: int,
                 equation_dir: Path) -> ChapterPlan:
    """按类型把一份资料转成"页面图片"。**Markdown 也转成图片**。

    为什么 Markdown 这次不走"融合文字"：产物是一个 PDF，
    而 PDF 里的文字要能**一模一样地呈现**原 Markdown 的排版（标题、表格、公式），
    我们现有的 Markdown→PDF 排版（PyMuPDF Story）本来就是干这个的。
    所以所有类型最终都归到"页面图片"这一条路上 —— 只有一条路就不会有
    "两种资料拼起来版面不一致"的问题。
    """
    source = Path(source)
    plan = ChapterPlan(label=label, source=source)
    if not source.is_file():
        plan.error = "文件不存在"
        return plan
    suffix = source.suffix.lower()
    if suffix in set(C.IMAGE_EXTENSIONS):
        result = _copy_image_source(source, work_dir, index)
    elif suffix == ".pdf":
        result = _render_pdf_source(source, work_dir, index)
    elif suffix in (".md", ".markdown", ".txt"):
        # 这类本来就是文本：直接走"排版成图片"（保留标题/表格层次）
        plan.kind = "text"
        try:
            text = source.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            plan.error = f"读取失败：{exc}"
            return plan
        plan.hint_text = " ".join(text.split())[:HINT_CHARS]
        out = work_dir / f"{index:03d}_md"
        item = source_merge.render_markdown_as_images(
            text, source, out, f"{index:03d}", equation_dir=equation_dir
        )
        plan.error = item.error
        if item.note:
            plan.note = item.note
        plan.images = list(item.images)
        return plan
    else:
        result = _render_document_source(source, work_dir, index, equation_dir)
    result.label = label
    return result


def flatten_chapter_images(chapters: list[ChapterPlan]) -> list[tuple[int, int, Path]]:
    """把各章节的页面图片摊平：``[(章节下标, 页下标, 图片路径), ...]``。"""
    flat: list[tuple[int, int, Path]] = []
    for chapter_index, chapter in enumerate(chapters):
        if chapter.error:
            continue
        for page_index, image in enumerate(chapter.images):
            flat.append((chapter_index, page_index, image))
    return flat


def mix_chapter_images(ai_manager, chapters: list[ChapterPlan], *,
                       on_progress=None) -> tuple[bool, str]:
    """让 AI 决定页序（可选步骤）。返回 ``(是否成功, 说明)``。

    需求（早先提过）："AI可以根据自己的理解改变图片插入顺序，
    实现不同文件夹内容，的混排插入"。

    这里的实现方式：把每份资料的**第一页**的开头一小段文字作为"这页讲什么"
    的线索交给 AI。为什么只给第一页的文字：

    * 目的是判断主题，不是理解全文；
    * 一次请求里塞进成百上千页的全文会让请求又贵又慢，
      而对"该排在哪"几乎没有额外帮助。

    **校验很严**：AI 必须给出不多不少、不重不漏的全集编号，
    少一个就整条拒绝、退回原顺序 —— 排错一份就是丢页。
    失败**不算错误**：混排只是锦上添花。

    ``on_progress`` 的签名是 ``(message, percent, detail)``，
    与界面的 ``BusyDialog.report`` 一致（**不要写成单参数**，
    那是踩过的坑：一旦混排被触发就 TypeError）。
    """
    flat = flatten_chapter_images(chapters)
    if len(flat) < 2:
        return False, "只有一页，不需要混排"
    if len(flat) > source_merge.MAX_MIX_PAGES:
        return False, (f"页数太多（{len(flat)} 页 > "
                       f"{source_merge.MAX_MIX_PAGES}），已按原顺序")

    from gwp.ai.base import ChatMessage

    if on_progress is not None:
        on_progress(f"正在让 AI 安排 {len(flat)} 页的顺序……", -1, "")
    lines = [f"共 {len(flat)} 页。", ""]
    for number, (chapter_index, page_index, _image) in enumerate(flat, start=1):
        chapter = chapters[chapter_index]
        preview = ""
        if page_index == 0:
            preview = _page_preview(chapter)
        lines.append(f"{number}. [{chapter.label}] "
                     f"{preview or '（这一页没有可提取的文字）'}")
    messages = [
        ChatMessage(role="system", content=source_merge.MIX_SYSTEM_PROMPT),
        ChatMessage(role="user", content="\n".join(lines)),
    ]
    try:
        reply, provider = ai_manager.chat_with_fallback(
            messages, None, None, None, None
        )
    except Exception as exc:  # noqa: BLE001 - 混排失败不影响合并
        log.warning("AI 混排请求失败", exc_info=True)
        return False, f"AI 不可用（{type(exc).__name__}），已按原顺序"

    ordered, reason = _parse_chapter_order(reply, len(flat))
    if ordered is None:
        log.info("AI 混排结果没通过校验：%s", reason)
        return False, f"{reason}，已按原顺序"

    # 按新页序重排（只动顺序，不增不减）
    buckets: dict[int, list[Path]] = {i: [] for i in range(len(chapters))}
    for number in ordered:
        chapter_index, page_index, image = flat[number - 1]
        buckets[chapter_index].append(image)
    for chapter_index, images in buckets.items():
        if images:
            chapters[chapter_index].images = images
    return True, f"AI（{provider}）已重排 {len(flat)} 页"


def _page_preview(chapter: ChapterPlan) -> str:
    """取一份资料"第一页讲什么"的线索。

    文字型资料用正文开头；图片型资料没有文字，就用文件名
    （文件名往往就是章节名，比空着有用）。
    """
    source = chapter.source
    suffix = source.suffix.lower()
    if suffix in (".md", ".markdown", ".txt"):
        try:
            text = source.read_text(encoding="utf-8", errors="replace")
            return " ".join(text.split())[: source_merge.PAGE_PREVIEW_CHARS]
        except OSError:
            return source.stem
    return source.stem


def _parse_chapter_order(reply: str, total: int) -> tuple[list[int] | None, str]:
    """解析并**严格校验** AI 给的页序。"""
    from gwp.data_manager.wordbook import extract_json

    data = extract_json(reply or "")
    if not isinstance(data, dict):
        return None, "AI 没有返回可解析的 JSON"
    order = data.get("order")
    if not isinstance(order, list):
        return None, "AI 返回的 JSON 里没有 order 列表"
    numbers: list[int] = []
    for value in order:
        try:
            numbers.append(int(value))
        except (TypeError, ValueError):
            continue
    valid = set(range(1, total + 1))
    missing = valid - set(numbers)
    unknown = set(numbers) - valid
    if unknown:
        return None, f"AI 给出了不存在的页编号：{sorted(unknown)[:5]}"
    if missing:
        return None, f"AI 漏掉了 {len(missing)} 页（例如 {sorted(missing)[:5]}）"
    if len(numbers) != total:
        return None, "AI 返回的页编号有重复"
    return numbers, ""


def build_summary_pdf(book, sources: list[tuple[str, Path]], *,
                      on_progress=None, mix_progress=None, ai_manager=None,
                      want_mix: bool = False, want_supplement: bool = False,
                      theme: str = "light") -> BuildResult:
    """把资料合并成一个 PDF（原子替换目标文件）。

    ``sources`` 是 ``[(标签, 路径), ...]``，由
    :func:`gwp.services.source_merge.collect_sources` 给出。

    * ``want_mix=True`` 时会让 ``ai_manager`` 决定页序（可选步骤）；
    * ``want_supplement=True`` 时会在**最末尾**追加「长庚知道」补充页
      （需求："可以在文档最后加入一些关于知识点的你的补充"）。

    **不留中间物**：所有页面图片与公式图片都放在一个本次专用的临时目录里，
    结束时（成功或失败）整个删掉；目标 PDF 只在全部成功后才被替换。
    """
    result = BuildResult()
    target = summary_pdf_path(book)
    work_dir = Path(tempfile.mkdtemp(prefix=WORK_PREFIX))
    equation_dir = work_dir / "equations"
    building = target.with_name(target.name + BUILDING_SUFFIX)
    try:
        # ---- 1) 逐份资料转成页面图片 ----
        total = len(sources)
        for index, (label, path) in enumerate(sources, start=1):
            if on_progress is not None:
                try:
                    on_progress(index, total, Path(path).name)
                except Exception:  # noqa: BLE001
                    log.debug("进度回调失败", exc_info=True)
            plan = plan_chapter(label, path, work_dir, index, equation_dir)
            result.chapters.append(plan)
            if plan.error:
                log.warning("资料未能转成页面：%s -> %s", path, plan.error)

        usable = [c for c in result.chapters if c.images and not c.error]
        if not usable:
            return result            # 一份都没成：目标文件保持原样

        # ---- 1.5) 可选：让 AI 决定页序 ----
        if want_mix and ai_manager is not None:
            ok, message = mix_chapter_images(ai_manager, usable,
                                             on_progress=mix_progress)
            result.mix_message = message
            result.mixed = ok
            log.info("混排结果：%s", message)

        # ---- 1.6) 可选：AI 知识点补充（放在最末尾）----
        supplement_pdf: Path | None = None
        if want_supplement and ai_manager is not None:
            supplement_pdf = _make_supplement_pdf(
                ai_manager, usable, work_dir, result,
                base_dir=Path(book.path), theme=theme,
                on_progress=mix_progress,
            )

        # ---- 2) 写进临时 PDF ----
        doc = fitz.open()
        try:
            for chapter in usable:
                for image in chapter.images:
                    page = doc.new_page(width=595, height=842)
                    page.insert_image(
                        fitz.Rect(0, 0, 595, 842), filename=str(image)
                    )
            result.content_pages = doc.page_count
            # 补充页接在**最后**（需求："在文档最后加入"）
            if supplement_pdf is not None and supplement_pdf.is_file():
                with fitz.open(str(supplement_pdf)) as extra:
                    doc.insert_pdf(extra)
                    result.supplement_pages = extra.page_count
            result.page_count = doc.page_count
            doc.save(str(building), garbage=4, deflate=True)
        finally:
            doc.close()

        if not building.is_file() or building.stat().st_size == 0:
            _quiet_unlink(building)
            return result

        # ---- 3) 替换目标（这一步之前，目标文件完全没被碰过）----
        _install_building(building, target)
        result.pdf_path = target
        result.size_bytes = target.stat().st_size
        log.info("summary PDF 已生成：%s（正文 %d 页 + 补充 %d 页，%.1f MB）",
                 target, result.content_pages, result.supplement_pages,
                 result.size_bytes / 1024 / 1024)
        return result
    finally:
        # ---- 4) 无论成败，中间物全部清掉 ----
        _quiet_rmtree(work_dir)
        _quiet_unlink(building)


def _make_supplement_pdf(ai_manager, chapters, work_dir: Path,
                         result: BuildResult, *, base_dir: Path,
                         theme: str, on_progress=None) -> Path | None:
    """生成「长庚知道」补充 PDF。失败**不算错误**，只是少一段补充。"""
    from gwp.services import knowledge_supplement

    if on_progress is not None:
        try:
            on_progress(f"正在让 AI 写「{knowledge_supplement.LABEL}」补充……",
                        -1, "")
        except Exception:  # noqa: BLE001
            log.debug("进度回调失败", exc_info=True)
    try:
        text, message = knowledge_supplement.generate_supplement(ai_manager,
                                                                 chapters)
    except Exception as exc:  # noqa: BLE001 - 补充失败不该让总结失败
        log.warning("生成知识点补充失败", exc_info=True)
        result.supplement_message = f"补充失败（{type(exc).__name__}），已跳过"
        return None
    result.supplement_message = message
    if not text:
        return None
    output = work_dir / "supplement.pdf"
    try:
        knowledge_supplement.render_supplement_pdf(
            text, output, base_dir=base_dir, theme=theme
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("补充内容排版失败", exc_info=True)
        result.supplement_message = f"补充排版失败（{type(exc).__name__}），已跳过"
        return None
    return output if output.is_file() else None


def _install_building(building: Path, target: Path) -> None:
    """把构建好的 PDF 放到目标位置。失败会**重试几次**。

    为什么要重试：目标文件经常**正被占用** ——

    * 用户用阅读器开着它（很正常：刚生成的总结当然要看）；
    * 我们自己生成后按 ``summary.auto_open_after_generate`` 打开了它。

    实测（在测试里连续生成两次）会报 ``PermissionError [WinError 5]``
    或 ``WinError 32``。这类占用**往往只持续几百毫秒**（阅读器在读盘、
    或者进程刚收到关闭请求），重试几次通常就过了。

    实在替换不了才抛错 —— 这时目标文件仍然是**原样**的，不会留下半成品；
    错误信息里明确告诉用户"先关掉正在打开它的阅读器"。
    """
    last_error: OSError | None = None
    # 多试几轮、每轮之间退让一下：阅读器可能是"打开后一直占着"的，
    # 也可能是"刚收到关闭请求、正在释放"。前者等多久都没用（最终报错让用户处理），
    # 后者几百毫秒就过了。
    for attempt in range(6):
        for name, action in (("replace", os.replace),
                             ("unlink+replace", _unlink_then_replace)):
            try:
                action(building, target)
                return
            except OSError as exc:
                last_error = exc
                log.debug("替换尝试 %d/%s 失败：目标存在=%s errno=%s %s",
                          attempt + 1, name, target.exists(),
                          getattr(exc, "errno", None), exc)
        time.sleep(0.25 * (attempt + 1))
    raise OSError(
        f"目标 PDF 正被其它程序占用，替换失败：{target}\n"
        f"请先关闭正在打开它的阅读器（或预览窗口），然后重试。\n"
        f"（原始文件没有被改动。{last_error}）"
    )


def _unlink_then_replace(building: Path, target: Path) -> None:
    """退一步：先删掉目标再改名（有些阅读器允许删除、不允许覆盖）。"""
    if target.exists():
        target.unlink()
    os.replace(building, target)


def _quiet_unlink(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        log.debug("删除临时文件失败：%s", path, exc_info=True)


def _quiet_rmtree(path: Path) -> None:
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    except OSError:
        log.debug("删除临时目录失败：%s", path, exc_info=True)


def remove_legacy_markdown_summary(book) -> list[Path]:
    """删掉旧的 Markdown 总结（需求："不再生成md文档，旧的md之间删掉"）。

    只删**本软件生成的那个** ``<书目>_summary.md``，
    不动用户自己写的任何 md。返回被删掉的路径。
    """
    removed: list[Path] = []
    book_path = Path(book.path)
    canonical = book_path / f"{book.name}{C.SUMMARY_SUFFIX}"
    # 除了正牌名字，历史上还可能有别名（见 store._SUMMARY_ALIASES）
    candidates = [canonical]
    for alias in ("summary.md", "Summary.md", "总结.md"):
        candidates.append(book_path / alias)
    for path in candidates:
        if not path.is_file():
            continue
        try:
            path.unlink()
            removed.append(path)
            log.info("已删除旧的 Markdown 总结：%s", path)
        except OSError:
            log.warning("删除旧 Markdown 总结失败：%s", path, exc_info=True)
    return removed


__all__ = [
    "BUILDING_SUFFIX",
    "BuildResult",
    "ChapterPlan",
    "build_summary_pdf",
    "plan_chapter",
    "remove_legacy_markdown_summary",
    "summary_pdf_path",
]
