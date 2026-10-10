"""把文件夹里的多张图片，用 AI 提取成一份合并的 Markdown。

需求原话：

> 增加文件夹内多图片AI提取内容（无把握识别准确就直接插入图片）并合并为md功能

这里的"没有把握就直接插入图片"是整个功能的**安全底线**：
宁可少写一行字、多插一张图，也不要让 AI 编出一段看着很像、
实际是幻觉的正文。用户是想拿这份 md 当复习资料用的，
**编造的内容比缺失的内容危险得多**。

因此本模块把"可靠 / 不可靠"的判断做成**纯函数**，
不依赖界面、不依赖网络，可以直接被测试覆盖（见 tests/smoke_core.py）。

分三层：

* :func:`collect_images` —— 找出一个文件夹里的图片（含顺序）；
* :func:`build_prompt` / :func:`evaluate_extraction` —— 给 AI 的指令，
  以及**判断它这次答得靠不靠谱**；
* :func:`build_markdown` —— 把逐张的结果拼成最终 md（含图片嵌入）。

界面层（``gwp/ui/dialogs/image_digest_dialog.py``）只负责
"显示列表 / 收发剪贴板 / 落盘"，判断逻辑全在这里。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# --------------------------------------------------------------------------
# 图片识别
# --------------------------------------------------------------------------

#: 认作"图片"的扩展名（与导入白名单保持一致）
IMAGE_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff",
})

#: 自然排序用的"数字段"（让 `第2页` 排在 `第10页` 前面，而不是按字典序）
_NUMBER_RE = re.compile(r"(\d+)")


def is_image(path: Path | str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def natural_key(path: Path | str) -> tuple:
    """自然排序键：``第2页`` 在 ``第10页`` 之前。

    朴素的 ``sorted()`` 按字符比较，会把 ``第10页`` 排到 ``第2页`` 前面 ——
    对"按页拍的课件照片"来说顺序全乱。所以把连续数字当整数比。
    """
    name = Path(path).name.lower()
    parts = _NUMBER_RE.split(name)
    key: list = []
    for index, part in enumerate(parts):
        if index % 2 == 1:                 # 奇数位是数字
            key.append((1, int(part), ""))
        else:
            key.append((0, 0, part))
    return tuple(key)


def collect_images(folder: Path | str, *, recursive: bool = False) -> list[Path]:
    """列出文件夹里的图片，按**自然顺序**排好。

    ``recursive=True`` 时连子文件夹一起收（适合"一章一个子文件夹"的情况）。
    隐藏文件（``.`` 开头）跳过。
    """
    root = Path(folder)
    if not root.is_dir():
        return []
    found: list[Path] = []
    try:
        iterator = root.rglob("*") if recursive else root.iterdir()
        for entry in iterator:
            if entry.is_file() and is_image(entry) and not entry.name.startswith("."):
                found.append(entry)
    except OSError:
        return []
    return sorted(found, key=natural_key)


# --------------------------------------------------------------------------
# 给 AI 的提示词
# --------------------------------------------------------------------------

IMAGE_EXTRACT_PROMPT = """请把这张图片里的**全部书面内容**转写成 Markdown，供我整理复习资料用。

要求：
1. **完整转写，不要概括**：正文、标题、公式、表格、代码、注释、页码、手写批注都要写出来。
2. **公式用 LaTeX**：行内 `$...$`，独立 `$$...$$`。看不清的符号用 `\\square` 占位。
3. **表格用 Markdown 表格**；代码用围栏代码块并标注语言。
4. **图片里的图（示意图、图表、几何图、照片）**：不要凭空描述细节，
   用一行 ``> [图：<一句话说明它是什么>]`` 标出位置即可，我会自己插图。
5. **绝对不要猜测**。任何你看不清、不确定、被遮挡、模糊的地方，
   就地写成 ``[[无法辨认]]``，不要用"大概是……"这类推测补全。
