"""把 LaTeX 公式渲染成图片。

为什么需要它
------------
软件内的 Markdown 预览用的是 ``QTextBrowser`` —— 它只支持 HTML4 + CSS2.1
的一个子集，**不认识 LaTeX**（没有 MathJax/KaTeX）。
而总结提示词明确要求"公式使用 LaTeX（行内 ``$...$``，独立 ``$$...$$``）"，
于是用户看到的是一堆源码：

    设 $\\varepsilon > 0$，存在 $N$ 使 $|a_n - A| < \\varepsilon$。

实测（``QTextDocument.toPlainText()``）确认：QTextBrowser **原样显示**了
反斜杠与美元号。这正是用户报的"数学符号、公式显示异常"。

为什么自己排版而不是装 matplotlib
--------------------------------
matplotlib 的 mathtext 能渲染得很好，但它会明显增大安装包
（本项目一直控制安装包体积，当前约 77MB），而这只是"一种显示需求"。
所以这里用项目已有的 **Pillow** 自己排一个**够用的子集**：

* 上标 / 下标、分式、根号；
* 希腊字母与常用数学符号（→ ε δ α β θ λ μ π σ φ ω γ Δ Σ Π Ω 等）；
* 关系与运算符号（≤ ≥ ≠ ≈ ∈ ∉ ⊂ ⊆ ∪ ∩ ∞ → ⇒ ∀ ∃ ± × ÷ ⋅ √ ∂ ∫ ∑ ∏）；
* 常用函数名（sin cos tan log ln lim max min 等）保持正体。

**排不出来的（矩阵、多行对齐等）不猜** —— 退回等宽的纯文本表示，
并在结果里标出 ``degraded=True``，让调用方能说明"这条没排好"。

这个模块**不依赖 Qt**，可以单独测试。
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

#: 渲染出来的公式图片放在哪里（相对数据目录）。
#:
#: 需求："图片本地可以专门找一个新位置存储"。
#: 放在 ``else data``（软件数据侧）而不是书目里 —— 它是**生成物**，
#: 不该混进用户的资料目录；集中存放也便于清理与复用。
EQUATION_DIR_NAME = "equations"

#: 公式图片的默认像素密度（字号的倍数）。给大一点，PDF 导出时更清晰。
DEFAULT_SCALE = 4

#: 优先使用的字体（按顺序找第一个能用的）。
#: Cambria Math 是 Windows 自带的数学字体，符号最全、观感最接近公式。
_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\cambria.ttc",
    r"C:\Windows\Fonts\cambriab.ttf",
    r"C:\Windows\Fonts\seguisym.ttf",
    r"C:\Windows\Fonts\DejaVuSans.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)

#: 命令 → 字符（希腊字母、运算符、关系符……）
_SYMBOLS: dict[str, str] = {
    # 希腊字母（小写）
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε",
    "varepsilon": "ε", "zeta": "ζ", "eta": "η", "theta": "θ", "vartheta": "ϑ",
    "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ",
    "pi": "π", "varpi": "ϖ", "rho": "ρ", "varrho": "ϱ", "sigma": "σ",
    "varsigma": "ς", "tau": "τ", "upsilon": "υ", "phi": "φ", "varphi": "φ",
    "chi": "χ", "psi": "ψ", "omega": "ω",
    # 希腊字母（大写）
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ",
    "Omega": "Ω",
    # 运算
    "pm": "±", "mp": "∓", "times": "×", "div": "÷", "cdot": "·",
    "ast": "∗", "star": "⋆", "circ": "∘", "bullet": "•",
    # 关系
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠",
    "equiv": "≡", "approx": "≈", "sim": "∼", "simeq": "≃", "cong": "≅",
    "propto": "∝", "ll": "≪", "gg": "≫",
    # 集合与逻辑
    "in": "∈", "notin": "∉", "ni": "∋", "subset": "⊂", "supset": "⊃",
    "subseteq": "⊆", "supseteq": "⊇", "cup": "∪", "cap": "∩",
    "emptyset": "∅", "varnothing": "∅", "forall": "∀", "exists": "∃",
    "nexists": "∄", "neg": "¬", "lnot": "¬", "land": "∧", "lor": "∨",
    "implies": "⇒", "iff": "⇔", "therefore": "∴", "because": "∵",
    # 箭头
    "to": "→", "rightarrow": "→", "leftarrow": "←", "leftrightarrow": "↔",
    "Rightarrow": "⇒", "Leftarrow": "⇐", "Leftrightarrow": "⇔",
    "mapsto": "↦", "uparrow": "↑", "downarrow": "↓",
    # 大型运算符与其它
    "infty": "∞", "partial": "∂", "nabla": "∇", "surd": "√", "angle": "∠",
    "perp": "⊥", "parallel": "∥", "prime": "′", "ldots": "…", "cdots": "⋯",
    "dots": "…", "quad": " ", "qquad": "  ", "colon": ":", "mid": "|",
    "int": "∫", "iint": "∬", "oint": "∮", "sum": "∑", "prod": "∏",
    "lim": "lim", "min": "min", "max": "max", "sup": "sup", "inf": "inf",
    "sin": "sin", "cos": "cos", "tan": "tan", "cot": "cot", "sec": "sec",
    "csc": "csc", "arcsin": "arcsin", "arccos": "arccos", "arctan": "arctan",
    "sinh": "sinh", "cosh": "cosh", "tanh": "tanh",
    "log": "log", "ln": "ln", "lg": "lg", "exp": "exp", "det": "det",
    "dim": "dim", "ker": "ker", "deg": "deg", "gcd": "gcd",
    # 转义字符
    "{": "{", "}": "}", "_": "_", "%": "%", "&": "&", "#": "#", "$": "$",
    ",": " ", ";": " ", " ": " ", "!": "",
    "left": "", "right": "", "displaystyle": "", "textstyle": "",
}

#: 这些命令带一个"参数"，渲染方式特殊
_BIG_OPERATORS = {"sum", "prod", "int", "iint", "oint", "bigcup", "bigcap"}

#: 需要"上下堆叠上下标"的运算符（而不是放到右边）：
#: ``\lim_{n\to\infty}`` 应当把 ``n→∞`` 排在 ``lim`` **正下方**，
#: ``\sum_{i=1}^{n}`` 把上下限排在 Σ 的上方与下方。
#: 右边那种写法（``lim`` 右下角挂一个小字）在数学排版里是错的。
_STACK_OPERATORS = {
    "lim", "min", "max", "sup", "inf", "sum", "prod",
    "int", "iint", "oint", "bigcup", "bigcap", "log", "ln", "exp",
}

#: 字体类命令：只取其内容（不改变字形，但**不要**因为不认识就整条退化）
_FONT_COMMANDS = {
    "mathbb", "mathcal", "mathbf", "mathrm", "mathit", "mathsf", "mathtt",
    "text", "textbf", "textit", "operatorname", "boldsymbol", "pmb",
}

#: 空格类命令
_HSPACE = {"quad": "  ", "qquad": "    ", ",": " ", ";": " ", " ": " "}


# --------------------------------------------------------------------------
# 字体
# --------------------------------------------------------------------------

_font_cache: dict[tuple[int, bool], ImageFont.FreeTypeFont] = {}


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    """按大小取字体。找不到任何候选时退回 PIL 内置位图字体。"""
    key = (size, bold)
    cached = _font_cache.get(key)
    if cached is not None:
        return cached
    for candidate in _FONT_CANDIDATES:
        path = Path(candidate)
        if not path.is_file():
            continue
        if bold and "cambria.ttc" in candidate:
            # cambria.ttc 的第一张是正体，粗体要用 cambriab
            sibling = path.with_name("cambriab.ttf")
            if sibling.is_file():
                path = sibling
        try:
            font = ImageFont.truetype(str(path), size)
            _font_cache[key] = font
            return font
        except OSError:
            continue
    log.warning("找不到可用的数学字体，公式将用内置位图字体（观感较差）")
    font = ImageFont.load_default()
    _font_cache[key] = font        # type: ignore[assignment]
    return font                   # type: ignore[return-value]


# --------------------------------------------------------------------------
# 简易盒子模型
# --------------------------------------------------------------------------

@dataclass
class _Box:
    """一块排好版的图形：一张图 + 相对基线的上下高度。"""

    image: Image.Image
    above: int                    # 基线以上（正数）
    below: int                    # 基线以下（正数）
    degraded: bool = False        # 是否用了"退化的纯文本"表示

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height


@dataclass
class RenderResult:
    """一次公式渲染的结果。"""

    image: Image.Image | None = None
    degraded: bool = False
    source: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.image is not None


# --------------------------------------------------------------------------
# 解析
# --------------------------------------------------------------------------

def _split_top_level(text: str, separator: str = "") -> list[str]:
    """按分隔符切分，但**不切进花括号里**（``\\frac{a}{b}`` 必须当成整体）。"""
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            current.append(char)
            current.append(text[index + 1])
            index += 2
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth = max(0, depth - 1)
        if depth == 0 and separator and text.startswith(separator, index):
            parts.append("".join(current))
            current = []
            index += len(separator)
            continue
        current.append(char)
        index += 1
    parts.append("".join(current))
    return parts


def _group_at(text: str, start: int) -> tuple[str, int]:
    """取 ``start`` 处的一个"参数"：``{...}`` 或单个字符。返回 (内容, 下一个下标)。"""
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text):
        return "", start
    if text[start] == "{":
        depth = 0
        index = start
        while index < len(text):
            if text[index] == "\\":
                index += 2
                continue
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    return text[start + 1:index], index + 1
            index += 1
        return text[start + 1:], len(text)
    if text[start] == "\\":
        match = re.match(r"\\[A-Za-z]+", text[start:])
        if match:
            return match.group(0), start + len(match.group(0))
    return text[start], start + 1


# --------------------------------------------------------------------------
# 排版
# --------------------------------------------------------------------------

def _render_plain(text: str, size: int) -> _Box:
    """把一段（已不含需要特殊排版的）文本画成一行。"""
    font = _font(size)
    # 用一个临时画布测量
    probe = Image.new("L", (1, 1))
    draw = ImageDraw.Draw(probe)
    ascent, descent = font.getmetrics()
    width = int(draw.textlength(text, font=font)) + 2
    height = ascent + descent
    image = Image.new("RGBA", (max(1, width), max(1, height)), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((1, 0), text, font=font, fill=(0, 0, 0, 255))
    return _Box(image=image, above=ascent, below=descent)


def _hstack(boxes: list[_Box], spacing: int = 1) -> _Box:
    """横向拼接，按基线对齐。"""
    boxes = [b for b in boxes if b.image.width > 0]
    if not boxes:
        return _Box(image=Image.new("RGBA", (1, 1), (0, 0, 0, 0)), above=0, below=0)
    above = max(b.above for b in boxes)
    below = max(b.below for b in boxes)
    width = sum(b.width for b in boxes) + spacing * (len(boxes) - 1)
    image = Image.new("RGBA", (width, above + below), (0, 0, 0, 0))
    x = 0
    for box in boxes:
        image.alpha_composite(box.image, (x, above - box.above))
        x += box.width + spacing
    return _Box(image=image, above=above, below=below,
                degraded=any(b.degraded for b in boxes))


def _overlay(upper: _Box, lower: _Box, gap: int = 1) -> _Box:
    """把两块图按左上角叠起来（用于分号/根号这类组合）。"""
    width = max(upper.width, lower.width)
    height = upper.height + gap + lower.height
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    image.alpha_composite(upper.image, (0, 0))
    image.alpha_composite(lower.image, (0, upper.height + gap))
    total = upper.above + upper.below + gap + lower.above + lower.below
    # 基线定在下半块的基线上
    return _Box(image=image, above=total - lower.below, below=lower.below,
                degraded=upper.degraded or lower.degraded)


def _render_fraction(numerator: str, denominator: str, size: int) -> _Box:
    top = _render_expression(numerator, max(6, int(size * 0.82)))
    bottom = _render_expression(denominator, max(6, int(size * 0.82)))
    width = max(top.width, bottom.width) + 4
    rule_height = max(1, size // 14)
    height = top.height + rule_height + 2 + bottom.height
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    image.alpha_composite(top.image, ((width - top.width) // 2, 0))
    rule_y = top.height + 1
    draw.rectangle([1, rule_y, width - 2, rule_y + rule_height - 1],
                   fill=(0, 0, 0, 255))
    image.alpha_composite(bottom.image, ((width - bottom.width) // 2,
                                         rule_y + rule_height + 1))
    center = height // 2
    return _Box(image=image, above=center, below=height - center,
                degraded=top.degraded or bottom.degraded)


def _render_sqrt(inner: str, size: int) -> _Box:
    body = _render_expression(inner, size)
    font = _font(int(size * 1.15))
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    sign_width = int(probe.textlength("√", font=font)) + 2
    image = Image.new("RGBA", (sign_width + body.width, body.height + 2),
                      (0, 0, 0, 0))
    ImageDraw.Draw(image).text((0, 0), "√", font=font, fill=(0, 0, 0, 255))
    image.alpha_composite(body.image, (sign_width, 2))
    draw = ImageDraw.Draw(image)
    draw.line([sign_width - 1, 1, image.width - 1, 1], fill=(0, 0, 0, 255),
              width=max(1, size // 16))
    return _Box(image=image, above=body.above + 2, below=body.below,
                degraded=body.degraded)


def _script(base: _Box, script: _Box, *, above: bool) -> _Box:
    """把 ``script`` 放到 ``base`` 的右上（上标）或右下（下标）。"""
    shift_up = max(1, base.above // 2) if above else 0
    shift_down = 0 if above else max(1, base.below // 2)
    width = base.width + script.width
    top_extra = max(0, script.above - shift_up)
    bottom_extra = max(0, script.below - shift_down)
    image = Image.new(
        "RGBA",
        (width, base.above + base.below + top_extra + bottom_extra),
        (0, 0, 0, 0),
    )
    base_y = top_extra
    image.alpha_composite(base.image, (0, base_y))
    script_y = base_y + (base.above - shift_up - script.above) if above \
        else base_y + (base.above + shift_down - script.above)
    image.alpha_composite(script.image, (base.width, max(0, script_y)))
    above_total = image.height - (base.below + bottom_extra)
    return _Box(image=image, above=above_total, below=base.below + bottom_extra,
                degraded=base.degraded or script.degraded)


def _fallback(text: str, size: int) -> _Box:
    """排不出来时的退化表示：**保留原文**并标成 degraded。

    刻意不"猜"用户想表达什么 —— 宁可显示 ``\\begin{pmatrix}`` 原文，
    也不要画出错误的东西（数学里画错比画丑严重得多）。
    """
    box = _render_plain(text, size)
    box.degraded = True
    return box


def _stack(base: _Box, sub: _Box | None, sup: _Box | None) -> _Box:
    """把上下限**堆在运算符的正上/正下**（``\\lim_{n\\to\\infty}`` 的正确排法）。"""
    width = max(base.width, sub.width if sub else 0, sup.width if sup else 0)
    gap = 1
    pieces: list[tuple[_Box, int]] = []
    height = 0
    if sup is not None:
        pieces.append((sup, height))
        height += sup.height + gap
    base_y = height
    height += base.height
    sub_y = height + gap
    if sub is not None:
        height += gap + sub.height
    image = Image.new("RGBA", (max(1, width), max(1, height)), (0, 0, 0, 0))
    for box, y in pieces:
        image.alpha_composite(box.image, ((width - box.width) // 2, y))
    image.alpha_composite(base.image, ((width - base.width) // 2, base_y))
    if sub is not None:
        image.alpha_composite(sub.image, ((width - sub.width) // 2, sub_y))
    above = base_y + base.above
    return _Box(image=image, above=above, below=height - above,
                degraded=base.degraded
                or (sub.degraded if sub else False)
                or (sup.degraded if sup else False))


def _render_expression(text: str, size: int) -> _Box:
    """把一段 LaTeX 排成一行（含上下标、分式、根号、符号替换）。"""
    boxes: list[_Box] = []
    index = 0
    #: 上一块是不是"可堆叠的运算符"（``\\lim`` / ``\\sum`` 这类）
    last_is_stackable = False

    def _take_scripts(position: int, script_size: int) -> tuple[_Box | None, _Box | None, int]:
        """吃掉紧随其后的 ``_...`` 与 ``^...``（顺序任意），返回 (下, 上, 新下标)。"""
        sub: _Box | None = None
        sup: _Box | None = None
        while position < len(text) and text[position] in "^_":
            is_super = text[position] == "^"
            argument, position = _group_at(text, position + 1)
            rendered = _render_expression(argument, script_size)
            if is_super:
                sup = rendered
            else:
                sub = rendered
        return sub, sup, position

    while index < len(text):
        char = text[index]

        # -- 上下标：作用在上一块上 --
        if char in "^_" and boxes:
            script_size = max(6, int(size * 0.72))
            sub, sup, index = _take_scripts(index, script_size)
            if last_is_stackable:
                # 运算符（lim / sum / int…）：上下限堆在**正上/正下**
                boxes[-1] = _stack(boxes[-1], sub, sup)
            else:
                if sub is not None:
                    boxes[-1] = _script(boxes[-1], sub, above=False)
                if sup is not None:
                    boxes[-1] = _script(boxes[-1], sup, above=True)
            continue

        # -- 命令 --
        if char == "\\":
            match = re.match(r"\\([A-Za-z]+)\s*", text[index:])
            if match:
                name = match.group(1)
                index += match.end()
                if name in ("frac", "dfrac", "tfrac"):
                    numerator, index = _group_at(text, index)
                    denominator, index = _group_at(text, index)
                    boxes.append(_render_fraction(numerator, denominator, size))
                    last_is_stackable = False
                    continue
                if name == "sqrt":
                    argument, index = _group_at(text, index)
                    boxes.append(_render_sqrt(argument, size))
                    last_is_stackable = False
                    continue
                if name in _FONT_COMMANDS:
                    # 字体类命令：**取内容继续排**，别因为不认识就整条退化
                    argument, index = _group_at(text, index)
                    boxes.append(_render_expression(argument, size))
                    last_is_stackable = False
                    continue
                if name in (
                    "begin", "end", "pmatrix", "bmatrix", "matrix", "cases",
                    "array", "align", "aligned", "overset", "underset",
                    "overline", "underline", "hat", "bar", "vec", "dot",
                ):
                    # 这些**不猜**：整条公式退化显示原文
                    # （数学里画错比画丑严重得多）
                    return _fallback(text, size)
                if name in _HSPACE:
                    boxes.append(_render_plain(_HSPACE[name], size))
                    last_is_stackable = False
                    continue
                symbol = _SYMBOLS.get(name)
                if symbol is None:
                    # **不认识就原样显示这一条命令**，而不是让整条公式退化 ——
                    # 一条公式里有个别生僻命令时，其余部分仍然应该正常排出
                    # （我第一版是整条退化，结果 \mathbb 让整行变成源码）。
                    unknown = _render_plain(f"\\{name}", size)
                    unknown.degraded = True
                    boxes.append(unknown)
                    last_is_stackable = False
                    continue
                if symbol:
                    boxes.append(_render_plain(symbol, size))
                last_is_stackable = name in _STACK_OPERATORS
                continue
            # 单个转义字符（\; \, \{ \} 等）
            if index + 1 < len(text):
                symbol = _SYMBOLS.get(text[index + 1])
                index += 2
                if symbol:
                    boxes.append(_render_plain(symbol, size))
                last_is_stackable = False
                continue
            index += 1
            continue

        # -- 普通字符（成段处理，避免逐字建图） --
        run_start = index
        while index < len(text) and text[index] not in "^_\\":
            index += 1
        chunk = text[run_start:index]
        if chunk:
            boxes.append(_render_plain(chunk, size))
        last_is_stackable = False
        continue

    return _hstack(boxes)


# --------------------------------------------------------------------------
# 对外接口
# --------------------------------------------------------------------------

#: 行内公式：$...$（不跨行、不匹配 $$）
_INLINE_RE = re.compile(r"(?<!\$)\$(?!\$)([^$\n]+?)\$(?!\$)")
#: 独立公式：$$...$$
_DISPLAY_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)


def render_formula(latex: str, *, size: int = 22,
                   scale: int = DEFAULT_SCALE) -> RenderResult:
    """把一条 LaTeX 公式渲染成图片。**永不抛异常**。"""
    source = (latex or "").strip()
    if not source:
        return RenderResult(source=source, error="空公式")
    try:
        box = _render_expression(source, max(8, int(size)))
        if box.width <= 1 or box.height <= 1:
            return RenderResult(source=source, error="公式为空")
        image = box.image
        if scale > 1:
            image = image.resize(
                (image.width * scale, image.height * scale), Image.LANCZOS
            )
        return RenderResult(image=image, degraded=box.degraded, source=source)
    except Exception as exc:  # noqa: BLE001 - 渲染失败不该影响生成
        log.debug("公式渲染失败：%s", source, exc_info=True)
        return RenderResult(source=source, error=f"{type(exc).__name__}: {exc}")


def formula_cache_name(latex: str, *, size: int = 22,
                       scale: int = DEFAULT_SCALE) -> str:
    """公式图片的文件名（内容哈希 → 同一条公式只存一份）。"""
    digest = hashlib.sha1(
        f"{size}|{scale}|{latex.strip()}".encode("utf-8")
    ).hexdigest()[:20]
    return f"eq_{digest}.png"


def render_to_png(latex: str, target: Path, *, size: int = 22,
                  scale: int = DEFAULT_SCALE) -> tuple[Path | None, bool]:
    """渲染并落盘。返回 ``(文件路径, 是否退化)``；失败返回 ``(None, False)``。"""
    result = render_formula(latex, size=size, scale=scale)
    if not result.ok:
        return None, False
    path = Path(target)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file():                 # 同一公式只写一次
            result.image.save(path, format="PNG")
        return path, result.degraded
    except OSError:
        log.warning("公式图片写入失败：%s", path, exc_info=True)
        return None, result.degraded


def iter_formulas(text: str):
    """按出现顺序产出 ``(匹配对象, 是否独立公式)``，供替换用。"""
    matches = [
        (match, False) for match in _INLINE_RE.finditer(text or "")
    ]
    matches += [
        (match, True) for match in _DISPLAY_RE.finditer(text or "")
    ]
    matches.sort(key=lambda pair: pair[0].start())
    return matches


__all__ = [
    "DEFAULT_SCALE",
    "EQUATION_DIR_NAME",
    "RenderResult",
    "formula_cache_name",
    "iter_formulas",
    "render_formula",
    "render_to_png",
]
