"""把 Word 公式（OMML）转换成 LaTeX。

为什么需要这个模块
------------------
需求："文字形pdf、doc/docx 仍然插入文字（**公式部分插入图片**）"。

但 Word 里的公式**不是文字**：它是一套 XML（OMML，
``<m:oMath>`` / ``<m:f>`` / ``<m:sSup>`` …）。``paragraph.text``
**完全看不到它** —— 所以原来公式要么整段消失，要么只能拍平成一行字符。

要把它变成图片，就必须先把它变成 :mod:`gwp.services.math_render`
认识的东西 —— 也就是 LaTeX。这个模块就干这一件事。

支持范围（覆盖真实文档里的绝大多数公式）
----------------------------------------
* 分式 ``m:f`` -> ``\\frac{}{}``
* 上标/下标 ``m:sSup`` / ``m:sSub`` / ``m:sSubSup`` -> ``^{}`` / ``_{}``
* 根号 ``m:rad`` -> ``\\sqrt{}``
* 大型运算符 ``m:nary``（求和、积分）-> ``\\sum_{}^{}`` / ``\\int_{}^{}``
* 括号 ``m:d`` -> ``\\left( \\right)``（会自动选 ``()[]{}``）
* 函数 ``m:func`` -> ``\\sin`` 等正体
* 重音 ``m:acc`` / 上划线 ``m:bar`` -> ``\\hat{}`` / ``\\overline{}``
* 矩阵 ``m:m`` -> ``\\begin{matrix}…\\end{matrix}``
* 常用符号表（``m:r`` 里的 Unicode 符号 -> LaTeX 命令）

**认不出来的一律退回纯文字**：宁可显示得朴素，也不要生成一条渲染不出来的
LaTeX（数学里画错比画丑严重得多）。
"""

from __future__ import annotations

import logging
import re

log = logging.getLogger(__name__)

#: OMML 命名空间
_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"

#: Unicode 数学符号 -> LaTeX 命令。
#:
#: Word 公式里的字符是 Unicode（``ε``、``∑``），而我们的渲染器吃 LaTeX，
#: 所以要把它们翻译回去。只列真正常见的。
_UNICODE_TO_LATEX: dict[str, str] = {
    "α": r"\alpha", "β": r"\beta", "γ": r"\gamma", "δ": r"\delta",
    "ε": r"\varepsilon", "ϵ": r"\epsilon", "ζ": r"\zeta", "η": r"\eta",
    "θ": r"\theta", "ϑ": r"\vartheta", "ι": r"\iota", "κ": r"\kappa",
    "λ": r"\lambda", "μ": r"\mu", "ν": r"\nu", "ξ": r"\xi", "π": r"\pi",
    "ρ": r"\rho", "σ": r"\sigma", "ς": r"\varsigma", "τ": r"\tau",
    "υ": r"\upsilon", "φ": r"\varphi", "ϕ": r"\phi", "χ": r"\chi",
    "ψ": r"\psi", "ω": r"\omega",
    "Γ": r"\Gamma", "Δ": r"\Delta", "Θ": r"\Theta", "Λ": r"\Lambda",
    "Ξ": r"\Xi", "Π": r"\Pi", "Σ": r"\Sigma", "Υ": r"\Upsilon",
    "Φ": r"\Phi", "Ψ": r"\Psi", "Ω": r"\Omega",
    "×": r"\times", "÷": r"\div", "·": r"\cdot", "⋅": r"\cdot",
    "±": r"\pm", "∓": r"\mp", "≤": r"\le", "≥": r"\ge", "≠": r"\ne",
    "≈": r"\approx", "≡": r"\equiv", "∼": r"\sim", "∝": r"\propto",
    "∈": r"\in", "∉": r"\notin", "⊂": r"\subset", "⊃": r"\supset",
    "⊆": r"\subseteq", "⊇": r"\supseteq", "∪": r"\cup", "∩": r"\cap",
    "∅": r"\emptyset", "∀": r"\forall", "∃": r"\exists", "¬": r"\neg",
    "∞": r"\infty", "∂": r"\partial", "∇": r"\nabla", "√": r"\sqrt",
    "→": r"\to", "←": r"\leftarrow", "↔": r"\leftrightarrow",
    "⇒": r"\Rightarrow", "⇐": r"\Leftarrow", "⇔": r"\Leftrightarrow",
    "∫": r"\int", "∬": r"\iint", "∮": r"\oint",
    "∑": r"\sum", "∏": r"\prod",
    "′": "'", "″": "''", "…": r"\ldots", "⋯": r"\cdots",
    "∠": r"\angle", "⊥": r"\perp", "∥": r"\parallel",
}

