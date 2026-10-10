"""「长庚知道」——AI 在总结末尾补充的知识点，每页左上角带标记。

需求
----
> 生成AI总结时，可以在文档最后加入一些关于知识点的你的补充
> （标记 "长庚知道" 在页面左上角）

所以这一块的产物是**总结 PDF 最后面的几页**，每页左上角印着
「长庚知道」四个字，内容是对当前书目**知识点**的补充。

关于"补充"的定位（很重要）
--------------------------
总结的正文是**用户自己的资料**（图片或排版好的页面），
这一块是**唯一由 AI 写文字的地方**，所以必须有明确边界：

* 只讲**补充**：术语辨析、常见误区、与其它知识的联系、延伸；
* **不重复**资料里已有的内容 —— 复述一遍没有任何价值，还占篇幅；
* 明确标注这是 AI 的补充，**不混进正文**，不和资料页混在一起；
* 生成失败**不算错误**：资料页该出还是出，只是少一段补充。

参数（模型、温度、上限）由 :mod:`gwp.services.ai_options` 统一决定，
不在这里硬编码 —— 换模型不用改这个文件。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

#: 左上角那个标记的文字
LABEL = "长庚知道"

#: 每个来源最多取多少字符送给 AI 当"这本书讲什么"的线索
HINT_CHARS_PER_SOURCE = 1200

#: 最多送多少个来源（再多就该分次生成，而不是一次塞进去）
MAX_HINT_SOURCES = 24

#: AI 写多少字左右（给模型的软约束）
TARGET_CHARS = 700

#: 提示词版本（改了要能看出来是新版）
PROMPT_REVISION = 1

SYSTEM_PROMPT = f"""你是一位耐心、严谨的理科与工科辅导者，自称「长庚」。

学习者在整理一本书目的资料（笔记、易错题、扫描讲义）。你的任务是在这些资料的
**末尾**写一小节**补充**。

# 只写"补充"，不要复述
* **不要**重复资料里已经写过的内容 —— 复述一遍没有任何价值；
* 只写下面这几类：
  1. **概念辨析**：容易混的两个概念到底差在哪；
  2. **常见误区**：学习者最容易在这里犯什么错，为什么会犯；
  3. **知识联系**：这个概念和别的章节/别的科目怎么连起来；
  4. **延伸**：值得再往下想一步的地方（点到为止，别写成教材）。

# 硬性要求
1. 用 Markdown 写；**小标题**用 `###`；
2. 篇幅 **{TARGET_CHARS} 字左右**（上下浮动 30% 都可以）；
3. **公式**用 LaTeX，行内 `$...$`、独立公式 `$$...$$`；
4. 语言**具体**：说"把 ε 取成 ε/2 是因为……"，
   不要写"注意理解概念"这类空话；
