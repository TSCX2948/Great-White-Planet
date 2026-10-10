"""Markdown → HTML 渲染。

用于软件内的 Markdown 查看模式（QTextBrowser）以及 PDF 导出。
样式来自 :mod:`gwp.services.themes`，与代码分离，方便调整观感而不用改逻辑。
"""

from __future__ import annotations

import base64
import html
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import markdown as md_lib

from gwp.services import themes

log = logging.getLogger(__name__)

_MD_EXTENSIONS = [
    "fenced_code",
    "tables",
    "toc",
    "sane_lists",
    "attr_list",
    "footnotes",
    "def_list",
    "nl2br",
    "md_in_html",
]

_CODE_BLOCK_RE = re.compile(
    r'<pre><code(?P<attrs>[^>]*)>(?P<body>.*?)</code></pre>', re.DOTALL
)
_LANG_RE = re.compile(r'class="[^"]*language-([\w+#.-]+)[^"]*"')
_IMG_SRC_RE = re.compile(r'(<img[^>]*\ssrc=")([^"]+)(")', re.IGNORECASE)


@dataclass
class RenderOptions:
    """渲染参数。"""

    base_dir: Path | None = None      # 解析相对图片路径的基准目录
    theme: str = "light"              # light | dark
    resolve_images: bool = True       # 把相对图片转成绝对 file:// 路径
    inline_theme: bool = True         # 是否内嵌 CSS（QTextBrowser 需要）
    body_only: bool = False           # 只要 <body> 片段（导出 PDF 时用）
    highlight: bool = True            # 代码高亮
    title: str = ""
    #: 把 LaTeX 公式渲染成图片的目录（``None`` = 不改写公式）。
    #:
    #: 为什么需要：**QTextBrowser 与 PyMuPDF Story 都不认识 LaTeX**。
    #: 而总结提示词明确要求"公式使用 LaTeX"，实测预览里原样显示了
    #: ``$\varepsilon > 0$`` 这种源码（用户报障："公式显示异常"）。
    #: 给一个目录，渲染前就会把公式换成 ``![](...png)`` 图片引用。
    equation_dir: Path | None = None
    #: 公式字号与像素密度。
    #: 字号要**和正文接近**：22 时公式比正文大一半，会把整行撑开、基线也下沉
    #: （第一版就是这个观感）。15 配上 scale=3 在预览与 PDF 里都清晰。
    equation_size: int = 15
    equation_scale: int = 3
    #: 把图片**内嵌成 data URI**（而不是 file:// 引用）。
    #: PyMuPDF 的 Story 不加载 file:// 图片（只会显示 [image]），
    #: 所以走 Story 的场合（合并/导出 PDF）必须打开它。
    inline_images: bool = False


# --------------------------------------------------------------------------
# 公式 → 图片
# --------------------------------------------------------------------------

def substitute_equations(text: str, equation_dir: Path, *,
                         size: int = 15, scale: int = 3) -> tuple[str, int]:
    """把文本里的 LaTeX 公式换成图片引用。返回 ``(新文本, 替换条数)``。

    只处理 **行内 ``$...$``** 与 **独立 ``$$...$$``** 两种定界符 ——
    这也是提示词里规定的格式。渲染失败的公式**保留原文**
    （宁可显示源码，也不要凭空丢掉一条公式）。
    """
    from gwp.services import math_render

    source = text or ""
    if "$" not in source:
        return source, 0

    pieces: list[str] = []
    cursor = 0
    replaced = 0
    # 独立公式优先（``$$`` 比 ``$`` 长，先匹配它，否则会被拆成两个空的）
    for match, is_display in math_render.iter_formulas(source):
        start, end = match.span()
        if start < cursor:
            continue                      # 已被更长的匹配覆盖
        latex = match.group(1).strip()
        if not latex:
            continue
        name = math_render.formula_cache_name(latex, size=size, scale=scale)
        path, _degraded = math_render.render_to_png(
            latex, Path(equation_dir) / name, size=size, scale=scale
        )
        if path is None:
            continue                      # 渲染失败：保留原文
        pieces.append(source[cursor:start])
        # alt 用固定前缀 + 原始 LaTeX：既能被 _mark_equation_images 认出来，
        # 又保留了"这是什么公式"的信息（图片加载失败时也会显示）
        alt = _EQ_ALT_PREFIX + latex.replace("]", ")").replace("[", "(")
        if is_display:
            pieces.append(f"\n\n![{alt}]({path.as_posix()})\n\n")
        else:
            # **必须用 Markdown 图片语法**，不要写裸 <img> ——
            # 本项目启用了 attr_list 扩展，裸 HTML 会被当成字面文本
            # 原样显示出来（实测把整段 <img class=...> 打在了正文里）。
            pieces.append(f"![{alt}]({path.as_posix()})")
        cursor = end
        replaced += 1
    if not replaced:
        return source, 0
    pieces.append(source[cursor:])
    return "".join(pieces), replaced