#: ``m:nary`` 的算子字符 -> LaTeX
_NARY: dict[str, str] = {
    "∑": r"\sum", "∏": r"\prod", "∫": r"\int", "∬": r"\iint",
    "∮": r"\oint", "⋃": r"\bigcup", "⋂": r"\bigcap",
}

#: 括号选项（OMML 的 m:begChr / m:endChr 没给时的默认）
_DEFAULT_DELIMITERS = {"(", ")", "[", "]", "{", "}", "|", "‖", "⟨", "⟩"}

#: 这些字符在 LaTeX 里要转义
_ESCAPE = {"%": r"\%", "&": r"\&", "#": r"\#", "_": r"\_", "$": r"\$"}


def _tag(element) -> str:
    """去掉命名空间前缀的标签名。"""
    return str(getattr(element, "tag", "")).replace(_NS, "")


def _children(element) -> list:
    return [child for child in list(element)]


def _find(element, name: str):
    """取第一个名为 ``m:<name>`` 的直接子元素。"""
    for child in list(element):
        if _tag(child) == name:
            return child
    return None


def _find_all(element, name: str) -> list:
    return [child for child in list(element) if _tag(child) == name]


def _text_latex(raw: str) -> str:
    """把一串文字转成 LaTeX 片段（符号查表 + 转义）。"""
    out: list[str] = []
    for char in raw or "":
        if char in _UNICODE_TO_LATEX:
            out.append(_UNICODE_TO_LATEX[char] + " ")
            continue
        if char in _ESCAPE:
            out.append(_ESCAPE[char])
            continue
        out.append(char)
    return "".join(out).strip()


def _run_text(run) -> str:
    """``m:r`` -> 文字（含其中的 ``m:t``）。"""
    parts: list[str] = []
    for node in run.iter():
        if _tag(node) == "t":
            parts.append(node.text or "")
    return "".join(parts)


def _subscript_text(element_name_wrap) -> str:
    return ""


