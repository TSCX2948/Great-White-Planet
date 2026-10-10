"""页码范围解析。

用户在导出 PDF 时可以指定要哪些页，写法与常见打印对话框一致：

    1-3, 5, 8-10     第 1~3 页、第 5 页、第 8~10 页
    e                最后一页（e = end）
    e-1              倒数第二页
    e-2-e            倒数第三页到最后一页
    3-e              第 3 页到最后一页

规则与校验
----------
* 以逗号（中英文均可）分隔多段，段内用 ``-`` 表示区间；
* ``e`` 只能出现在页码的位置上，单独使用或与其他数字组合（如 ``e-1``）；
* 区间必须是递增的：``2-1`` 会直接报错并提示用户；
* 页码必须落在 1~总页数之间；
* 会自动去重并**按输入顺序**返回（因此可以打乱顺序或重复取页）。

解析失败时抛 :class:`PageRangeError`，其消息可直接展示给用户。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: 允许的分隔符：英文逗号、中文逗号、顿号、分号、空白
_SEPARATORS = re.compile(r"[,，、;；\s]+")
#: 一个页码表达式：数字或 e，可带 +/- 偏移（如 e、e-1、e+2、12）
_PAGE_TOKEN = re.compile(r"^(?P<base>e|\d+)(?P<sign>[+-])(?P<offset>\d+)$|^(?P<plain>e|\d+)$")

MAX_PAGES = 5000


class PageRangeError(ValueError):
    """页码范围不合法，消息可直接展示给用户。"""


@dataclass
class PageRange:
    """解析结果。"""

    pages: list[int]              # 1 基页码，按输入顺序、已去重
    total: int                    # 文档总页数
    normalized: str               # 规范化后的写法，例如 "1-3, 5, 8-8"

    @property
    def is_all(self) -> bool:
        return self.pages == list(range(1, self.total + 1))

    @property
    def count(self) -> int:
        return len(self.pages)


def _resolve_token(token: str, total: int, original: str) -> int:
    """把单个页码表达式（如 ``e-1``）解析成具体页码。"""
    match = _PAGE_TOKEN.match(token)
    if match is None:
        raise PageRangeError(
            f"「{original}」不是有效的页码范围。\n"
            "正确写法示例：1-3, 5, 8-10 或 e（最后一页）、e-1（倒数第二页）。"
        )

    if match.group("plain") is not None:
        base_text = match.group("plain")
        offset = 0
    else:
        base_text = match.group("base") or ""
        sign = match.group("sign")
        offset = int(match.group("offset") or 0)
        if sign == "-":
            offset = -offset

    if base_text == "e":
        base = total
    else:
        base = int(base_text)

    page = base + offset
    if page < 1:
        raise PageRangeError(
            f"「{original}」超出了范围：文档共 {total} 页，"
            f"按此写法得到的是第 {page} 页（不存在）。"
        )
    if page > total:
        raise PageRangeError(
            f"「{original}」超出了范围：文档共 {total} 页，"
            f"但这里要求第 {page} 页。"
        )
    return page


def parse_page_range(text: str, total: int, allow_empty_as_all: bool = True) -> PageRange:
    """解析页码范围。

    ``text`` 为空且 ``allow_empty_as_all`` 为真时，表示"全部页"。
    """
    if total < 1:
        raise PageRangeError("文档没有任何页面，无法导出。")
    if total > MAX_PAGES:
        raise PageRangeError(f"文档页数过多（{total} 页），超出处理上限 {MAX_PAGES} 页。")

    raw = (text or "").strip()
    if not raw:
        if allow_empty_as_all:
            pages = list(range(1, total + 1))
            return PageRange(pages=pages, total=total, normalized=_normalize(pages))
        raise PageRangeError("请输入要导出的页码范围，例如 1-3。")

    # 全角/长连字符与波浪号统一成半角 '-'
    raw = raw.replace("－", "-").replace("—", "-").replace("–", "-")
    raw = raw.replace("～", "-").replace("~", "-")
    # 去掉所有空白，这样 "1 - 3" 与 "1-3" 等价
    raw = re.sub(r"\s+", "", raw)

    parts = [part for part in _SEPARATORS.split(raw) if part]
    if not parts:
        raise PageRangeError("没有识别到任何页码，请输入例如 1-3, 5 这样的内容。")

    pages: list[int] = []
    for part in parts:
        pieces = _split_range(part)
        if len(pieces) == 1:
            pages.append(_resolve_token(pieces[0], total, part))
            continue
        if len(pieces) != 2:
            raise PageRangeError(_range_hint(part))
        start = _resolve_token(pieces[0], total, part)
        end = _resolve_token(pieces[1], total, part)
        if start > end:
            raise PageRangeError(
                f"「{part}」区间反了：起始页 {start} 大于结束页 {end}。\n"
                f"如果你想要第 {end} 到第 {start} 页，请写成 {end}-{start}。"
            )
        pages.extend(range(start, end + 1))

    if not pages:
        raise PageRangeError("没有识别到任何页码。")

    for page in pages:
        if page < 1 or page > total:
            raise PageRangeError(f"第 {page} 页不存在：文档共 {total} 页。")

    ordered = _dedupe_keep_order(pages)
    return PageRange(pages=ordered, total=total, normalized=_normalize(ordered))


def _split_range(part: str) -> list[str]:
    """把 ``1-3``、``e``、``e-1``、``e-2-e`` 切成 1~2 个"页码表达式"。

    切法：从左往右扫，遇到 ``-`` 时判断它是不是"偏移符号"——
    仅当它前面紧邻 ``e`` 且后面紧跟数字时，才属于同一个表达式（如 ``e-1``）。
    这样 ``e-2-e`` 会被正确切成 ``['e-2', 'e']``，而 ``2-1`` 切成 ``['2','1']``
    （后者交给区间递增校验去报"区间反了"）。
    """
    if not part:
        return []
    pieces: list[str] = []
    current = ""
    index = 0
    while index < len(part):
        char = part[index]
        if char == "-":
            is_offset = (
                current.endswith("e")
                and index + 1 < len(part)
                and part[index + 1].isdigit()
            )
            if is_offset:
                current += char
            else:
                pieces.append(current)
                current = ""
        else:
            current += char
        index += 1
    pieces.append(current)
    # 空片段说明写法有问题（例如 "1-"、"-3"、"--"）
    if any(piece == "" for piece in pieces):
        return [part, part, part]      # 交给调用方报"不是有效的区间"
    return pieces


def _range_hint(part: str) -> str:
    return (
        f"「{part}」不是有效的区间。\n"
        "区间应写成 起始-结束（例如 3-8）；也可以用 e 表示最后一页，"
        "例如 e、e-1（倒数第二页）、3-e（第 3 页到最后一页）。"
    )


def _dedupe_keep_order(pages: list[int]) -> list[int]:
    seen: set[int] = set()
    result: list[int] = []
    for page in pages:
        if page not in seen:
            seen.add(page)
            result.append(page)
    return result


def _normalize(pages: list[int]) -> str:
    """把页码列表压成 ``1-3, 5, 8-8`` 这样的写法（用于回显）。"""
    if not pages:
        return ""
    chunks: list[str] = []
    start = previous = pages[0]
    for page in pages[1:]:
        if page == previous + 1:
            previous = page
            continue
        chunks.append(_chunk(start, previous))
        start = previous = page
    chunks.append(_chunk(start, previous))
    return ", ".join(chunks)


def _chunk(start: int, end: int) -> str:
    if start == end:
        return str(start)
    if end == start + 1:
        return f"{start}, {end}"
    return f"{start}-{end}"


def describe(pages: list[int], total: int, limit: int = 30) -> str:
    """生成给用户看的说明文字。"""
    if not pages:
        return "没有选中任何页面。"
    shown = ", ".join(str(page) for page in pages[:limit])
    if len(pages) > limit:
        shown += f" …（共 {len(pages)} 页）"
    suffix = "（全部）" if pages == list(range(1, total + 1)) else ""
    return f"共 {len(pages)} 页{suffix}：{shown}"


__all__ = [
    "MAX_PAGES",
    "PageRange",
    "PageRangeError",
    "describe",
    "parse_page_range",
]