# --------------------------------------------------------------------------
# Markdown → HTML
# --------------------------------------------------------------------------

def markdown_to_html(text: str, options: RenderOptions | None = None) -> str:
    """把 Markdown 转成 HTML 片段（不含 <html>/<head>）。"""
    options = options or RenderOptions()
    source = text or ""
    if options.equation_dir is not None:
        source, _count = substitute_equations(
            source, Path(options.equation_dir),
            size=options.equation_size, scale=options.equation_scale,
        )
    try:
        converter = md_lib.Markdown(extensions=_MD_EXTENSIONS, output_format="html")
        body = converter.convert(source)
    except Exception:  # noqa: BLE001 - 渲染失败不应导致界面崩溃
        log.exception("Markdown 渲染失败，退回纯文本显示")
        body = f"<pre>{html.escape(source)}</pre>"

    if options.highlight:
        body = _highlight_code_blocks(body)
    if options.resolve_images:
        body = _resolve_images(body, options.base_dir,
                                as_data_uri=options.inline_images)
    if options.equation_dir is not None:
        body = _mark_equation_images(body)
    body = _group_image_runs(body)
    return body


#: 只含图片与换行标记的段落：``<p><img><br><img></p>``
_IMG_ONLY_P = re.compile(
    r"<p>\s*((?:<img\b[^>]*>|<br\s*/?>|\s)+)</p>", re.IGNORECASE
)
#: 相邻的图片组（中间只有空白）
_IMG_GROUP_RUN = re.compile(
    r"(?:<div class=\"gwp-figure\">.*?</div>\s*)+", re.DOTALL
)
_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_BR_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)


def _group_image_runs(body: str) -> str:
    """把**连续的图片**合成一组，好让 CSS 去掉它们之间的缝隙。

    为什么要做：Markdown 里连着写多张图（``![](a.png)`` 换行 ``![](b.png)``），
    渲染出来是**同一个段落**里的多个 ``<img>``（本项目启用了 ``nl2br``，
    换行会变成 ``<br>``），而段落有 ``0.6em`` 上下边距、图片又有 ``0.5em`` ——
    图与图之间就能看到明显空白（用户报障："图片之间不要有间隙，
    图片结尾与下面的文字不要有间隙"）。

    做法：

    1. 先**剥掉图片之间的 ``<br>``** —— 那正是缝隙的来源
       （我第一版没做这一步，结果"全是图片的段落"根本匹配不上，
       HTML 里是 ``<p><img><br><img></p>``，看着像多个段落其实是同一个）；
    2. 把"只含图片的 ``<p>``"换成 ``<div class="gwp-figure">``；
    3. 把**相邻**的这类 div 合并成一个。

    然后由 CSS 负责：组内 ``img`` 间距为 **0**；组末尾留极小边距 ——
    而不是 0，否则最后一张图会**贴死**下面的文字（需求也说"不要有间隙"，
    但完全贴上会挤在一起、读起来更糟，所以留一个极小值）。
    """
    def _p_to_div(match: re.Match) -> str:
        inner = _BR_TAG.sub("", match.group(1))
        # 剥掉 br 之后仍可能只剩空白（例如空段落），那就原样退回
        if "<img" not in inner:
            return match.group(0)
        return f'<div class="gwp-figure">{inner}</div>'

    body = _IMG_ONLY_P.sub(_p_to_div, body)

    def _merge_run(match: re.Match) -> str:
        run = match.group(0)
        images = _IMG_TAG.findall(run)
        if len(images) <= 1:
            return run
        # **只留图片，把原来那些单个的 div 丢掉**。
        # 我第一版写成 `"<div>" + run + "</div>"` —— 那样等于把
        # `<div>图1</div><div>图2</div>` 又包了一层，组内仍然是两个 div，
        # 看起来"合并了"其实没有。
        return '<div class="gwp-figure">' + "".join(images) + "</div>"

    return _IMG_GROUP_RUN.sub(_merge_run, body)