def _convert(element, depth: int = 0) -> str:
    """递归把 OMML 元素转成 LaTeX。深度超限就退回文字。"""
    if depth > 24 or element is None:
        return ""
    name = _tag(element)

    # ---- 文字 run ----
    if name == "r":
        return _text_latex(_run_text(element))

    # ---- 分式 m:f ----
    if name == "f":
        num = _convert(_find(element, "num"), depth + 1)
        den = _convert(_find(element, "den"), depth + 1)
        if not num and not den:
            return ""
        return rf"\frac{{{num}}}{{{den}}}"

    # ---- 上标 / 下标 / 上下标 ----
    if name in ("sSup", "sSub", "sSubSup"):
        base = _convert(_find(element, "e"), depth + 1)
        if name in ("sSup", "sSubSup"):
            sup = _convert(_find(element, "sup"), depth + 1)
            base = f"{base}^{{{sup}}}" if sup else base
        if name in ("sSub", "sSubSup"):
            sub = _convert(_find(element, "sub"), depth + 1)
            base = f"{base}_{{{sub}}}" if sub else base
        return base

    # ---- 根号 m:rad ----
    if name == "rad":
        body = _convert(_find(element, "e"), depth + 1)
        degree = _convert(_find(element, "deg"), depth + 1)
        if degree:
            return rf"\sqrt[{degree}]{{{body}}}"
        return rf"\sqrt{{{body}}}"

    # ---- 大型运算符 m:nary（求和 / 积分）----
    if name == "nary":
        chr_node = _find(element, "naryPr")
        operator = r"\int"
        if chr_node is not None:
            char = chr_node.get(_NS + "chr") or chr_node.get("chr") or ""
            operator = _NARY.get(char, "")
            if not operator:
                return _fallback_text(element)
        elif chr_node is None:
            operator = r"\int"
        sub = _convert(_find(element, "sub"), depth + 1)
        sup = _convert(_find(element, "sup"), depth + 1)
        body = _convert(_find(element, "e"), depth + 1)
        limits = ""
        if sub:
            limits += f"_{{{sub}}}"
        if sup:
            limits += f"^{{{sup}}}"
        return f"{operator}{limits} {body}".strip()

    # ---- 括号 m:d ----
    if name == "d":
        props = _find(element, "dPr")
        begin, end = "(", ")"
        if props is not None:
            begin = props.get(_NS + "begChr") or props.get("begChr") or "("
            end = props.get(_NS + "endChr") or props.get("endChr") or ")"
        inner = "".join(_convert(child, depth + 1)
                        for child in _find_all(element, "e"))
        return rf"\left{begin} {inner} \right{end}" if inner else ""

    # ---- 函数 m:func ----
    if name == "func":
        fname = _convert(_find(element, "fName"), depth + 1)
        body = _convert(_find(element, "e"), depth + 1)
        return f"{fname} {body}".strip()

    # ---- 重音 / 上划线 ----
    if name == "acc":
        props = _find(element, "accPr")
        char = ""
        if props is not None:
            char = props.get(_NS + "chr") or props.get("chr") or ""
        body = _convert(_find(element, "e"), depth + 1)
        command = {r"\hat": "hat", "^": "hat", "¯": "bar",
                   "→": "vec", ".": "dot"}.get(
            _UNICODE_TO_LATEX.get(char, char), "hat")
        return rf"\{command}{{{body}}}"

    if name == "bar":
        body = _convert(_find(element, "e"), depth + 1)
        return rf"\overline{{{body}}}"

    # ---- 矩阵 m:m ----
    if name == "m":
        rows: list[str] = []
        for mr in _find_all(element, "mr"):
            cells = [_convert(child, depth + 1)
                     for child in _find_all(mr, "e")]
            rows.append(" & ".join(cells))
        if rows:
            return r"\begin{matrix}" + r" \\ ".join(rows) + r"\end{matrix}"
        return ""

    # ---- 上/下限块（本身不产生符号，只把内容接起来）----
    if name in ("num", "den", "e", "sub", "sup", "deg", "fName", "oMath",
                "oMathPara", "eqArr", "limLow", "limUpp"):
        if name in ("limLow", "limUpp"):
            base = _convert(_find(element, "e") or _find(element, "lim"),
                            depth + 1)
            limit = _convert(_find(element, "lim") or _find(element, "e"),
                             depth + 1)
            if name == "limLow":
                return f"{base}_{{{limit}}}"
            return f"{base}^{{{limit}}}"
        return "".join(_convert(child, depth + 1)
                       for child in _children(element))

    # ---- 属性块 / 其它：跳过，不影响文字 ----
    if name.endswith("Pr") or name in ("ctrlPr", "rPr", "fPr", "sSupPr",
                                       "sSubPr", "dPr", "naryPr", "radPr",
                                       "funcPr", "accPr", "barPr", "mPr"):
        return ""

    # ---- 认不出来：退回纯文字（不猜）----
    return _fallback_text(element)


def _fallback_text(element) -> str:
    """把元素里所有 ``m:t`` 文字取出来，作为"看不懂时"的保底。"""
    try:
        return _text_latex("".join(
            node.text or "" for node in element.iter() if _tag(node) == "t"
        ))
    except Exception:  # noqa: BLE001
        return ""


def omml_to_latex(element) -> str:
    """把一段 OMML（``m:oMath`` / ``m:oMathPara``）转成 LaTeX。

    转不出来（或结果里没有任何"公式感"）时返回空串 ——
    调用方据此退回纯文字，**绝不硬凑**。
    """
    try:
        latex = _convert(element)
    except Exception:  # noqa: BLE001
        log.debug("OMML 转换失败", exc_info=True)
        return ""
    latex = re.sub(r"\s+", " ", latex or "").strip()
    # 全是普通字母数字的话，当成"就是文字"，不必当公式渲染
    if not latex:
        return ""
    if not re.search(r"[\\^_{}]", latex) and len(latex) <= 3:
        return ""
    return latex


__all__ = ["omml_to_latex"]
