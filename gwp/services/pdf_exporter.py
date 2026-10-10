"""Markdown → PDF 导出。

实现方式：Markdown → HTML（复用 markdown_renderer）→ PyMuPDF Story → PDF。
不依赖 LibreOffice / Word / 浏览器，导出速度快、结果稳定，且完全本地完成
（need.md 第 5 条要求"自定义导出位置"；需求文档要求本地可用）。

如果将来想换成"调用 Office 打印"或"浏览器打印"，只需要替换本模块的实现。
"""

from __future__ import annotations

import base64
import gc
import logging
import mimetypes
import os
import re
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from gwp.core.config import Config
from gwp.services import themes
from gwp.services.markdown_renderer import RenderOptions, render_document, resolve_image_src

log = logging.getLogger(__name__)

PAGE_SIZES = {
    "A4": (595.0, 842.0),
    "A5": (420.0, 595.0),
    "Letter": (612.0, 792.0),
    "Legal": (612.0, 1008.0),
    "B5": (499.0, 709.0),
}

_IMG_SRC_RE = re.compile(r'(<img[^>]*\ssrc=")([^"]+)(")', re.IGNORECASE)


@dataclass
class PDFExportOptions:
    page_size: str = "A4"
    margin_mm: float = 18.0
    theme: str = "light"
    embed_images: bool = True
    page_numbers: bool = True
    title: str = ""
    base_dir: Path | None = None
    #: 公式转图片时，图片放在哪（不设就放在目标 PDF 旁边的一个隐藏目录里）
    equation_dir: Path | None = None
    equation_size: int = 15
    equation_scale: int = 3
    #: 本次导出的目标路径（``_build_html`` 用它决定公式图片目录的位置）
    output_path: Path | None = None

    @classmethod
    def from_config(cls, config: Config | None = None) -> "PDFExportOptions":
        config = config or Config.load()
        return cls(
            page_size=str(config.get("export.pdf_page_size", "A4") or "A4"),
            margin_mm=float(config.get("export.pdf_margin_mm", 18) or 18),
            theme=str(config.get("ui.theme", "light") or "light"),
            embed_images=bool(config.get("export.pdf_embed_images", True)),
            page_numbers=bool(config.get("export.pdf_page_numbers", True)),
        )


class PDFExportError(Exception):
    """导出失败，消息可直接展示给用户。"""


class PDFExportCancelled(Exception):
    """用户中止了导出。"""


# --------------------------------------------------------------------------