#: 公式图片的 alt 前缀（= 原始 LaTeX），用来在 HTML 里认出它们
_EQ_ALT_PREFIX = "GWP-EQ:"


def _mark_equation_images(body: str) -> str:
    """给公式图片加 ``class="gwp-eq"``。

    为什么要"打标记"再做 CSS：公式图是**高分辨率**渲染的
    （15 号字 + scale=3 会得到约 84×57 像素），
    直接在 HTML 里 1:1 显示会比正文大好几倍 —— 实测就是这个观感。
    所以用 CSS 把它按 ``em`` 缩回"和文字一样高"，
    既清晰又不会把行撑开。
    """
    def _replace(match: re.Match) -> str:
        tag = match.group(0)
        if "gwp-eq" in tag or _EQ_ALT_PREFIX not in tag:
            return tag
        if "class=" in tag:
            return tag
        return tag[:-1] + " class=\"gwp-eq\">" if tag.endswith(">") else tag

    return re.sub(r"<img[^>]*>", _replace, body)


def render_document(text: str, options: RenderOptions | None = None) -> str:
    """渲染成完整 HTML（含 <style>），可直接给 QTextBrowser 或 PyMuPDF Story。"""
    options = options or RenderOptions()
    body = markdown_to_html(text, options)
    css = themes.markdown_css(theme=options.theme, for_pdf=not options.inline_theme)
    if options.body_only:
        return f"<div class='gwp-doc'>{body}</div>"
    title = html.escape(options.title or "Markdown")
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title>"
        f"<style>{css}</style>"
        "</head><body><div class='gwp-doc'>"
        f"{body}"
        "</div></body></html>"
    )


# --------------------------------------------------------------------------
# 代码高亮
# --------------------------------------------------------------------------

def _highlight_code_blocks(body: str) -> str:
    try:
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import TextLexer, get_lexer_by_name
        from pygments.util import ClassNotFound
    except ImportError:
        return body

    formatter = HtmlFormatter(nowrap=True, cssclass="hl")

    def _replace(match: re.Match) -> str:
        attrs = match.group("attrs") or ""
        code = match.group("body")
        language_match = _LANG_RE.search(attrs)
        language = language_match.group(1) if language_match else ""
        # markdown 会把代码里的实体转义，这里先还原成源码再高亮
        source = html.unescape(code)
        try:
            lexer = get_lexer_by_name(language) if language else TextLexer()
        except ClassNotFound:
            lexer = TextLexer()
        try:
            highlighted = highlight(source, lexer, formatter)
        except Exception:  # noqa: BLE001
            highlighted = html.escape(source)
        css_class = f"highlight language-{language}" if language else "highlight"
        return f'<pre class="{css_class}"><code>{highlighted}</code></pre>'

    return _CODE_BLOCK_RE.sub(_replace, body)


# --------------------------------------------------------------------------
# 图片路径解析
# --------------------------------------------------------------------------

