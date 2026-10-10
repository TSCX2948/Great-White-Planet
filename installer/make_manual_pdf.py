"""把 Document 下的说明文档渲染成 PDF。

复用软件自己的 Markdown→HTML 管线（`gwp.services.markdown_renderer`）与
PyMuPDF Story 排版，保证 PDF 样式和软件导出的 PDF 一致。

图片（如安装说明里的界面截图）用**相对文档目录**的路径引用，
本脚本会把 ``src`` 改写成绝对路径，PyMuPDF 才找得到。
"""

from __future__ import annotations

import gc
import re
import sys
from pathlib import Path

CODE = Path(r"D:\Great White Planet\code")
sys.path.insert(0, str(CODE))

import pymupdf  # noqa: E402

from gwp.services import markdown_renderer  # noqa: E402
from gwp.services.themes import markdown_css  # noqa: E402

PROJECT = Path(r"D:\Great White Planet")
DOCUMENT = PROJECT / "Document"
A4 = (595.0, 842.0)          # A4：595 x 842 pt
MARGIN = 46.0

#: 要生成的文档：(Markdown 文件名, PDF 文件名)
DOCUMENTS = (
    ("Great_White_Planet_简要说明书.md", "Great White Planet 简要说明书.pdf"),
    ("Great_White_Planet_安装步骤说明.md", "Great White Planet 安装步骤说明.pdf"),
)


def markdown_to_html(text: str, title: str) -> str:
    """Markdown -> 完整 HTML 文档（带中文字体与打印样式）。

    图片保持 Markdown 里的**相对路径**即可 —— 排版时通过
    ``pymupdf.Archive(<文档目录>)`` 解析，不需要改成绝对路径。
    """
    body = markdown_renderer.markdown_to_html(text)
    css = markdown_css(theme="light", for_pdf=True)
    return (
        "<!DOCTYPE html><html><head><meta charset='utf-8'>"
        f"<title>{title}</title><style>{css}</style></head>"
        f"<body>{body}</body></html>"
    )


def render_pdf(html_text: str, output: Path, asset_dir: Path) -> int:
    """用 Story 分页写出 PDF，返回页数。

    ``asset_dir`` 交给 ``pymupdf.Archive``，这样 HTML 里的相对路径图片
    （如安装说明的界面截图）才能被找到 —— 只给 src 绝对路径是**不生效**的。
    """
    archive = pymupdf.Archive(str(asset_dir))
    story = pymupdf.Story(html=html_text, archive=archive)
    writer = pymupdf.DocumentWriter(str(output))
    pages = 0
    try:
        mediabox = pymupdf.Rect(0, 0, *A4)
        where = pymupdf.Rect(MARGIN, MARGIN, A4[0] - MARGIN, A4[1] - MARGIN)
        more = 1
        while more:
            device = writer.begin_page(mediabox)
            more, _filled = story.place(where)
            story.draw(device)
            writer.end_page()
            pages += 1
            if pages > 500:
                break
    finally:
        try:
            writer.close()
        except Exception:  # noqa: BLE001
            pass
        del writer
        del story
        gc.collect()
    return pages


def count_images(path: Path) -> int:
    """统计 PDF 里的图片数量，用于自检截图是否真的嵌进去了。"""
    with pymupdf.open(path) as document:
        return sum(
            len(document[index].get_images(full=True))
            for index in range(document.page_count)
        )


def main(argv: list[str]) -> int:
    only = argv[0] if argv else ""
    built = 0
    for source_name, pdf_name in DOCUMENTS:
        if only and only not in source_name:
            continue
        source = DOCUMENT / source_name
        if not source.is_file():
            print(f"跳过（找不到）：{source}")
            continue
        text = source.read_text(encoding="utf-8")
        wanted = text.count("![")
        html_text = markdown_to_html(text, pdf_name.removesuffix(".pdf"))
        target = DOCUMENT / pdf_name
        pages = render_pdf(html_text, target, DOCUMENT)
        images = count_images(target)
        flag = "" if images >= wanted else "  ← 有图片没嵌进去！"
        print(
            f"生成: {target.name}   {pages} 页  "
            f"{target.stat().st_size / 1024:.0f} KB  "
            f"图片 {images}/{wanted}{flag}"
        )
        built += 1

    if not built:
        print("没有生成任何 PDF。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