6. 只输出转写结果本身，**不要**加"以下是我提取的内容"这类开场白。
"""


def build_prompt(index: int, total: int, image_name: str = "") -> str:
    """拼一张图的完整提示词（图片本身由用户粘贴给网页版 AI）。"""
    head = f"（这是第 {index}/{total} 张"
    if image_name:
        head += f"，文件名：{image_name}"
    head += "）"
    return f"{head}\n\n{IMAGE_EXTRACT_PROMPT}"


# --------------------------------------------------------------------------
# "有没有把握" —— 判断一次提取可不可靠
# --------------------------------------------------------------------------

#: 出现这些词，基本可以认为 AI 在说"我看不清"
_HEDGE_WORDS = (
    "无法辨认", "无法识别", "无法看清", "看不清", "不可辨认", "模糊不清",
    "无法读取", "图片不清晰", "未能识别", "无法确定", "不确定", "可能不是",
    "抱歉", "无法完成", "无法提供", "cannot", "unable to", "not clear",
)

#: AI 明说自己没把握时留下的占位符
_PLACEHOLDERS = ("[[无法辨认]]", "[无法辨认]", "（无法辨认）", "(无法辨认)")

#: 结果至少要有的字符数（少于此基本等于"什么都没读出来"）
MIN_CHARS = 12

#: 长篇文档（按图片数量粗估）单张至少该有的字符数
MIN_CHARS_PER_IMAGE = 24


@dataclass
class Verdict:
    """一次提取的可靠性判断结果。"""

    reliable: bool
    reasons: list[str] = field(default_factory=list)

    @property
    def reason_text(self) -> str:
        return "；".join(self.reasons) if self.reasons else "识别正常"


def evaluate_extraction(
    text: str,
    *,
    min_chars: int = MIN_CHARS,
    user_unsure: bool = False,
) -> Verdict:
    """判断一次 AI 提取结果**够不够可信**。

    宁可误判为"不可信"（那就插图片），也不要误判为"可信"（那会留下幻觉）。
    所以这里的阈值都偏保守。

    判为不可信的情况：

    * 调用方标了"没把握"（``user_unsure``）—— 两种情况会带这个标记：
      用户手动标记，或本模块（界面层）自动判定后回头补上这个标记；
      用户看过原文，他说不准就是不准，优先于其它判断；
    * 正文过短（连一行都没读出来）；
    * 出现"无法辨认 / 看不清 / 抱歉"这类自认失败的措辞；
    * 出现 ``[[无法辨认]]`` 占位符（说明 AI 自己标了盲区）；
    * 替换字符（``\\ufffd``）或乱码方块占比过高 —— 通常是编码/字体问题。
    """
    reasons: list[str] = []
    if user_unsure:
        reasons.append("被标记为没把握（识别结果未被采信）")

    stripped = (text or "").strip()
    if len(stripped) < max(1, int(min_chars)):
        reasons.append(f"提取到的内容太短（{len(stripped)} 字符）")
        return Verdict(reliable=False, reasons=reasons)   # 短到没必要再查别的

    lowered = stripped.lower()
    hedges = [word for word in _HEDGE_WORDS if word.lower() in lowered]
    if hedges:
        reasons.append("AI 自己表示看不清：" + "、".join(dict.fromkeys(hedges[:3])))

    placeholders = sum(stripped.count(mark) for mark in _PLACEHOLDERS)
    if placeholders:
        reasons.append(f"有 {placeholders} 处被标为无法辨认")

    # 乱码比例：只统计"可能是乱码"的字符，避免把正常中文误判
    suspicious = stripped.count("\ufffd") + stripped.count("□")
    if suspicious >= 4 and suspicious / max(1, len(stripped)) > 0.02:
        reasons.append(f"乱码字符偏多（{suspicious} 个）")

    return Verdict(reliable=not reasons, reasons=reasons)


# --------------------------------------------------------------------------
# 组装最终 Markdown
# --------------------------------------------------------------------------

#: 不可信时插在图片前的醒目提示
UNSURE_BANNER = (
    "> ⚠️ **这一页没能可靠识别**，因此直接插入原图，请自行查看。\n"
    "> 原因：{reason}\n"
)


@dataclass
class ImageResult:
    """一张图的处理结果。"""

    image: Path
    #: AI 转写出来的正文（空表示没提取）
    text: str = ""
    #: 用户是否手动标记"没把握"
    user_unsure: bool = False
    #: 用户手动改了正文（此时不再自动判不可信 —— 人改过的就是权威）
    edited: bool = False

    @property
    def verdict(self) -> Verdict:
        if self.edited and self.text.strip():
            return Verdict(reliable=True, reasons=[])
        return evaluate_extraction(self.text, user_unsure=self.user_unsure)

    @property
    def usable(self) -> bool:
        return self.verdict.reliable


def _demote_headings(text: str, levels: int = 2) -> str:
    """把正文里的 Markdown 标题整体降级。

    为什么需要：每张图我用了 ``## N. 文件名`` 当节标题，而 AI 转写出来的
    正文里也常有 ``## 第一节`` 之类的标题。两者同级会让结构彻底乱掉
    （看图的人分不清"这是图片分隔"还是"这是内容标题"）。
    把内容标题统一降两级，层次就清楚了。
    """
    if levels <= 0:
        return text
    out: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            out.append(line)
            continue
        if not in_fence and stripped.startswith("#"):
            hashes = len(stripped) - len(stripped.lstrip("#"))
            if 1 <= hashes <= 6:
                out.append("#" * min(6, hashes + levels) + stripped[hashes:])
                continue
        out.append(line)
    return "\n".join(out)


def _relative_url(image: Path, base_dir: Path) -> str:
    """Markdown 里图片地址：优先相对路径（便于整本打包搬走）。"""
    try:
        return image.relative_to(base_dir).as_posix()
    except ValueError:
        return image.as_posix()


def build_markdown(
    results: list[ImageResult],
    *,
    base_dir: Path,
    title: str = "",
    include_source_note: bool = True,
) -> str:
    """把逐张结果拼成一份 Markdown。

    结构（每张图一节）：

    * 可靠的 → 正文；标题里带原图名，便于回查；
    * 不可靠的 → **醒目提示 + 直接嵌入原图**（需求的核心要求）。

    ``base_dir`` 用来把图片路径写成相对形式（相对这份 md 所在的目录），
    这样整个文件夹拷到别处，图片链接依然有效。
    """
    base = Path(base_dir)
    name = title or (base.name or "图片提取")
    stamp = datetime.now().strftime("%Y-%m-%d")
    lines: list[str] = [f"# {name} · 图片提取", ""]

    if include_source_note:
        total = len(results)
        images = "、".join(r.image.name for r in results[:6])
        if total > 6:
            images += f" 等 {total} 张"
        lines += [
            f"> 来源：`{base.name}` 下的 {total} 张图片（{images}）。",
            f"> 由 AI 逐张转写后合并，生成日期 {stamp}。",
            "> **未能可靠识别的部分直接插入了原图**，未做任何推测性补全。",
            "",
        ]

    if not results:
        lines += ["_这个文件夹里没有找到图片。_", ""]
        return "\n".join(lines)

    reliable = sum(1 for r in results if r.usable)
    lines += [
        "## 总览",
        "",
        f"| 项目 | 数量 |",
        f"| --- | --- |",
        f"| 图片总数 | {len(results)} |",
        f"| 文字提取成功 | {reliable} |",
        f"| 插入原图（无法可靠识别） | {len(results) - reliable} |",
        "",
    ]

    for order, result in enumerate(results, start=1):
        lines += [f"## {order}. {result.image.name}", ""]
        verdict = result.verdict
        if verdict.reliable:
            # 正文里的标题降两级，避免和 "## N. 文件名" 撞级、破坏文档结构
            lines += [_demote_headings(result.text.strip(), 2), ""]
        else:
            lines += [
                UNSURE_BANNER.format(reason=verdict.reason_text).rstrip(),
                "",
                f"![{result.image.name}]({_relative_url(result.image, base)})",
                "",
            ]
    return "\n".join(lines).rstrip() + "\n"


def suggest_filename(folder_name: str, *, when: datetime | None = None) -> str:
    """建议的输出文件名：``<文件夹名>_图片提取_<日期>.md``。"""
    stamp = (when or datetime.now()).strftime("%Y-%m-%d")
    stem = (folder_name or "图片").strip() or "图片"
    return f"{stem}_图片提取_{stamp}.md"


def summary_line(results: list[ImageResult]) -> str:
    """给状态栏用的一句话统计。"""
    if not results:
        return "没有可处理的图片"
    ok = sum(1 for r in results if r.usable)
    return f"共 {len(results)} 张：{ok} 张提取成功，{len(results) - ok} 张改为插入原图"


__all__ = [
    "IMAGE_EXTENSIONS",
    "IMAGE_EXTRACT_PROMPT",
    "UNSURE_BANNER",
    "ImageResult",
    "Verdict",
    "build_markdown",
    "build_prompt",
    "collect_images",
    "evaluate_extraction",
    "is_image",
    "natural_key",
    "suggest_filename",
    "summary_line",
]