def _resolve_images(body: str, base_dir: Path | None, *,
                    as_data_uri: bool = False) -> str:
    def _replace(match: re.Match) -> str:
        prefix, src, suffix = match.group(1), match.group(2), match.group(3)
        if as_data_uri:
            embedded = image_to_data_uri(src, base_dir)
            if embedded is not None:
                return f"{prefix}{embedded}{suffix}"
        resolved = resolve_image_src(src, base_dir)
        return f"{prefix}{resolved}{suffix}"

    return _IMG_SRC_RE.sub(_replace, body)


#: 内嵌成 data URI 的单张图片上限（超过就退回文件引用，避免 HTML 过大）
MAX_INLINE_IMAGE_BYTES = 4 * 1024 * 1024


def image_to_data_uri(src: str, base_dir: Path | None) -> str | None:
    """把本地图片转成 ``data:`` URI（base64 内嵌）。失败返回 None。

    为什么需要它：**PyMuPDF 的 ``Story`` 不加载 ``file://`` 引用的图片** ——
    实测即使把源目录挂成 ``Archive``、或把 src 写成绝对 ``file:///`` URL，
    排版结果里也只会出现 ``[image]`` 占位符。
    而 ``data:`` URI 是**直接嵌入 HTML 的内容**，不依赖任何文件访问，
    实测能正常画出来。

    （注意这与"预览"那条路不同：QTextBrowser **能**加载 ``file://``，
    所以只有走 Story 的场合才需要内嵌。）
    """
    candidate = _local_image_path(src, base_dir)
    if candidate is None:
        return None
    try:
        if candidate.stat().st_size > MAX_INLINE_IMAGE_BYTES:
            return None
        payload = base64.b64encode(candidate.read_bytes()).decode("ascii")
    except (OSError, ValueError):
        return None
    return f"data:{_mime_for(candidate)};base64,{payload}"


def _mime_for(path: Path) -> str:
    return {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".bmp": "image/bmp", ".webp": "image/webp",
        ".tif": "image/tiff", ".tiff": "image/tiff", ".svg": "image/svg+xml",
    }.get(path.suffix.lower(), "application/octet-stream")


def _local_image_path(src: str, base_dir: Path | None) -> Path | None:
    """把 Markdown 里的图片地址解析成本地文件路径（解析不出返回 None）。"""
    raw = (src or "").strip()
    if not raw or raw.startswith(("http://", "https://", "data:", "qrc:")):
        return None
    if raw.startswith("file:"):
        try:
            from urllib.parse import unquote, urlparse

            parsed = urlparse(raw)
            path = unquote(parsed.path or "")
            # Windows 上 file:///C:/x 的 path 是 "/C:/x"
            if re.match(r"^/[A-Za-z]:", path):
                path = path[1:]
            candidate = Path(path)
        except (ValueError, OSError):
            return None
    else:
        candidate = Path(raw)
        if not candidate.is_absolute() and base_dir is not None:
            candidate = base_dir / candidate
    try:
        return candidate if candidate.is_file() else None
    except (OSError, ValueError):
        return None


def resolve_image_src(src: str, base_dir: Path | None) -> str:
    """把 Markdown 里的图片地址变成可以真正打开的形式。

    * http(s)/data URI 原样返回；
    * 绝对路径或相对 ``base_dir`` 的路径转成 ``file:///...``；
    * 找不到文件时原样返回（由界面显示占位）。
    """
    src = src.strip()
    if not src:
        return src
    if src.startswith(("http://", "https://", "data:", "file:", "qrc:")):
        return src
    candidate = Path(src)
    if not candidate.is_absolute() and base_dir is not None:
        candidate = (base_dir / candidate)
    try:
        if candidate.exists():
            return candidate.resolve().as_uri()
    except (OSError, ValueError):
        return src
    return src


def plain_text(markdown_text: str, limit: int = 400) -> str:
    """把 Markdown 压成一行摘要（列表/预览里显示用）。"""
    text = markdown_text or ""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#>*_`~\-]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text[:limit] + ("…" if len(text) > limit else "")


__all__ = [
    "RenderOptions",
    "markdown_to_html",
    "plain_text",
    "render_document",
    "resolve_image_src",
]