def export_markdown_to_pdf(
    markdown_text: str,
    output_path: Path,
    options: PDFExportOptions | None = None,
    base_dir: Path | None = None,
    on_progress: Callable[[str, int], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
    page_numbers: bool | None = None,
    style: str | None = None,
    prepared_path: Path | None = None,
    pages: list[int] | None = None,
) -> Path:
    """把 Markdown 导出为 PDF，返回实际写入的文件路径。

    ``style`` 决定要哪种产物：

    * ``None``（默认）：直接产出最终文件，页面取自 ``prepared_path``（若已排版）
      或现场排版，页码按 ``page_numbers`` 决定。
    * ``"prepare"``：只排版到**临时文件**，用于先问用户"要哪些页"——
      返回的路径是临时 PDF，此时 ``output_path`` 参数被忽略。

    ``prepared_path`` 传入上一次 ``style="prepare"`` 得到的临时文件，
    即可跳过排版直接切页/编号，避免二次排版（长文档能省一半时间）。
    """
    options = options or PDFExportOptions.from_config()
    if base_dir is not None:
        options.base_dir = base_dir
    if page_numbers is not None:
        options.page_numbers = bool(page_numbers)
    # 让 _build_html 知道公式图片该放哪（以及目标是哪个文件）
    options.output_path = Path(output_path)
    # 本次导出自己建了公式目录吗？是的话用完要删掉（不留中间物）
    equation_dir_owned = options.equation_dir is None

    def report(message: str, percent: int) -> None:
        if on_progress is not None:
            on_progress(message, percent)

    def cancelled() -> bool:
        return bool(should_cancel is not None and should_cancel())

    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf  # 旧版本包名
        except ImportError as exc:  # pragma: no cover
            raise PDFExportError("未安装 PyMuPDF，无法导出 PDF。请执行：pip install pymupdf") from exc

    if style == "prepare":
        # 只排版，产物是临时文件，交给调用方后续处理
        temporary = Path(output_path)
        temporary.parent.mkdir(parents=True, exist_ok=True)
        report("正在排版……", 5)
        html_text = _build_html(markdown_text, options)
        width, height = PAGE_SIZES.get(str(options.page_size).upper(), PAGE_SIZES["A4"])
        margin = max(0.0, float(options.margin_mm)) * 72.0 / 25.4
        try:
            _write_story(
                pymupdf, html_text, temporary, width, height, margin, report, cancelled
            )
        except PDFExportCancelled:
            _discard(temporary)
            raise
        except PDFExportError:
            _discard(temporary)
            raise
        if not temporary.exists() or temporary.stat().st_size == 0:
            _discard(temporary)
            raise PDFExportError("PDF 导出失败：排版结果为空。")
        report("排版完成", 88)
        return temporary

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if prepared_path is not None:
        # 复用已排版好的文件，直接进入切页/编号阶段
        source = Path(prepared_path)
        if not source.exists():
            raise PDFExportError("排版结果已丢失，请重新导出。")
        prepared_total = count_pdf_pages(source)
        report(f"复用已排版好的 {prepared_total} 页", 60)
    else:
        report("正在排版……", 5)
        html_text = _build_html(markdown_text, options)
        width, height = PAGE_SIZES.get(str(options.page_size).upper(), PAGE_SIZES["A4"])
        margin = max(0.0, float(options.margin_mm)) * 72.0 / 25.4
        source = output_path.with_name(output_path.stem + ".layout.pdf")
        try:
            _write_story(
                pymupdf, html_text, source, width, height, margin, report, cancelled
            )
        except PDFExportCancelled:
            _discard(source)
            raise
        except PDFExportError:
            _discard(source)
            raise
        if not source.exists() or source.stat().st_size == 0:
            _discard(source)
            raise PDFExportError("PDF 导出失败：排版结果为空。")

    if cancelled():
        _discard(source)
        raise PDFExportCancelled("已取消导出")

    try:
        _finalize(
            pymupdf,
            source,
            output_path,
            options,
            page_numbers,
            report,
            cancelled,
            pages=pages,
            own_source=prepared_path is None,
        )
    finally:
        # 公式图片只在排版期间有用（已经内联进 HTML 了），用完就删。
        #
        # **只在"目录是我们自己建的"时才删** —— 调用方显式指定了
        # ``equation_dir``（例如「长庚知道」复用它）时不能动，那是别人的东西。
        if equation_dir_owned:
            _discard_equation_dir(Path(output_path))
    report("完成", 100)
    return output_path


def _finalize(
    pymupdf,
    source: Path,
    output_path: Path,
    options: PDFExportOptions,
    page_numbers: bool | None,
    report: Callable[[str, int], None],
    cancelled: Callable[[], bool],
    pages: list[int] | None = None,
    own_source: bool = True,
) -> None:
    """把排版结果加工成最终文件：切页 → 页码 → 原子替换。

    ``pages`` 为空表示用全部页；给定页码时抽出这些页，且**保留原页号**
    （第 8 页抽出来后页脚仍显示 8，分母为原文档总页数）。

    ``own_source`` 表示 ``source`` 是不是本函数自己临时排出来的；
    复用调用方传入的排版文件时不要删除它（调用方可能还要再导一次）。
    """
    want_numbers = options.page_numbers if page_numbers is None else bool(page_numbers)
    source = Path(source)
    output_path = Path(output_path)
    total = count_pdf_pages(source)

    try:
        selected = list(pages) if pages else list(range(1, total + 1))
        same_place = False
        try:
            same_place = source.resolve() == output_path.resolve()
        except OSError:
            same_place = source == output_path

        if not same_place:
            # 切页（若需要）写到最终位置，随后在最终位置加页码
            if selected == list(range(1, total + 1)):
                report("正在写入文件……", 90)
                try:
                    _replace_with_retry(source, output_path)
                except OSError as exc:
                    raise PDFExportError(f"保存 PDF 失败：{exc}") from exc
            else:
                report(f"正在抽取 {len(selected)} 页……", 88)
                extract_pages(source, output_path, selected)
                if own_source:
                    _discard(source)
            if want_numbers:
                report("正在添加页码……", 93)
                # 页码显示原文档中的页号，分母用原文档总页数
                add_page_numbers(output_path, numbers=selected, total=total)
        elif want_numbers and selected != list(range(1, total + 1)):
            # 就地切页：先抽出到临时文件，再替换回来
            report(f"正在抽取 {len(selected)} 页……", 88)
            extracted = output_path.with_name(output_path.stem + ".extract.pdf")
            extract_pages(output_path, extracted, selected)
            report("正在添加页码……", 93)
            add_page_numbers(extracted, numbers=selected, total=total)
            _replace_with_retry(extracted, output_path)
        elif want_numbers:
            report("正在添加页码……", 92)
            add_page_numbers(output_path)

        report(f"共 {len(selected)} 页", 97)
    except PDFExportCancelled:
        if own_source:
            _discard(source)
        raise
    except PDFExportError:
        if own_source:
            _discard(source)
        raise


def _write_story(
    pymupdf,
    html_text: str,
    output_path: Path,
    width: float,
    height: float,
    margin: float,
    report: Callable[[str, int], None],
    cancelled: Callable[[], bool],
) -> int:
    """用 PyMuPDF Story 把 HTML 排版写成多页 PDF。

    嵌套的 ``render()`` 是**有意为之**：Story 与 DocumentWriter 都是它的局部变量，
    函数一返回就释放，底层文件句柄随之归还。否则：
    * 取消时删不掉半成品；
    * 加页码时要替换这个文件会报 WinError 5。
    """
    try:
        pages = _render(
            pymupdf, html_text, output_path, width, height, margin, report, cancelled
        )
    except PDFExportCancelled:
        _discard(output_path)
        raise
    except Exception as exc:  # noqa: BLE001
        log.exception("PDF 导出失败")
        _discard(output_path)
        raise PDFExportError(f"PDF 导出失败：{exc}") from exc

    # 到了这里 render() 已返回，文件句柄已释放（删除半成品才可能成功）
    if cancelled():
        _discard(output_path)
        raise PDFExportCancelled("已取消导出")
    return pages


def _render(
    pymupdf,
    html_text: str,
    output_path: Path,
    width: float,
    height: float,
    margin: float,
    report: Callable[[str, int], None],
    cancelled: Callable[[], bool],
) -> int:
    """真正排版的一层，保证 PyMuPDF 对象在本层结束时全部释放。"""
    story = pymupdf.Story(html=html_text)
    writer = pymupdf.DocumentWriter(str(output_path))
    pages = 0
    cancelled_here = False
    # 排版不收敛的检测（见下面 _STALL_PAGE_LIMIT 的说明）
    last_filled: tuple[float, ...] | None = None
    stall = 0
    try:
        mediabox = pymupdf.Rect(0, 0, width, height)
        more = 1
        while more:
            # 每页都检查一次取消，排版中途也能停下来
            if cancelled():
                cancelled_here = True
                raise PDFExportCancelled("已取消导出")
            device = writer.begin_page(mediabox)
            # **每页都要新建一个矩形**。
            #
            # story.place(rect) 会把传进去的 rect **就地改写**成"这一页实际用掉的
            # 区域"；如果在循环外只建一次、反复传同一个对象，
            # 矩形会一轮轮被压缩、内容永远排不完。
            where = pymupdf.Rect(margin, margin, width - margin, height - margin)
            more, filled = story.place(where)
            story.draw(device)
            writer.end_page()
            pages += 1
            # 百分比只报到 85%，剩下的留给页码与最终写入
            report(f"正在排版第 {pages} 页……", min(85, 10 + pages * 3))

            # ---- 不收敛检测 ----
            #
            # 实测：某些内容组合会让 PyMuPDF 的 Story **永远返回 more=1**，
            # 而且每页都填满同样的高度 —— 于是一路排到 5001 页、
            # 产出近 1 GB 的废 PDF（书稿就这样坏过一次）。
            #
            # 正常文档每页的填充高度都在变；连续几百页"填充高度一模一样"
            # 只可能是排版器卡住了。这里宁可报错，也不要写出一个
            # 几百 MB、打开就卡死的文件。
            # 注意 `filled` 是一个**四元组** (x0, y0, x1, y1)，不是 Rect。
            current = tuple(round(float(v), 1) for v in filled)
            if current == last_filled:
                stall += 1
                if stall >= _STALL_PAGE_LIMIT:
                    raise PDFExportError(
                        f"排版无法收敛：连续 {_STALL_PAGE_LIMIT} 页内容完全重复"
                        f"（已排到第 {pages} 页）。这通常意味着文档里有"
                        "排版器处理不了的元素组合，请把内容拆成几个较小的文件，"
                        "或先导出其中一部分。"
                    )
            else:
                stall = 0
                last_filled = current
    finally:
        # 先释放写句柄：只有句柄归还之后，才可能删掉半成品文件
        try:
            writer.close()
        except Exception:  # noqa: BLE001
            log.debug("关闭 DocumentWriter 失败", exc_info=True)
        del writer
        del story
        gc.collect()
        if cancelled_here:
            _discard(output_path)
    return pages


#: 连续多少页"填充区域完全一样"就判定排版器卡死了。
#:
#: 取值权衡：正常文档不会有几十页填充区域一模一样，所以这个阈值很宽松；
#: 但它必须在"排到 5001 页"之前生效，否则又会写出一个几百 MB 的废文件。
_STALL_PAGE_LIMIT = 120


def count_pdf_pages(pdf_path: Path) -> int:
    """读出一个 PDF 的页数（用于导出后询问页码范围）。"""
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover
        raise PDFExportError("未安装 PyMuPDF，无法读取页数") from exc
    pdf_path = Path(pdf_path)
    try:
        document = pymupdf.open(pdf_path)
    except Exception as exc:  # noqa: BLE001
        raise PDFExportError(f"无法打开 PDF 读取页数：{exc}") from exc
    try:
        return document.page_count
    finally:
        document.close()
        del document
        gc.collect()


def extract_pages(source_pdf: Path, target_pdf: Path, pages: list[int]) -> Path:
    """按给定页码（1 基，可乱序、可重复）抽取页面，生成新的 PDF。

    页码**保持原文档的编号**：抽取后每页显示的仍是它在原文档中的页号，
    与"页码范围"输入一致，便于引用。
    """
    if not pages:
        raise PDFExportError("没有选中任何页面。")
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover
        raise PDFExportError("未安装 PyMuPDF，无法抽取页面") from exc

    source_pdf = Path(source_pdf)
    target_pdf = Path(target_pdf)
    target_pdf.parent.mkdir(parents=True, exist_ok=True)
    temporary = target_pdf.with_name(target_pdf.stem + ".part.pdf")

    # 同样放在独立函数里，保证句柄在替换/删除之前释放
    try:
        _copy_pages(pymupdf, source_pdf, temporary, pages)
    except PDFExportError:
        _discard(temporary)
        raise
    except Exception as exc:  # noqa: BLE001
        _discard(temporary)
        raise PDFExportError(f"抽取页面失败：{exc}") from exc

    try:
        _replace_with_retry(temporary, target_pdf)
    except OSError as exc:
        _discard(temporary)
        raise PDFExportError(f"保存抽取结果失败：{exc}") from exc
    return target_pdf


def _copy_pages(pymupdf, source_pdf: Path, temporary: Path, pages: list[int]) -> None:
    """真正做页面复制的一层（保证 PyMuPDF 对象在此层释放）。"""
    source = pymupdf.open(source_pdf)
    output = pymupdf.open()
    try:
        total = source.page_count
        for number in pages:
            if number < 1 or number > total:
                raise PDFExportError(f"第 {number} 页不存在：原文档共 {total} 页。")
            output.insert_pdf(source, from_page=number - 1, to_page=number - 1)
        output.save(str(temporary), garbage=3, deflate=True)
    finally:
        try:
            output.close()
        except Exception:  # noqa: BLE001
            log.debug("关闭输出文档失败", exc_info=True)
        source.close()
        del output
        del source
        gc.collect()


def add_page_numbers(
    pdf_path: Path,
    footer_text: str = "- {page} / {total} -",
    font_size: float = 8.5,
    numbers: list[int] | None = None,
    total: int | None = None,
) -> int:
    """给已生成的 PDF 逐页插入页码，返回处理的页数。

    ``numbers`` 用于"抽取后保留原页码"的场景：第 i 页显示的编号取 ``numbers[i]``。
    ``total`` 是页脚分母（``{total}``），通常传**原文档总页数**——
    这样从 10 页里抽第 8 页出来，页脚仍然是「8 / 10」而不是「1 / 3」。
    """
    try:
        import pymupdf
    except ImportError as exc:  # pragma: no cover
        raise PDFExportError("未安装 PyMuPDF，无法添加页码") from exc

    pdf_path = Path(pdf_path)
    try:
        document = pymupdf.open(pdf_path)
    except Exception as exc:  # noqa: BLE001
        raise PDFExportError(f"无法打开已生成的 PDF：{exc}") from exc

    temporary = pdf_path.with_name(pdf_path.stem + ".pages.pdf")
    actual_pages = 0
    try:
        actual_pages = document.page_count
        if numbers and len(numbers) != actual_pages:
            # 页码表与页数不一致：退回顺序编号，避免错位
            log.debug(
                "页码表长度(%s)与页数(%s)不一致，改用顺序编号", len(numbers), actual_pages
            )
            numbers = None
        display_total = int(total) if total else (len(numbers) if numbers else actual_pages)
        for index, page in enumerate(document, start=1):
            shown = numbers[index - 1] if numbers else index
            text = footer_text.replace("{page}", str(shown)).replace("{total}", str(display_total))
            # 页码固定在页面底部居中，不随正文页边距变化，避免压到内容
            box = pymupdf.Rect(
                page.rect.width / 2 - 90,
                page.rect.height - 34,
                page.rect.width / 2 + 90,
                page.rect.height - 16,
            )
            try:
                page.insert_textbox(
                    box,
                    text,
                    fontname="china-s",
                    fontsize=font_size,
                    color=(0.42, 0.45, 0.50),
                    align=pymupdf.TEXT_ALIGN_CENTER,
                )
            except Exception:  # noqa: BLE001 - 单页失败不影响其它页
                log.debug("第 %s 页写页码失败", index, exc_info=True)
        document.save(str(temporary), garbage=3, deflate=True)
    except Exception as exc:  # noqa: BLE001
        _discard(temporary)
        raise PDFExportError(f"添加页码失败：{exc}") from exc
    finally:
        # Windows 上必须先释放原文件句柄，否则下面的 os.replace 会被拒绝。
        # PyMuPDF 关闭后偶尔仍有句柄被 GC 延迟回收，这里显式清理一次。
        document.close()
        del document
        gc.collect()

    try:
        _replace_with_retry(temporary, pdf_path)
    except OSError as exc:
        _discard(temporary)
        raise PDFExportError(f"替换带页码的文件失败：{exc}") from exc
    return actual_pages


def _replace_with_retry(source: Path, target: Path, attempts: int = 5) -> None:
    """原子替换，遇到"文件被占用"时短暂重试（Windows 上杀毒/索引服务会短暂持锁）。"""
    last: OSError | None = None
    for index in range(attempts):
        try:
            os.replace(source, target)
            return
        except PermissionError as exc:
            last = exc
            time.sleep(0.06 * (index + 1))
    if last is not None:
        raise last


def _discard(path: Path) -> None:
    """导出失败或取消时清掉半成品文件。

    Windows 上文件句柄可能被延迟释放，因此带少量重试；删不掉也不影响主流程。
    """
    for attempt in range(4):
        try:
            if path.exists():
                path.unlink()
            return
        except OSError:
            gc.collect()
            time.sleep(0.05 * (attempt + 1))
    log.debug("清理未完成的 PDF 失败：%s", path, exc_info=True)


def _build_html(markdown_text: str, options: PDFExportOptions) -> str:
    """生成适合分页排版的完整 HTML。

    **公式要在这里先换成图片**。为什么要专门做这件事：
    原先这里没设 ``equation_dir``，于是 :func:`render_document` 里的
    公式替换**整个没启用** —— 导出的 PDF 里 ``$\\lim(a_n+b_n)=A+B$``
    会**原样显示 LaTeX 源码**（实测：预览图上就是一串 ``\\lim``）。
    公式是这个软件的核心内容，不能就这么漏掉。

    图片落在一个临时目录里（放在目标 PDF 旁边），
    紧接着的 :func:`_embed_images` 会把它们内联成 data URI，
    所以最终 PDF **不依赖**那个临时目录；调用方负责清掉它。
    """
    render_options = RenderOptions(
        base_dir=options.base_dir,
        theme=options.theme,
        resolve_images=True,
        highlight=True,
    )
    # 公式 -> 图片（临时目录），随后内联成 data URI
    equation_dir = _prepare_equation_dir(options)
    if equation_dir is not None:
        render_options.equation_dir = equation_dir
        render_options.equation_size = options.equation_size
        render_options.equation_scale = options.equation_scale
    body = render_document(markdown_text, render_options)
    if options.embed_images:
        body = _embed_images(body, options.base_dir)

    extra_css = f"""
@page {{ size: {options.page_size}; margin: {options.margin_mm}mm; }}
body {{ margin: 0; }}
.gwp-doc {{ background: #FFFFFF; }}
"""
    if "</head>" in body:
        body = body.replace("</head>", f"<style>{extra_css}</style></head>")
    else:
        body = f"<style>{extra_css}</style>{body}"
    return body


def _prepare_equation_dir(options: PDFExportOptions) -> Path | None:
    """给这次导出准备一个放公式图片的临时目录。

    目录建在**目标 PDF 旁边**（而不是系统临时目录）：这样万一清理失败，
    用户在自己的目录里能看到残留、也删得掉，不会留下看不见的垃圾。
    名字带前导点（``.<名字>_equations``），在文件管理器里是隐藏的，
    不会和用户的文件混在一起。
    """
    try:
        base = options.equation_dir
        if base is not None:
            Path(base).mkdir(parents=True, exist_ok=True)
            return Path(base)
        output = Path(options.output_path) if options.output_path else None
        if output is None:
            return None
        target = output.parent / f".{output.stem}_equations"
        target.mkdir(parents=True, exist_ok=True)
        return target
    except OSError:
        log.debug("无法准备公式图片目录，本次不做公式替换", exc_info=True)
        return None


def _discard_equation_dir(output_path: Path) -> None:
    """删掉本次导出用的公式图片目录（失败也不报错）。"""
    try:
        target = Path(output_path).parent / f".{Path(output_path).stem}_equations"
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
    except OSError:
        log.debug("清理公式图片目录失败：%s", output_path, exc_info=True)


def _embed_images(html_text: str, base_dir: Path | None) -> str:
    """把本地图片内联为 data URI，导出的 PDF 不依赖原文件位置。"""

    def _replace(match: re.Match) -> str:
        prefix, src, suffix = match.group(1), match.group(2), match.group(3)
        data_uri = _to_data_uri(src, base_dir)
        return f"{prefix}{data_uri or src}{suffix}"

    return _IMG_SRC_RE.sub(_replace, html_text)


def _to_data_uri(src: str, base_dir: Path | None) -> str:
    src = (src or "").strip()
    if not src or src.startswith("data:"):
        return src
    if src.startswith(("http://", "https://")):
        return ""       # 不联网抓图：失败时保留原地址
    path: Path | None = None
    if src.startswith("file:"):
        try:
            from urllib.request import url2pathname
            from urllib.parse import urlparse

            parsed = urlparse(src)
            path = Path(url2pathname(parsed.path))
        except Exception:  # noqa: BLE001
            return ""
    else:
        resolved = resolve_image_src(src, base_dir)
        if resolved.startswith("file:"):
            try:
                from urllib.request import url2pathname
                from urllib.parse import urlparse

                path = Path(url2pathname(urlparse(resolved).path))
            except Exception:  # noqa: BLE001
                return ""
        else:
            candidate = Path(src)
            path = candidate if candidate.is_absolute() else (base_dir / candidate if base_dir else None)

    if path is None or not path.is_file():
        return ""
    try:
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{payload}"
    except OSError:
        return ""


def suggested_filename(markdown_path: Path | str) -> str:
    stem = Path(markdown_path).stem or "document"
    return f"{stem}.pdf"


def pdf_css_preview(theme: str = "light") -> str:
    """导出对话框里做样式预览用。"""
    return themes.markdown_css(theme=theme, for_pdf=True)


__all__ = [
    "PAGE_SIZES",
    "PDFExportCancelled",
    "PDFExportError",
    "PDFExportOptions",
    "add_page_numbers",
    "count_pdf_pages",
    "export_markdown_to_pdf",
    "extract_pages",
    "pdf_css_preview",
    "suggested_filename",
]
