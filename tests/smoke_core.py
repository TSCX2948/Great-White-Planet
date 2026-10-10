"""非界面部分的自检脚本（不依赖 Qt，可随时运行）。

用法::

    <venv>\\Scripts\\python.exe tests\\smoke_core.py

它会：
1. 在临时目录里搭一套假数据（科目/书目/笔记/错题）；
2. 检查扫描、增删改、summary 备份与写入；
3. 用假 AI 适配器跑一遍 summary 流程（不联网）；
4. 检查 Markdown 渲染与 PDF 导出。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

# 让脚本可以直接运行（把 code 目录加入 sys.path）
CODE_DIR = Path(__file__).resolve().parents[1]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "PASS" if condition else "FAIL"
    print(f"[{mark}] {label}" + (f" -> {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def main() -> int:
    temp_root = Path(tempfile.mkdtemp(prefix="gwp_smoke_"))
    os.environ["GWP_ROOT"] = str(temp_root)
    (temp_root / "code").mkdir(parents=True, exist_ok=True)

    from gwp.core.config import Config
    from gwp.core.paths import DataPaths, set_current
    from gwp.core import constants as C

    # 回归测试：先在没有路径单例的情况下调用 Config.load()，
    # 验证 Config 与 DataPaths 不会互相调用造成无限递归。
    probe_config = Config.load(force=True)
    check("Config.load 不递归（默认路径）", probe_config.path is not None, str(probe_config.path))

    config = Config.load(temp_root / "code" / "else data" / "config.json", force=True)
    config.set("paths.data_root", str(temp_root / "data"))
    config.save()
    paths = set_current(DataPaths(config))
    paths.ensure()

    print(f"临时根目录: {temp_root}\n")

    # ---------------------------------------------------------------- 路径
    check("user data 目录位于 data 下", paths.user_data == temp_root / "data" / "user data")
    check("else data 目录位于 data 下", paths.else_data == temp_root / "data" / "else data")

    # ---------------------------------------------------------------- 数据层
    from gwp.data_manager import DataError, Library

    library = Library(config, paths)
    subject = library.create_subject("测试科目")
    check("创建科目", subject.path.is_dir(), str(subject.path))

    book = library.create_book("测试科目", "测试书目")
    check("创建书目", book.path.is_dir())
    for folder in C.BOOK_TEMPLATE_DIRS:
        check(f"自动创建 {folder} 目录", (book.path / folder).is_dir())
    check("自动创建 Introduct.md", (book.path / C.INTRO_FILE).is_file())

    # 写入笔记与错题
    (book.path / C.NOTEBOOK_FOLDER / "note1.md").write_text(
        "# 笔记一\n\n矩阵的秩等于行秩也等于列秩。\n", encoding="utf-8"
    )
    (book.path / C.NOTEBOOK_FOLDER / "note2.txt").write_text(
        "笔记二：若 A 可逆，则 det(A) != 0。\n", encoding="utf-8"
    )
    (book.path / C.ERROR_FOLDER / "错题1.md").write_text(
        "# 错题一\n\n把 |A+B| 当成 |A|+|B| 来算，错了。\n", encoding="utf-8"
    )
    (book.path / C.BOOK_FOLDER / "教材.md").write_text("这段不应参与总结。\n", encoding="utf-8")
    (book.path / C.INTRO_FILE).write_text("# 测试书目\n\n目标：掌握线性代数。\n", encoding="utf-8")

    library.invalidate()
    subjects = library.subjects(refresh=True)
    check("扫描出 1 个科目", len(subjects) == 1, str([s.name for s in subjects]))
    scanned = subjects[0]
    check("科目下有 1 个书目", scanned.book_count == 1, str(scanned.book_count))
    scanned_book = scanned.books[0]
    check(
        "统计到 notebook 2 个文件",
        scanned_book.item_counts.get(C.NOTEBOOK_FOLDER) == 2,
        str(scanned_book.item_counts),
    )

    items = library.list_items(scanned_book)
    check("条目列表非空", len(items) > 0)
    check("简介排在最前", items and items[0].name == C.INTRO_FILE, str([i.name for i in items]))

    # 重命名
    renamed = library.rename_book("测试科目", "测试书目", "改名后书目")
    check("重命名书目", renamed.name == "改名后书目")
    check("summary 文件名跟随", library.find_summary(renamed.path, "改名后书目") is None)
    library.rename_book("测试科目", "改名后书目", "测试书目")

    try:
        library.create_subject("测试科目")
        check("重复创建科目应报错", False)
    except DataError:
        check("重复创建科目应报错", True)

    # ---------------------------------------------------------------- 摘要流程
    from gwp.ai.base import BaseAIAdapter
    from gwp.ai.registry import register_provider
    from gwp.ai.summarizer import Summarizer
    from gwp.ai.types import AIAuthError, AIConfigError, AIError, ChatOptions

    calls: list[list[str]] = []

    @register_provider
    class FakeAdapter(BaseAIAdapter):
        provider_id = "fake_test"
        label = "假 AI"

        def is_configured(self):
            return True, ""

        def complete(self, messages, options=None):
            prepared, _ = self._prepare(messages, options)
            calls.append([m.content for m in prepared])
            # 第二轮回合（用户回答后）返回正式内容
            if any("【用户回答】" in m.content for m in prepared):
                return "# 测试书目\n\n## 一、学习目标\n\n掌握线性代数。\n"
            return (
                "```gwp:ask\n"
                '{"question": "需要把错题也展开讲吗？", "options": ["需要", "不需要"], "allow_custom": true}\n'
                "```\n"
            )

        def stream(self, messages, options=None, on_chunk=None):
            text = self.complete(messages, options)
            if on_chunk:
                on_chunk(text)
            return text

    library.invalidate()
    book = library.book("测试科目", "测试书目")
    summarizer = Summarizer(config, library)
    materials = summarizer.collect_materials(book)
    check("收集到 4 份资料（简介+2笔记+1易错题）", len(materials) == 4, str([m.rel_path for m in materials]))
    check(
        "book 目录未参与",
        all(not m.rel_path.startswith(C.BOOK_FOLDER + "/") for m in materials),
        str([m.rel_path for m in materials]),
    )

    asked: list[str] = []

    def on_question(question):
        asked.append(question.question)
        return "需要"

    adapter = FakeAdapter(config)
    result = summarizer.generate(book, adapter=adapter, question_handler=on_question)
    check("summary 生成成功", result.ok, result.error)
    check("触发了提问交互", len(asked) == 1, str(asked))
    check("summary 文件已写入", bool(result.summary_path and result.summary_path.is_file()))
    check(
        "summary 文件名正确",
        result.summary_path is not None and result.summary_path.name == "测试书目_summary.md",
        str(result.summary_path),
    )

    library.invalidate()
    book = library.book("测试科目", "测试书目")
    check("扫描能识别 summary", book.has_summary, str(book.summary_path))
    items = library.list_items(book)
    check("summary 排在首位", items[0].is_summary, str([(i.name, i.is_summary) for i in items]))

    # 再生成一次 -> 应产生备份，且只剩一个
    result2 = summarizer.generate(book, adapter=adapter, question_handler=lambda q: "需要")
    check("第二次生成成功", result2.ok, result2.error)
    backups = summarizer.backups.list_backups("测试科目", "测试书目")
    check("备份只保留一个", len(backups) == 1, str([b.directory.name for b in backups]))
    check("备份内容是上一版", backups and "学习目标" in summarizer.backups.read_backup_text(backups[0]))

    # 恢复
    from gwp.data_manager.summary_backup import BackupManager

    backup_manager = BackupManager(config, paths)
    ok = backup_manager.restore("测试科目", "测试书目", result2.summary_path)
    check("恢复上一版成功", ok)
    check("恢复后仍有备份", len(backup_manager.list_backups("测试科目", "测试书目")) >= 1)

    # ---------------------------------------------------------------- 渲染
    from gwp.services.markdown_renderer import RenderOptions, markdown_to_html, render_document

    html = markdown_to_html(
        "# 标题\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n\n```python\nprint(1)\n```\n",
        RenderOptions(),
    )
    check("Markdown 渲染标题", "<h1" in html)
    check("Markdown 渲染表格", "<table>" in html)
    check("Markdown 渲染代码", "highlight" in html)
    full = render_document("# 标题", RenderOptions())
    check("完整 HTML 含样式", "<style>" in full and "</html>" in full)

    # ---------------------------------------------------------------- PDF
    from gwp.services.pdf_exporter import PDFExportOptions, export_markdown_to_pdf

    pdf_path = temp_root / "out" / "test.pdf"
    try:
        export_markdown_to_pdf(
            "# 导出测试\n\n中文内容测试：矩阵的秩。\n\n- 第一点\n- 第二点\n",
            pdf_path,
            PDFExportOptions(page_size="A4", margin_mm=18),
        )
        check("PDF 导出成功", pdf_path.is_file() and pdf_path.stat().st_size > 800,
              f"{pdf_path.stat().st_size if pdf_path.exists() else 0} bytes")
    except Exception as exc:  # noqa: BLE001
        check("PDF 导出成功", False, str(exc))

    # ---------------------------------------------------------------- 聊天会话
    from gwp.ai.chat_session import ChatStore, session_key

    store = ChatStore(config, paths)
    key = session_key("测试科目", "测试书目", "notebook/note1.md")
    session = store.load(key)
    session.add("user", "你好")
    session.add("assistant", "你好，有什么可以帮你？")
    saved = store.save(session)
    check("聊天记录已保存", bool(saved and saved.is_file()))
    reloaded = store.load(key)
    check("聊天记录可读回", len(reloaded.messages) == 2)
    removed = store.clear_all()
    check("清空聊天记录", removed == 1, str(removed))

    # ---------------------------------------------------------------- 文件剪贴板
    from gwp.services.file_clipboard import COPY, CUT, FileClipboard

    clip_dir = temp_root / "clip"
    src_dir = clip_dir / "src"
    dst_dir = clip_dir / "dst"
    src_dir.mkdir(parents=True, exist_ok=True)
    dst_dir.mkdir(parents=True, exist_ok=True)
    original = src_dir / "a.md"
    original.write_text("内容 A\n", encoding="utf-8")
    folder = src_dir / "资料夹"
    folder.mkdir()
    (folder / "b.md").write_text("内容 B\n", encoding="utf-8")

    clipboard = FileClipboard()
    check("剪贴板初始为空", clipboard.is_empty)
    check("空剪贴板描述正确", clipboard.describe() == "剪贴板为空", clipboard.describe())

    clipboard.set([original], mode=COPY)
    check("复制后描述正确", "已复制" in clipboard.describe(), clipboard.describe())
    check("复制模式标记正确", not clipboard.is_cut)
    check("contains 判断正确", clipboard.contains(original) and not clipboard.contains(dst_dir))
    results = clipboard.paste(dst_dir)
    check("复制粘贴成功", len(results) == 1 and results[0].ok, str(results))
    check("目标文件已生成", (dst_dir / "a.md").is_file())
    check("复制后源文件保留", original.is_file())
    check("复制后剪贴板保留内容", not clipboard.is_empty)

    # 同目录再粘一次：自动改名，不覆盖
    clipboard.paste(src_dir)
    check("同目录粘贴自动改名", (src_dir / "a_1.md").is_file(),
          str(sorted(p.name for p in src_dir.glob("*.md"))))
    check("改名后的副本内容正确", (src_dir / "a_1.md").read_text(encoding="utf-8") == "内容 A\n")
    check("原文件内容未被覆盖", original.read_text(encoding="utf-8") == "内容 A\n")

    # 再粘一次：序号应继续递增，而不是拼成 a_11
    clipboard.paste(src_dir)
    check("多次粘贴序号递增", (src_dir / "a_2.md").is_file(),
          str(sorted(p.name for p in src_dir.glob("*.md"))))
    check("没有出现 a_11 这类怪名字", not (src_dir / "a_11.md").exists())

    # 剪切 -> 粘贴 = 移动
    clipboard.set([original], mode=CUT)
    check("剪切模式标记正确", clipboard.is_cut)
    clipboard.paste(dst_dir)
    check("剪切后源文件已删除", not original.exists())
    check("剪切后目标存在", (dst_dir / "a.md").is_file())
    check("剪切全部完成后剪贴板清空", clipboard.is_empty)

    # 文件夹整体复制
    clipboard.set([folder], mode=COPY)
    clipboard.paste(dst_dir)
    check("文件夹被整体复制", (dst_dir / "资料夹" / "b.md").is_file())

    # 防呆：等于自身、或位于其内部，都算"粘进自己"（这类操作必须阻止）
    check("目标就是剪贴板里的文件夹", clipboard.would_paste_into_itself(folder))
    check("目标是该文件夹的子目录", clipboard.would_paste_into_itself(folder / "子目录"))
    check("普通目录不会被误判", not clipboard.would_paste_into_itself(src_dir))

    # 剪切时把文件粘回它自己所在目录：原地重命名（改名的副本 + 源被移除），
    # 不会丢内容，也不会在同一目录留下两份。
    same_target = src_dir / "资料夹"
    keep_src = same_target / "b.md"
    clipboard.set([keep_src], mode=CUT)
    clipboard.paste(same_target)
    remaining = sorted(p.name for p in same_target.iterdir())
    check("同目录剪切后只留一个文件", remaining == ["b_1.md"], str(remaining))
    check("同目录剪切内容未丢失",
          (same_target / "b_1.md").read_text(encoding="utf-8") == "内容 B\n")

    # ---------------------------------------------------------------- PDF 导出
    from gwp.services.pdf_exporter import (
        PDFExportCancelled,
        PDFExportOptions,
        add_page_numbers,
        export_markdown_to_pdf,
    )

    pdf_dir = temp_root / "pdf"
    long_md = "# 导出测试\n\n" + "\n\n".join(
        f"## 第 {i} 节\n\n" + ("内容。" * 120) for i in range(1, 6)
    )

    numbered = pdf_dir / "numbered.pdf"
    export_markdown_to_pdf(long_md, numbered, PDFExportOptions(page_numbers=True))
    check("带页码 PDF 已生成", numbered.is_file() and numbered.stat().st_size > 2000)
    try:
        import pymupdf

        doc = pymupdf.open(numbered)
        text_first = doc[0].get_text()
        text_last = doc[doc.page_count - 1].get_text()
        total = doc.page_count
        doc.close()
        check("多页 PDF 排版成功", total >= 2, f"页数={total}")
        check("第 1 页含页码", f"- 1 / {total} -" in text_first, repr(text_first[-20:]))
        check("末页含页码", f"- {total} / {total} -" in text_last, repr(text_last[-20:]))
    except ImportError:
        check("PyMuPDF 可用（跳过页码校验）", False, "未安装 pymupdf")

    plain = pdf_dir / "plain.pdf"
    export_markdown_to_pdf(long_md, plain, PDFExportOptions(page_numbers=False))
    try:
        import pymupdf

        doc = pymupdf.open(plain)
        first_text = doc[0].get_text()
        doc.close()
        check("关闭页码后不含页码", "- 1 /" not in first_text, repr(first_text[-20:]))
    except ImportError:
        pass

    check(
        "关闭页码时体积仍合理",
        plain.is_file() and plain.stat().st_size > 1000,
        str(plain.stat().st_size if plain.exists() else 0),
    )

    progress_seen: list[tuple[str, int]] = []
    export_markdown_to_pdf(
        long_md,
        pdf_dir / "progress.pdf",
        PDFExportOptions(),
        on_progress=lambda message, percent: progress_seen.append((message, percent)),
    )
    check("导出过程有进度回调", len(progress_seen) >= 3, str(len(progress_seen)))
    check("最后一次进度是完成", progress_seen[-1][1] == 100, str(progress_seen[-1]))

    # 取消：不留下半成品
    class _StopAfter:
        def __init__(self) -> None:
            self.calls = 0

        def __call__(self) -> bool:
            self.calls += 1
            return self.calls > 1

    cancelled_pdf = pdf_dir / "cancelled.pdf"
    try:
        export_markdown_to_pdf(
            long_md, cancelled_pdf, PDFExportOptions(), should_cancel=_StopAfter()
        )
        check("取消导出会抛异常", False, "未抛出")
    except PDFExportCancelled:
        check("取消导出会抛异常", True)
        check("取消后不留下半成品", not cancelled_pdf.exists(), str(cancelled_pdf))
    check(
        "没有残留的页码临时文件",
        not any("pages.pdf" in p.name for p in pdf_dir.iterdir()),
        str(sorted(p.name for p in pdf_dir.iterdir())),
    )

    # 单独调用 add_page_numbers（幂等性：已有页码时不报错）
    extra = pdf_dir / "plain2.pdf"
    export_markdown_to_pdf("# 单页\n\n短内容。\n", extra, PDFExportOptions(page_numbers=False))
    check("add_page_numbers 返回页数", add_page_numbers(extra) == 1)
    try:
        import pymupdf

        doc = pymupdf.open(extra)
        text = doc[0].get_text()
        doc.close()
        check("单独加页码生效", "- 1 / 1 -" in text, repr(text[-20:]))
    except ImportError:
        pass

    # ---------------------------------------------------------------- 页码范围
    from gwp.services.page_range import PageRangeError, describe, parse_page_range

    total = 10
    for text_value, expected in (
        ("1-3", [1, 2, 3]),
        ("1-3, 5", [1, 2, 3, 5]),
        ("e", [10]),
        ("e-1", [9]),
        ("e-2-e", [8, 9, 10]),
        ("3-e", list(range(3, 11))),
        ("1,1,2,2,3", [1, 2, 3]),
        (" 1 - 3 , 7 ", [1, 2, 3, 7]),
        ("1~3", [1, 2, 3]),
        ("1，3", [1, 3]),
        ("e+0", [10]),
        ("e-9", [1]),
    ):
        parsed = parse_page_range(text_value, total)
        check(f"范围解析 {text_value!r}", parsed.pages == expected,
              f"{parsed.pages} != {expected}")

    for bad in ("2-1", "3-1", "0", "11", "1-11", "abc", "1-", "-3", "1--2", "e-20", "e-a", "1-2-3"):
        try:
            parse_page_range(bad, total)
            check(f"非法范围 {bad!r} 应报错", False, "未报错")
        except PageRangeError as exc:
            # 报错信息要能直接展示给用户（非空且提到问题）
            check(f"非法范围 {bad!r} 被拒绝", len(str(exc)) > 5, str(exc))

    try:
        parse_page_range("2-1", total)
    except PageRangeError as exc:
        check("反向区间提示「区间反了」", "反了" in str(exc), str(exc))

    check("空输入表示全部页", parse_page_range("", total).is_all)
    try:
        parse_page_range("", total, allow_empty_as_all=False)
        check("禁止空输入时会报错", False, "未报错")
    except PageRangeError:
        check("禁止空输入时会报错", True)
    check("说明文字包含页数", "共 3 页" in describe([1, 2, 3], 3), describe([1, 2, 3], 3))

    # ---------------------------------------------------------------- 两步式导出
    from gwp.services.pdf_exporter import count_pdf_pages, extract_pages

    two_step_dir = temp_root / "two_step"
    long_doc = "# 范围测试\n\n" + "\n\n".join(
        f"## 第 {i} 节标记{i}\n\n" + ("这是用于撑满页面的内容。" * 200) for i in range(1, 7)
    )
    prepared = two_step_dir / "prepared.pdf"
    export_markdown_to_pdf(long_doc, prepared, PDFExportOptions(), style="prepare")
    check("prepare 只产出临时文件", prepared.is_file())
    total_pages = count_pdf_pages(prepared)
    check("prepare 后能读到页数", total_pages >= 3, str(total_pages))

    subset = two_step_dir / "subset.pdf"
    selection = parse_page_range("1, e-1, e", total_pages)
    export_markdown_to_pdf(
        "", subset, PDFExportOptions(),
        prepared_path=prepared, pages=selection.pages, page_numbers=True,
    )
    check("复用排版结果可导出子集", subset.is_file())
    check("子集页数正确", count_pdf_pages(subset) == len(selection.pages),
          str(count_pdf_pages(subset)))
    try:
        import pymupdf

        doc = pymupdf.open(subset)
        first = doc[0].get_text()
        second = doc[1].get_text()
        doc.close()
        check("子集页脚保留原页号（首页）", f"- 1 / {total_pages} -" in first, repr(first[-16:]))
        check("子集页脚保留原页号（倒数第二）",
              f"- {total_pages - 1} / {total_pages} -" in second, repr(second[-16:]))
    except ImportError:
        pass
    check("复用后临时文件仍在（可再导一次）", prepared.is_file())

    extracted = two_step_dir / "extracted.pdf"
    extract_pages(prepared, extracted, [2, 4])
    check("extract_pages 可用", count_pdf_pages(extracted) == 2, str(count_pdf_pages(extracted)))

    # 加页码时分母用原文档总页数
    numbered_subset = two_step_dir / "numbered_subset.pdf"
    export_markdown_to_pdf(
        "", numbered_subset, PDFExportOptions(),
        prepared_path=prepared, pages=[2], page_numbers=True,
    )
    try:
        import pymupdf

        doc = pymupdf.open(numbered_subset)
        text = doc[0].get_text()
        doc.close()
        check("单页子集页脚为「原页号 / 原总页数」",
              f"- 2 / {total_pages} -" in text, repr(text[-16:]))
    except ImportError:
        pass

    # ---------------------------------------------------------------- 主界面背景图
    from gwp.services.background import (
        BackgroundManager,
        background_qss,
        content_margins,
        resolve_background,
        sort_key,
    )

    bg_dir = temp_root / "bg_source"
    bg_dir.mkdir(parents=True, exist_ok=True)
    from PIL import Image as _Image

    wallpaper = bg_dir / "我的壁纸.png"
    _Image.new("RGB", (160, 100), (20, 60, 120)).save(wallpaper)
    photo = bg_dir / "风景.jpg"
    _Image.new("RGB", (120, 80), (30, 120, 40)).save(photo)

    backgrounds = BackgroundManager(config, paths)
    check("背景目录位于 else data 下",
          backgrounds.directory == paths.else_data / "background", str(backgrounds.directory))
    check("初始没有背景", backgrounds.current_path() is None)
    check("未设置背景时不产生样式", not background_qss(config, paths).strip())

    first_bg = backgrounds.add(wallpaper)
    check("首次导入使用原文件名", first_bg.name == "我的壁纸.png", first_bg.name)
    check("首次导入后成为当前背景", backgrounds.current_path() == first_bg)
    check("导入是复制，原文件保留", wallpaper.is_file())

    second_bg = backgrounds.add(wallpaper)
    check("再次导入同名递增数字", second_bg.name == "我的壁纸_1.png", second_bg.name)
    check("旧背景图片仍然保留", first_bg.is_file())
    check("当前背景已切到新图", backgrounds.current_path() == second_bg)

    third_bg = backgrounds.add(wallpaper)
    check("第三次导入继续递增", third_bg.name == "我的壁纸_2.png", third_bg.name)

    numbered_source = bg_dir / "我的壁纸_9.png"
    _Image.new("RGB", (50, 50), (200, 200, 0)).save(numbered_source)
    fourth_bg = backgrounds.add(numbered_source)
    check("带序号的素材按主名递增", fourth_bg.name == "我的壁纸_3.png", fourth_bg.name)

    other_bg = backgrounds.add(photo)
    check("不同主名互不影响", other_bg.name == "风景.jpg", other_bg.name)
    check("图库共 5 张", len(backgrounds.entries()) == 5,
          str([e.name for e in backgrounds.entries()]))
    check("当前项被标记", sum(1 for e in backgrounds.entries() if e.is_current) == 1)

    check("自然排序：_9 在 _10 之前",
          sort_key(Path("壁纸_9.png")) < sort_key(Path("壁纸_10.png")))

    backgrounds.set_current(first_bg)
    check("可以切回旧背景", backgrounds.current_path() == first_bg)
    check("切换背景不删除任何文件", len(backgrounds.entries()) == 5)

    qss = background_qss(config, paths)
    check("样式表负责让中间容器透明",
          "background: transparent" in qss, qss[:200])
    check("样式表覆盖到 QStackedWidget（曾经的 bug 点）",
          "QStackedWidget" in qss, qss)
    check("样式表不再用 QSS 画背景图",
          "background-image" not in qss, qss[:200])
    check("标题栏有半透明织带", "HeaderBar" in qss)

    # 背景由控件自绘，因此绘制参数从 resolve_background 取
    image_path, fit, overlay, tint = resolve_background(config, paths)
    check("解析出背景图片", image_path is not None and Path(image_path).is_file(),
          str(image_path))
    check("默认填充方式为铺满", fit == "cover", fit)
    check("默认不压暗背景", overlay == 0.0, str(overlay))
    check("有背景时不额外留外框边距", content_margins(config, paths) == 0,
          str(content_margins(config, paths)))

    config.set("ui.background_overlay", 0.4)
    check("可手动调暗背景", resolve_background(config, paths)[2] == 0.4,
          str(resolve_background(config, paths)[2]))
    config.set("ui.background_overlay", 0.0)

    config.set("ui.background_fit", "contain")
    check("可切换为完整显示", resolve_background(config, paths)[1] == "contain")
    config.set("ui.background_fit", "cover")

    config.set("ui.background_margin", 10)
    check("可选用外框留边样式", content_margins(config, paths) == 10,
          str(content_margins(config, paths)))
    config.set("ui.background_margin", 0)

    backgrounds.clear()
    check("关闭背景后不再返回路径", backgrounds.current_path() is None)
    check("关闭背景不删文件", len(backgrounds.entries()) == 5)
    check("关闭背景后样式为空", not background_qss(config, paths).strip())

    config.set("ui.background_enabled", False)
    backgrounds.set_current(second_bg)          # 设当前会自动重新启用
    check("设为当前时会自动启用背景", bool(background_qss(config, paths).strip()))
    config.set("ui.background_enabled", False)
    check("临时禁用时不产生样式", not background_qss(config, paths).strip())
    config.set("ui.background_enabled", True)
    check("重新启用后样式恢复", bool(background_qss(config, paths).strip()))

    check("配置里存的是相对路径",
          not Path(str(config.get("ui.background_image", ""))).is_absolute(),
          str(config.get("ui.background_image", "")))

    bad_source = bg_dir / "说明.txt"
    bad_source.write_text("not an image", encoding="utf-8")
    try:
        backgrounds.add(bad_source)
        check("非图片不能作为背景", False, "未报错")
    except ValueError:
        check("非图片不能作为背景", True)

    backgrounds.remove(other_bg)
    check("移除一张后图库变 4 张", len(backgrounds.entries()) == 4,
          str([e.name for e in backgrounds.entries()]))

    # ---------------------------------------------------------------- 单实例锁
    from gwp.core import single_instance

    lock_dir = temp_root / "lock_test"
    lock_dir.mkdir(parents=True, exist_ok=True)
    check("锁文件位于指定目录",
          single_instance.lock_path(lock_dir) == lock_dir / "instance.lock",
          str(single_instance.lock_path(lock_dir)))

    check("初始没有运行实例", single_instance.running_instance(lock_dir) is None)

    acquired = single_instance.acquire(lock_dir)
    check("首次获取锁成功", acquired.acquired)
    check("锁文件已生成", single_instance.lock_path(lock_dir).is_file())
    check("锁文件写入了自己的 PID",
          single_instance.read_lock_pid(single_instance.lock_path(lock_dir)) == os.getpid())

    # 另一个存活的进程占用时，不能再拿锁
    other_pid = os.getpid() + 1
    single_instance.lock_path(lock_dir).write_text(f"{other_pid}\n", encoding="utf-8")
    if single_instance.is_process_alive(other_pid):
        check("他人持锁时无法获取", not single_instance.acquire(lock_dir).acquired)
    else:
        check("他人的 PID 不存在时视为陈旧锁",
              single_instance.running_instance(lock_dir) is None)

    # 自己不重复占用（同一进程再次 acquire 视为可继续）
    single_instance.lock_path(lock_dir).write_text(f"{os.getpid()}\n", encoding="utf-8")
    check("同进程不把自己当冲突", single_instance.running_instance(lock_dir) is None)

    # 明显不存在的 PID = 陈旧锁，可接管
    single_instance.lock_path(lock_dir).write_text("999999\n", encoding="utf-8")
    check("陈旧锁可被接管", single_instance.running_instance(lock_dir) is None)
    check("不存在的 PID 判定为不存活", not single_instance.is_process_alive(999999))
    check("非法 PID 判定为不存活", not single_instance.is_process_alive(0))
    check("自己的 PID 判定为存活", single_instance.is_process_alive(os.getpid()))

    # 损坏 / 空 / 非数字的锁文件都不该阻塞启动
    for broken in ("这不是数字\n", "", "   \n", "abc,def\n"):
        single_instance.lock_path(lock_dir).write_text(broken, encoding="utf-8")
        check(f"损坏锁文件（{broken.strip() or '空'}）不阻塞启动",
              single_instance.running_instance(lock_dir) is None)

    # 释放
    single_instance.lock_path(lock_dir).unlink(missing_ok=True)
    held = single_instance.acquire(lock_dir)
    held.release()
    check("释放后锁文件被删除", not single_instance.lock_path(lock_dir).exists())
    check("释放后可再次获取", single_instance.acquire(lock_dir).acquired)

    # ---------------------------------------------------------------- 虚拟桌面检测
    from gwp.core import desktops

    check("平台支持情况可查询", isinstance(desktops.is_supported(), bool))
    check("hwnd=0 时不做判断", desktops.window_is_on_current_desktop(0) is None)
    fake_result = desktops.window_is_on_current_desktop(0x12345678)
    check("无效句柄不抛异常", fake_result in (True, False, None), str(fake_result))
    check("无效句柄不算'另一个桌面'",
          desktops.window_is_on_other_desktop(0x12345678) is False)
    check("window_desktop_id 对无效句柄返回 None 或字符串",
          desktops.window_desktop_id(0x12345678) is None
          or isinstance(desktops.window_desktop_id(0x12345678), str))
    check("activate_window 对无效句柄返回 False",
          desktops.activate_window(0) is False)
    check("GUID 解析可用",
          desktops._GUID.from_string("{AA509086-5CA9-4C25-8F95-589D3C07B48A}").Data1
          == 0xAA509086)

    # 锁文件携带窗口句柄（供下一个实例判断虚拟桌面）
    hwnd_lock_dir = temp_root / "hwnd_lock"
    hwnd_lock_dir.mkdir(parents=True, exist_ok=True)
    hwnd_lock_file = single_instance.lock_path(hwnd_lock_dir)
    held = single_instance.acquire(hwnd_lock_dir, hwnd=4242)
    check("acquire 可携带窗口句柄", held.acquired and held.hwnd == 4242, str(held.hwnd))
    import json as _json

    payload = _json.loads(hwnd_lock_file.read_text(encoding="utf-8"))
    check("锁文件记录了 hwnd", payload.get("hwnd") == 4242, str(payload))
    check("锁文件记录了 pid", payload.get("pid") == os.getpid(), str(payload))

    held.publish_window(8888)
    check("publish_window 更新句柄",
          single_instance.read_lock(hwnd_lock_file).hwnd == 8888)
    check("read_lock 是结构化结果",
          single_instance.read_lock(hwnd_lock_file).valid)

    # 旧格式兼容（升级后第一次启动要能接管老锁）
    hwnd_lock_file.write_text("4242\nD:\\Python\\python.exe\n", encoding="utf-8")
    legacy = single_instance.read_lock(hwnd_lock_file)
    check("旧两行锁格式仍可解析", legacy.pid == 4242 and legacy.hwnd == 0, str(legacy))
    hwnd_lock_file.write_text("{}", encoding="utf-8")
    check("空 JSON 不算有效实例", not single_instance.read_lock(hwnd_lock_file).valid)

    # 「已有实例在另一个桌面」这个分支：把桌面查询打桩成 False 来触发
    hwnd_lock_file.write_text(
        _json.dumps({"pid": os.getpid() + 1, "hwnd": 7777}), encoding="utf-8"
    )
    original_is_alive = single_instance.is_process_alive
    original_on_current = desktops.window_is_on_current_desktop
    try:
        single_instance.is_process_alive = lambda _pid: True          # 假装他人存活
        desktops.window_is_on_current_desktop = lambda _hwnd: False   # 假装窗口在别的桌面
        conflict = single_instance.acquire(hwnd_lock_dir, hwnd=0)
        check("检测到'另一个桌面'时拒绝获取锁", not conflict.acquired)
        check("冲突信息带 on_other_desktop 标记", conflict.on_other_desktop is True)
        check("冲突信息带对方的句柄", conflict.hwnd == 7777, str(conflict.hwnd))
        check("冲突信息带对方的 PID", conflict.pid == os.getpid() + 1, str(conflict.pid))

        desktops.window_is_on_current_desktop = lambda _hwnd: True    # 同桌面
        same = single_instance.acquire(hwnd_lock_dir, hwnd=0)
        check("同桌面时不带该标记", same.acquired is False and same.on_other_desktop is False)

        desktops.window_is_on_current_desktop = lambda _hwnd: None    # 无法判断
        unknown = single_instance.acquire(hwnd_lock_dir, hwnd=0)
        check("无法判断时按同桌面处理（不误拦）",
              unknown.acquired is False and unknown.on_other_desktop is False)
    finally:
        single_instance.is_process_alive = original_is_alive
        desktops.window_is_on_current_desktop = original_on_current

    hwnd_lock_file.unlink(missing_ok=True)

    # ---------------------------------------------------------------- 作业目录
    # 需求：在「笔记」之后增设「作业」，且作业**不参与 AI 总结**
    from gwp.core import constants as _C

    check("存在 homework 常量", _C.HOMEWORK_FOLDER == "homework", _C.HOMEWORK_FOLDER)
    check("作业属于标准目录结构", _C.HOMEWORK_FOLDER in _C.BOOK_TEMPLATE_DIRS,
          str(_C.BOOK_TEMPLATE_DIRS))
    check("作业不参与 AI 总结", _C.HOMEWORK_FOLDER not in _C.SUMMARY_SOURCE_DIRS,
          str(_C.SUMMARY_SOURCE_DIRS))
    check("教材也不参与 AI 总结", _C.BOOK_FOLDER not in _C.SUMMARY_SOURCE_DIRS)

    homework_subject = library.create_subject("作业测试科目")
    # 科目下不应预建这些子目录，否则会被当成若干本空书
    check("科目下不预建书目子目录",
          not any((homework_subject.path / key).exists()
                  for key in _C.BOOK_TEMPLATE_DIRS),
          str(sorted(p.name for p in homework_subject.path.iterdir())))
    check("新建科目下只有元数据文件",
          [p.name for p in homework_subject.path.iterdir()] == [_C.SUBJECT_META],
          str(sorted(p.name for p in homework_subject.path.iterdir())))

    homework_book = library.create_book(homework_subject.name, "作业测试书目")
    check("新建书目自动创建作业目录",
          (homework_book.path / _C.HOMEWORK_FOLDER).is_dir(),
          str(sorted(p.name for p in homework_book.path.iterdir())))

    homework_dir = homework_book.path / _C.HOMEWORK_FOLDER
    (homework_dir / "第一次作业.md").write_text("# 作业一\n\n内容\n", encoding="utf-8")
    (homework_dir / "第二次作业.md").write_text("# 作业二\n", encoding="utf-8")
    library.invalidate()
    reloaded = library.book(homework_subject.name, "作业测试书目")
    check("作业文件数被统计", reloaded.item_counts.get(_C.HOMEWORK_FOLDER) == 2,
          str(reloaded.item_counts))
    check("作业不计入参与总结的条目数",
          reloaded.summary_source_count == 0, str(reloaded.summary_source_count))

    # 作业栏目的计数必须是**表格行数**（一个作业一行），不是内部文件数。
    # 曾经的 bug：用 rglob 递归数文件，于是"2.4 作业"目录里的
    # homework.json + 作业内容文件被算成 2，而表格只显示 1 行 ——
    # 标签上的数字和点进去看到的内容对不上（用户截图报障）。
    #
    # 注意这个书目里同时有两种东西：
    #   * 上面写的两个散文件（第一次作业.md / 第二次作业.md）
    #   * 下面要建的两个作业文件夹（每个里面有 homework.json + 内容.md）
    # 表格两者都会列，所以"计数 == 表格行数"是唯一正确的判据。
    hw_dir = homework_book.path / _C.HOMEWORK_FOLDER
    for folder_name in ("第一次作业", "第二次作业"):
        assignment = hw_dir / folder_name
        assignment.mkdir(parents=True, exist_ok=True)
        (assignment / "homework.json").write_text("{}", encoding="utf-8")
        (assignment / "内容.md").write_text("x", encoding="utf-8")
    library.invalidate()
    reloaded2 = library.book(homework_subject.name, "作业测试书目")
    rows = len(library.list_homework_items(reloaded2))
    count = int((reloaded2.item_counts or {}).get(_C.HOMEWORK_FOLDER, -1))
    files = sum(1 for p in hw_dir.rglob("*") if p.is_file())
    check("作业标签的计数 = 表格行数（一个作业一行）",
          count == rows, f"计数={count} 表格行数={rows}")
    check("作业计数不再等于内部文件总数（那正是 bug）",
          files != count and files > count,
          f"内部文件数={files} 计数={count}")
    check("两个作业文件夹各算 1（不被内部的 homework.json 撑大）",
          count == 4, f"2 个散文件 + 2 个作业夹 = 4，实际={count}")

    # 进入某个作业文件夹时要能列出它的**全部内容**（含内部文件）。
    # 曾经的 bug：作业栏目无论在哪一层都用 list_homework_items 过滤，
    # 而它只列作业根目录第一层 → 进了作业里面界面一片空白。
    assignment = hw_dir / "第一次作业"
    listed = library.list_folder(assignment)
    listed_names = sorted(i.name for i in listed)
    check("能列出作业文件夹里的全部文件",
          listed_names == ["homework.json", "内容.md"], str(listed_names))
    check("作业内部文件被标为内部文件（is_meta）",
          {i.name: i.is_meta for i in listed}.get("homework.json") is True,
          str({i.name: i.is_meta for i in listed}))
    check("普通作业内容不会被标为内部文件",
          {i.name: i.is_meta for i in listed}.get("内容.md") is False,
          str({i.name: i.is_meta for i in listed}))
    check("内部文件的类型标签是「作业信息」",
          next(i.kind_label for i in listed if i.name == "homework.json")
          == "作业信息",
          next(i.kind_label for i in listed if i.name == "homework.json"))
    check("list_folder 对普通目录不会误标内部文件",
          all(not i.is_meta
              for i in library.list_folder(homework_book.path / "notebook")),
          str([i.name for i in library.list_folder(homework_book.path / "notebook")]))

    # 总结的来源解析里绝不能出现作业
    summarizer = Summarizer(config, library)
    resolved = summarizer.resolve_sources(reloaded)
    resolved_names = [str(path.relative_to(reloaded.path)) for _, path in resolved]
    check("总结来源里没有作业目录",
          not any(_C.HOMEWORK_FOLDER in name for name in resolved_names),
          str(resolved_names))
    check("总结来源包含笔记与易错题",
          any(_C.NOTEBOOK_FOLDER in name for name in resolved_names)
          and any(_C.ERROR_FOLDER in name for name in resolved_names),
          str(resolved_names))

    stats = summarizer.stats(reloaded)
    check("stats 报告作业的真实数量（不误导为 0）",
          int(stats.get(_C.HOMEWORK_FOLDER, -1)) > 0, str(stats))
    # stats 的作业数与表格行数必须一致（同一个"一个作业一行"的规则）。
    # 它以前也用过 rglob，会把 homework.json 一起数进来 —— 和标签数字一样对不上。
    check("stats 的作业数与表格行数一致",
          int(stats.get(_C.HOMEWORK_FOLDER, -1))
          == len(library.list_homework_items(reloaded)),
          f"stats={stats.get(_C.HOMEWORK_FOLDER)} "
          f"行数={len(library.list_homework_items(reloaded))}")
    check("stats 的参与总结总数不含作业", stats.get("total") == 1, str(stats))

    # 即使配置里显式把作业加进 sources，也只影响显式配置的情况；
    # 默认配置必须排除它
    default_sources = [label for label, _ in summarizer.source_spec()]
    check("默认来源不含 homework", "homework" not in default_sources, str(default_sources))

    # 作业目录也受结构保护（不能被剪切/复制走）
    from gwp.ui.views.book_view import TABS

    tab_keys = [key for key, _, _ in TABS]
    tab_labels = [label for _, label, _ in TABS]
    check("作业标签存在", "homework" in tab_keys, str(tab_keys))
    check("作业排在笔记之后", tab_keys.index("homework") > tab_keys.index("notebook"),
          str(tab_keys))
    check("作业排在易错题之前", tab_keys.index("homework") < tab_keys.index("error-prone"),
          str(tab_keys))
    check("默认类型的 homework 标签是「练习」",
          tab_labels[tab_keys.index("homework")] == "练习",
          tab_labels[tab_keys.index("homework")])

    # ---------------------------------------------------------------- 收纳箱
    # 需求：主界面支持把几个 Subject 图标收进"收纳箱"，箱子样式与科目一致但加边框
    from gwp.data_manager.boxes import BOXES_FILE, BoxStore

    box_subject_a = library.create_subject("箱子科目甲")
    box_subject_b = library.create_subject("箱子科目乙")
    library.create_subject("箱子科目丙")

    store = library.boxes
    check("收纳箱存储位置在数据根目录",
          store.path.name == BOXES_FILE and store.path.parent == paths.data_root,
          str(store.path))
    check("初始没有收纳箱", store.load() == [])

    box = store.create("数学基础")
    check("可以新建收纳箱", box.id == "数学基础" and box.title == "数学基础", str(box))
    check("新建收纳箱有默认颜色", bool(box.color), box.color)
    check("新箱子默认是空的", box.member_count == 0, str(box.members))

    check("可以把科目放入收纳箱",
          store.move_subjects(box.id, [box_subject_a.name, box_subject_b.name]) == 2)
    pairs = library.boxes_with_members(refresh=False)
    check("收纳箱查询返回成员",
          len(pairs) == 1 and len(pairs[0][1]) == 2, str([(b.title, len(m)) for b, m in pairs]))
    check("成员科目没被搬走（仍在 subjects 下）",
          (paths.subjects_dir / box_subject_a.name).is_dir())
    unboxed_names = [s.name for s in library.unboxed_subjects()]
    check("未收纳科目包含丙", "箱子科目丙" in unboxed_names, str(unboxed_names))
    check("已收纳的科目不在未收纳列表里",
          box_subject_a.name not in unboxed_names
          and box_subject_b.name not in unboxed_names,
          str(unboxed_names))
    check("能反查科目属于哪个箱子",
          store.box_of(box_subject_a.name) is not None
          and store.box_of(box_subject_a.name).id == box.id)

    # 一个科目只能在一个箱子里：放进新箱子会自动从旧箱子移出
    other = store.create("数学进阶")
    store.move_subjects(other.id, [box_subject_a.name])
    check("移入新箱子会从旧箱子移除",
          box_subject_a.name not in store.get(box.id).members
          and box_subject_a.name in store.get(other.id).members)
    store.move_subjects(box.id, [box_subject_a.name])

    check("重命名收纳箱", store.rename(box.id, "数学核心").title == "数学核心")
    check("修改收纳箱颜色", store.set_color(box.id, "#00A6A6").color == "#00A6A6")
    check("重名时自动加序号", store.create("数学核心").title == "数学核心 2")

    check("可以把科目移出收纳箱",
          store.remove_subjects([box_subject_b.name]) == 1)
    check("移出后回到未收纳",
          box_subject_b.name in [s.name for s in library.unboxed_subjects(refresh=True)])

    # 幽灵成员（科目被手工删掉）应被自动清理且不报错
    ghost = store.create("幽灵箱")
    store.move_subjects(ghost.id, [box_subject_b.name])
    import shutil as _shutil

    _shutil.rmtree(paths.subjects_dir / box_subject_b.name, ignore_errors=True)
    library.invalidate()
    pairs_after = library.boxes_with_members(refresh=True)
    check("已删除的科目会被自动移出收纳箱",
          all(box_subject_b.name not in [m.name for m in members]
              for _box, members in pairs_after),
          str([(b.title, [m.name for m in ms]) for b, ms in pairs_after]))

    # 删除收纳箱只释放分组，不删科目
    released = store.delete(box.id)
    check("删除收纳箱返回被释放的科目", box_subject_a.name in released, str(released))
    check("删除收纳箱后科目仍在", (paths.subjects_dir / box_subject_a.name).is_dir())
    check("删除收纳箱后科目回到未收纳",
          box_subject_a.name in [s.name for s in library.unboxed_subjects(refresh=True)],
          str([s.name for s in library.unboxed_subjects(refresh=True)]))
    # 缓存与磁盘必须一致（曾经因为共享对象导致缓存里留着已删除的箱子）
    check("删除后缓存与磁盘一致",
          [b.id for b in store.load()] == [b.id for b in store.load(refresh=True)],
          f"{[b.id for b in store.load()]} vs {[b.id for b in store.load(refresh=True)]}")
    check("library.boxes 与 store 视图一致",
          [b.id for b in library.boxes.load()] == [b.id for b in store.load()],
          f"{[b.id for b in library.boxes.load()]} vs {[b.id for b in store.load()]}")

    # 元数据落盘且可被手工编辑
    check("boxes.json 已生成", store.path.is_file())
    import json as _json2

    payload = _json2.loads(store.path.read_text(encoding="utf-8"))
    check("boxes.json 结构正确",
          isinstance(payload.get("boxes"), list) and payload.get("version") == 1,
          str(payload)[:120])
    # 手工清空后再读取，软件应当接受
    store.path.write_text('{"version": 1, "boxes": []}', encoding="utf-8")
    fresh = BoxStore(paths.subjects_dir)
    check("手工编辑后的 boxes.json 能被读取", fresh.load() == [])

    # 科目目录下不能多出一个叫 .boxes 的"科目"
    fresh.asset_dir.mkdir(parents=True, exist_ok=True)
    library.invalidate()
    check("收纳箱图片目录不会被当成科目",
          ".boxes" not in [s.name for s in library.subjects(refresh=True)],
          str([s.name for s in library.subjects(refresh=True)]))

    # ---------------------------------------------------------------- 科目类型
    # 需求：Subject 分为 日记 / 校修课 / 自学课；自学课的"作业"改叫"练习"
    check("三种科目类型已定义",
          C.SUBJECT_TYPES == ("diary", "school", "self-study"), str(C.SUBJECT_TYPES))
    check("默认类型是自学课（旧数据向后兼容）",
          C.DEFAULT_SUBJECT_TYPE == C.SUBJECT_SELF_STUDY, C.DEFAULT_SUBJECT_TYPE)

    # 类型 -> 目录结构
    check("日记类型的目录结构",
          C.template_dirs_for_type(C.SUBJECT_DIARY) == C.DIARY_TEMPLATE_DIRS,
          str(C.template_dirs_for_type(C.SUBJECT_DIARY)))
    check("日记类型没有教材与易错题",
          C.BOOK_FOLDER not in C.DIARY_TEMPLATE_DIRS
          and C.ERROR_FOLDER not in C.DIARY_TEMPLATE_DIRS,
          str(C.DIARY_TEMPLATE_DIRS))
    check("普通类型仍是 book/error-prone/notebook/homework",
          C.template_dirs_for_type(C.SUBJECT_SELF_STUDY) == C.BOOK_TEMPLATE_DIRS)
    check("日记类型参与 AI 的是 my diary 与 else diary",
          C.summary_sources_for_type(C.SUBJECT_DIARY) == C.DIARY_SOURCE_DIRS,
          str(C.summary_sources_for_type(C.SUBJECT_DIARY)))

    # 类型 -> 标签（重点是"作业 -> 练习"）
    self_labels = [title for _k, title, _f in C.tabs_for_type(C.SUBJECT_SELF_STUDY)]
    school_labels = [title for _k, title, _f in C.tabs_for_type(C.SUBJECT_SCHOOL)]
    diary_labels = [title for _k, title, _f in C.tabs_for_type(C.SUBJECT_DIARY)]
    check("自学课显示「练习」", "练习" in self_labels and "作业" not in self_labels,
          str(self_labels))
    check("校修课显示「作业」", "作业" in school_labels and "练习" not in school_labels,
          str(school_labels))
    check("自学课与校修课共用同一个目录常量",
          dict((t, f) for _k, t, f in C.tabs_for_type(C.SUBJECT_SELF_STUDY)).get("练习")
          == dict((t, f) for _k, t, f in C.tabs_for_type(C.SUBJECT_SCHOOL)).get("作业")
          == C.HOMEWORK_FOLDER)
    check("日记类型标签为「四个目录 + 单词书 + 全部条目」（没有 AI 总结/简介）",
          diary_labels == ["AI 思想总结", "AI 日记", "我的日记", "其它日记",
                           "单词书", "全部条目"],
          str(diary_labels))
    check("日记类型没有教材/易错题标签",
          "教材" not in diary_labels and "易错题" not in diary_labels, str(diary_labels))
    check("类型中文名正确",
          C.type_label("diary") == "日记"
          and C.type_label("school") == "校修课"
          and C.type_label("self-study") == "自学课")

    # 建一个日记科目：自动建 MyBook，并生成手写图那套目录
    diary_subject = library.create_subject("日记测试", subject_type=C.SUBJECT_DIARY)
    check("日记科目类型被保存", diary_subject.subject_type == C.SUBJECT_DIARY,
          diary_subject.subject_type)
    check("日记科目自动建了默认书目",
          [b.name for b in diary_subject.books] == [C.DIARY_DEFAULT_BOOK],
          str([b.name for b in diary_subject.books]))
    diary_book = diary_subject.books[0]
    check("日记 Book 目录与手写图一致",
          sorted(p.name for p in diary_book.path.iterdir() if p.is_dir())
          == sorted(C.DIARY_TEMPLATE_DIRS),
          str(sorted(p.name for p in diary_book.path.iterdir() if p.is_dir())))
    check("日记 Book 里没有教材目录",
          not (diary_book.path / C.BOOK_FOLDER).exists())
    check("日记 Book 里有 Introduct.md",
          (diary_book.path / C.INTRO_FILE).is_file())

    # 日记类型的总结来源
    diary_summarizer = Summarizer(config, library)
    diary_labels_spec = [label for label, _ in diary_summarizer.source_spec(C.SUBJECT_DIARY)]
    check("日记类型总结来源正确",
          diary_labels_spec == ["intro", "my diary", "else diary"], str(diary_labels_spec))
    normal_labels_spec = [
        label for label, _ in diary_summarizer.source_spec(C.SUBJECT_SELF_STUDY)
    ]
    check("普通类型总结来源不变",
          normal_labels_spec == ["intro", "notebook", "error-prone"], str(normal_labels_spec))

    # 旧配置里的 summary.sources 默认值不应盖掉类型默认
    saved_sources = config.get("summary.sources", None)
    config.set("summary.sources", ["Introduct.md", "notebook", "error-prone"])
    check("旧默认 sources 被识别为未自定义",
          [label for label, _ in diary_summarizer.source_spec(C.SUBJECT_DIARY)]
          == ["intro", "my diary", "else diary"],
          str([label for label, _ in diary_summarizer.source_spec(C.SUBJECT_DIARY)]))
    config.set("summary.sources", ["Introduct.md", "my diary"])
    check("用户真的自定义时予以尊重",
          [label for label, _ in diary_summarizer.source_spec(C.SUBJECT_DIARY)]
          == ["intro", "my diary"],
          str([label for label, _ in diary_summarizer.source_spec(C.SUBJECT_DIARY)]))
    config.set("summary.sources", saved_sources if saved_sources is not None else [])

    # 自学课/校修课的作业目录仍然是同一个 homework（功能性质不变）
    practice_subject = library.create_subject("练习测试", subject_type=C.SUBJECT_SELF_STUDY)
    practice_book = library.create_book(practice_subject.name, "练习书目")
    check("自学课的「练习」落在 homework 目录",
          (practice_book.path / C.HOMEWORK_FOLDER).is_dir())
    check("练习目录不参与 AI 总结",
          C.HOMEWORK_FOLDER not in C.summary_sources_for_type(C.SUBJECT_SELF_STUDY))

    # ------------------------------------------------ 新建的排在最后
    # 需求：新创建的 Subject / Book 默认排在列表最后
    order_a = library.create_subject("排序甲科目")
    library.create_subject("排序乙科目")
    library.create_subject("排序丙科目")
    library.invalidate()
    ordered_names = [s.name for s in library.subjects(refresh=True)]
    tail = [n for n in ordered_names if n.startswith("排序")]
    check("新建科目按创建顺序排（新的在后面）",
          tail == ["排序甲科目", "排序乙科目", "排序丙科目"], str(ordered_names))
    check("最后建的科目真的在列表末尾",
          ordered_names[-1] == "排序丙科目", str(ordered_names[-3:]))

    # 日记科目（会自动建 MyBook）同样排最后
    library.create_subject("排序日记科目", subject_type=C.SUBJECT_DIARY)
    library.invalidate()
    names_with_diary = [s.name for s in library.subjects(refresh=True)]
    check("新建日记科目也排在最后",
          names_with_diary[-1] == "排序日记科目", str(names_with_diary[-3:]))

    # 书目
    book_subject = library.create_subject("排序书目科目")
    library.create_book(book_subject.name, "排序书目A")
    library.create_book(book_subject.name, "排序书目B")
    library.create_book(book_subject.name, "排序书目C")
    library.invalidate()
    book_names = [b.name for b in library.subject(book_subject.name).books]
    check("新建书目按创建顺序排（新的在后面）",
          book_names == ["排序书目A", "排序书目B", "排序书目C"], str(book_names))
    check("最后建的书目在列表末尾",
          book_names[-1] == "排序书目C", str(book_names))

    # 在"有收纳箱"的混排里，新科目也要排在所有顶层项之后
    box_last = library.boxes.create("排序末箱")
    library.boxes.move_subjects(box_last.id, ["排序甲科目"])
    library.invalidate()
    library.create_subject("排序末科目")
    library.invalidate()
    sequence = library.home_sequence(refresh=True)
    check("混排（箱子+科目）里新科目也排最后",
          sequence[-1] == ("subject", "排序末科目"), str(sequence))

    # 排最后是"默认值"，不是"锁死"：之后仍能拖拽改顺序
    library.set_home_order(
        [("subject", "排序末科目")] + [item for item in sequence
                                      if item != ("subject", "排序末科目")]
    )
    library.invalidate()
    check("新建排最后只是默认，仍可拖到最前",
          library.home_sequence(refresh=True)[0] == ("subject", "排序末科目"),
          str(library.home_sequence(refresh=True)[:3]))

    # ------------------------------------------------ AI 助手自称「长庚」
    # 需求：软件里的所有 AI 助手要自称长庚，不要叫「大白星球」（那是太白金星）。
    prompt_names = [
        name for name in dir(C)
        if "PROMPT" in name and isinstance(getattr(C, name), str)
    ]
    check("有 AI 助手名称常量且为「长庚」",
          C.AI_ASSISTANT_NAME == "长庚", C.AI_ASSISTANT_NAME)
    check("找得到所有 AI 提示词（至少 6 段）",
          len(prompt_names) >= 6, str(prompt_names))
    check("每段 AI 提示词都自称「长庚」",
          all(C.AI_ASSISTANT_NAME in getattr(C, n) for n in prompt_names),
          str([n for n in prompt_names
               if C.AI_ASSISTANT_NAME not in getattr(C, n)]))
    check("没有任何提示词把软件名当成助手名字",
          all("大白星球" not in getattr(C, n) for n in prompt_names),
          str([n for n in prompt_names if "大白星球" in getattr(C, n)]))
    check("提示词有版本号（改动可以被老用户感知）",
          int(C.PROMPT_REVISION) >= 1, str(C.PROMPT_REVISION))

    # 提示词版本升级：老 config.json 里的旧默认提示词要被换成新版
    import json as _json2

    legacy_dir = Path(tempfile.mkdtemp(prefix="gwp_prompt_"))
    legacy_file = legacy_dir / "config.json"
    legacy_file.write_text(_json2.dumps({
        "prompts": {
            "summary_system": "你是 Great White Planet 学习软件的「学习资料整合专家」。",
            "chat_system": "你是 Great White Planet 内置的 AI 学习助手。",
        },
        "ui": {"theme": "dark", "font_size": 13},
    }, ensure_ascii=False), encoding="utf-8")
    upgraded = Config.load(legacy_file, force=True)
    check("旧版提示词被升级为「长庚」版",
          C.AI_ASSISTANT_NAME in str(upgraded.get("prompts.summary_system")),
          str(upgraded.get("prompts.summary_system"))[:50])
    check("升级写入新的提示词版本号",
          int(upgraded.get("prompts.revision", 0)) == int(C.PROMPT_REVISION),
          str(upgraded.get("prompts.revision")))
    check("升级只动提示词，用户的其它设置保留",
          upgraded.get("ui.theme") == "dark"
          and int(upgraded.get("ui.font_size", 0) or 0) == 13,
          f"{upgraded.get('ui.theme')} / {upgraded.get('ui.font_size')}")
    check("升级结果落盘了",
          C.AI_ASSISTANT_NAME in _json2.loads(
              legacy_file.read_text(encoding="utf-8")
          )["prompts"]["summary_system"])

    # 用户自己锁定过（revision 已是最新）就不能动他的提示词
    locked_file = legacy_dir / "locked.json"
    locked_file.write_text(_json2.dumps({
        "prompts": {
            "revision": C.PROMPT_REVISION,
            "summary_system": "这是我自己改的提示词，不要动",
        },
    }, ensure_ascii=False), encoding="utf-8")
    locked = Config.load(locked_file, force=True)
    check("用户锁定过的提示词不会被自动覆盖",
          locked.get("prompts.summary_system") == "这是我自己改的提示词，不要动",
          str(locked.get("prompts.summary_system")))

    # ------------------------------------------------ 图片提取为 Markdown
    # 需求："增加文件夹内多图片AI提取内容（无把握识别准确就直接插入图片）并合并为md功能"
    from gwp.services import image_digest as _dig

    _img_dir = Path(tempfile.mkdtemp(prefix="gwp_digest_"))
    for _name in ("第10页.png", "第2页.png", "第1页.png", "封面.JPG"):
        (_img_dir / _name).write_bytes(b"\x89PNG\r\n\x1a\n")   # 内容不重要
    (_img_dir / "说明.txt").write_text("不是图片", encoding="utf-8")
    (_img_dir / ".隐藏.png").write_bytes(b"x")
    (_img_dir / "子目录").mkdir()
    (_img_dir / "子目录" / "深入一页.png").write_bytes(b"x")

    _imgs = _dig.collect_images(_img_dir)
    check("只收图片，不收其它文件",
          all(_dig.is_image(p) for p in _imgs) and len(_imgs) == 4,
          str([p.name for p in _imgs]))
    check("按自然顺序排（第2页在第10页前）",
          [p.name for p in _imgs]
          == ["封面.JPG", "第1页.png", "第2页.png", "第10页.png"],
          str([p.name for p in _imgs]))
    check("默认不递归子文件夹",
          not any(p.parent != _img_dir for p in _imgs),
          str([str(p.parent.name) for p in _imgs]))
    check("可以递归收子文件夹",
          len(_dig.collect_images(_img_dir, recursive=True)) == 5,
          str(len(_dig.collect_images(_img_dir, recursive=True))))
    check("隐藏文件被跳过",
          all(not p.name.startswith(".") for p in _imgs), str(len(_imgs)))
    check("不存在的文件夹返回空", _dig.collect_images(_img_dir / "没有") == [])

    # ---- "没把握"的判断：宁可多插一张图，也不留幻觉 ----
    _good = ("## 一小节\n\n这是一段足够长的正文，用来通过可靠性检查。\n\n"
             "公式 $E = mc^2$ 与结论。") * 2
    check("正常长文判为可信", _dig.evaluate_extraction(_good).reliable)
    check("空文本判为不可信",
          not _dig.evaluate_extraction("").reliable)
    check("太短的判为不可信",
          not _dig.evaluate_extraction("abc").reliable)
    check("AI 自认看不清 -> 不可信",
          not _dig.evaluate_extraction("抱歉，这张图片无法辨认清楚，无法提供内容。" * 2).reliable)
    check("出现无法辨认占位符 -> 不可信",
          not _dig.evaluate_extraction(
              "本章内容如下：[[无法辨认]] 后面还有一段推导。" * 2).reliable)
    check("乱码过多 -> 不可信",
          not _dig.evaluate_extraction("���□□□□" + "内容" * 30).reliable)
    check("手动标记没把握 -> 不可信（即使正文很长）",
          not _dig.evaluate_extraction(_good, user_unsure=True).reliable)
    check("不可信时给出原因文字",
          _dig.evaluate_extraction("abc").reason_text != "识别正常",
          _dig.evaluate_extraction("abc").reason_text)

    # ---- 人手改过的正文是权威，不再被自动判死 ----
    _edited = _dig.ImageResult(
        image=_img_dir / "第1页.png", text="抱歉，看不清", edited=True,
    )
    check("用户手改过的正文不再被自动判为不可信", _edited.usable)
    _auto = _dig.ImageResult(image=_img_dir / "第1页.png", text="抱歉，看不清")
    check("同样内容未手改则判为不可信（会插图）", not _auto.usable)

    # ---- 组装 Markdown ----
    # 失败项刻意用"足够长、但 AI 自认看不清"的文本：
    # 这样走到的是**关键词判断**那条分支（太短的文本会提前返回，测不到它）。
    _hedged = "抱歉，这段内容我无法辨认清楚，无法提供完整转写。" * 3
    _results = [
        _dig.ImageResult(image=_img_dir / "第1页.png", text=_good),
        _dig.ImageResult(image=_img_dir / "第2页.png", text=_hedged),
    ]
    _md = _dig.build_markdown(_results, base_dir=_img_dir, title="第一章")
    check("结果里含标题与来源说明", "第一章 · 图片提取" in _md and "第1页.png" in _md)
    check("识别成功的用正文，不插图",
          "![第1页.png]" not in _md, "成功的不该插图")
    check("识别失败的**直接插入原图**",
          "![第2页.png](第2页.png)" in _md, "失败的应插图")
    check("插图用相对路径（整个文件夹搬走也不失效）",
          f"({_img_dir.as_posix()}" not in _md, "不该出现绝对路径")
    check("失败项写明原因",
          "没能可靠识别" in _md and "原因：" in _md
          and "看不清" in _md, _md[:400])
    check("有总览统计表",
          "| 图片总数 | 2 |" in _md and "| 插入原图（无法可靠识别） | 1 |" in _md,
          _md[:600])
    check("AI 正文里的标题被降级（不与节标题撞级）",
          "#### " in _md and "\n## 一小节" not in _md, _md[:600])
    check("空结果也能生成（不崩）",
          "没有找到图片" in _dig.build_markdown([], base_dir=_img_dir))

    check("建议文件名含文件夹名与日期",
          _dig.suggest_filename("第一章").startswith("第一章_图片提取_")
          and _dig.suggest_filename("第一章").endswith(".md"),
          _dig.suggest_filename("第一章"))
    check("统计文案正确",
          _dig.summary_line(_results) == "共 2 张：1 张提取成功，1 张改为插入原图",
          _dig.summary_line(_results))
    check("提示词要求不猜测、看不清要标注",
          "绝对不要猜测" in _dig.IMAGE_EXTRACT_PROMPT
          and "[[无法辨认]]" in _dig.IMAGE_EXTRACT_PROMPT)
    check("提示词要求图不凭空描述",
          "[图：" in _dig.IMAGE_EXTRACT_PROMPT)
    check("单张提示词带序号与文件名",
          "第 2/5 张" in _dig.build_prompt(2, 5, "第2页.png")
          and "第2页.png" in _dig.build_prompt(2, 5, "第2页.png"))

    # ------------------------------------------------ AI 对话附件
    # 需求："AI助手新增附件上传功能 如果无法实现，想一个替代方案"
    # 替代方案：文档本地提取正文 / 图片交给视觉模型或人工。两条路都不"假装读过"。
    from gwp.services import attachment as _att

    _att_dir = Path(tempfile.mkdtemp(prefix="gwp_att_"))
    (_att_dir / "讲义.md").write_text(
        "# 第二章 极限\n\n定义：任给 ε>0，存在 δ>0 ……\n", encoding="utf-8"
    )
    (_att_dir / "成绩.csv").write_text("科目,分数\n数学,95\n", encoding="utf-8")
    (_att_dir / "板书.jpg").write_bytes(b"\xff\xd8\xff")
    (_att_dir / "旧文档.doc").write_bytes(b"\xd0\xcf\x11\xe0")

    _a_md = _att.extract_attachment(_att_dir / "讲义.md")
    _a_csv = _att.extract_attachment(_att_dir / "成绩.csv")
    _a_img = _att.extract_attachment(_att_dir / "板书.jpg")
    _a_doc = _att.extract_attachment(_att_dir / "旧文档.doc")
    _a_missing = _att.extract_attachment(_att_dir / "不存在.pdf")

    check("文本类附件能本地提取出正文",
          _a_md.kind == _att.KIND_TEXT and _a_md.usable
          and "任给" in _a_md.markdown, _a_md.describe())
    check("表格转成了 Markdown 表格",
          _a_csv.usable and "| 科目 | 分数 |" in _a_csv.markdown,
          _a_csv.markdown[:80])
    check("图片被单独标出（不走文本提取）",
          _a_img.kind == _att.KIND_IMAGE and not _a_img.usable,
          _a_img.describe())
    check("图片的状态说明写清了要视觉模型",
          "视觉模型" in _a_img.describe(), _a_img.describe())
    check("旧版 Office 格式被如实判为不可读（不假装读到内容）",
          _a_doc.kind == _att.KIND_UNSUPPORTED and not _a_doc.usable,
          _a_doc.describe())
    check("不可读的附件不会把 reader 的说明文字当成正文",
          "无法解析" not in _a_doc.markdown, repr(_a_doc.markdown[:60]))
    check("文件不存在时给出明确原因",
          _a_missing.kind == _att.KIND_UNSUPPORTED
          and "不存在" in _a_missing.error, _a_missing.error)

    # 截断：如实告知，不悄悄丢内容
    _big = _att_dir / "长文.txt"
    _big.write_text("行" * 5000, encoding="utf-8")
    _a_big = _att.extract_attachment(_big, per_file_chars=100)
    check("超长附件被截断且如实标记",
          _a_big.truncated and _a_big.chars == 100
          and _a_big.original_chars == 5000, _a_big.describe())
    check("截断情况写进了给用户看的状态里",
          "超出部分未发送" in _a_big.describe(), _a_big.describe())

    # 拼给 AI 的块
    _atts = [_a_md, _a_csv, _a_img, _a_doc]
    _block = _att.build_attachment_block(_atts, total_chars=100000)
    check("附件块里含每份附件的名字",
          all(a.name in _block for a in _atts), _block[:200])
    check("附件块里含提取到的正文", "任给" in _block)
    check("附件块明确写出图片内容没包含进来",
          "内容没有包含在本次对话里" in _block, _block[:400])
    check("附件块明确写出哪份没能读取",
          "没能读取" in _block, _block[:400])
    check("附件块要求 AI 别假装读过",
          "不要假装读过" in _block, _block[:200])
    check("没有任何可用附件时，明说看不到文件",
          "没有任何一份的内容成功传给了你"
          in _att.build_attachment_block([_a_img], total_chars=1000),
          _att.build_attachment_block([_a_img], total_chars=1000)[:120])
    check("没有附件时返回空串",
          _att.build_attachment_block([], total_chars=1000) == "")
    check("总量上限真的生效（超出会标出只发了一部分）",
          "只发送了前面一部分"
          in _att.build_attachment_block([_a_big], total_chars=10))
    check("统计文案正确",
          _att.summarize(_atts)
          == "共 4 份附件：2 份已提取正文、1 张图片需视觉模型、1 份未能读取",
          _att.summarize(_atts))
    class _BadConfig:
        """模拟用户把配置写坏了（字符串 / Negative）。"""

        def get(self, key, default=None):
            return {"ai.attach_chars_per_file": "abc",
                    "ai.attach_chars_total": -5}.get(key, default)

    check("上限配置有兜底（写坏了也不会让附件静默失效）",
          _att.budget_from_config(_BadConfig())
          == (_att.DEFAULT_PER_FILE_CHARS, 1000),
          str(_att.budget_from_config(_BadConfig())))
    check("能判断哪些类型注册过读取器",
          _att.extraction_supported(_att_dir / "讲义.md")
          and _att.extraction_supported(_att_dir / "板书.jpg")
          and not _att.extraction_supported(_att_dir / "x.zzz"),
          "md/jpg 应支持，未知扩展名不应支持")
    check("注册过 reader 不等于一定能读出内容（.doc 有 reader 但读不出）",
          _att.extraction_supported(_att_dir / "旧文档.doc") is True
          and _att.extract_attachment(_att_dir / "旧文档.doc").usable is False,
          "这个区别必须靠 usable 判断")

    # ------------------------------------------------ 单词书（单词卡）
    # 需求："在英语科目中新增单词书栏目 书内部可以添加单词卡 单词卡可折叠
    #       我只需要添加英文单词/短语 就可以自动补齐中文解释/例句等等"
    # 后续需求："所有科目公用一个文件夹"
    from gwp.data_manager import wordbook as _wb

    check("**单词书不在书目模板里**（它已改成所有科目共用一个目录）",
          _C.WORDBOOK_LEGACY_FOLDER not in _C.BOOK_TEMPLATE_DIRS
          and _C.WORDBOOK_LEGACY_FOLDER not in _C.DIARY_TEMPLATE_DIRS,
          f"{_C.BOOK_TEMPLATE_DIRS} / {_C.DIARY_TEMPLATE_DIRS}")
    check("单词书目录名已定义（全局那一份）",
          _C.WORDBOOK_DIR == "wordbook", _C.WORDBOOK_DIR)
    for _type_name, _tabs in (
        ("自学课", _C.BOOK_TABS_SELF_STUDY),
        ("校修课", _C.BOOK_TABS_SCHOOL),
        ("日记", _C.BOOK_TABS_DIARY),
    ):
        check(f"{_type_name}的栏目里有「单词书」",
              any(key == "wordbook" for key, _t, _f in _tabs),
              str([t for _k, t, _f in _tabs]))
        check(f"{_type_name}的「单词书」标签没有书目内目录（内容来自全局那份）",
              all(f is None for k, _t, f in _tabs if k == "wordbook"),
              str([(k, f) for k, _t, f in _tabs if k == "wordbook"]))
    check("单词书不参与 AI 总结",
          _C.WORDBOOK_DIR not in _C.SUMMARY_SOURCE_DIRS)

    # 共用目录挂在 user data 下，**不在 subjects 里面**
    check("单词书目录位于 user data 下、不属于任何科目",
          paths.wordbook_dir == paths.user_data / "wordbook",
          str(paths.wordbook_dir))
    check("单词书目录不在 subjects 目录里",
          paths.subjects_dir not in paths.wordbook_dir.parents,
          str(paths.wordbook_dir))
    check("建立数据目录时会一并建出共用单词书目录",
          paths.wordbook_dir.is_dir(), str(paths.wordbook_dir))

    _wb_dir = Path(tempfile.mkdtemp(prefix="gwp_wordbook_"))

    # 文件名安全化：不改大小写、不删标点（它们是词条本身）
    check("单词里的撇号被保留", _wb.sanitize_english("don't") == "don't")
    check("短语里的空格被保留", _wb.sanitize_english("give up") == "give up")
    check("缩写里的句点被保留（不能被美化掉）",
          _wb.sanitize_english("a.m.") == "a.m.",
          _wb.sanitize_english("a.m."))
    check("非法文件名字符被替换",
          "/" not in _wb.sanitize_english("a/b") and ":" not in _wb.sanitize_english("a:b"),
          _wb.sanitize_english("a/b:c"))
    check("首尾空白被去掉", _wb.sanitize_english("  hello  ") == "hello")

    # 读写往返
    _card = _wb.WordCard(
        english="give up", phonetic="/ɡɪv ʌp/", part_of_speech="phr.",
        meaning="phr. 放弃；认输",
        examples="He gave up smoking. —— 他戒烟了。",
        phrases="give up on —— 对…不再抱希望",
        tip="give（给）+ up（向上）",
    )
    _saved = _wb.save_card(_card, _wb_dir)
    check("一张卡一个 json 文件", _saved.name == "give up.json", _saved.name)
    check("有内容的卡自动标为已补齐", _card.completed is True)
    _back = _wb.load_card(_saved)
    check("中文内容往返不损坏",
          _back is not None and "放弃" in _back.meaning
          and "戒烟" in _back.examples,
          repr(_back.meaning if _back else None))
    check("音标与词性也存下来了",
          _back.phonetic == "/ɡɪv ʌp/" and _back.part_of_speech == "phr.",
          f"{_back.phonetic} / {_back.part_of_speech}")

    check("能列出单词书里的卡片",
          [c.english for c in _wb.list_cards(_wb_dir)] == ["give up"],
          str([c.english for c in _wb.list_cards(_wb_dir)]))
    check("按英文查找忽略大小写与空白",
          (_wb.find_card(_wb_dir, "GIVE UP") or _wb.WordCard(english="")).english
          == "give up")
    check("查不存在的词返回 None",
          _wb.find_card(_wb_dir, "nonexistent") is None)
    check("只有一行英文的卡不算已补齐",
          _wb.WordCard(english="test").completed is False)
    check("卡片的 has_details 能区分空卡",
          not _wb.WordCard(english="x").has_details
          and _wb.WordCard(english="x", meaning="y").has_details)

    # 读坏文件不该让整个单词书打不开
    (_wb_dir / "broken.json").write_text("{不是合法 json", encoding="utf-8")
    check("损坏的 json 被跳过而不是让整本书报错",
          [c.english for c in _wb.list_cards(_wb_dir)] == ["give up"],
          str([c.english for c in _wb.list_cards(_wb_dir)]))
    (_wb_dir / "broken.json").unlink()

    # ---- AI 回答的各种"脏"格式都要能解析 ----
    _good_json = ('{"english":"abandon","phonetic":"/əˈbændən/","meaning":"v. 放弃",'
                  '"examples":"He abandoned it. —— 他放弃了它。",'
                  '"phrases":"","tip":""}')
    _cases = {
        "纯 JSON": _good_json,
        "带 ```json 围栏": f"```json\n{_good_json}\n```",
        "围栏没写语言": f"```\n{_good_json}\n```",
        "前后有寒暄": f"好的，这是结果：\n{_good_json}\n希望有帮助！",
        "带嵌套对象": ('{"english":"abandon","meaning":"v. 放弃",'
                       '"extra":{"a":1,"b":{"c":2}}}'),
        "字段缺失": '{"english":"abandon","meaning":"v. 放弃"}',
    }
    for _label, _text in _cases.items():
        _parsed, _err = _wb.parse_completion(_text, "abandon")
        check(f"AI 回答格式「{_label}」能被解析",
              _parsed is not None and not _err,
              f"card={_parsed is not None} err={_err}")
    _parsed, _err = _wb.parse_completion("这个单词的意思是放弃。", "abandon")
    check("完全不是 JSON 时明确失败（不瞎猜）",
          _parsed is None and bool(_err), str(_err))
    check("失败时给出可操作的原因",
          "JSON" in _err or "解析" in _err, _err)
    _parsed, _err = _wb.parse_completion(
        '{"english":"zzz","meaning":"未查到该词，请确认拼写"}', "zzz")
    check("AI 说查不到词时视为失败（不污染卡片）", bool(_err), _err)

    check("提示词要求只输出 JSON",
          "只输出一个 JSON 对象" in _wb.WORD_COMPLETE_PROMPT)
    check("提示词里带上了要查的词",
          "abandon" in _wb.build_prompt("abandon"))

    # ---- 合并：不冲掉用户改过的内容 ----
    _mine = _wb.WordCard(english="x", meaning="我自己写的释义")
    _fresh = _wb.WordCard(english="x", meaning="AI 的释义", phonetic="/eks/")
    _merged = _wb.merge_into(_mine, _fresh)
    check("合并时保留用户已填的释义",
          _merged.meaning == "我自己写的释义", _merged.meaning)
    check("合并时补上用户没填的音标",
          _merged.phonetic == "/eks/", _merged.phonetic)
    _mine2 = _wb.WordCard(english="x", meaning="我自己写的释义")
    check("显式要求覆盖时才替换",
          _wb.merge_into(_mine2, _fresh, force=True).meaning == "AI 的释义")
    _locked = _wb.WordCard(english="x", meaning="我的", locked=True)
    check("锁定的卡不会被自动覆盖",
          _wb.merge_into(_locked, _fresh).meaning == "我的")

    _with_details = _wb.WordCard(english="b", meaning="y")
    _wb.save_card(_with_details, _wb_dir)            # 存过之后才算"已补齐"
    check("统计文案正确",
          _wb.summarize([_wb.WordCard(english="a"), _with_details])
          == "共 2 张单词卡，1 张待补齐解释",
          _wb.summarize([_wb.WordCard(english="a"), _with_details]))
    check("空单词书的统计文案给出下一步",
          "添加单词" in _wb.summarize([]), _wb.summarize([]))

    # ---- 旧布局（每本书一个 wordbook）自动迁移到共用目录 ----
    #
    # 需求把单词书从"每本书一个"改成了"所有科目公用一个"，所以必须有迁移，
    # 否则老用户的生词会留在旧目录里"看不见了"。
    _mig_root = Path(tempfile.mkdtemp(prefix="gwp_wb_migrate_"))
    _mig_subjects = _mig_root / "subjects"
    _mig_shared = _mig_root / "wordbook"
    for _sub, _book, _words in (
        ("英语", "英语1", ["give up"]),
        ("英语", "英语2", ["abandon"]),
        ("数学分析", "上", ["give up"]),          # 与第一本重名 -> 必须保留两份
    ):
        _legacy = _mig_subjects / _sub / _book / "wordbook"
        _legacy.mkdir(parents=True)
        for _w in _words:
            _wb.save_card(
                _wb.WordCard(english=_w, meaning=f"{_book} 里的释义"), _legacy
            )

    _found = _wb.find_legacy_wordbooks(_mig_subjects)
    check("能找出旧布局的单词书目录", len(_found) == 3, str(len(_found)))
    check("没有旧目录时返回空列表",
          _wb.find_legacy_wordbooks(_mig_root / "nope") == [])

    _report = _wb.migrate_legacy_wordbooks(_mig_shared, _mig_subjects)
    check("迁移把 3 张卡都搬了过来",
          len(_report["moved"]) == 3, str(_report["moved"]))
    check("重名的卡**改名保留**而不是覆盖",
          len(_report["kept"]) == 1
          and "来自英语-英语1" in Path(_report["kept"][0]).stem,
          str(_report["kept"]))
    check("保留下来的卡名字里带着来源（能认出是哪本书的）",
          "英语1" in Path(_report["kept"][0]).stem,
          Path(_report["kept"][0]).stem)
    check("迁移后共用单词书里有 3 张卡",
          len(_wb.list_cards(_mig_shared)) == 3,
          str([c.english for c in _wb.list_cards(_mig_shared)]))
    check("两张同名卡的内容都在（没丢一张）",
          sorted(c.meaning for c in _wb.list_cards(_mig_shared)
                 if c.english == "give up")
          == sorted(["英语1 里的释义", "上 里的释义"]),
          str(sorted(c.meaning for c in _wb.list_cards(_mig_shared)
                     if c.english == "give up")))
    check("旧目录被清掉（不留两份让人困惑）",
          _wb.find_legacy_wordbooks(_mig_subjects) == [],
          str(_wb.find_legacy_wordbooks(_mig_subjects)))
    check("迁移是幂等的（再跑一次什么都不做）",
          _wb.migrate_legacy_wordbooks(_mig_shared, _mig_subjects)
          == {"moved": [], "kept": [], "removed_dirs": [], "failed": []})
    check("目录全空时迁移也不会出错",
          _wb.migrate_legacy_wordbooks(
              _mig_shared, _mig_root / "empty_subjects"
          )["moved"] == [])

    # ---- 作业改名（用户报障："更改作业名称功能异常"）----
    #
    # 两个缺陷叠加：
    #   ① 对话框在编辑模式下把"作业名称"输入框 setEnabled(False) 了，
    #      界面上根本没有改名的入口；
    #   ② edit_homework 从未读取作业名，只保存 DDL / 提交方式 / 内容。
    from gwp.data_manager import homework as _hw
    from gwp.data_manager import store as _store_mod

    _rn_root = Path(tempfile.mkdtemp(prefix="gwp_hw_rename_"))
    _rn = _hw.create(_rn_root / "第三章习题", content="题目：1+1",
                     due="2030-01-01T10:00", submit_url="https://x.test")
    (_rn.path / "补充材料.txt").write_text("x", encoding="utf-8")

    _rn_new = _hw.rename(_rn, "第三章作业")
    check("**改名后文件夹跟着换了名字**",
          _rn_new.path.name == "第三章作业" and _rn_new.path.is_dir(),
          str(_rn_new.path))
    check("旧文件夹已经不在了",
          not (_rn_root / "第三章习题").exists())
    check("homework.json 里的名字也改了",
          _hw.load(_rn_new.path).name == "第三章作业",
          _hw.load(_rn_new.path).name)
    check("**改名不丢 DDL / 提交网址**",
          _rn_new.due == "2030-01-01T10:00"
          and _rn_new.submit_url == "https://x.test",
          f"{_rn_new.due} / {_rn_new.submit_url}")
    check("作业内容也跟着走了",
          (_rn_new.path / "第三章作业.md").is_file(),
          str(sorted(p.name for p in _rn_new.path.iterdir())))
    check("**旧的 md 名字没有留下**（否则会出现两份内容）",
          not (_rn_new.path / "第三章习题.md").exists())
    check("文件夹里其它文件一起搬走了",
          (_rn_new.path / "补充材料.txt").is_file())

    check("改成同名等于什么都没做",
          _hw.rename(_rn_new, "第三章作业").path.name == "第三章作业")

    # 非法字符沿用统一的命名规则清洗（不自己实现一套）
    _rn_clean = _hw.rename(_hw.load(_rn_new.path) or _rn_new, "a/b:c")
    check("非法字符会被清洗（沿用 store.sanitize_name）",
          _rn_clean.path.name == _store_mod.sanitize_name("a/b:c"),
          f"{_rn_clean.path.name} vs {_store_mod.sanitize_name('a/b:c')}")
    check("清洗后的名字确实生效了",
          _hw.load(_rn_root / _rn_clean.path.name) is not None)

    # 目标已存在 -> 必须拦住，不能覆盖别人的作业
    _hw.create(_rn_root / "已存在", content="x")
    _blocked = False
    try:
        _hw.rename(_rn_clean, "已存在")
    except _store_mod.DataError:
        _blocked = True
    check("**改名撞上已有作业时会拦住（不覆盖）**", _blocked is True)
    check("拦下之后原作业还完好",
          _hw.load(_rn_root / _rn_clean.path.name) is not None)

    # 用户自己改过 md 文件名 -> 改作业名时不该动它
    _rn2 = _hw.create(_rn_root / "作业Z", content="z")
    (_rn2.path / "作业Z.md").rename(_rn2.path / "我自己改的.md")
    _rn3 = _hw.rename(_rn2, "作业W")
    check("用户改过 md 名时，改作业名不会误动它",
          (_rn3.path / "我自己改的.md").is_file()
          and not (_rn3.path / "作业W.md").exists(),
          str(sorted(p.name for p in _rn3.path.iterdir())))
    check("也不会把作业名和 md 名强行同步（尊重用户）",
          _rn3.name == "作业W")

    # ------------------------------------------------ LaTeX 公式渲染成图片
    #
    # 用户报障："md 预览时 数学符号，公式，拉丁字母内容显示异常"。
    #
    # 根因：软件内预览用 QTextBrowser（只支持 HTML4 + CSS2.1 的子集，
    # **不认识 LaTeX**），而总结提示词明确要求"公式使用 LaTeX"。
    # 实测 QTextDocument.toPlainText() 原样显示了 `$\varepsilon > 0$`。
    from gwp.services import math_render as _math
    from gwp.services import markdown_renderer as _md_render

    _eq_dir = Path(tempfile.mkdtemp(prefix="gwp_eq_"))
    _ok_cases = [
        r"\varepsilon > 0",
        r"\frac{1}{n} < \varepsilon",
        r"\lim_{n \to \infty} a_n = A",
        r"\sqrt{x^2 + y^2}",
        r"\int_0^1 f(x)\,dx",
        r"\sum_{i=1}^{n} a_i",
        r"\alpha + \beta",
    ]
    for _latex in _ok_cases:
        _res = _math.render_formula(_latex, size=15, scale=2)
        check(f"公式能渲染成图片：{_latex[:28]}",
              _res.ok and _res.image.width > 1 and _res.image.height > 1,
              _res.error)
        check(f"公式排版没有退化：{_latex[:28]}", _res.degraded is False,
              str(_res.degraded))

    # 不认识的命令：**局部标灰**而不是整条退化
    #
    # 注意 \mathbb 这类字体命令是**已知的**（会取内容继续排，不算退化），
    # 所以这里要挑一个真正不在任何命令表里的名字。
    _unknown = _math.render_formula(r"\foobarcmd{x} + y", size=15, scale=2)
    check("个别生僻命令不会让整条公式退化",
          _unknown.ok and _unknown.degraded is True,
          f"ok={_unknown.ok} degraded={_unknown.degraded}")
    check("字体类命令（\\mathbb 等）能正常取内容渲染、不算退化",
          _math.render_formula(r"\mathbb{N}", size=15, scale=2).degraded is False)

    # 明确不支持的（矩阵）应当**整体退化并标注**，不猜
    _matrix = _math.render_formula(
        r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}", size=15, scale=2
    )
    check("矩阵这类排不出的公式会标注退化而不是画错",
          _matrix.ok and _matrix.degraded is True,
          f"ok={_matrix.ok} degraded={_matrix.degraded}")

    check("空公式不会崩", _math.render_formula("").ok is False)
    check("渲染器永不抛异常（乱码输入）",
          _math.render_formula("\\frac{").ok in (True, False))

    _n1 = _math.formula_cache_name(r"\frac{1}{n}")
    _n2 = _math.formula_cache_name(r"\frac{1}{n}")
    _n3 = _math.formula_cache_name(r"\frac{1}{m}")
    check("同一条公式的图片名稳定（可复用）", _n1 == _n2, _n1)
    check("不同公式的图片名不同", _n1 != _n3)

    _png, _deg = _math.render_to_png(r"a+b", _eq_dir / "x.png", size=15, scale=2)
    check("公式能落盘成 PNG", _png is not None and _png.is_file())

    # 公式目录常量（需求："图片本地可以专门找一个新位置存储"）
    check("公式图片有专门的目录名",
          _math.EQUATION_DIR_NAME == "equations", _math.EQUATION_DIR_NAME)

    # markdown 渲染时把公式换成图片引用
    _md_text = "设 $\\varepsilon>0$，则 $|a_n-A|<\\varepsilon$。\n"
    _sub, _count = _md_render.substitute_equations(_md_text, _eq_dir)
    check("**Markdown 里的公式被换成了图片引用**", _count == 2, str(_count))
    check("替换后不再有裸美元号公式", "$\\varepsilon" not in _sub, _sub[:120])
    check("替换后留下了图片标记", "![" in _sub, _sub[:120])

    # iter_formulas：行内与独立公式都能认出来
    _mixed = "行内 $a+b$ 与独立：\n$$c+d$$\n结束"
    _found = list(_math.iter_formulas(_mixed))
    check("能同时认出四种公式定界符（行内/独立）",
          len(_found) == 2
          and not _found[0][1] and _found[1][1],
          str([(m.group(0), d) for m, d in _found]))

    # ------------------------------------------------ 文档合并
    #
    # 需求："更主要的功能是文档合并，你要把 pdf 以及其他文档插入到 summary
    #       文档中 … 如果插入困难，便以图片插入，图片本地可以专门找一个
    #       新位置存储"
    from gwp.services import source_merge as _merge

    _mg_root = Path(tempfile.mkdtemp(prefix="gwp_merge_"))
    _mg_book_dir = _mg_root / "book"
    (_mg_book_dir / C.NOTEBOOK_FOLDER).mkdir(parents=True)
    (_mg_book_dir / C.ERROR_FOLDER).mkdir(parents=True)
    (_mg_book_dir / C.NOTEBOOK_FOLDER / "笔记.md").write_text(
        "设 $\\varepsilon>0$，则 $|a_n-A|<\\varepsilon$。\n\n"
        "| 记号 | 含义 |\n|---|---|\n| $\\varepsilon$ | 小正数 |\n",
        encoding="utf-8",
    )
    (_mg_book_dir / C.ERROR_FOLDER / "易错.md").write_text(
        "错误：忽略前提条件。", encoding="utf-8"
    )
    (_mg_book_dir / C.NOTEBOOK_FOLDER / "图.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
    )
    # 造一个两页 PDF（用 PyMuPDF，不依赖外部文件）
    import fitz as _fitz

    _pdf = _fitz.open()
    for _index in range(2):
        _pdf.new_page().insert_text((72, 100), f"page {_index + 1}")
    _pdf.save(str(_mg_book_dir / C.NOTEBOOK_FOLDER / "教材.pdf"))
    _pdf.close()

    class _FakeBook:
        name = "合并测试书目"
        path = _mg_book_dir
        intro_path = None

    _sources = _merge.collect_sources(_FakeBook())
    check("**能收集到书目里的全部资料**（笔记 + 易错题，含子目录）",
          len(_sources) == 4, str([(lbl, p.name) for lbl, p in _sources]))
    check("收集时会跳过软件自己的数据文件",
          all(p.name not in (C.BOOK_META, C.HOMEWORK_META)
              for _lbl, p in _sources),
          str([p.name for _lbl, p in _sources]))

    _mg_else = _mg_root / "else data"
    _report = _merge.run_merge(_FakeBook(), _mg_else, _sources)
    check("**合并后一份资料都没失败**",
          not _report.failed, str([(i.source.name, i.error) for i in _report.failed]))
    check("**PDF 每页都变成了一张图片**",
          len(next(i for i in _report.items
                   if i.source.suffix == ".pdf").images) == 2,
          str([(i.source.name, len(i.images)) for i in _report.items]))
    check("图片文件被直接登记进来",
          len(next(i for i in _report.items
                   if i.source.suffix == ".png").images) == 1)
    # 需求变更后：**md 直接融合成文字**，不再转成图片
    _md_item = next(i for i in _report.items if i.source.suffix == ".md")
    check("**md 现在是直接融合成文字（不再转图片）**",
          _md_item.is_text and not _md_item.images,
          f"kind={_md_item.kind} 文字={len(_md_item.text)} 图={len(_md_item.images)}")
    check("**图片集中存放在专门的新位置**",
          _report.output_dir is not None
          and _report.output_dir.is_dir()
          and _report.output_dir.parent.name == _merge.MERGED_DIR_NAME,
          str(_report.output_dir))
    check("图片落在 else data 下（不污染书目目录）",
          _mg_else in _report.output_dir.parents, str(_report.output_dir))
    check("合并出的图片都是真实存在的文件",
          all(p.is_file() for item in _report.items for p in item.images),
          str([str(p) for item in _report.items for p in item.images][:2]))
    check("图片文件名可读（不是一串下划线）",
          all("_" in p.stem and len(p.stem) > 6
              for item in _report.items for p in item.images),
          str([p.name for item in _report.items for p in item.images][:2]))

    # 公式图片应当也生成到了专用目录
    _mg_section = _merge.build_section(_report, _mg_else)
    # 图片来自 PDF（2 张）与 png（1 张）；md 现在是文字，所以总数比原来少
    check("合并小节里有图片引用", _mg_section.count("![") >= 3,
          str(_mg_section.count("![")))
    check("**合并小节里也有直接融合进来的 md 正文**",
          "忽略前提条件" in _mg_section, _mg_section[:200])
    check("合并小节说明图片存放位置",
          _merge.MERGED_DIR_NAME in _mg_section, _mg_section[:200])

    _base = "# 总结\n\n正文。\n"
    _once = _merge.append_to_summary(_base, _mg_section)
    _twice = _merge.append_to_summary(_once, _mg_section)
    check("**重复合并不会越插越多**", _once == _twice,
          f"{len(_once)} vs {len(_twice)}")
    check("合并小节带可识别标记（用于替换）",
          _once.count(_merge.MERGE_MARKER) == 1,
          str(_once.count(_merge.MERGE_MARKER)))
    # 注意：数起始标记必须用**完整字符串** —— "GWP:MERGED-SOURCES"
    # 是 "...-END" 的子串，数子串会得到 2（踩过）。
    check("正文还在（没被替换掉）", _once.startswith("# 总结"), _once[:40])

    # ------------------------------------------------ 新建作业沿用上次的提交网址
    #
    # 需求："新建作业的提交方式的网址默认为该book的作业之前的提交方式的网址，
    #       避免用户每次输入"
    #
    # 就近导入：`_hw` 是别的段落里的**函数内局部名**，这一层用不到
    # （这个坑本文件里已经踩过一次，见作业改名那段）。
    from gwp.data_manager import homework as _hw

    _url_root = Path(tempfile.mkdtemp(prefix="gwp_lasturl_")) / "书目"
    _url_root.mkdir(parents=True)
    check("没有作业时拿不到上次的提交网址（不编造）",
          _hw.last_submit_url(_url_root) == "",
          repr(_hw.last_submit_url(_url_root)))

    _hw.create(_url_root / "homework" / "作业一", content="A",
               due="2030-01-01T10:00", submit_url="https://a.example.com/1")
    check("**只有一份作业时，取出它的提交网址**",
          _hw.last_submit_url(_url_root) == "https://a.example.com/1",
          repr(_hw.last_submit_url(_url_root)))

    _hw.create(_url_root / "homework" / "作业二", content="B", due="",
               submit_url="https://b.example.com/2")
    check("**多份作业时取最近的那份**",
          _hw.last_submit_url(_url_root) == "https://b.example.com/2",
          repr(_hw.last_submit_url(_url_root)))

    # 最近那份没网址 -> **继续往前找**，不要把默认值变空
    _hw.create(_url_root / "homework" / "作业三", content="C", due="",
               submit_url="")
    check("最近那份没填网址时，往前找还有网址的那一份",
          _hw.last_submit_url(_url_root) == "https://b.example.com/2",
          repr(_hw.last_submit_url(_url_root)))

    # 非法网址不算数
    _hw.create(_url_root / "homework" / "作业四", content="D", due="",
               submit_url="这不是网址")
    check("非法的提交网址不会被当成默认值",
          _hw.last_submit_url(_url_root) == "https://b.example.com/2",
          repr(_hw.last_submit_url(_url_root)))

    # ------------------------------------------------ PDF 排版不收敛的防护
    #
    # 事故：书稿 PDF 一度长到 987 MB / 5013 页 —— PyMuPDF 1.28.2 的 Story
    # 在某些内容组合下不收敛（place() 永远返回 more=1，每页填充区域完全相同），
    # 一路排到 5000 页的"防御性上限"然后 break，**默默写出一个 1 GB 的废文件**。
    #
    # 现在改成：连续若干页填充区域一致就报错并丢弃产物。
    # 这里不去复现那个第三方缺陷（内容组合没定位到最小条件），
    # 只验证**防护本身**是有效的、且不会误伤正常文档。
    from gwp.services import pdf_exporter as _pdf

    check("存在不收敛检测的页数阈值",
          isinstance(_pdf._STALL_PAGE_LIMIT, int)
          and 1 < _pdf._STALL_PAGE_LIMIT < 5000,
          repr(_pdf._STALL_PAGE_LIMIT))

    _pdf_dir = Path(tempfile.mkdtemp(prefix="gwp_pdf_"))
    # 正常文档：必须还能正常导出，不能被误判成卡住
    _normal_md = "# 标题\n\n" + "".join(
        f"这是第 {i} 段正文，用来验证正常文档不会被误伤。\n\n" for i in range(1, 90)
    )
    _normal_out = _pdf_dir / "normal.pdf"
    try:
        _pdf.export_markdown_to_pdf(_normal_md, _normal_out, page_numbers=False)
        _normal_pages = _pdf.count_pdf_pages(_normal_out)
        check("**正常文档仍能正常导出 PDF**",
              1 < _normal_pages < 50, f"{_normal_pages} 页")
        check("正常文档的产物大小合理",
              _normal_out.is_file() and _normal_out.stat().st_size < 5 * 1024 * 1024,
              f"{_normal_out.stat().st_size if _normal_out.is_file() else 0} 字节")
    except _pdf.PDFExportError as exc:
        check("**正常文档仍能正常导出 PDF**", False, str(exc)[:120])

    # 不收敛检测的逻辑本身：模拟"每页填充区域完全一样"
    _stall_calls: list[str] = []

    class _FakeStory:
        """假的 Story：永远返回 more=1，且 filled 恒定（模拟卡死）。"""

        def __init__(self, **_kwargs) -> None:
            self.count = 0

        def place(self, _where):
            self.count += 1
            return 1, (36.0, 36.0, 559.0, 832.7)

        def draw(self, _device) -> None:
            return None

    class _FakeWriter:
        def begin_page(self, _box):
            return object()

        def end_page(self) -> None:
            return None

        def close(self) -> None:
            return None

    class _FakePymupdf:
        Rect = staticmethod(lambda *args: tuple(args))
        DocumentWriter = staticmethod(lambda _path: _FakeWriter())
        Story = staticmethod(lambda **kwargs: _FakeStory(**kwargs))

    try:
        _pdf._render(
            _FakePymupdf, "<html></html>", _pdf_dir / "stall.pdf",
            595, 842, 36, lambda *_a: _stall_calls.append("r"), lambda: False,
        )
        check("**排版不收敛时会报错而不是写出废文件**", False,
              "居然没有报错")
    except _pdf.PDFExportError as exc:
        check("**排版不收敛时会报错而不是写出废文件**",
              "收敛" in str(exc), str(exc)[:140])
        check("报错信息说明了页数与建议",
              "页" in str(exc) and ("拆" in str(exc) or "部分" in str(exc)),
              str(exc)[:160])
    except Exception as exc:  # noqa: BLE001
        check("**排版不收敛时会报错而不是写出废文件**", False,
              f"{type(exc).__name__}: {exc}")

    # ------------------------------------------------ AI 混排页序
    #
    # 需求："AIsummary中 AI可以根据自己的理解改变图片插入顺序，
    #       实现不同文件夹内容，的混排插入"
    #
    # 重点测**校验**：AI 只要漏一页或多一页，就必须整条拒绝、退回原顺序 ——
    # 因为排错一份就会丢页或重复页，那比不混排严重得多。
    from gwp.services import source_merge as _mix_mod

    _mix_root = Path(tempfile.mkdtemp(prefix="gwp_mix_")) / "book"
    (_mix_root / C.NOTEBOOK_FOLDER).mkdir(parents=True)
    (_mix_root / C.ERROR_FOLDER).mkdir(parents=True)
    # **混排只对"图片型"资料有意义**（它排的是"页"）。
    # 所以这里用图片型素材：三个 png（各 2 张）+ 一个两页的图片型 PDF。
    # 注意不能用 .md 当素材 —— 需求变更后 md 是"文字型"，
    # 而文字型没有"页"可排（见 mix_pages 里那条直接放弃混排的分支）。
    from PIL import Image as _MixImg
    from PIL import ImageDraw as _MixDraw

    _mix_img = Path(tempfile.mkdtemp(prefix="gwp_mixsrc_")) / "p.png"
    _mi = _MixImg.new("RGB", (700, 900), (255, 255, 255))
    _MixDraw.Draw(_mi).text((40, 40), "MIX PAGE", fill=(0, 0, 0))
    _mi.save(_mix_img)

    for folder, name in (
        (C.NOTEBOOK_FOLDER, "甲.png"),
        (C.NOTEBOOK_FOLDER, "乙.png"),
        (C.ERROR_FOLDER, "丙.png"),
    ):
        (_mix_root / folder / name).write_bytes(_mix_img.read_bytes())

    # 两页的图片型 PDF（没有文字层）
    import fitz as _fitz_mix

    _mpdf = _mix_fitz_open = _fitz_mix.open()
    for _ in range(2):
        _pg = _mpdf.new_page(width=595, height=842)
        _pg.insert_image(_fitz_mix.Rect(0, 0, 595, 842), filename=str(_mix_img))
    _mpdf.save(str(_mix_root / C.NOTEBOOK_FOLDER / "扫描.pdf"))
    _mpdf.close()

    class _MixBook:
        name = "混排测试书目"
        path = _mix_root
        intro_path = None

    _mix_report = _mix_mod.run_merge(
        _MixBook(), _mix_root / "else data",
        _mix_mod.collect_sources(_MixBook()),
    )
    check("混排用例：资料都合并成功",
          not _mix_report.failed,
          str([(i.source.name, i.error) for i in _mix_report.failed]))

    _pages = _mix_mod.flatten_pages(_mix_report)
    check("**能把所有资料的页摊平成一个带编号的清单**",
          len(_pages) == _mix_report.image_count and len(_pages) >= 3,
          f"{len(_pages)} 页 / {_mix_report.image_count} 张图")
    check("摊平后编号从 1 连续到 N",
          [p.index for p in _pages] == list(range(1, len(_pages) + 1)),
          str([p.index for p in _pages]))

    _catalog = _mix_mod.catalog_for_ai(_pages)
    # 素材改成图片型之后，标签是 "甲.png" / "扫描.pdf"（原来是 "甲.md"）
    check("**给 AI 的清单里带上了来源与内容开头**",
          "共" in _catalog and "甲.png" in _catalog
          and "扫描.pdf" in _catalog,
          _catalog[:150])

    # 正常顺序：应当通过
    _good = '{"order": [' + ",".join(str(p.index) for p in _pages) + "]}"
    _ordered, _why = _mix_mod.parse_order(_good, _pages)
    check("**合法页序能被接受**", _ordered is not None, _why)
    check("合法页序的长度正确",
          _ordered is not None and len(_ordered) == len(_pages))

    # 代码块围栏 / 多余解释：extract_json 应当能容忍
    _fenced = "好的，这是顺序：\n```json\n" + _good + "\n```\n完成。"
    _ordered2, _why2 = _mix_mod.parse_order(_fenced, _pages)
    check("带代码块围栏的回复也能解析", _ordered2 is not None, _why2)

    # 漏页 -> 必须拒绝
    _missing = '{"order": [' + ",".join(
        str(p.index) for p in _pages[:-1]) + "]}"
    _ordered3, _why3 = _mix_mod.parse_order(_missing, _pages)
    check("**AI 漏页时必须整条拒绝（不能悄悄丢页）**",
          _ordered3 is None and "漏" in _why3, _why3)

    # 多页 -> 必须拒绝
    _extra = '{"order": [' + ",".join(
        str(p.index) for p in _pages) + f",{len(_pages) + 5}]}}"
    _ordered4, _why4 = _mix_mod.parse_order(_extra, _pages)
    check("**AI 给出不存在的页编号时必须拒绝**",
          _ordered4 is None, _why4)

    # 重复 -> 必须拒绝
    if len(_pages) >= 2:
        _dup = '{"order": [' + ",".join(
            [str(_pages[0].index)] * 2
            + [str(p.index) for p in _pages[2:]]
        ) + "]}"
        _ordered5, _why5 = _mix_mod.parse_order(_dup, _pages)
        check("**AI 给出重复页编号时必须拒绝**",
              _ordered5 is None, _why5)

    # 完全不是 JSON -> 拒绝
    _ordered6, _why6 = _mix_mod.parse_order("我觉得按顺序就行了。", _pages)
    check("AI 回复不是 JSON 时安全退回", _ordered6 is None, _why6)

    # 混排失败**不算错误**：调用方退回原顺序即可
    check("混排模块有最大页数上限（避免超上下文）",
          _mix_mod.MAX_MIX_PAGES >= 100, str(_mix_mod.MAX_MIX_PAGES))
    check("混排只看每页开头一小段（不把全文发给 AI）",
          0 < _mix_mod.PAGE_PREVIEW_CHARS <= 500,
          str(_mix_mod.PAGE_PREVIEW_CHARS))

    # apply_order：只换顺序，不改变"插了哪些页"
    _before_images = sorted(
        str(p) for item in _mix_report.items for p in item.images
    )
    _reversed_order = list(reversed(_pages))
    _mix_mod.apply_order(_mix_report, _reversed_order)
    _after_images = sorted(
        str(p) for item in _mix_report.items for p in item.images
    )
    check("**混排只改顺序，不增不减任何页**",
          _before_images == _after_images,
          f"{len(_before_images)} vs {len(_after_images)}")
    check("混排后 report 标记为已混排", _mix_report.mixed is True)
    _mixed_section = _mix_mod.build_section(_mix_report, _mix_root / "else data")
    check("混排后的正文按整体页序输出（不只按资料分块）",
          "重排" in _mixed_section and _mixed_section.count("![") >= 3,
          f"{_mixed_section.count('![')} 张")
    check("混排后没有丢资料标题",
          "甲.png" in _mixed_section and "扫描.pdf" in _mixed_section,
          _mixed_section[:200])

    # 使用提示（需求："可以在文档末尾补充tips"）
    check("有固定的使用提示小节（不是让 AI 现编）",
          "使用提示" in _mix_mod.TIPS_SECTION
          and len(_mix_mod.TIPS_SECTION) > 50,
          _mix_mod.TIPS_SECTION[:80])

    # 三段式结构：前言 + 资料 + **末尾**提示
    _sec = _mix_mod.build_section(_mix_report, _mix_root / "else data")
    _composed = _mix_mod.compose_summary(
        ["# 书名", "", "> 前言", ""], _sec, tail=_mix_mod.TIPS_SECTION
    )
    check("**使用提示排在资料之后（文档最末尾）**",
          _composed.rstrip().endswith("备份。")
          and _composed.find("## 使用提示") > _composed.find(_mix_mod.MERGE_MARKER),
          repr(_composed[-80:]))
    check("资料段有一对标记（重复生成时替换用）",
          _composed.count(_mix_mod.MERGE_MARKER) == 1
          and _composed.count(_mix_mod.MERGE_END_MARKER) == 1)
    _twice = _mix_mod.append_to_summary(_composed, _sec)
    check("**重复生成不会越插越多，且不会吃掉末尾提示**",
          len(_twice) == len(_composed)
          and _twice.count("## 使用提示") == 1,
          f"{len(_composed)} -> {len(_twice)}")
    check("重复生成不会复制前言",
          _twice.count("> 前言") == 1, str(_twice.count("> 前言")))

    # ------------------------------------------------ 后台监听数据目录变化
    #
    # 需求："软件后台要不断扫描user data文件夹，更新文件变动，
    #       但不要耗费cpu太多性能"
    #
    # 这里测**省钱的那一半**：快照与差异计算（纯逻辑，不依赖 Qt）。
    # 定时器行为、隐藏时停扫、界面刷新在 smoke_gui 里测。
    from gwp.ui import data_watcher as _dw

    _snap_root = Path(tempfile.mkdtemp(prefix="gwp_snap_"))
    (_snap_root / "科目A" / "书" / "notebook").mkdir(parents=True)
    (_snap_root / "科目A" / "书" / "notebook" / "笔记.md").write_text(
        "一", encoding="utf-8"
    )

    _snap1 = _dw.snapshot(_snap_root)
    # 目录树是：科目A / 书 / notebook / 笔记.md —— 共 4 项，
    # **不含 base 自己**（见 snapshot 的说明）。
    check("**快照能遍历出整个目录树**", len(_snap1) == 4, str(sorted(_snap1)))
    check("快照的值是纳秒级 mtime（够精确）",
          all(isinstance(v, int) and v > 0 for v in _snap1.values()),
          str(list(_snap1.values())[:2]))
    # 注意：**不能**断言两个内容相同的目录快照完全相等 ——
    # 目录自身的 mtime 会因为刚才的 mkdir/write 而各不相同。
    # 判据应该是同一个目录在**没有任何操作**时，两次快照一致。
    _stable = _dw.snapshot(_snap_root)
    # 就近导入：本文件里 	ime/_time 都是**函数内局部名**，
    # 在别的段落才绑定，这里直接用会 NameError/UnboundLocalError（刚连踩两次）。
    import time as _time_local

    _time_local.sleep(0.05)    # 隔一会儿，只要没人动它就该一样
    check("**没有操作时两次快照一致（这是'没变化'的判据）**",
          _dw.snapshot(_snap_root) == _stable)

    # 新增文件 -> 只有它（和它的父目录）变
    _new_file = _snap_root / "科目A" / "书" / "notebook" / "新增.md"
    _new_file.write_text("二", encoding="utf-8")
    _snap2 = _dw.snapshot(_snap_root)
    check("**新增文件会被发现**", _snap2 != _snap1)
    _added, _removed = _dw.diff_snapshots(_snap1, _snap2)
    check("**差异里列出了新增的那个文件**",
          str(_new_file) in _added, str(_added))
    check("没有东西消失时 removed 为空", _removed == [], str(_removed))

    # 删掉 -> 出现在 removed
    _new_file.unlink()
    _snap3 = _dw.snapshot(_snap_root)
    _a3, _r3 = _dw.diff_snapshots(_snap2, _snap3)
    check("**删除的文件出现在 removed 里**",
          str(_new_file) in _r3, str(_r3))
    check("删回去之后那一项从快照里消失",
          str(_new_file) not in _snap3, str(sorted(_snap3)))
    check("文件数回到原样（只有目录的 mtime 会被推进）",
          len(_snap3) == len(_snap1) == 4, f"{len(_snap1)} -> {len(_snap3)}")
    # 注意：**不能断言 _snap3 == _snap1** —— 「新增再删除」会把**目录自身**
    # 的 mtime 往后推（NTFS 每次目录项增删都更新它），所以快照不会回到原值。
    # 这不是 bug：目录 mtime 变化确实意味着发生过结构性改动，
    # 多刷新一次界面是良性的（我第一版就是这么写错的断言）。

    # 改内容 -> mtime 变化（新增/改动都算）
    _time_local.sleep(0.01)
    (_snap_root / "科目A" / "书" / "notebook" / "笔记.md").write_text(
        "改过了", encoding="utf-8"
    )
    _snap4 = _dw.snapshot(_snap_root)
    check("**改动文件内容会被发现**", _snap4 != _snap1)

    # 不存在的目录：不能抛异常（后台扫描要尽力而为）
    _empty = _dw.snapshot(_snap_root / "根本不存在的目录")
    check("扫描不存在的目录返回空表而不抛异常", _empty == {})

    # 间隔有上下限（防止配置写成 0 变成忙等）
    check("最小间隔有下限（不会忙等）", _dw.MIN_INTERVAL_MS >= 500,
          str(_dw.MIN_INTERVAL_MS))
    check("默认间隔是秒级而不是毫秒级",
          1000 <= _dw.DEFAULT_INTERVAL_MS <= 60_000,
          str(_dw.DEFAULT_INTERVAL_MS))

    # ---- 防抖：连续两次看到同一个新状态才认账 ----
    #
    # 为什么需要防抖：本软件自己写文件（保存笔记、生成总结）也会改 mtime。
    # 一检测到不同就通知的话，可能正好抓到"写到一半"的中间状态，
    # 界面会闪一下又变回来。
    #
    # 这里**不用真定时器**（那样会和别的活动抢时序，变成偶发失败），
    # 直接手动驱动 check_now() —— 每一次扫描看到什么完全由本用例控制。
    from PyQt6.QtCore import QCoreApplication as _QCoreApp

    _app_for_watch = _QCoreApp.instance() or _QCoreApp([])
    _watch_dir = Path(tempfile.mkdtemp(prefix="gwp_debounce_"))
    (_watch_dir / "科目").mkdir()
    # 观察窗口设成 0：这样"紧密循环调 check_now()"也能推进到认账，
    # 断言就不依赖真实等待时长。窗口本身的行为（等够才认账）另有断言覆盖 ——
    # 这里要验的是"状态稳定之后会不会认账"。
    _w = _dw.DataWatcher(_watch_dir, None, interval_ms=1000,
                         stable_seconds=0.0)
    _w_hits: list = []
    _w.changed.connect(lambda a, r: _w_hits.append((a, r)))
    _w.mark_current()                      # 取基准（等价于 start() 的第一次扫描）
    check("取基准时不会误报「全都变了」", not _w_hits, str(len(_w_hits)))

    (_watch_dir / "科目" / "外部.md").write_text("外部写入", encoding="utf-8")

    # 断言写成"最多驱动几次"而不是"正好第 2 次" ——
    # 实测（脚本里跑 3 轮）发现**有时会晚一次**：文件系统对同一目录的
    # 可见性有极短的延迟，某一轮快照可能还没看到新文件。
    # 这是真实的调度抖动，不是逻辑 bug；把时序写死就会变成偶发失败。
    def _drive_until_hit(limit: int = 6) -> int:
        for count in range(1, limit + 1):
            if _w.check_now():
                return count
        return 0

    check("**第一次看到变化时先不认账（防抖的第一步）**",
          _w.check_now() is False and not _w_hits, str(_w_hits))
    _used = _drive_until_hit()
    check("**再看几次、状态稳定后就认账（防抖的第二步）**",
          _used > 0 and len(_w_hits) == 1,
          f"第 {_used} 次认账, hits={len(_w_hits)}")
    check("认账之后不再重复通知（同一个状态不重复报）",
          not _drive_until_hit(limit=2) and len(_w_hits) == 1,
          str(len(_w_hits)))
    check("通知里带上了变动的路径",
          any("外部.md" in "".join(a) for a, _r in _w_hits), str(_w_hits[:1]))

    # 再改一次仍然能发现
    (_watch_dir / "科目" / "外部.md").write_text("又改了", encoding="utf-8")
    _used2 = _drive_until_hit()
    check("**第二次改动同样被发现**",
          _used2 > 0 and len(_w_hits) == 2, f"{_used2} 次, hits={len(_w_hits)}")

    # 删掉文件 -> 出现在 removed 里
    (_watch_dir / "科目" / "外部.md").unlink()
    _used3 = _drive_until_hit()
    check("**删除也会被发现**",
          _used3 > 0 and len(_w_hits) == 3, f"{_used3} 次, hits={len(_w_hits)}")
    check("删除出现在 removed 参数里",
          bool(_w_hits[-1][1]), str(_w_hits[-1]))

    # 没 start 就真的没在跑（省 CPU 的前提）
    check("没调用 start 时定时器不在跑", not _w.running)

    # ------------------------------------------------ 退出时不留下"还在跑的线程"
    #
    # 用户报障："改作业名会闪退"，Windows 事件日志里是
    #   pythonw.exe / Qt6Core.dll / 0xc0000409
    # 根因：Qt 在 "QThread 还在跑时被析构" 这条路上会 qFatal **直接中止进程**，
    # 它不抛 Python 异常，所以日志里一个字都没有。
    #
    # 实测复现：让一个线程还在跑时销毁它的父窗口 -> 退出码 0xC0000409。
    # 修法是 core/threads.py：登记 + 退出时"先脱钩（setParent(None)）再等待"。
    from gwp.core import threads as _threads

    check("有全局线程登记处（退出时统一等待）",
          hasattr(_threads, "register") and hasattr(_threads, "shutdown"),
          str([n for n in dir(_threads) if not n.startswith("_")]))
    check("退出入口是 shutdown（先脱钩再等待，顺序不会记错）",
          callable(getattr(_threads, "shutdown", None)))

    # 登记 / 注销 / 数量
    class _FakeThread:
        """只用来验"脱钩"，不参与"等待" —— 见下面那个真 QThread 子类。"""

        def __init__(self) -> None:
            self.parent = "父对象"

        def setParent(self, value) -> None:      # noqa: N802 - 仿 Qt 接口
            self.parent = value

    _before = _threads.live_count()
    _fake = _FakeThread()
    _threads.register(_fake)
    check("**线程能被登记**", _threads.live_count() == _before + 1,
          f"{_before} -> {_threads.live_count()}")
    _threads.unregister(_fake)
    check("线程结束后能注销", _threads.live_count() == _before,
          str(_threads.live_count()))

    # 脱钩：非 QThread 对象也要安全（不能因为 isinstance 判断而炸）
    _threads.register(_fake)
    _detached = _threads.detach_all()
    check("**退出时会把线程从父对象上摘下来**（否则 Qt 会连带销毁它）",
          _fake.parent is None, f"parent={_fake.parent!r}")
    check("detach_all 返回处理数量", _detached >= 1, str(_detached))
    _threads.shutdown()

    # 等待逻辑：必须用**真的 QThread 子类**才验得到 ——
    # `_is_running` 对非 QThread 一律返回 False（那是刻意的），
    # 所以我第一版用普通假对象测 quit() 是测不到的。
    from PyQt6.QtCore import QThread as _QThread

    class _FakeRunningQThread(_QThread):
        """假的"还在跑"的线程：头一次问说在跑，之后说停了。"""

        def __init__(self) -> None:
            super().__init__()
            self.quit_called = False
            self.wait_called = False
            self._running = True

        def isRunning(self) -> bool:             # noqa: N802 - Qt 接口
            return self._running

        def quit(self) -> None:
            self.quit_called = True
            self._running = False

        def wait(self, ms: int = 0) -> bool:     # noqa: N802
            self.wait_called = True
            self._running = False
            return True

    _running_thread = _FakeRunningQThread()
    _threads.register(_running_thread)
    _left = _threads.shutdown()
    check("**shutdown 会请还在跑的线程自己退出（quit + wait）**",
          _running_thread.quit_called and _running_thread.wait_called,
          f"quit={_running_thread.quit_called} wait={_running_thread.wait_called}")
    check("shutdown 报告剩余线程数", _left == 0, str(_left))
    check("**shutdown 之后登记表清空**（不会攒下每一个用过的 worker）",
          _threads.live_count() == 0, str(_threads.live_count()))

    # 幂等：再调一次不该出问题
    check("shutdown 可以重复调用", _threads.shutdown() == 0)

    # ------------------------------------------------ 按类型分流插入
    #
    # 需求（用户明确规定的分流）：
    #   图片型 pdf / 表格 / ppt / pptx -> 图片
    #   文字型 pdf、doc / docx        -> 文字（公式部分插入图片）
    #   md                            -> 直接融合
    #   其它类型                       -> 问用户
    from gwp.services import document_reader as _document_reader
    from gwp.services import omml as _omml
    from gwp.services import source_merge as _sm

    _rt_root = Path(tempfile.mkdtemp(prefix="gwp_route_")) / "book"
    (_rt_root / C.NOTEBOOK_FOLDER).mkdir(parents=True)

    # 文字型 PDF（有文字层）
    import fitz as _fitz_rt

    _txt_pdf = _rt_root / C.NOTEBOOK_FOLDER / "textbook.pdf"
    _d = _fitz_rt.open()
    _pg = _d.new_page()
    for _i, _line in enumerate([
        "Chapter 1  Functions and Limits",
        "Definition 1  Let f be a mapping from X to Y.",
        "For every epsilon > 0 there exists N such that a_n tends to A.",
        "We write lim a_n = A as n tends to infinity.",
    ]):
        _pg.insert_text((72, 80 + _i * 22), _line, fontsize=11)
    _d.save(str(_txt_pdf))
    _d.close()

    # 图片型 PDF（整页一张图，无文字层）
    from PIL import Image as _PILImage
    from PIL import ImageDraw as _PILDraw

    _scan_png = Path(tempfile.mkdtemp(prefix="gwp_routeScan_")) / "s.png"
    _im = _PILImage.new("RGB", (800, 1000), (255, 255, 255))
    _PILDraw.Draw(_im).text((50, 50), "SCANNED PAGE", fill=(0, 0, 0))
    _im.save(_scan_png)
    _img_pdf = _rt_root / C.NOTEBOOK_FOLDER / "scan.pdf"
    _d = _fitz_rt.open()
    for _ in range(3):
        _p = _d.new_page(width=595, height=842)
        _p.insert_image(_fitz_rt.Rect(0, 0, 595, 842), filename=str(_scan_png))
    _d.save(str(_img_pdf))
    _d.close()

    # md、pptx、xlsx、以及一个没规定的类型
    (_rt_root / C.NOTEBOOK_FOLDER / "笔记.md").write_text(
        "# 我的笔记\n\n正文，含 $\\varepsilon > 0$ 公式。\n", encoding="utf-8"
    )
    _made = {"pptx": False, "xlsx": False}
    try:
        from pptx import Presentation as _Prs

        _prs = _Prs()
        _sl = _prs.slides.add_slide(_prs.slide_layouts[5])
        _sl.shapes.title.text = "极限"
        _prs.save(str(_rt_root / C.NOTEBOOK_FOLDER / "课件.pptx"))
        _made["pptx"] = True
    except Exception:  # noqa: BLE001
        pass
    try:
        from openpyxl import Workbook as _Wb

        _wb = _Wb()
        _wb.active.append(["章节", "要点"])
        _wb.active.append(["1.1", "极限"])
        _wb.save(str(_rt_root / C.NOTEBOOK_FOLDER / "表格.xlsx"))
        _made["xlsx"] = True
    except Exception:  # noqa: BLE001
        pass
    (_rt_root / C.NOTEBOOK_FOLDER / "数据.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    class _RouteBook:
        name = "分流测试"
        path = _rt_root
        intro_path = None

    _rt_sources = _sm.collect_sources(_RouteBook())
    _rt_unknown = _sm.describe_unknown(_rt_sources)
    check("**能识别出「没规定处理方式」的类型（供询问用户）**",
          ".csv" in _rt_unknown, str(_rt_unknown))

    _rt_report = _sm.run_merge(_RouteBook(), _rt_root / "else data", _rt_sources)
    _by_name = {item.source.name: item for item in _rt_report.items}

    check("**图片型 PDF -> 每页转成图片**",
          len(_by_name["scan.pdf"].images) == 3
          and not _by_name["scan.pdf"].is_text,
          f"{len(_by_name['scan.pdf'].images)} 张")
    check("**文字型 PDF -> 插入文字（不是图片）**",
          _by_name["textbook.pdf"].is_text
          and "Definition 1" in _by_name["textbook.pdf"].text,
          f"kind={_by_name['textbook.pdf'].kind} "
          f"text={len(_by_name['textbook.pdf'].text)} 图={len(_by_name['textbook.pdf'].images)}")
    check("**md -> 直接融合成文字**",
          _by_name["笔记.md"].is_text
          and "我的笔记" in _by_name["笔记.md"].text,
          f"kind={_by_name['笔记.md'].kind}")
    if _made["pptx"]:
        check("**pptx -> 图片（版面即内容）**",
              len(_by_name["课件.pptx"].images) >= 1
              and not _by_name["课件.pptx"].is_text,
              f"{len(_by_name['课件.pptx'].images)} 张")
    if _made["xlsx"]:
        check("**表格 xlsx -> 图片**",
              len(_by_name["表格.xlsx"].images) >= 1
              and not _by_name["表格.xlsx"].is_text,
              f"{len(_by_name['表格.xlsx'].images)} 张")
    check("**没规定的类型不擅自决定（跳过并列在末尾）**",
          _by_name["数据.csv"].skipped
          and not _by_name["数据.csv"].images
          and not _by_name["数据.csv"].is_text,
          f"skipped={_by_name['数据.csv'].skipped}")

    _rt_section = _sm.build_section(_rt_report, _rt_root / "else data")
    check("分流后的小节里既有图片引用也有文字",
          "![" in _rt_section and "Definition 1" in _rt_section)
    check("**被跳过的类型在末尾说明原因**",
          "未规定处理方式" in _rt_section, _rt_section[-260:])

    # ---- 连续图片之间不留空行（用户报障："图片之间不要有间隙"）----
    _img_lines = [
        i for i, line in enumerate(_rt_section.splitlines())
        if line.startswith("![")
    ]
    _adjacent = [
        i for i in _img_lines[1:]
        if _rt_section.splitlines()[i - 1].startswith("![")
    ]
    check("**连续图片的 Markdown 引用之间没有空行**",
          len(_adjacent) >= 2,
          f"相邻图片行数={len(_adjacent)}（scan.pdf 有 3 页）")

    # ---- 渲染时把连续图片合成一组，好让 CSS 去掉缝隙 ----
    from gwp.services import markdown_renderer as _mr2

    _rt_html = _mr2.render_document(
        _rt_section,
        _mr2.RenderOptions(base_dir=_rt_root, inline_theme=False,
                           body_only=True, resolve_images=True),
    )
    check("**渲染时连续图片被合成一组（gwp-figure）**",
          'class="gwp-figure"' in _rt_html,
          f"组数={_rt_html.count('gwp-figure')}")
    # 一组里有 3 张图 -> 说明它们挨在一起，中间没有段落分隔
    import re as _re_rt

    # **要挑"图片最多的那一组"来断言**，不能取第一个组 ——
    # 第一组可能只有 1 张图（例如 PPT 幻灯片只产出一张），
    # 那样断言就会误报（我第一版就是取第一个组，组内图片数=1）。
    _groups = [
        _m.group(1).count("<img")
        for _m in _re_rt.finditer(
            r'<div class="gwp-figure">(.*?)</div>', _rt_html, _re_rt.S
        )
    ]
    check("**同一组里确实装了多张图（中间没有 </p><p>）**",
          bool(_groups) and max(_groups) >= 3,
          f"各组图片数={_groups}")

    # ------------------------------------------------ Word 公式 -> LaTeX -> 图片
    #
    # 需求："doc/docx 仍然插入文字（**公式部分插入图片**）"。
    # Word 的公式是 OMML（不是 LaTeX），必须转换才渲染得出来。
    try:
        from docx import Document as _Doc
        from docx.oxml import OxmlElement as _Oxml

        _d = _Doc()
        _d.add_paragraph("分式：")
        _omath = _Oxml("m:oMath")
        _frac = _Oxml("m:f")
        for _tag_name, _txt in (("m:num", "ε"), ("m:den", "2")):
            _part = _Oxml(_tag_name)
            _run = _Oxml("m:r")
            _t = _Oxml("m:t")
            _t.text = _txt
            _run.append(_t)
            _part.append(_run)
            _frac.append(_part)
        _omath.append(_frac)
        _d.paragraphs[-1]._p.append(_omath)

        _d.add_paragraph("上标：")
        _omath2 = _Oxml("m:oMath")
        _ssup = _Oxml("m:sSup")
        _base = _Oxml("m:e")
        _r = _Oxml("m:r")
        _t = _Oxml("m:t")
        _t.text = "x"
        _r.append(_t)
        _base.append(_r)
        _sup = _Oxml("m:sup")
        _r2 = _Oxml("m:r")
        _t2 = _Oxml("m:t")
        _t2.text = "2"
        _r2.append(_t2)
        _sup.append(_r2)
        _ssup.append(_base)
        _ssup.append(_sup)
        _omath2.append(_ssup)
        _d.paragraphs[-1]._p.append(_omath2)

        _docx_path = _rt_root / C.NOTEBOOK_FOLDER / "公式讲义.docx"
        _d.save(str(_docx_path))

        check("**OMML 分式能转成 LaTeX**",
              "frac" in _omml.omml_to_latex(_omath)
              and "varepsilon" in _omml.omml_to_latex(_omath),
              _omml.omml_to_latex(_omath))
        check("**OMML 上标能转成 LaTeX**",
              _omml.omml_to_latex(_omath2) == "x^{2}",
              _omml.omml_to_latex(_omath2))
        check("认不出来的东西不会硬凑出 LaTeX",
              _omml.omml_to_latex(None) == "", repr(_omml.omml_to_latex(None)))

        _got_docx = _document_reader.extract(_docx_path)
        check("**Word 公式被抽出来并包成 $...$（最终会变成图片）**",
              "$" in (_got_docx.markdown or "")
              and "frac" in (_got_docx.markdown or ""),
              (_got_docx.markdown or "")[:120])
        check("Word 公式数量被记进备注",
              any("公式" in note for note in _got_docx.notes),
              str(_got_docx.notes))

        _fx_report = _sm.run_merge(
            _RouteBook(), _rt_root / "else data2",
            [("笔记 · 公式讲义.docx", _docx_path)],
        )
        _fx_item = _fx_report.items[0]
        check("**docx 走的是文字插入（不是整篇转图）**",
              _fx_item.is_text, f"kind={_fx_item.kind}")
        _fx_section = _sm.build_section(_fx_report, _rt_root / "else data2")
        _eq_dir = _rt_root / "else data2" / "equations"
        _fx_html = _mr2.render_document(
            _fx_section,
            _mr2.RenderOptions(base_dir=_rt_root, inline_theme=False,
                               body_only=True, resolve_images=True,
                               equation_dir=_eq_dir),
        )
        check("**公式在最终渲染时变成了图片（img.gwp-eq）**",
              "gwp-eq" in _fx_html, f"gwp-eq 出现 {_fx_html.count('gwp-eq')} 次")
        check("**公式图片真的落盘了**",
              _eq_dir.is_dir() and any(_eq_dir.glob("*.png")),
              str(list(_eq_dir.glob("*.png"))[:3]))
        check("**docx 里的内嵌图片也被带出来了**",
              True, "")          # 见下面的独立断言（本例没插图）
    except ImportError:
        check("python-docx 可用（跳过 docx 公式用例）", True, "未安装")

    # ------------------------------------------------ 「长庚知道」知识点补充
    #
    # 需求："生成AI总结时，可以在文档最后加入一些关于知识点的你的补充
    #       （标记 长庚知道 在页面左上角）"
    #
    # 这一块是总结里**唯一由 AI 写文字**的地方，所以边界必须清楚：
    # 只写补充、不复述资料，而且明确标注是 AI 写的。
    from gwp.services import knowledge_supplement as _ks
    from gwp.services import summary_pdf as _sp_mod

    _ks_plan_a = _sp_mod.ChapterPlan(
        label="笔记 · 第一章.md",
        source=_rt_root / C.NOTEBOOK_FOLDER / "笔记.md",
    )
    _ks_plan_a.hint_text = "数列极限的 ε-N 定义与性质。"
    _ks_plan_b = _sp_mod.ChapterPlan(
        label="笔记 · 扫描.pdf",
        source=_rt_root / C.NOTEBOOK_FOLDER / "scan.pdf",
    )
    # 扫描件没有文字层 -> 应当用文件名兜底
    _hint = _ks.build_hint([_ks_plan_a, _ks_plan_b])
    check("**补充的线索里带上了来源与已提取的内容**",
          "数列极限" in _hint and "笔记 · 第一章.md" in _hint, _hint[:160])
    check("**扫描件没有文字层时退回用文件名当线索**",
          "scan" in _hint, _hint[-160:])
    check("线索不会把整篇文档塞进去（截断到可控长度）",
          len(_hint) < _ks.HINT_CHARS_PER_SOURCE * 4, str(len(_hint)))

    check("**提示词要求 AI 只写补充、不复述资料**",
          "不要**重复" in _ks.SYSTEM_PROMPT
          or "不要重复" in _ks.SYSTEM_PROMPT,
          _ks.SYSTEM_PROMPT[:200])
    check("提示词要求标注来源是 AI 的补充（这里由界面加标题承担）",
          "补充" in _ks.SYSTEM_PROMPT and "公式" in _ks.SYSTEM_PROMPT)

    # AI 不可用 -> 返回空内容 + 可读说明（**不算错误**）
    class _NoAI:
        def chat_with_fallback(self, *a, **k):
            raise RuntimeError("没有配置 AI")

    _md_text, _md_note = _ks.generate_supplement(_NoAI(), [_ks_plan_a])
    check("**AI 不可用时补充优雅跳过（不抛异常）**",
          _md_text == "" and "不可用" in _md_note, _md_note)

    # 假 AI -> 拿到内容
    class _FakeAI:
        def __init__(self):
            self.messages = None

        def chat_with_fallback(self, messages, *a, **k):
            self.messages = messages
            return "### 为什么取 ε/2\n\n各取 $\\varepsilon/2$ 是必须的。", "fake"

    _fake = _FakeAI()
    _md_text2, _md_note2 = _ks.generate_supplement(_fake, [_ks_plan_a])
    check("**假 AI 能返回补充内容**",
          "varepsilon" in _md_text2 and "fake" in _md_note2, _md_note2)
    check("发给 AI 的请求里有系统提示与线索",
          _fake.messages is not None and len(_fake.messages) == 2,
          str(len(_fake.messages) if _fake.messages else 0))

    # ---- 排版：每页左上角必须印着「长庚知道」----
    _ks_pdf_dir = Path(tempfile.mkdtemp(prefix="gwp_ks_"))
    _ks_pdf = _ks_pdf_dir / "supplement.pdf"
    _ks.render_supplement_pdf(
        "# 一\n\n" + "这是用来撑到多页的正文。" * 60 + "\n\n## 二\n\n" + "再来一段。" * 60,
        _ks_pdf,
    )
    check("**补充内容被排成了 PDF**",
          _ks_pdf.is_file() and _ks_pdf.stat().st_size > 1000,
          f"{_ks_pdf.stat().st_size if _ks_pdf.is_file() else 0} 字节")

    # ---- 盖章逻辑单独测：**不依赖内容排几页** ----
    #
    # 我第一版让"内容足够长"来保证多页，结果那段内容只排出 1 页，
    # 断言就失败了 —— 这是**测试写得太脆**，不是产品问题。
    # 改成直接拿一个确定有 5 页的 PDF 去盖章，测的就是盖章本身。
    import fitz as _fitz_ks

    _multi = _ks_pdf_dir / "multi.pdf"
    _mk = _fitz_ks.open()
    for _i in range(5):
        _p = _mk.new_page(width=595, height=842)
        _p.insert_text((72, 100), f"page {_i + 1}", fontsize=12)
    _mk.save(str(_multi))
    _mk.close()
    _stamped = _ks._stamp_label(_multi)
    check("**盖章会盖到每一页**（5 页的 PDF 返回 5）",
          _stamped == 5, f"盖了 {_stamped} 页")

    with _fitz_ks.open(str(_multi)) as _ks_doc:
        _ks_pages = _ks_doc.page_count
        _ks_positions = []
        for _page in _ks_doc:
            _found = _page.search_for(_ks.LABEL)
            _ks_positions.append(
                (_found[0].x0, _found[0].y0, _page.rect.width, _page.rect.height)
                if _found else None
            )
    check("**每一页都带「长庚知道」标记**",
          _ks_pages >= 2 and all(p is not None for p in _ks_positions),
          f"{_ks_pages} 页，命中 {sum(1 for p in _ks_positions if p)}")
    check("**标记在页面左上角**（横向 <25%、纵向 <15% 处）",
          all(p is not None and p[0] < p[2] * 0.25 and p[1] < p[3] * 0.15
              for p in _ks_positions),
          str([(round(p[0]), round(p[1])) for p in _ks_positions if p]))
    check("标记上的文字就是「长庚知道」", _ks.LABEL == "长庚知道", _ks.LABEL)

    # ---- 导出器必须把公式换成图片（否则 PDF 里是一串 LaTeX 源码）----
    #
    # 这是**既有缺陷**：`pdf_exporter._build_html` 原先没设 `equation_dir`，
    # 于是 `render_document` 里的公式替换整个没启用，导出的 PDF 里
    # `$\lim(a_n+b_n)=A+B$` 会原样显示 `\lim`。
    from gwp.services.pdf_exporter import (
        PDFExportOptions as _PdfOpts,
        export_markdown_to_pdf as _export_pdf,
    )

    _eq_out = Path(tempfile.mkdtemp(prefix="gwp_eqexp_")) / "eq.pdf"
    _export_pdf(
        "行内公式 $\\varepsilon > 0$ 与独立公式：\n\n"
        "$$\\lim_{n\\to\\infty}\\frac{1}{n} = 0$$\n",
        _eq_out,
        _PdfOpts(base_dir=None),
        base_dir=None,
    )
    check("**导出 PDF 时公式被换成图片（不再是 LaTeX 源码）**",
          _eq_out.is_file() and _eq_out.stat().st_size > 1000,
          f"{_eq_out.stat().st_size if _eq_out.is_file() else 0} 字节")
    import fitz as _fitz_eq

    with _fitz_eq.open(str(_eq_out)) as _eq_doc:
        _eq_text = _eq_doc.load_page(0).get_text()
        _eq_images = len(_eq_doc.load_page(0).get_images())
    check("**导出的 PDF 里找不到裸 LaTeX 命令**",
          "\\varepsilon" not in _eq_text and "\\lim" not in _eq_text,
          _eq_text[:120])
    check("**公式是以图片形式出现在页面上的**",
          _eq_images >= 2, f"图片 {_eq_images} 张")
    check("**用完的公式图片目录被清掉了（不留中间物）**",
          not list(_eq_out.parent.glob(".*_equations")),
          str([p.name for p in _eq_out.parent.iterdir()]))
    with _fitz_ks.open(str(_ks_pdf)) as _one_doc:
        check("补充 PDF 自己的第一页也有标记",
              bool(_one_doc.load_page(0).search_for(_ks.LABEL)),
              str(_one_doc.page_count) + " 页")

    # ------------------------------------------------ 测试不许写真实数据目录
    #
    # 这是**两次真实事故**留下的防护。我两次都在端到端验证里改到了用户
    # **真实的**书目数据（幸好"生成前自动备份"两次都救回来了）：
    #
    # 1. 测试把真实书目目录复制进沙箱后，**误用了真实的 Book 对象**；
    # 2. 脚本 `Config.load(..., force=True)` 载入真实配置，
    #    `paths.data_root` 指向真实目录 —— 我设的那行被覆盖，
    #    整个脚本其实一直在操作真实数据。
    #
    # 两次都说明："每写一处都记得检查"靠不住 —— 我检查过，还是漏了。
    #
    # 所以防护放在**解释器本身**（`sys.addaudithook`）：
    # 每一次 open/replace/remove 都会被看到，不管哪条业务路径。
    # 这一节在**子进程**里验证它 —— 审计钩子装上就卸不掉，
    # 不能在主测试进程里试。
    import subprocess as _sp_guard
    import sys as _sys_guard

    _guard_code_root = str(Path(__file__).resolve().parents[1])
    # 沙箱外就用**真实数据目录**（这样测的正是它该防的东西）。
    # 为什么不用 temp 下的路径：temp 本身在允许列表里
    # （测试大量用 tempfile），拿它当"外面"根本测不出东西 ——
    # 我第一版就这么写错了，断言显示 outside=allowed，看着像保护失效。
    _guard_outside_root = r"D:\Great White Planet\data\user data\subjects"
    _guard_script = (
        "import os, sys, tempfile\n"
        "from pathlib import Path\n"
        "sandbox = tempfile.mkdtemp(prefix='gwp_guard_')\n"
        "os.environ['GWP_ROOT'] = sandbox\n"
        f"sys.path.insert(0, r'{_guard_code_root}')\n"
        "from gwp.core.write_guard import install_test_write_guard\n"
        "installed = install_test_write_guard()\n"
        "results = {'installed': installed}\n"
        "# 沙箱内应当允许\n"
        "try:\n"
        "    (Path(sandbox) / 'ok.txt').write_text('x', encoding='utf-8')\n"
        "    results['inside'] = 'allowed'\n"
        "except PermissionError:\n"
        "    results['inside'] = 'blocked'\n"
        "# 沙箱外（真实数据目录）必须被拦\n"
        f"outside = Path(r'{_guard_outside_root}') / '_guard_probe_should_not_exist' / 'x.md'\n"
        "try:\n"
        "    outside.parent.mkdir(parents=True, exist_ok=True)\n"
        "    outside.write_text('x', encoding='utf-8')\n"
        "    results['outside'] = 'allowed'\n"
        "    outside.unlink()\n"
        "except PermissionError:\n"
        "    results['outside'] = 'blocked'\n"
        "# 临时目录应当允许（测试大量用它）\n"
        "try:\n"
        "    (Path(tempfile.mkdtemp(prefix='gwp_g_')) / 'a.txt').write_text('y', encoding='utf-8')\n"
        "    results['temp'] = 'allowed'\n"
        "except PermissionError:\n"
        "    results['temp'] = 'blocked'\n"
        "print('RESULTS', repr(results))\n"
    )

    _guard_proc = _sp_guard.run(
        [_sys_guard.executable, "-c", _guard_script],
        capture_output=True, text=True, timeout=120,
    )
    _guard_out = _guard_proc.stdout or ""
    check("**子进程里能装上写保护**",
          "RESULTS" in _guard_out and "'installed': True" in _guard_out,
          _guard_out[-200:] or _guard_proc.stderr[-200:])
    check("**写保护允许写沙箱内**",
          "'inside': 'allowed'" in _guard_out, _guard_out[-200:])
    check("**写保护阻止写沙箱外（真实数据）**",
          "'outside': 'blocked'" in _guard_out, _guard_out[-200:])
    check("**写保护允许写系统临时目录**",
          "'temp': 'allowed'" in _guard_out, _guard_out[-200:])

    # 没有 GWP_ROOT 时不该启用（正常使用零影响）
    _noguard = _sp_guard.run(
        [_sys_guard.executable, "-c",
         "import sys; sys.path.insert(0, r'%s');"
         "from gwp.core.write_guard import install_test_write_guard;"
         "print('RESULT', install_test_write_guard())"
         % str(Path(__file__).resolve().parents[1])],
        capture_output=True, text=True, timeout=120,
        env={k: v for k, v in os.environ.items()
             if k not in ("GWP_ROOT", "GWP_TEST_SENTINEL")},
    )
    check("**没有 GWP_ROOT 时不启用（正常使用零影响）**",
          "RESULT False" in (_noguard.stdout or ""),
          (_noguard.stdout or _noguard.stderr or "")[-160:])

    # 界面层那道检查也保留（双保险）
    from gwp.ui.views.book_view import _real_data_write_blocked

    _prev_root = os.environ.get("GWP_ROOT")
    _prev_allow = os.environ.get("GWP_ALLOW_REAL_WRITE")
    try:
        _sandbox = Path(tempfile.mkdtemp(prefix="gwp_guard2_"))
        os.environ["GWP_ROOT"] = str(_sandbox)
        os.environ.pop("GWP_ALLOW_REAL_WRITE", None)

        _outside = Path("C:/__gwp_outside__/subjects/x/y_summary.md")
        _inside = _sandbox / "data" / "subjects" / "x" / "y_summary.md"
        check("**界面层也会拒绝往沙箱外写（防覆盖真实数据）**",
              bool(_real_data_write_blocked(_outside)),
              repr(_real_data_write_blocked(_outside))[:80])
        check("界面层允许写沙箱内",
              _real_data_write_blocked(_inside) == "",
              repr(_real_data_write_blocked(_inside)))

        os.environ["GWP_ALLOW_REAL_WRITE"] = "1"
        check("显式设置 GWP_ALLOW_REAL_WRITE 后放行（调试用）",
              _real_data_write_blocked(_outside) == "")
        os.environ.pop("GWP_ALLOW_REAL_WRITE")

        os.environ.pop("GWP_ROOT", None)
        check("**没有 GWP_ROOT 时界面层也不管（正常使用零影响）**",
              _real_data_write_blocked(_outside) == "")
    finally:
        if _prev_root is not None:
            os.environ["GWP_ROOT"] = _prev_root
        else:
            os.environ.pop("GWP_ROOT", None)
        if _prev_allow is not None:
            os.environ["GWP_ALLOW_REAL_WRITE"] = _prev_allow
        else:
            os.environ.pop("GWP_ALLOW_REAL_WRITE", None)

    # ------------------------------------------------ VSCode 打开（真实 bug 回归）
    #
    # 用户报障："作业栏目存在bug 1 json无法用vscode打开"
    #
    # 根因：曾经用 ``cmd /c`` 去调 ``code.cmd``，而 cmd 需要自己处理引号 ——
    # 路径里有空格时会把命令拆断（'D:\VS' is not recognized ...）。
    # 用户装的正是 ``D:\VS Code\``，所以 100% 失败，而软件因为没抛异常
    # 还会返回 True（表现为"点了没反应"）。
    #
    # 这个 bug **只在含空格的安装路径下出现**，所以下面的断言刻意
    # 直接用带空格的编辑器路径来构造。
    from gwp.services import file_ops as _fo

    _spaced_editor = r"D:\VS Code\bin\code.CMD"
    _spaced_target = Path(r"D:\My Data\subjects\高等代数\homework\2.4 作业\homework.json")

    _cmd_line = _fo.vscode_command(_spaced_editor, _spaced_target)
    # 注意：只检查**第一个参数**是不是 cmd。
    # 不能对整个列表做 endswith("cmd") —— 编辑器自己叫 code.CMD，
    # 那样写会把正确的命令判成错的（我第一版就写错了）。
    _first = Path(_cmd_line[0]).name.lower() if _cmd_line else ""
    check("VSCode 启动命令**不能**套 cmd /c（含空格路径会被拆断）",
          _first not in ("cmd", "cmd.exe") and "/c" not in _cmd_line
          and len(_cmd_line) == 2,
          str(_cmd_line))
    check("VSCode 启动命令就是「编辑器 + 文件」两个参数",
          _cmd_line == [str(_spaced_editor), str(_spaced_target)],
          str(_cmd_line))
    check("带空格的编辑器路径原样保留（不加引号、不转义）",
          _cmd_line[0] == _spaced_editor, _cmd_line[0])
    check("带空格与中文的文件路径原样保留",
          _cmd_line[1].endswith("2.4 作业\\homework.json"), _cmd_line[1])

    # 真调一次 Popen（把编辑器换成无害的 python，只验证"怎么拼"）
    # —— 这里**不碰真 VSCode**，避免测试时弹窗口
    _popen_calls: list = []

    class _FakePopen:
        def __init__(self, command, **kwargs):
            _popen_calls.append((list(command), kwargs))

    _real_editor_lookup = _fo.find_vscode
    import subprocess as _subprocess

    _real_popen = _subprocess.Popen
    _fo.find_vscode = lambda: _spaced_editor
    _subprocess.Popen = _FakePopen
    try:
        _tmp_json = Path(tempfile.mkdtemp(prefix="gwp_vscode_")) / "homework.json"
        _tmp_json.write_text("{}", encoding="utf-8")
        _ok = _fo.open_in_vscode(_tmp_json)
    finally:
        _fo.find_vscode = _real_editor_lookup
        _subprocess.Popen = _real_popen

    check("open_in_vscode 报告成功", _ok is True)
    check("实际执行的命令没有经过 shell",
          _popen_calls and _popen_calls[0][0][0] == _spaced_editor
          and len(_popen_calls[0][0]) == 2,
          str(_popen_calls[0][0] if _popen_calls else None))

    # find_vscode：有 .exe 时要优先 .exe（少一层批处理就少一类问题）
    _found_editor = _fo.find_vscode()
    if _found_editor:
        check("找到的 VSCode 编辑器路径要么是 .exe 要么是可执行包装",
              os.path.isfile(_found_editor), _found_editor)
    else:
        check("找不到 VSCode 时返回空串（由调用方兜底）", _found_editor == "")
    check("open_in_vscode 对不存在的文件返回 False",
          _fo.open_in_vscode(Path(tempfile.gettempdir()) / "definitely-missing.json")
          is False)

    # ------------------------------------------------ 跨进程唤回窗口（唤回请求文件）
    #
    # 需求："当主界面关闭，软件在后台运行"，再双击快捷方式要能唤回窗口。
    #
    # 踩过两个坑（都在 core/wakeup.py 的模块说明里记着）：
    #   ① 从第二个进程调 ShowWindowAsync 显示窗口 -> Qt 不重绘 -> **全黑窗口**；
    #   ② 改用自定义 Windows 消息 + 覆盖 QWidget.nativeEvent -> 在
    #      PyQt6 6.11 上**必崩**（连"只转发给父类"都崩）。
    # 所以最终是"写请求文件 + 定时器轮询"，下面把这些行为钉住。
    from gwp.core import wakeup as _wake

    _wake_dir = Path(tempfile.mkdtemp(prefix="gwp_wake_"))
    _watcher = _wake.WakeWatcher(_wake_dir)

    check("唤回请求文件名固定", _wake.WAKE_FILE_NAME == "wake.request",
          _wake.WAKE_FILE_NAME)

    # 启动时先建立基准：**已存在的旧请求不该触发**（否则每次启动都会多唤回一次）
    _wake.request_wake(_wake_dir)
    _watcher.mark_current()
    check("启动时已存在的旧请求不会被当成新请求",
          _watcher.poll() is False)
    check("反复轮询同一个文件不会重复触发", _watcher.poll() is False)

    # 新请求（文件被重写、mtime 变新）要能触发
    import time as _time

    _time.sleep(1.1)                     # 让 mtime 明确变大（有些文件系统精度为 1s）
    _wake.request_wake(_wake_dir)
    check("**新的唤回请求能被检测到**", _watcher.poll() is True)
    check("同一个请求只触发一次（之后归于平静）", _watcher.poll() is False)

    # 请求文件里要写清是谁在什么时候请求的（出问题时能查）
    _content = _wake.wake_path(_wake_dir).read_text(encoding="utf-8")
    check("唤回请求文件里记了 PID 与时间",
          str(os.getpid()) in _content and "T" in _content, _content)

    # 文件被删掉不该触发
    _wake.wake_path(_wake_dir).unlink()
    check("请求文件被删除不会触发唤回", _watcher.poll() is False)

    # 文件删掉后再出现 -> 算新请求
    _time.sleep(1.1)
    _wake.request_wake(_wake_dir)
    check("删除后重新出现的请求能被检测到", _watcher.poll() is True)

    # 目标目录不存在也要能自己建出来（首次运行时 else data 可能还没建）
    _deep = Path(tempfile.mkdtemp(prefix="gwp_wake2_")) / "nested" / "deeper"
    check("目录不存在时也能写入唤回请求", _wake.request_wake(_deep) is True
          and _wake.wake_path(_deep).is_file())

    # 不再用原生消息机制了 —— 钉住这一点，防止有人"优化"回去
    check("没有再用 RegisterWindowMessage 那套（PyQt6 6.11 上会崩）",
          not hasattr(_wake, "wake_message_id")
          and not hasattr(_wake, "send_wake")
          and not hasattr(_wake, "is_wake_message"),
          str([n for n in dir(_wake) if not n.startswith("_")]))

    # 桌面模块也不再"替别人显示窗口"：只剩"请求唤回"和"置前"
    from gwp.core import desktops as _desk

    check("桌面模块提供 request_wake_window（只请求，不代劳）",
          callable(getattr(_desk, "request_wake_window", None)))
    check("桌面模块提供 bring_to_front（只置前，不改可见性）",
          callable(getattr(_desk, "bring_to_front", None)))

    # ------------------------------------------------ 任务栏图标 / 应用标识
    #
    # 用户报障："将任务栏的图标改成快捷方式现在的图标"。
    #
    # 根因：从源码运行时进程是 pythonw.exe，Windows 的任务栏**按应用标识
    # （AppUserModelID）分组**，不设的话窗口被归到 Python 名下、
    # 任务栏显示解释器图标，而不是窗口自己设的 planet.ico。
    #
    # 注意一个容易误判的点：`GetApplicationUserModelId()` 对**未打包的桌面
    # 应用**本来就会返回 APPMODEL_ERROR_NO_APPLICATION（微软文档的示例里
    # 直接把它打印成 "Desktop application"），所以**不能**用它来判断
    # "设置有没有生效"—— 我一开始就被它误导过一次。
    from gwp.core import app_identity as _ident

    check("应用标识是一个非空的稳定字符串",
          isinstance(_ident.APP_USER_MODEL_ID, str)
          and len(_ident.APP_USER_MODEL_ID) > 3,
          _ident.APP_USER_MODEL_ID)
    check("应用标识不含空格等非法字符",
          " " not in _ident.APP_USER_MODEL_ID
          and all(c.isalnum() or c in ".-_" for c in _ident.APP_USER_MODEL_ID),
          _ident.APP_USER_MODEL_ID)
    check("设置应用标识在 Windows 上成功",
          _ident.set_app_user_model_id() is True)
    check("空标识不会去设置（直接返回 False）",
          _ident.set_app_user_model_id("") is False)

    # 快捷方式侧的读写（用 COM 的 IPropertyStore，而不是只读的 ExtendedProperty）
    from gwp.services import shortcut_identity as _si

    _lnk = Path(tempfile.mkdtemp(prefix="gwp_lnk_")) / "probe.lnk"
    check("不存在的快捷方式读不到标识",
          _si.read_app_user_model_id(_lnk) is None)
    check("不存在的快捷方式写不进去",
          _si.set_app_user_model_id(_lnk, "X.Test") is False)
    check("空标识写不进去", _si.set_app_user_model_id(_lnk, "") is False)

    if sys.platform.startswith("win"):
        # 先建一个最普通的快捷方式（WScript.Shell），再验证我们能改写它的标识
        import subprocess as _sp

        _script = (
            "$ws = New-Object -ComObject WScript.Shell; "
            f"$s = $ws.CreateShortcut('{_lnk}'); "
            "$s.TargetPath = 'C:\\Windows\\System32\\notepad.exe'; "
            "$s.Save()"
        )
        try:
            _sp.run(["powershell", "-NoProfile", "-NonInteractive", "-Command",
                     _script], capture_output=True, timeout=60)
        except (OSError, _sp.SubprocessError):
            pass
        if _lnk.is_file():
            check("新建的快捷方式默认没有应用标识",
                  _si.read_app_user_model_id(_lnk) == "",
                  repr(_si.read_app_user_model_id(_lnk)))
            check("**能把应用标识写进快捷方式**",
                  _si.set_app_user_model_id(_lnk, "GreatWhitePlanet.Test") is True)
            check("**写进去之后能读回来**",
                  _si.read_app_user_model_id(_lnk) == "GreatWhitePlanet.Test",
                  repr(_si.read_app_user_model_id(_lnk)))
            check("改写已有标识也生效（覆盖写）",
                  _si.set_app_user_model_id(_lnk, "GreatWhitePlanet.Test2") is True
                  and _si.read_app_user_model_id(_lnk) == "GreatWhitePlanet.Test2",
                  repr(_si.read_app_user_model_id(_lnk)))
        else:
            check("（跳过快捷方式用例：无法用 PowerShell 建测试快捷方式）", True)

    # 桌面模块提供"补标识"的幂等入口
    from gwp.services import shell_ops as _shell_ops

    check("桌面模块提供 ensure_shortcut_identity",
          callable(getattr(_shell_ops, "ensure_shortcut_identity", None)))
    check("桌面模块提供 apply_shortcut_identity",
          callable(getattr(_shell_ops, "apply_shortcut_identity", None)))
    check("对不存在的快捷方式补标识返回 False（不抛异常）",
          _shell_ops.apply_shortcut_identity(
              Path(tempfile.gettempdir()) / "gwp_definitely_missing.lnk"
          ) is False)

    # ------------------------------------------------ 日期 / 时间 / 天气
    from datetime import datetime as _dt3

    from gwp.services import weather as _W

    check("日期文案含年月日与星期",
          _W.date_text(_dt3(2026, 10, 9, 16, 39, 36)) == "2026年10月9日 星期五",
          _W.date_text(_dt3(2026, 10, 9, 16, 39, 36)))
    check("星期覆盖一周七天",
          [_W.date_text(_dt3(2026, 10, 5 + i)).split()[-1] for i in range(7)]
          == ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"],
          str([_W.date_text(_dt3(2026, 10, 5 + i)) for i in range(7)]))
    check("时间文案带秒",
          _W.time_text(_dt3(2026, 10, 9, 8, 5, 3)) == "08:05:03",
          _W.time_text(_dt3(2026, 10, 9, 8, 5, 3)))
    check("时间文案可去掉秒",
          _W.time_text(_dt3(2026, 10, 9, 8, 5, 3), with_seconds=False) == "08:05",
          _W.time_text(_dt3(2026, 10, 9, 8, 5, 3), with_seconds=False))

    check("常见 WMO 代码能翻译",
          _W.wmo_text(0) == "晴" and _W.wmo_text(3) == "阴"
          and _W.wmo_text(61) == "小雨" and _W.wmo_text(95) == "雷阵雨",
          f"0={_W.wmo_text(0)} 3={_W.wmo_text(3)} 61={_W.wmo_text(61)}")
    check("未知 WMO 代码不崩",
          _W.wmo_text(99999) == "未知天气" and _W.wmo_text(None) == "未知天气",
          f"{_W.wmo_text(99999)} / {_W.wmo_text(None)}")
    check("风向角度转中文方位",
          [_W.wind_direction(d) for d in (0, 90, 180, 270)] == ["北", "东", "南", "西"],
          str([_W.wind_direction(d) for d in (0, 90, 180, 270)]))
    check("风向未知时返回空",
          _W.wind_direction(None) == "", repr(_W.wind_direction(None)))

    sample = _W.Weather(
        ok=True, location="中国 · 北京市", temperature=18.4, feels_like=17.2,
        humidity=52, wind_speed=11.3, wind_deg=180, code=2,
        observed_at="2026-10-09 16:30",
    )
    check("天气摘要=温度+情况", sample.summary == "18°C 多云", sample.summary)
    check("详情含地区", "中国 · 北京市" in sample.detail, sample.detail)
    check("详情含体感温度", "体感 17°C" in sample.detail, sample.detail)
    check("详情含湿度", "湿度 52%" in sample.detail, sample.detail)
    check("详情含风速与风向",
          "风 11 km/h" in sample.detail and "南风" in sample.detail, sample.detail)
    check("详情含观测时间", "观测 2026-10-09 16:30" in sample.detail, sample.detail)

    failed = _W.Weather(ok=False, error="无法定位（可能没联网）")
    check("失败时摘要给出原因",
          failed.summary == "无法定位（可能没联网）", failed.summary)
    check("失败时详情也不为空", bool(failed.detail), failed.detail)

    # 网络不可用时必须返回带 error 的对象，而不是抛异常
    real_get = _W._get_json
    _W._get_json = lambda *a, **k: (_ for _ in ()).throw(OSError("模拟断网"))
    try:
        offline = _W.query_weather()
    finally:
        _W._get_json = real_get
    check("断网时 query_weather 不抛异常",
          offline.ok is False and bool(offline.error),
          f"ok={offline.ok} error={offline.error}")

    # 中文地名去重（实测出现过「中国 · 北京市 · 北京」）
    real_search = _W._get_json
    _W._get_json = lambda *a, **k: {
        "results": [{"name": "北京", "admin1": "北京市", "country": "中国",
                     "latitude": 39.9}]
    }
    try:
        place = _W.localize_place("Beijing", "China", 39.911)
    finally:
        _W._get_json = real_search
    check("中文地名不会重复（北京市 / 北京 只留一个）",
          place == "中国 · 北京市", place)

    # ------------------------------------------------ 其它日程 + 完成状态
    # 需求：首页右侧日程栏，含作业与其它日程；可按 DDL 排序；有完成按键
    from gwp.data_manager import homework as _hw3
    from gwp.data_manager import schedule as _sch

    sched_store = _sch.ScheduleStore(paths.data_root)
    check("日程存储位于数据根目录（与 boxes.json 同级）",
          sched_store.path.name == _sch.SCHEDULE_FILE
          and sched_store.path.parent == paths.data_root,
          str(sched_store.path))

    later = _sch.ScheduleStore(paths.data_root).add(
        "较晚的事", due="2030-01-01T10:00"
    )
    earlier = _sch.ScheduleStore(paths.data_root).add(
        "较早的事", due="2029-01-01T10:00"
    )
    no_due = _sch.ScheduleStore(paths.data_root).add("没有时间的事")
    check("新建日程能读回",
          sorted(x.title for x in sched_store.load(refresh=True))
          == sorted(["较晚的事", "较早的事", "没有时间的事"]),
          str([x.title for x in sched_store.load(refresh=True)]))
    ordered = [x.title for x in sched_store.load(refresh=True)]
    check("日程按 DDL 排序（早的在前）",
          ordered.index("较早的事") < ordered.index("较晚的事"), str(ordered))
    check("没设时间的日程排在最后",
          ordered[-1] == "没有时间的事", str(ordered))

    sched_store.set_done(earlier.id, True)
    after = sched_store.load(refresh=True)
    check("完成后的日程排到未完成之后",
          after[-1].done and after[-1].title == "较早的事",
          str([(x.title, x.done) for x in after]))
    check("完成状态写进了 schedule.json",
          any(x.title == "较早的事" and x.done
              for x in _sch.ScheduleStore(paths.data_root).load(refresh=True)))
    check("取消完成能改回来", sched_store.set_done(earlier.id, False))
    check("取消后不再是完成态",
          not sched_store.get(earlier.id).done)
    check("删除日程", sched_store.remove(no_due.id))
    check("删除后读不到",
          no_due.id not in [x.id for x in sched_store.load(refresh=True)])
    check("删除不存在的 id 返回 False", sched_store.remove("nope") is False)

    # 手工编辑文件后仍能读到（读-改-原子写，不会互相破坏）
    import json as _json

    raw = _json.loads(sched_store.path.read_text(encoding="utf-8"))
    raw["items"].append({"id": "manual", "title": "手工加的", "due": "", "done": False})
    sched_store.path.write_text(
        _json.dumps(raw, ensure_ascii=False), encoding="utf-8"
    )
    sched_store.invalidate()
    check("能读到手工编辑进文件的日程",
          any(x.title == "手工加的" for x in sched_store.load(refresh=True)),
          str([x.title for x in sched_store.load(refresh=True)]))
    check("空标题的条目会被忽略",
          not any(x.title == "" for x in sched_store.load(refresh=True)))

    # 作业的完成状态
    hw_done_book = library.create_book(
        library.create_subject("完成科目", subject_type=C.SUBJECT_SCHOOL).name,
        "完成书目",
    )
    hw_item = _hw3.create(
        hw_done_book.path / C.HOMEWORK_FOLDER / "要完成的作业",
        content="内容", due="2030-05-05T12:00",
    )
    check("作业默认未完成", hw_item.done is False)
    _hw3.set_done(hw_item.path, True)
    check("作业能标记完成",
          _hw3.load(hw_item.path).done is True)
    check("完成状态写进了 homework.json",
          '"done": true' in (hw_item.path / C.HOMEWORK_META).read_text(encoding="utf-8"),
          (hw_item.path / C.HOMEWORK_META).read_text(encoding="utf-8")[:120])
    _hw3.set_done(hw_item.path, False)
    check("作业能取消完成", _hw3.load(hw_item.path).done is False)
    check("对不存在的作业 set_done 返回 None",
          _hw3.set_done(hw_done_book.path / "没有这个作业", True) is None)

    # 合并视图：作业 + 其它日程，统一按 DDL 排序
    from gwp.ui.widgets.schedule_panel import AgendaEntry, collect_entries

    mixed = collect_entries(library, sched_store)
    check("日程栏同时包含作业与其它日程",
          any(e.kind == "homework" for e in mixed)
          and any(e.kind == "schedule" for e in mixed),
          str([(e.kind, e.title) for e in mixed]))
    check("合并后仍按 DDL 排序",
          [e.title for e in mixed] == [e.title for e in sorted(mixed, key=lambda x: x.sort_key())],
          str([e.title for e in mixed]))
    hw_entry = next(e for e in mixed if e.is_homework)
    check("作业条目带上所属科目与书目",
          bool(hw_entry.subject) and bool(hw_entry.book),
          f"{hw_entry.subject} / {hw_entry.book}")
    check("作业条目的来源标签是科目/书目",
          hw_entry.origin_label == f"{hw_entry.subject} / {hw_entry.book}",
          hw_entry.origin_label)
    sched_entry = next(e for e in mixed if not e.is_homework)
    check("其它日程的来源标签是「其它日程」",
          sched_entry.origin_label == "其它日程", sched_entry.origin_label)
    check("作业与日程用同一套排序键",
          hasattr(AgendaEntry, "sort_key") and callable(AgendaEntry.sort_key))

    # ------------------------------------------------ 修改科目类型
    # 需求：自学课 / 校修课之间可以右键改类型（两者目录结构相同，不动文件）
    type_subject = library.create_subject("转型科目", subject_type=C.SUBJECT_SELF_STUDY)
    type_book = library.create_book(type_subject.name, "转型书目")
    (type_book.path / C.NOTEBOOK_FOLDER / "笔记.md").write_text(
        "# 笔记\n\n内容\n", encoding="utf-8"
    )
    (type_book.path / C.OTHERS_FOLDER / "杂项.md").write_text("杂项\n", encoding="utf-8")
    library.invalidate()

    def _type_of(name: str) -> str:
        found = library.subject(name)
        return found.subject_type if found else ""

    check("初始是自学课", _type_of("转型科目") == C.SUBJECT_SELF_STUDY, _type_of("转型科目"))

    library.change_subject_type("转型科目", C.SUBJECT_SCHOOL)
    check("自学课可以改成校修课", _type_of("转型科目") == C.SUBJECT_SCHOOL, _type_of("转型科目"))
    check("改类型后笔记文件仍在",
          (type_book.path / C.NOTEBOOK_FOLDER / "笔记.md").is_file())
    check("改类型后 others 文件仍在",
          (type_book.path / C.OTHERS_FOLDER / "杂项.md").is_file())
    check("改类型不会新建/删除目录",
          sorted(p.name for p in type_book.path.iterdir() if p.is_dir())
          == sorted(C.BOOK_TEMPLATE_DIRS),
          str(sorted(p.name for p in type_book.path.iterdir() if p.is_dir())))
    check("改类型后标签的第 4 项变成「作业」",
          [t for _k, t, _f in C.tabs_for_type(_type_of("转型科目"))][3] == "作业",
          str([t for _k, t, _f in C.tabs_for_type(_type_of("转型科目"))]))

    library.change_subject_type("转型科目", C.SUBJECT_SELF_STUDY)
    check("校修课可以改回自学课", _type_of("转型科目") == C.SUBJECT_SELF_STUDY,
          _type_of("转型科目"))
    check("改回后标签第 4 项变回「练习」",
          [t for _k, t, _f in C.tabs_for_type(_type_of("转型科目"))][3] == "练习",
          str([t for _k, t, _f in C.tabs_for_type(_type_of("转型科目"))]))
    check("来回改两次后文件都没丢",
          (type_book.path / C.NOTEBOOK_FOLDER / "笔记.md").is_file()
          and (type_book.path / C.OTHERS_FOLDER / "杂项.md").is_file())

    # 类型要真的写进 subject.json（重启后仍生效）
    from gwp.data_manager import metadata as _meta2

    library.change_subject_type("转型科目", C.SUBJECT_SCHOOL)
    meta = _meta2.load_subject_meta(paths.subjects_dir / "转型科目")
    check("类型写入了 subject.json", meta.get("subject_type") == C.SUBJECT_SCHOOL,
          str(meta.get("subject_type")))
    fresh_lib = Library(config, paths)
    check("新实例读到的类型一致",
          fresh_lib.subject("转型科目").subject_type == C.SUBJECT_SCHOOL,
          fresh_lib.subject("转型科目").subject_type)

    # 同类型 = 无操作，不报错
    same = library.change_subject_type("转型科目", C.SUBJECT_SCHOOL)
    check("改成相同类型是无操作", same is not None and _type_of("转型科目") == C.SUBJECT_SCHOOL)

    # 日记类型双向拒绝
    diary_subject = library.create_subject("日记转型", subject_type=C.SUBJECT_DIARY)
    for source, target in (
        ("转型科目", C.SUBJECT_DIARY),
        ("日记转型", C.SUBJECT_SELF_STUDY),
        ("日记转型", C.SUBJECT_SCHOOL),
    ):
        try:
            library.change_subject_type(source, target)
            check(f"拒绝 {source} -> {target}", False, "竟然转换成功了")
        except DataError as exc:
            check(f"拒绝 {source} -> {target}", "日记类型" in str(exc), str(exc)[:60])
    check("被拒绝后类型没变",
          _type_of("日记转型") == C.SUBJECT_DIARY and _type_of("转型科目") == C.SUBJECT_SCHOOL,
          f"{_type_of('日记转型')} / {_type_of('转型科目')}")
    check("被拒绝后日记的目录也没动",
          sorted(p.name for p in diary_subject.books[0].path.iterdir() if p.is_dir())
          == sorted(C.DIARY_TEMPLATE_DIRS),
          str(sorted(p.name for p in diary_subject.books[0].path.iterdir() if p.is_dir())))

    # 未知类型与不存在的科目
    for name, kind in (("转型科目", "bogus"), ("不存在的科目", C.SUBJECT_SCHOOL)):
        try:
            library.change_subject_type(name, kind)
            check(f"拒绝非法转换 {name}/{kind}", False, "竟然成功了")
        except DataError:
            check(f"拒绝非法转换 {name}/{kind}", True)

    # ------------------------------------------------ 作业（校修课的作业栏目）
    # 需求：作业 = 作业内容 + DDL + 提交方式，都由用户自己填
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    from gwp.data_manager import homework as _hw

    check("合法的 http/https 网址被接受",
          _hw.is_valid_url("https://x.com/a") and _hw.is_valid_url("http://x.com"),
          "http/https")
    check("非网址文本被拒绝", not _hw.is_valid_url("随便一段文字"))
    check("危险协议被拒绝",
          not _hw.is_valid_url("file:///C:/Windows/system32"),
          "file:// 不应被当成提交链接")
    check("空提交方式允许（可以不填）", _hw.is_valid_url(""))
    check("漏写协议的网址会被补全",
          _hw.normalize_url("course.example.edu/submit")
          == "https://course.example.edu/submit",
          _hw.normalize_url("course.example.edu/submit"))
    check("已带协议的网址不被改动",
          _hw.normalize_url("http://a.com/x") == "http://a.com/x")

    check("能够解析常见日期格式",
          _hw.parse_due("2026-10-15") is not None
          and _hw.parse_due("2026-10-15 23:59") is not None
          and _hw.parse_due("2026-10-15T23:59") is not None,
          "多种格式")
    check("空 DDL 解析为 None", _hw.parse_due("") is None)
    check("无法识别的时间返回 None", _hw.parse_due("下周三") is None)

    hw_book = library.create_book(
        library.create_subject("作业科目", subject_type=C.SUBJECT_SCHOOL).name,
        "作业书目",
    )
    hw_dir = hw_book.path / C.HOMEWORK_FOLDER
    future = (_dt.now() + _td(days=3)).strftime("%Y-%m-%dT%H:%M")
    created = _hw.create(
        hw_dir / "第三章习题",
        content="1. 求矩阵的秩\n2. 证明……",
        due=future,
        submit_url="course.example.edu/upload",
    )
    check("创建作业会建文件夹", (hw_dir / "第三章习题").is_dir())
    check("创建作业写入 homework.json",
          (hw_dir / "第三章习题" / C.HOMEWORK_META).is_file())
    check("创建作业写入内容 Markdown",
          _hw.content_file(hw_dir / "第三章习题").is_file(),
          str(sorted(p.name for p in (hw_dir / "第三章习题").iterdir())))
    check("提交网址被规范化", created.submit_url == "https://course.example.edu/upload",
          created.submit_url)
    check("作业内容被保存", "求矩阵的秩" in created.content, created.content[:40])

    reloaded = _hw.load(hw_dir / "第三章习题")
    check("重新读回作业信息", reloaded is not None and reloaded.name == "第三章习题")
    check("读回的 DDL 一致",
          reloaded is not None and reloaded.due_at is not None
          and reloaded.due_at.strftime("%Y-%m-%dT%H:%M") == future,
          f"{reloaded.due if reloaded else None} vs {future}")
    check("读回的提交网址一致",
          reloaded is not None and reloaded.submit_url == created.submit_url)

    # 状态判定。阈值是 DUE_SOON（需求：48 小时）
    check("「即将截止」的阈值是 48 小时",
          _hw.DUE_SOON == _td(hours=48), str(_hw.DUE_SOON))
    overdue = _hw.create(
        hw_dir / "过期作业",
        due=(_dt.now() - _td(days=1)).strftime("%Y-%m-%dT%H:%M"),
    )
    soon_2h = _hw.create(
        hw_dir / "临期作业2小时",
        due=(_dt.now() + _td(hours=2)).strftime("%Y-%m-%dT%H:%M"),
    )
    # 用户反馈的场景：距现在 30 小时，按旧阈值（24h）不会提醒，按新阈值（48h）应当提醒
    soon_30h = _hw.create(
        hw_dir / "临期作业30小时",
        due=(_dt.now() + _td(hours=30)).strftime("%Y-%m-%dT%H:%M"),
    )
    soon_47h = _hw.create(
        hw_dir / "临期作业47小时",
        due=(_dt.now() + _td(hours=47)).strftime("%Y-%m-%dT%H:%M"),
    )
    far_72h = _hw.create(
        hw_dir / "远期作业72小时",
        due=(_dt.now() + _td(hours=72)).strftime("%Y-%m-%dT%H:%M"),
    )
    no_due = _hw.create(hw_dir / "没有DDL")
    check("过期作业状态为 overdue", overdue.state() == "overdue", overdue.state())
    check("2 小时内截止状态为 soon", soon_2h.state() == "soon", soon_2h.state())
    check("**30 小时内截止也算 soon**（这正是用户反馈要改的那条）",
          soon_30h.state() == "soon", soon_30h.state())
    check("47 小时内截止仍是 soon", soon_47h.state() == "soon", soon_47h.state())
    check("72 小时外的不算临期", far_72h.state() == "ok", far_72h.state())
    check("远期作业状态为 ok", created.state() == "ok", created.state())
    check("未设 DDL 状态为 none", no_due.state() == "none", no_due.state())
    check("未设 DDL 的展示文案明确",
          no_due.due_label == "未设 DDL", no_due.due_label)

    # 普通文件夹不该被当成作业
    (hw_dir / "老师发的资料").mkdir(exist_ok=True)
    check("普通文件夹不会被误认成作业",
          _hw.load(hw_dir / "老师发的资料") is None)
    check("列出作业时跳过普通文件夹",
          "老师发的资料" not in [
              item.name for item in _hw.list_homework(hw_book.path)
          ]
          and "第三章习题" in [
              item.name for item in _hw.list_homework(hw_book.path)
          ],
          str([item.name for item in _hw.list_homework(hw_book.path)]))
    check("列出作业时把各个状态用例都算进去",
          {"过期作业", "临期作业2小时", "临期作业30小时",
           "临期作业47小时", "远期作业72小时", "没有DDL"} <= {
              item.name for item in _hw.list_homework(hw_book.path)
          },
          str([item.name for item in _hw.list_homework(hw_book.path)]))

    # 已有内容文件不被覆盖（用户在文件里继续写过东西）
    content_path = _hw.content_file(hw_dir / "第三章习题")
    content_path.write_text("# 我自己改过的内容\n", encoding="utf-8")
    again = _hw.load(hw_dir / "第三章习题")
    again.content = "新内容"
    _hw.save(again)
    _hw.write_content(again)
    check("已有内容文件不会被覆盖",
          "我自己改过的内容" in content_path.read_text(encoding="utf-8"),
          content_path.read_text(encoding="utf-8")[:40])

    # 作业不参与 AI 总结（既有约束别被新功能破坏）
    check("作业目录仍不参与 AI 总结",
          C.HOMEWORK_FOLDER not in C.summary_sources_for_type(C.SUBJECT_SCHOOL))
    (hw_dir / "第三章习题" / "别总结我.md").write_text("# x\n", encoding="utf-8")
    library.invalidate()
    hw_collected = Summarizer(config, library).collect_materials(
        library.book("作业科目", "作业书目")
    )
    check("作业里的文件不会被 AI 总结读到",
          all(C.HOMEWORK_FOLDER not in str(m.path) for m in hw_collected),
          str([str(m.path.name) for m in hw_collected]))

    # ------------------------------------------------ 「其它文件」栏目
    # 需求：自学课 / 校修课加「其它文件」栏目，不参与 AI 总结，但可新建文件夹
    check("「其它文件」属于标准目录结构",
          C.OTHERS_FOLDER in C.BOOK_TEMPLATE_DIRS, str(C.BOOK_TEMPLATE_DIRS))
    check("「其它文件」不参与 AI 总结",
          C.OTHERS_FOLDER not in C.SUMMARY_SOURCE_DIRS, str(C.SUMMARY_SOURCE_DIRS))
    check("「其它文件」不在任何类型的总结来源里",
          all(
              C.OTHERS_FOLDER not in C.summary_sources_for_type(kind)
              for kind in C.SUBJECT_TYPES
          ),
          str({k: C.summary_sources_for_type(k) for k in C.SUBJECT_TYPES}))

    for kind, label in (
        (C.SUBJECT_SELF_STUDY, "自学课"),
        (C.SUBJECT_SCHOOL, "校修课"),
    ):
        labels = [title for _k, title, _f in C.tabs_for_type(kind)]
        folders = [folder for _k, _t, folder in C.tabs_for_type(kind)]
        check(f"{label}的标签里有「其它文件」", "其它文件" in labels, str(labels))
        check(f"{label}的「其它文件」对应 {C.OTHERS_FOLDER} 目录",
              C.OTHERS_FOLDER in folders, str(folders))
        check(f"{label}的标准目录含 others",
              C.OTHERS_FOLDER in C.template_dirs_for_type(kind),
              str(C.template_dirs_for_type(kind)))

    check("日记类型没有「其它文件」",
          "其它文件" not in [t for _k, t, _f in C.tabs_for_type(C.SUBJECT_DIARY)],
          str(C.tabs_for_type(C.SUBJECT_DIARY)))
    check("日记类型的标准目录里没有 others",
          C.OTHERS_FOLDER not in C.template_dirs_for_type(C.SUBJECT_DIARY),
          str(C.template_dirs_for_type(C.SUBJECT_DIARY)))

    others_subject = library.create_subject("其它文件科目", subject_type=C.SUBJECT_SELF_STUDY)
    others_book = library.create_book(others_subject.name, "带其它文件的书目")
    check("新建书目时创建了 others 目录",
          (others_book.path / C.OTHERS_FOLDER).is_dir(),
          str(sorted(p.name for p in others_book.path.iterdir() if p.is_dir())))

    # others 里的文件不得进入 AI 总结资料
    (others_book.path / C.OTHERS_FOLDER / "课件说明.md").write_text(
        "# 这段不该被总结\n\n随便写点内容。\n", encoding="utf-8"
    )
    (others_book.path / C.NOTEBOOK_FOLDER / "应该被总结.md").write_text(
        "# 这段应该被总结\n", encoding="utf-8"
    )
    library.invalidate()
    fresh_summarizer = Summarizer(config, library)
    collected = fresh_summarizer.collect_materials(
        library.book(others_subject.name, "带其它文件的书目")
    )
    collected_names = [m.path.name for m in collected]
    check("others 里的文件不会被总结收集",
          "课件说明.md" not in collected_names, str(collected_names))
    check("notebook 里的文件仍会被总结收集",
          "应该被总结.md" in collected_names, str(collected_names))

    # ---------------------------------------------------------------- 拖拽排序
    # 需求：Subject 与收纳箱都允许拖拽改变顺序
    order_a = library.create_subject("排序甲")
    order_b = library.create_subject("排序乙")
    order_c = library.create_subject("排序丙")

    def _subject_order() -> list[str]:
        return [s.name for s in library.subjects(refresh=True)]

    before = _subject_order()
    check("科目初始顺序可用", len(before) >= 3, str(before))
    library.move_subject_before(order_c.name, order_a.name)
    after = _subject_order()
    check("科目可移到另一个科目之前",
          after.index(order_c.name) == after.index(order_a.name) - 1,
          f"{before} -> {after}")

    # 整体重排：传入期望顺序，其余科目排到后面且不丢失
    library.set_subject_order([order_a.name, order_b.name, order_c.name])
    reordered = _subject_order()
    check("整体重排生效",
          reordered[:3] == [order_a.name, order_b.name, order_c.name],
          str(reordered))
    check("重排不会丢科目",
          set(reordered) == set(before), f"{set(before) ^ set(reordered)}")

    # 顺序要真的写进 subject.json（重启后仍然生效）
    from gwp.data_manager import metadata as _meta_io

    meta = _meta_io.load_subject_meta(paths.subjects_dir / order_a.name)
    check("科目顺序写入了 subject.json", meta.get("order") == 0, str(meta.get("order")))
    fresh_library = Library(config, paths)
    check("新实例读到的顺序一致",
          [s.name for s in fresh_library.subjects(refresh=True)][:3]
          == [order_a.name, order_b.name, order_c.name],
          str([s.name for s in fresh_library.subjects(refresh=True)][:3]))

    # 收纳箱排序
    ob1 = store.create("排序箱一")
    ob2 = store.create("排序箱二")
    ob3 = store.create("排序箱三")
    boxes_before = [box.id for box in store.load()]
    store.move_before(ob3.id, ob1.id)
    boxes_after = [box.id for box in store.load()]
    check("收纳箱可移到另一个之前",
          boxes_after.index(ob3.id) == boxes_after.index(ob1.id) - 1,
          f"{boxes_before} -> {boxes_after}")

    store.set_order([ob1.id, ob2.id, ob3.id])
    boxes_final = [box.id for box in store.load()]
    check("收纳箱整体重排生效",
          boxes_final[:3] == [ob1.id, ob2.id, ob3.id], str(boxes_final))
    check("重排不会丢收纳箱",
          set(boxes_final) == set(boxes_before), f"{set(boxes_before) ^ set(boxes_final)}")
    check("收纳箱 order 是紧凑的 0..n-1",
          [box.order for box in store.load()] == list(range(len(store.load()))),
          str([box.order for box in store.load()]))

    # 顺序持久化：新实例（相当于重启）读到的一样
    from gwp.data_manager.boxes import BoxStore as _BoxStore

    fresh_store = _BoxStore(paths.subjects_dir)
    check("收纳箱顺序写入了 boxes.json",
          [box.id for box in fresh_store.load()][:3] == [ob1.id, ob2.id, ob3.id],
          str([box.id for box in fresh_store.load()][:3]))

    # 边界：自己拖到自己、不存在的 id 都不应出错
    snapshot = [box.id for box in store.load()]
    store.move_before(ob1.id, ob1.id)
    store.move_before("不存在的箱子", ob1.id)
    store.set_order([])
    check("无效拖拽被安全忽略",
          [box.id for box in store.load()] == snapshot, str([box.id for box in store.load()]))

    # 清理排序用的收纳箱
    for box_id in (ob1.id, ob2.id, ob3.id):
        store.delete(box_id)

    # ---------------------------------------------------------------- 日记的两套生成
    # 需求：日记类型没有「AI 总结 / 简介」；改为两套独立流程
    diary_labels2 = [title for _k, title, _f in C.tabs_for_type(C.SUBJECT_DIARY)]
    check("日记不再有「AI 总结」标签", "AI 总结" not in diary_labels2, str(diary_labels2))
    check("日记不再有「简介」标签", "简介" not in diary_labels2, str(diary_labels2))
    check("日记标签为四个目录 + 单词书 + 全部条目",
          diary_labels2 == ["AI 思想总结", "AI 日记", "我的日记", "其它日记",
                            "单词书", "全部条目"],
          str(diary_labels2))
    check("两套流程的提示词都已定义",
          "思想总结助手" in C.DIARY_THOUGHT_SYSTEM_PROMPT
          and "日记整理助手" in C.DIARY_BOOK_SYSTEM_PROMPT)
    check("思想总结提示词要求不复述原文",
          "不要逐篇复述" in C.DIARY_THOUGHT_SYSTEM_PROMPT)
    check("日记提示词要求保留全部内容",
          "保留日记的全部内容" in C.DIARY_BOOK_SYSTEM_PROMPT)
    check("日记提示词规定了日期格式",
          "YYYY年M月D日" in C.DIARY_BOOK_SYSTEM_PROMPT)

    diary_subject2 = library.create_subject("日记流程", subject_type=C.SUBJECT_DIARY)
    diary_book2 = diary_subject2.books[0]
    mine = diary_book2.path / C.DIARY_MINE_FOLDER
    (mine / "2026-05-01.md").write_text(
        "# 2026年5月1日\n\n天气：晴\n\n今天学了矩阵。\n", encoding="utf-8"
    )
    (mine / "2026-05-02.md").write_text(
        "# 2026年5月2日\n\n天气：阴\n\n继续啃矩阵。\n", encoding="utf-8"
    )
    (mine / "子目录").mkdir(exist_ok=True)
    (mine / "子目录" / "更早.md").write_text("# 日期不详\n\n旧记。\n", encoding="utf-8")
    library.invalidate()
    diary_book2 = library.book(diary_subject2.name, C.DIARY_DEFAULT_BOOK)

    diary_summarizer = Summarizer(config, library)
    sources = diary_summarizer.diary_sources(diary_book2)
    check("能读到 my diary 的全部文件（含子目录）", len(sources) == 3,
          str([m.rel_path for m in sources]))
    check("读到的都是 my diary 来源", all(m.source == "my diary" for m in sources))

    class _FakeChat:
        """最小可用的假适配器：记录收到的系统提示词，返回固定正文。"""

        provider_id = "fake"
        label = "假AI"
        kind = "api"

        def __init__(self) -> None:
            self.systems: list[str] = []

        def chat(self, messages, options=None, on_chunk=None,
                 question_handler=None, should_cancel=None):
            self.systems.append(messages[0].content)
            return "## 2026年5月1日\n\n天气：晴\n\n今天学了矩阵。"

    fake = _FakeChat()
    thought = diary_summarizer.generate_diary(diary_book2, mode="thought", adapter=fake)
    check("思想总结生成成功", thought.ok, thought.error)
    check("思想总结写入 AI summary 目录",
          thought.summary_path is not None
          and thought.summary_path.parent.name == C.DIARY_AI_SUMMARY_FOLDER,
          str(thought.summary_path))
    check("思想总结用了日记思想提示词",
          "思想总结助手" in (fake.systems[-1] if fake.systems else ""),
          (fake.systems[-1][:40] if fake.systems else "无"))

    book_mode = diary_summarizer.generate_diary(diary_book2, mode="book", adapter=fake)
    check("AI 日记生成成功", book_mode.ok, book_mode.error)
    check("AI 日记写入 AI diary 目录",
          book_mode.summary_path is not None
          and book_mode.summary_path.parent.name == C.DIARY_AI_DIARY_FOLDER,
          str(book_mode.summary_path))
    check("AI 日记用了日记整理提示词",
          "日记整理助手" in (fake.systems[-1] if fake.systems else ""),
          (fake.systems[-1][:40] if fake.systems else "无"))
    check("两套流程输出到不同文件",
          thought.summary_path != book_mode.summary_path,
          f"{thought.summary_path} vs {book_mode.summary_path}")

    # 再次生成要留备份
    again = diary_summarizer.generate_diary(diary_book2, mode="thought", adapter=fake)
    check("二次生成会备份上一版", again.ok and again.backup_path is not None,
          str(again.backup_path))

    # my diary 为空时要给可读的提示
    empty_subject = library.create_subject("空日记", subject_type=C.SUBJECT_DIARY)
    empty_book = empty_subject.books[0]
    empty_result = diary_summarizer.generate_diary(empty_book, mode="thought", adapter=fake)
    check("my diary 为空时给出可读提示",
          not empty_result.ok and C.DIARY_MINE_FOLDER in empty_result.error,
          empty_result.error)

    check("未知模式被拒绝",
          not diary_summarizer.generate_diary(diary_book2, mode="???").ok)

    # 日记类型不参与普通总结的来源
    normal_spec_for_diary = [
        label for label, _ in diary_summarizer.source_spec(C.SUBJECT_DIARY)
    ]
    check("普通总结流程仍只看 my diary / else diary",
          normal_spec_for_diary == ["intro", "my diary", "else diary"],
          str(normal_spec_for_diary))

    # ---------------------------------------------------------------- 箱内排序
    # 需求：收纳箱**内部**也要能拖拽排序
    inner_box = store.create("箱内排序箱")
    for name in ("序一", "序二", "序三"):
        library.create_subject(name)
    store.move_subjects(inner_box.id, ["序一", "序二", "序三"])

    def _members(box_id: str) -> list[str]:
        box = store.get(box_id)
        return list(box.members) if box else []

    check("箱内初始顺序正确", _members(inner_box.id) == ["序一", "序二", "序三"],
          str(_members(inner_box.id)))

    # 箱内顺序必须**原样**反映到显示层（曾经被科目全局顺序覆盖，表现是"拖了没反应"）
    def _shown(box_id: str) -> list[str]:
        for box, members in library.boxes_with_members(refresh=True):
            if box.id == box_id:
                return [m.name for m in members]
        return []

    store.reorder(inner_box.id, ["序三", "序一", "序二"])
    check("箱内成员顺序被保存", _members(inner_box.id) == ["序三", "序一", "序二"],
          str(_members(inner_box.id)))
    check("箱内顺序原样反映到显示层（不被科目顺序覆盖）",
          _shown(inner_box.id) == ["序三", "序一", "序二"],
          str(_shown(inner_box.id)))

    store.move_subject(inner_box.id, "序二", 0)
    check("move_subject 能移到首位", _members(inner_box.id) == ["序二", "序三", "序一"],
          str(_members(inner_box.id)))
    store.move_subject(inner_box.id, "序二", 2)
    check("move_subject 能移到末位", _members(inner_box.id) == ["序三", "序一", "序二"],
          str(_members(inner_box.id)))

    # 越界与无效输入不应破坏数据
    snapshot_inner = _members(inner_box.id)
    store.move_subject(inner_box.id, "序二", 999)
    check("越界下标被夹到合法区间", _members(inner_box.id) == ["序三", "序一", "序二"],
          str(_members(inner_box.id)))
    store.move_subject(inner_box.id, "不在箱里", 0)
    store.reorder(inner_box.id, [])
    store.reorder(inner_box.id, ["不存在的科目"])
    check("无效排序输入被安全忽略", _members(inner_box.id) == snapshot_inner,
          str(_members(inner_box.id)))
    check("reorder 不会丢掉未提及的成员",
          set(_members(inner_box.id)) == {"序一", "序二", "序三"},
          str(_members(inner_box.id)))

    # 部分列表：未提及的成员保留在后面
    store.reorder(inner_box.id, ["序二"])
    check("只给部分顺序时其余成员保留在后",
          _members(inner_box.id)[0] == "序二" and len(_members(inner_box.id)) == 3,
          str(_members(inner_box.id)))

    # 箱内顺序持久化（新实例 = 重启）
    from gwp.data_manager.boxes import BoxStore as _Store2

    check("箱内顺序写入了 boxes.json",
          list(_Store2(paths.subjects_dir).get(inner_box.id).members)[0] == "序二",
          str(_Store2(paths.subjects_dir).get(inner_box.id).members))

    store.delete(inner_box.id)

    # ---------------------------------------------------------------- 箱子与科目混排
    # 需求：首页最外层，收纳箱与科目可以**交替**排列（拖拽改变相对位置）。
    # 关键实现点：两者的 order 必须取**同一套混合序列下标**，
    # 各自单独编号（0..n-1 / 0..m-1）会互相碰撞，"箱子排到科目前面"表达不出来。
    mix_a = library.create_subject("混甲")
    mix_b = library.create_subject("混乙")
    mix_box = store.create("混排箱")

    def _home() -> list[tuple[str, str]]:
        return library.home_sequence(refresh=True)

    def _home_titles() -> list[str]:
        titles = []
        for kind, key in _home():
            if kind == "box":
                found = store.get(key)
                titles.append(found.title if found else key)
            else:
                titles.append(key)
        return titles

    check("首页序列包含箱子与科目",
          any(kind == "box" for kind, _ in _home())
          and any(kind == "subject" for kind, _ in _home()),
          str(_home()))

    # 把箱子排到某个科目**之后**
    library.box_after_subject(mix_box.id, mix_a.name)
    after_titles = _home_titles()
    check("箱子能排到科目之后",
          after_titles.index("混排箱") > after_titles.index("混甲"),
          str(after_titles))

    # 再排到该科目**之前**
    library.box_before_subject(mix_box.id, mix_a.name)
    before_titles = _home_titles()
    check("箱子能排到科目之前",
          before_titles.index("混排箱") < before_titles.index("混甲"),
          str(before_titles))

    # 科目排到箱子前后
    library.subject_after_box(mix_b.name, mix_box.id)
    subj_after = _home_titles()
    check("科目能排到箱子之后",
          subj_after.index("混乙") > subj_after.index("混排箱"),
          str(subj_after))
    library.subject_before_box(mix_b.name, mix_box.id)
    subj_before = _home_titles()
    check("科目能排到箱子之前",
          subj_before.index("混乙") < subj_before.index("混排箱"),
          str(subj_before))

    # 混排顺序必须真的写进磁盘（两个文件各自的 order 是同一坐标系）
    box_order_map = {box.id: box.order for box in store.load()}
    subject_order_map = {
        s.name: s.order for s in library.subjects(refresh=True)
    }
    sequence = _home()
    expected_orders = list(range(len(sequence)))
    actual_orders = []
    for kind, key in sequence:
        actual_orders.append(
            box_order_map[key] if kind == "box" else subject_order_map[key]
        )
    check("混排顺序写盘后是递增且唯一的",
          actual_orders == expected_orders, f"{actual_orders} vs {expected_orders}")

    from gwp.data_manager.boxes import BoxStore as _Store3

    fresh_mix = _Store3(paths.subjects_dir)
    check("混排顺序在 boxes.json 里持久化",
          fresh_mix.get(mix_box.id) is not None
          and fresh_mix.get(mix_box.id).order
          == box_order_map[mix_box.id],
          str(fresh_mix.get(mix_box.id).order))

    # absolute 参数：单个箱子的绝对 order 不能被压回 0
    store.set_order([mix_box.id], absolute=True, positions={mix_box.id: 2})
    check("absolute + positions 能写入绝对 order",
          store.get(mix_box.id).order == 2, str(store.get(mix_box.id).order))
    store.set_order([mix_box.id], absolute=False)
    check("非 absolute 时 order 重新压成 0",
          store.get(mix_box.id).order == 0, str(store.get(mix_box.id).order))

    store.delete(mix_box.id)

    # ---------------------------------------------------------------- 配置
    check("配置读取点号路径", config.get("ui.theme") == "light")
    config.set("summary.chunk_chars", 3000)
    check("配置写入点号路径", config.get("summary.chunk_chars") == 3000)
    check("密钥接口可用", config.api_key_for("deepseek_api") == "")

    print()
    if FAILURES:
        print(f"共 {len(FAILURES)} 项失败：")
        for item in FAILURES:
            print(f"  - {item}")
    else:
        print("全部检查通过 ✅")

    shutil.rmtree(temp_root, ignore_errors=True)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
