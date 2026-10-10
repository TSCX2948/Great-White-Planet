"""整理开发实践书稿：默认**只同步 Markdown，不生成 PDF**。

为什么不再默认生成 PDF
----------------------
书稿 PDF 曾一度长到 **987 MB / 5013 页**，根因是 PyMuPDF 1.28.2 的
``Story`` 排版器在本书某些内容组合下**不收敛**（``story.place()`` 永远返回
``more=1``，每页都填满同样的高度），一路排到 5001 页的上限。

定位过程中确认了以下几点：

* 与 CSS 无关（空 CSS 也照样卡住）；
* 与版心宽度无关（559 / 700 / 1000 / 1600 都卡）；
* 删掉表格里任何单个特征也照样卡 —— 是"**这个表格 + 后面的内容**"这个组合；
* 短文档看不出来（前 70 行正常 2 页，加到第 71 行就变成 5001 页）。

``gwp/services/pdf_exporter.py`` 里已经加了**不收敛检测**：连续若干页填充区域
完全一致就报错并丢弃产物，不会再写出几百 MB 的废文件。
但既然用户明确要求"**不要 PDF，留 md 就行**"，这个脚本就默认不生成 PDF。

想临时排一份 PDF（例如确认排版是否恢复正常）::

    python installer/make_dev_book.py --pdf      # 显式要求才排
    python installer/make_dev_book.py --check    # 只检查源文件是否存在

``--pdf`` 仍然受不收敛检测保护：真卡住了会报错退出，而不是写个大文件。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE))

from gwp.services import markdown_renderer        # noqa: E402
from gwp.services.pdf_exporter import export_markdown_to_pdf   # noqa: E402

ROOT = CODE.parent
DOCUMENT = ROOT / "Document"

#: 书稿文件名（Markdown 与 PDF 同名）
SOURCE_NAME = "开发实践——Great White Planet"

#: 源文件位置
SOURCE = DOCUMENT / f"{SOURCE_NAME}.md"

#: 所有需要写出 PDF 的位置（只有 --pdf 时才用）
OUTPUTS = (
    DOCUMENT / f"{SOURCE_NAME}.pdf",
    ROOT / f"{SOURCE_NAME}.pdf",
    # DeepseekData 里也留一份，方便随交付包一起走
    ROOT / "DeepseekData" / f"{SOURCE_NAME}.pdf",
)

#: 需要同步备份的 **Markdown 源文件** 位置。
#: 需求说"这两个文档要持续补充"，所以源文件本身也要有备份 ——
#: 只备份 PDF 的话，将来想继续写就得回到 Document 找源。
SOURCE_BACKUPS = (
    ROOT / f"{SOURCE_NAME}.md",
)


def build_markdown_html(text: str, title: str) -> str:
    """Markdown → 完整 HTML（带中文与打印样式）。"""
    from gwp.services.themes import markdown_css

    body = markdown_renderer.markdown_to_html(text)
    css = markdown_css(theme="light", for_pdf=True)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title><style>{css}</style></head>"
        f"<body>{body}</body></html>"
    )


def build_front_matter(text: str) -> str:
    """从书稿里抽出标题，生成目录页（Markdown）。

    用 ``<div style="page-break-before:always">`` 让目录单独起页 ——
    PyMuPDF 的 Story 支持这个 CSS，比手工插分页符可靠。
    """
    lines: list[str] = [
        "# 目录",
        "",
        "> 本目录不含页码：这是一本会**持续增补**的书，页数一直在变，"
        "印页码反而会很快失效。",
        "> 在 PDF 阅读器里用 `Ctrl+F` 搜索章节标题（例如「第 8 章」"
        "或「8.4」）即可直达。",
        "",
    ]
    in_code = False
    for raw in text.splitlines():
        line = raw.rstrip()
        # 跳过代码块内的 "# 注释"
        if line.lstrip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or not line.startswith("#"):
            continue
        if line.startswith("# "):
            lines.append(f"\n**{line[2:].strip()}**\n")
        elif line.startswith("## "):
            lines.append(f"\n　{line[3:].strip()}\n")
        elif line.startswith("### "):
            lines.append(f"\n　　· {line[4:].strip()}\n")
    return "\n".join(lines) + "\n"


def render(source: Path, target: Path) -> tuple[int, int]:
    """排出 PDF（目录 + 正文，页码连续），返回 (页数, 字节数)。"""
    text = source.read_text(encoding="utf-8")
    target.parent.mkdir(parents=True, exist_ok=True)

    # ---- 第一步：先排目录，数出它占几页 ----
    front = build_front_matter(text)
    front_tmp = target.with_name(target.stem + "_front.pdf")
    export_markdown_to_pdf(
        front, front_tmp, base_dir=source.parent, page_numbers=False
    )
    front_pages = _page_count(front_tmp)

    # ---- 第二步：排正文，页码从 front_pages + 1 开始 ----
    body = "\n".join([
        '<div style="page-break-before:always"></div>',
        text,
    ])
    export_markdown_to_pdf(
        body, target, base_dir=source.parent, page_numbers=True
    )

    # ---- 第三步：合并（目录在前、正文在后），再统一加页码 ----
    if front_pages:
        _merge_with_offset(front_tmp, target, front_pages)
    front_tmp.unlink(missing_ok=True)

    pages = _page_count(target)
    return pages, target.stat().st_size


def _page_count(path: Path) -> int:
    try:
        import pymupdf

        with pymupdf.open(path) as document:
            return document.page_count
    except Exception:  # noqa: BLE001 - 页数只是统计信息
        return 0


def _merge_with_offset(front_pdf: Path, body_pdf: Path, offset: int) -> None:
    """把目录页插到正文前面，并重编页码（目录页不编号）。

    为什么要"重编"：正文先排好时页码是 1..N，
    前面插了 offset 页之后就错位了。所以合并后统一重画页码。
    """
    import pymupdf

    with pymupdf.open(front_pdf) as front, pymupdf.open(body_pdf) as body:
        total = front.page_count + body.page_count
        merged = pymupdf.open()
        merged.insert_pdf(front)
        merged.insert_pdf(body)
        # 清掉旧页码区域：用白色矩形盖住底部
        for index, page in enumerate(merged):
            rect = page.rect
            page.draw_rect(
                pymupdf.Rect(0, rect.height - 48, rect.width, rect.height),
                color=None, fill=(1, 1, 1),
            )
            if index < front.page_count:
                continue                     # 目录页不编页码
            text = f"- {index + 1} / {total} -"
            page.insert_text(
                pymupdf.Point(rect.width / 2 - 22, rect.height - 28),
                text, fontsize=9, color=(0.45, 0.45, 0.45),
            )
        temporary = body_pdf.with_name(body_pdf.stem + "_merged.pdf")
        merged.save(str(temporary))
        merged.close()
    temporary.replace(body_pdf)
    del offset


def main() -> int:
    parser = argparse.ArgumentParser(description="整理《开发实践——Great White Planet》")
    parser.add_argument("--check", action="store_true", help="只检查源文件")
    parser.add_argument(
        "--pdf", action="store_true",
        help="顺便排版 PDF（默认不排：用户要求只保留 Markdown）",
    )
    args = parser.parse_args()

    if not SOURCE.is_file():
        print(f"[错误] 找不到书稿源文件：{SOURCE}")
        return 1
    text = SOURCE.read_text(encoding="utf-8")
    characters = len(text)
    # 粗略统计：中文字符约占 2 字节，用来估算篇幅
    print(f"书稿源文件：{SOURCE}")
    print(f"  {len(text.splitlines())} 行，{characters} 字符")
    print(f"  章节数：{text.count(chr(10) + '## ')} 节，"
          f"{text.count(chr(10) + '# ')} 篇")
    if args.check:
        return 0

    # Markdown 源也同步一份到根目录（需求：两个文档都要留备份）
    import shutil

    for backup in SOURCE_BACKUPS:
        if backup.resolve() == SOURCE.resolve():
            continue
        shutil.copy2(SOURCE, backup)
        print(f"  已备份源文件：{backup}")

    if not args.pdf:
        print("  已跳过 PDF 排版（默认只留 Markdown；需要时加 --pdf）")
        return 0

    for target in OUTPUTS:
        try:
            pages, size = render(SOURCE, target)
        except Exception as exc:  # noqa: BLE001 - 排版失败要给出可读的原因
            print(f"  [失败] {target.name}：{exc}")
            continue
        print(f"  已生成：{target}  ({pages} 页, {size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