5. 资料里看不出来的东西，**宁可不说**，不要编；
6. 直接给正文，**不要**写"好的""以下是补充"这类客套开场。"""


def build_hint(chapters) -> str:
    """把各份资料"讲什么"整理成给 AI 的线索。

    优先用 :attr:`ChapterPlan.hint_text` —— 那是转页面时**顺手留下**的，
    不用重新读一遍文件（几百页的 PDF 重读一次就是白等一场）。
    没留下（例如图片型资料没有文字层）就用文件名兜底：
    文件名往往就是章节名，比空着有用。
    """
    blocks: list[str] = []
    for chapter in list(chapters)[:MAX_HINT_SOURCES]:
        if getattr(chapter, "error", ""):
            continue
        source = Path(chapter.source)
        text = re.sub(r"\s+", " ", getattr(chapter, "hint_text", "") or "").strip()
        if not text:
            text = _fallback_hint(source)
        preview = text[:HINT_CHARS_PER_SOURCE] or "（扫描件，没有文字层）"
        blocks.append(f"## 来源：{chapter.label}\n{preview}")
    return "\n\n".join(blocks)


def _fallback_hint(source: Path) -> str:
    """线索为空时的兜底：文件名。

    图片型资料（扫描件、png）没有文字层，唯一能拿到的信息就是文件名。
    它能用吗？能用 —— 学生给资料命名通常就是章节名
    （"第二章 导数与微分.pdf"），比什么都不给强得多。
    """
    return source.stem


def generate_supplement(ai_manager, chapters) -> tuple[str, str]:
    """让 AI 写补充。返回 ``(markdown, 说明)``；失败时 markdown 为空。

    ``说明`` 会显示给用户（例如"AI 不可用"），失败**不算错误**。
    """
    from gwp.ai.base import ChatMessage

    hint = build_hint(chapters)
    if not hint.strip():
        return "", "没有可用于生成补充的内容"
    user = (
        "以下是这个书目的资料来源与开头内容：\n\n"
        f"{hint}\n\n"
        f"请按系统提示的要求，写约 {TARGET_CHARS} 字的**知识点补充**。"
    )
    messages = [
        ChatMessage(role="system", content=SYSTEM_PROMPT),
        ChatMessage(role="user", content=user),
    ]
    try:
        text, provider = ai_manager.chat_with_fallback(
            messages, None, None, None, None
        )
    except Exception as exc:  # noqa: BLE001 - 补充失败不该让总结失败
        log.warning("生成「%s」补充失败", LABEL, exc_info=True)
        return "", f"AI 不可用（{type(exc).__name__}），已跳过补充"
    text = (text or "").strip()
    if not text:
        return "", "AI 返回了空内容，已跳过补充"
    return text, f"AI（{provider}）已补充约 {len(text)} 字"


def render_supplement_pdf(markdown_text: str, output_path: Path, *,
                          base_dir: Path | None = None,
                          theme: str = "light") -> Path:
    """把补充内容排成 PDF，并给**每一页左上角**印上「长庚知道」。

    排版复用现有的 Markdown → PDF 导出器（它会处理标题、表格、公式、图片），
    这里只负责两件额外的事：

    1. 在最前面加一个标题，让读者知道这一段是 AI 的补充；
    2. 每页左上角盖一个标记（需求明确要求"标记在页面左上角"）。
    """
    from gwp.services.pdf_exporter import PDFExportOptions, export_markdown_to_pdf

    heading = (
        f"# {LABEL}（AI 补充）\n\n"
        "> 以下内容由 AI 根据资料主题补充，**不属于你的原始资料**。\n\n"
        "---\n\n"
    )
    body = heading + markdown_text.strip() + "\n"
    options = PDFExportOptions(
        theme=theme,
        page_numbers=True,
        base_dir=base_dir,
    )
    # 注意：这里不传 page_numbers 关键字（它已经在 options 里设好了），
    # 而且必须让导出器**先写出来**，我们再去补左上角标记。
    export_markdown_to_pdf(body, output_path, options, base_dir=base_dir)
    _stamp_label(output_path)
    return output_path


def _stamp_label(pdf_path: Path) -> int:
    """在每一页左上角印「长庚知道」，返回盖了几页。

    位置：正文区域（页边距之内）的左上角。
    需求说的是"页面左上角"，放在正文左上角最符合直觉，
    也不会被阅读器的页边距裁掉。

    **盖章必须写在页边距内的安全区**，所以这里按页面尺寸算比例：
    左边距约 10%、顶部约 4.5% —— 对 A4 来说就是左边约 21mm、顶约 13mm，
    正好落在 18mm 页边距附近偏内，任何阅读器都看得到。
    """
    import pymupdf

    stamped = 0
    with pymupdf.open(str(pdf_path)) as doc:
        for page in doc:
            rect = page.rect
            x = rect.width * 0.10
            baseline = rect.height * 0.055
            _draw_label(page, pymupdf, x, baseline, rect.width)
            stamped += 1
        # 用全量另存（带 garbage）而不是增量保存：
        # 这个文件是刚生成的，全量另存能保证体积干净。
        temporary = pdf_path.with_name(pdf_path.stem + ".stamped.pdf")
        doc.save(str(temporary), garbage=4, deflate=True)
    temporary.replace(pdf_path)
    return stamped


def _draw_label(page, pymupdf, x: float, baseline: float, width: float) -> None:
    """画一个"栏目标记"：文字 + 一条细底线。

    中文用 PyMuPDF 内置的 ``china-s``（宋体）—— 不需要随包附带字体文件，
    这是选它的原因（安装包里少一个字体就少一份出错的可能）。
    """
    color = (0.55, 0.40, 0.12)
    label = LABEL
    fontname = "china-s"
    size = 9.5
    try:
        page.insert_text((x, baseline), label, fontname=fontname,
                         fontsize=size, color=color)
    except Exception:  # noqa: BLE001 - 中文字体不可用时退回英文标记
        log.debug("中文字体不可用，改用 ASCII 标记", exc_info=True)
        label = "ChangGeng"
        fontname = "helv"
        size = 8.5
        page.insert_text((x, baseline), label, fontname=fontname,
                         fontsize=size, color=color)
    try:
        width_pt = pymupdf.get_text_length(label, fontname=fontname, fontsize=size)
    except Exception:  # noqa: BLE001
        width_pt = len(label) * size * 0.6
    try:
        page.draw_line(
            pymupdf.Point(x, baseline + 3.0),
            pymupdf.Point(x + width_pt, baseline + 3.0),
            color=(0.86, 0.74, 0.48), width=0.7,
        )
    except Exception:  # noqa: BLE001 - 底线画不上不影响标记本身
        log.debug("标记底线绘制失败", exc_info=True)


__all__ = [
    "LABEL",
    "PROMPT_REVISION",
    "SYSTEM_PROMPT",
    "build_hint",
    "generate_supplement",
    "render_supplement_pdf",
]
