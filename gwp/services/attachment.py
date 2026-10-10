"""AI 对话的**附件**：把用户选的文件变成 AI 能读的内容。

需求原话：

> AI助手新增附件上传功能 如果无法实现，想一个替代方案

"上传"在这里不能照字面做。原因很实在：

* 这个软件的 AI 默认是 DeepSeek 的**文本模型**，API 收不了文件；
* 就算换成支持视觉的模型，也只能看图，读不了 PDF / Word / Excel 的正文；
* 而"把文件编码后塞进对话"既没有标准做法，也会吃掉大量 token。

所以替代方案是**按文件类型走两条路**，而且**都是本地完成的**：

+----------------+------------------------------------------------------+
| 文件类型       | 做法                                                 |
+================+======================================================+
| PDF / Word /   | **本地提取文本**（`document_reader`），转成 Markdown  |
| PPT / Excel /  | 直接放进对话。**确定性、离线、免费、可核对**          |
| CSV / 文本 /   |                                                      |
| 代码           |                                                      |
+----------------+------------------------------------------------------+
| 图片           | 转交已有的「图片提取」流程：配了视觉模型就直接看图，  |
|                | 否则走网页版桥接（剪贴板 + 人工粘贴）                |
+----------------+------------------------------------------------------+

**这个划分不是妥协，而是各取所长**：文字类文件的提取是**确定性的**
（PDF 有文字层、docx 有结构化段落），比让 AI "看图猜字"可靠得多；
而图片恰恰相反 —— 只能靠视觉模型或人眼。

一条贯穿本模块的原则（与"图片提取"一致，见 `image_digest`）：

    **绝不假装读过。** 提取不出来、或图片没有视觉模型可用时，
    如实告诉用户"这份附件的内容没能传给 AI"，而不是让 AI
    对着一个文件名编内容。

界面层（``chat_panel``）只负责选文件、显示、并在发送时把
:func:`build_attachment_block` 的结果拼进提示词。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from gwp.core import constants as C
from gwp.services import document_reader

log = logging.getLogger(__name__)

#: 单个附件最多送进对话的字符数。
#: 取 20000 是因为：一份 20 页的讲义正文大约就是这个量级，
#: 再长的部分对问答帮助有限，却会把上下文挤满、让回答变差。
DEFAULT_PER_FILE_CHARS = 20_000

#: 一次对话里所有附件加起来的上限。
DEFAULT_TOTAL_CHARS = 60_000

#: 提取结果的三种状态
KIND_TEXT = "text"          # 本地提取出正文，可靠
KIND_IMAGE = "image"        # 图片：要交给视觉模型或人工
KIND_UNSUPPORTED = "unsupported"   # 认不出/提不出内容的类型


@dataclass
class Attachment:
    """一份待送进 AI 对话的附件。"""

    path: Path
    #: text / image / unsupported
    kind: str = KIND_TEXT
    #: 提取出来的 Markdown 正文（图片与不支持的类型为空）
    markdown: str = ""
    #: 原始字符数（截断前），用于如实告诉用户"被截断了"
    original_chars: int = 0
    #: 是否因为太长被截断
    truncated: bool = False
    #: 提取是否可靠（`document_reader` 的判断，例如扫描版 PDF 会是 False）
    reliable: bool = True
    #: 提取失败的原因（空表示没有出错）
    error: str = ""
    #: 说明性备注（来自 document_reader，例如"这份 PDF 没有文字层"）
    notes: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def suffix(self) -> str:
        return self.path.suffix.lower()

    @property
    def chars(self) -> int:
        return len(self.markdown)

    @property
    def has_text(self) -> bool:
        return bool(self.markdown.strip())

    @property
    def usable(self) -> bool:
        """这份附件能不能真的给 AI 提供信息。"""
        return self.kind == KIND_TEXT and self.has_text

    def describe(self) -> str:
        """给用户看的一行状态（界面上每个附件旁边显示这个）。"""
        if self.kind == KIND_IMAGE:
            return "图片（需要视觉模型或人工粘贴）"
        if self.kind == KIND_UNSUPPORTED:
            return self.error or "这个类型无法提取正文"
        if self.error:
            return f"提取失败：{self.error}"
        if not self.has_text:
            return "没有提取到正文"
        text = f"已提取 {self.chars} 字"
        if self.truncated:
            text += f"（原文 {self.original_chars} 字，超出部分未发送）"
        if not self.reliable:
            text += " · 提取质量可能不佳"
        return text


def budget_from_config(config) -> tuple[int, int]:
    """从配置读 (单文件上限, 总量上限)，带兜底。

    配置项是用户可以手改的，所以两项都要夹住下界，
    否则填个 0 或负数会让附件功能静默失效。
    """
    try:
        per_file = int(config.get("ai.attach_chars_per_file", DEFAULT_PER_FILE_CHARS)
                       or DEFAULT_PER_FILE_CHARS)
    except (TypeError, ValueError, AttributeError):
        per_file = DEFAULT_PER_FILE_CHARS
    try:
        total = int(config.get("ai.attach_chars_total", DEFAULT_TOTAL_CHARS)
                    or DEFAULT_TOTAL_CHARS)
    except (TypeError, ValueError, AttributeError):
        total = DEFAULT_TOTAL_CHARS
    return max(500, per_file), max(1000, total)


def extract_attachment(
    path: Path | str,
    *,
    per_file_chars: int = DEFAULT_PER_FILE_CHARS,
) -> Attachment:
    """把一份文件变成 :class:`Attachment`。

    图片不在这里提取（本模块不调用 AI），只标成 ``KIND_IMAGE``，
    由界面决定走视觉模型还是人工粘贴。
    """
    target = Path(path)
    lower = target.suffix.lower()

    if lower in C.IMAGE_EXTENSIONS:
        return Attachment(path=target, kind=KIND_IMAGE)

    if not target.is_file():
        return Attachment(
            path=target, kind=KIND_UNSUPPORTED, reliable=False,
            error="文件不存在（可能已被移动或删除）",
        )

    try:
        document = document_reader.extract(target)
    except Exception as exc:  # noqa: BLE001 - 单个附件失败不该影响别的
        log.warning("提取附件失败：%s", target, exc_info=True)
        return Attachment(
            path=target, kind=KIND_UNSUPPORTED, reliable=False,
            error=f"提取失败：{exc}",
        )

    markdown = document.markdown or ""
    original = len(markdown)
    truncated = False
    if per_file_chars > 0 and original > per_file_chars:
        markdown = markdown[:per_file_chars]
        truncated = True

    # 判定"这份附件到底有没有可用内容"。
    #
    # 两个坑：
    # 1. ``document_reader`` 对不认识的类型会返回 ``kind="binary"``、
    #    ``reliable=False``，而 markdown 里写的是一句**说明文字**
    #    （"> 无法解析的文件类型：xxx"）。如果只看"markdown 非空"，
    #    就会把这句说明当成正文喂给 AI —— 白占 token 还误导它。
    # 2. 所以除了 kind 判断，还加一道**按内容识别**的兜底：
    #    万一将来 reader 换了措辞（或者被注册了新 reader），
    #    句首的引用行仍然能识别出来。
    unsupported_markers = ("无法解析的文件类型", "暂不支持的文件类型")
    looks_like_notice = any(
        markdown.lstrip().startswith(f"> {marker}")
        for marker in unsupported_markers
    )
    is_binary = str(getattr(document, "kind", "")) == "binary"

    kind = KIND_TEXT
    error = ""
    if is_binary or looks_like_notice:
        kind = KIND_UNSUPPORTED
        markdown = ""
        if document.notes:
            error = document.notes[0]
        else:
            error = "这个类型无法直接读取（旧版 Office 请另存为 docx/pptx/xlsx）"
    elif not markdown.strip():
        kind = KIND_UNSUPPORTED
        error = document.error or "没能从这个文件里提取出文字（可能是扫描件或纯图片内容）"
    elif document.error:
        error = document.error

    return Attachment(
        path=target,
        kind=kind,
        markdown=markdown,
        original_chars=original,
        truncated=truncated,
        reliable=bool(document.reliable),
        error=error,
        notes=list(document.notes or []),
    )


def extraction_supported(path: Path | str) -> bool:
    """问一问这个类型**注册过读取器**没有（用于选文件时的过滤提示）。

    注意它回答的是"这个扩展名有没有 reader"，而不是"一定能提出正文"：
    例如 ``.doc`` 有 reader 但只会返回一句"旧版格式无法解析"，
    ``.pdf`` 若是扫描件也可能提不出文字。
    **真正判断能不能用要看 :func:`extract_attachment` 的结果**（``usable``）。
    """
    lower = Path(path).suffix.lower()
    if lower in C.IMAGE_EXTENSIONS:
        return True                     # 图片"支持"，只是走另一条路
    try:
        return lower in set(document_reader.supported_extensions())
    except Exception:  # noqa: BLE001
        return False


def build_attachment_block(
    attachments: list[Attachment],
    *,
    total_chars: int = DEFAULT_TOTAL_CHARS,
) -> str:
    """把所有附件拼成一段可以直接塞进提示词的文本。

    输出形如::

        【附件 1/2】第二章讲义.pdf（PDF，提取自本地文件）
        以下是它的完整内容：
        ...markdown...

        【附件 2/2】板书.jpg
        （这是一张图片，内容未包含在本次对话中：当前 AI 模型看不了图片。
          请在提问里说明你想了解什么，或改用「图片提取为 Markdown」。）

    **不可用的附件也照样列出来**，并说明为什么没内容 ——
    否则用户会以为附件已经传给 AI 了，从而相信一个其实没读过文件的回答。
    """
    usable = [a for a in attachments if a.kind == KIND_TEXT]
    blocks: list[str] = []
    remaining = max(0, int(total_chars))
    index = 0

    for attachment in attachments:
        index += 1
        head = f"【附件 {index}/{len(attachments)}】{attachment.name}"
        if attachment.kind == KIND_IMAGE:
            blocks.append(
                f"{head}\n"
                "（这是一张图片，**内容没有包含在本次对话里**："
                "当前 AI 模型看不了图片。想要它的内容，"
                "请用「工具 → 图片提取为 Markdown」，"
                "或在设置里配一个支持视觉的模型。）"
            )
            continue
        if not attachment.usable:
            reason = attachment.error or "没有提取到正文"
            blocks.append(f"{head}\n（这份附件的内容没能读取：{reason}）")
            continue

        text = attachment.markdown
        truncated_note = ""
        if len(text) > remaining:
            text = text[:remaining]
            truncated_note = (
                "\n（内容过长，本次只发送了前面一部分。）"
            )
        remaining -= len(text)
        label = _kind_label(attachment.suffix)
        blocks.append(
            f"{head}（{label}，提取自本地文件）"
            f"{'。注意：这份文件的提取质量可能不佳，请谨慎对待其中的细节。' if not attachment.reliable else ''}"
            f"\n以下是它的内容：\n{text}{truncated_note}"
        )

    if not blocks:
        return ""
    if usable:
        intro = (
            f"用户上传了 {len(attachments)} 份附件，"
            f"下面是它们的内容。请**基于这些内容**回答，"
            f"不要假装读过没给到你的部分。\n\n"
        )
    else:
        intro = (
            f"用户上传了 {len(attachments)} 份附件，"
            f"但**没有任何一份的内容成功传给了你**"
            f"（原因见下）。请如实告诉用户你看不到这些文件，"
            f"并建议他改用能读取的方式，不要编造文件内容。\n\n"
        )
    return intro + "\n\n".join(blocks)


def _kind_label(suffix: str) -> str:
    mapping = {
        ".pdf": "PDF", ".doc": "Word", ".docx": "Word",
        ".ppt": "PowerPoint", ".pptx": "PowerPoint",
        ".xls": "Excel", ".xlsx": "Excel", ".xlsm": "Excel",
        ".csv": "CSV 表格", ".tsv": "TSV 表格",
        ".md": "Markdown", ".markdown": "Markdown", ".txt": "文本",
    }
    return mapping.get(suffix, suffix.lstrip(".").upper() or "文件")


def summarize(attachments: list[Attachment]) -> str:
    """状态栏用的一句话统计。"""
    if not attachments:
        return ""
    text_ok = sum(1 for a in attachments if a.usable)
    images = sum(1 for a in attachments if a.kind == KIND_IMAGE)
    bad = len(attachments) - text_ok - images
    parts = [f"共 {len(attachments)} 份附件"]
    if text_ok:
        parts.append(f"{text_ok} 份已提取正文")
    if images:
        parts.append(f"{images} 张图片需视觉模型")
    if bad:
        parts.append(f"{bad} 份未能读取")
    return "：".join([parts[0], "、".join(parts[1:])]) if len(parts) > 1 else parts[0]


__all__ = [
    "DEFAULT_PER_FILE_CHARS",
    "DEFAULT_TOTAL_CHARS",
    "KIND_IMAGE",
    "KIND_TEXT",
    "KIND_UNSUPPORTED",
    "Attachment",
    "budget_from_config",
    "build_attachment_block",
    "extract_attachment",
    "extraction_supported",
    "summarize",
]
