"""命令行工具：不需要打开界面就能批量生成总结。

用途：
* 定时任务（例如每周日自动更新所有书目的总结）；
* 在没有显示器的环境里验证总结流程；
* 排查"界面里生成失败"的问题（命令行能看到完整错误）。

用法示例::

    cd "D:\\Great White Planet\\code"
    venv\\Scripts\\python.exe -m gwp.cli list
    venv\\Scripts\\python.exe -m gwp.cli materials --subject 高代 --book 数学分析
    venv\\Scripts\\python.exe -m gwp.cli summary --subject 高代 --book 数学分析
    venv\\Scripts\\python.exe -m gwp.cli summary --all --provider deepseek_api
    venv\\Scripts\\python.exe -m gwp.cli providers
    venv\\Scripts\\python.exe -m gwp.cli pdf --file "data/user data/.../x.md" --out D:\\out.pdf

这个工具直接使用与界面相同的核心模块，所以"命令行能成功、界面失败"往往意味着
配置或界面层的问题。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gwp.bootstrap import bootstrap
from gwp.resources import planet_icon


def _print(text: str = "") -> None:
    print(text)


def cmd_list(context, _args) -> int:
    subjects = context.library.subjects(refresh=True)
    if not subjects:
        _print("还没有任何科目。")
        _print(f"数据目录：{context.paths.subjects_dir}")
        return 0
    for subject in subjects:
        _print(f"科目：{subject.title}（{subject.book_count} 本书目）")
        for book in subject.books:
            sources = book.summary_source_count
            status = "已生成" if book.has_summary else "未生成"
            _print(f"    └─ {book.title}  资料 {sources} 份  总结：{status}")
    return 0


def cmd_providers(context, args) -> int:
    _print(f"当前 AI：{context.ai.active_id}")
    for provider_id, label, ok, reason in context.ai.available():
        mark = "可用" if ok else "不可用"
        _print(f"[{mark}] {label}（{provider_id}）" + ("" if ok else f"：{reason}"))
    if getattr(args, "test", False):
        _print()
        _print("正在测试当前 AI ……")
        ok, message = context.ai.refresh()
        _print(("成功：" if ok else "失败：") + message)
        return 0 if ok else 1
    return 0


def _find_book(context, subject_name: str, book_name: str):
    subject = context.library.subject(subject_name)
    if subject is None:
        _print(f"找不到科目：{subject_name}")
        _print("可用科目：" + "、".join(item.name for item in context.library.subjects()))
        return None
    for book in subject.books:
        if book.name == book_name or book.title == book_name:
            return book
    _print(f"科目 {subject_name} 下找不到书目：{book_name}")
    _print("可用书目：" + "、".join(item.name for item in subject.books))
    return None


def cmd_materials(context, args) -> int:
    book = _find_book(context, args.subject, args.book)
    if book is None:
        return 1
    materials, context_text = context.summarizer.preview(book)
    _print(f"书目：{book.title}")
    _print(f"{'参与':<6}{'来源':<10}{'类型':<8}{'字符':>8}  文件")
    for material in materials:
        mark = "是" if material.included and material.text.strip() else "否"
        _print(
            f"{mark:<6}{material.label:<10}{material.kind:<8}{material.char_count:>8}  {material.rel_path}"
        )
        for note in material.notes:
            _print(f"        · {note}")
    _print()
    _print(f"合计将发送给 AI 的内容：{len(context_text)} 字符")
    return 0


def cmd_summary(context, args) -> int:
    targets = []
    if args.all:
        for subject in context.library.subjects(refresh=True):
            targets.extend(subject.books)
    else:
        if not args.subject or not args.book:
            _print("请用 --subject 和 --book 指定书目，或者用 --all 处理全部书目。")
            return 2
        book = _find_book(context, args.subject, args.book)
        if book is None:
            return 1
        targets = [book]

    if not targets:
        _print("没有需要处理的书目。")
        return 0

    if args.provider:
        context.ai.set_active(args.provider, notify=False)
        context.ai.invalidate()
    _print(f"使用 AI：{context.ai.describe_active()}")

    failures = 0
    for book in targets:
        _print()
        _print(f"=== {book.subject_name} / {book.title} ===")
        last_message = ""

        def _progress(event, _book=book) -> None:
            nonlocal last_message
            if event.message != last_message:
                last_message = event.message
                _print(f"  {event.message}" + (f"（{event.percent}%）" if event.percent >= 0 else ""))

        result = context.summarizer.generate(book, on_progress=_progress)
        if result.ok:
            _print(f"  完成：{result.summary_path}")
            _print(
                f"  资料 {result.material_count} 份 / {result.char_count} 字符 · "
                f"分块 {result.chunks} · AI {result.provider} · 耗时 {result.elapsed:.1f}s"
            )
            if result.backup_path:
                _print(f"  上一版备份：{result.backup_path}")
            if result.skipped:
                _print(f"  跳过 {len(result.skipped)} 个空文件")
        else:
            failures += 1
            _print(f"  失败：{result.error}")

    _print()
    _print(f"处理完成：成功 {len(targets) - failures} / 共 {len(targets)}")
    return 1 if failures else 0


def cmd_pdf(context, args) -> int:
    from gwp.services.pdf_exporter import PDFExportOptions, export_markdown_to_pdf

    source = Path(args.file)
    if not source.is_file():
        _print(f"文件不存在：{source}")
        return 1
    target = Path(args.out) if args.out else source.with_suffix(".pdf")
    text = source.read_text(encoding="utf-8", errors="replace")
    options = PDFExportOptions.from_config(context.config)
    if args.page_size:
        options.page_size = args.page_size
    if args.margin is not None:
        options.margin_mm = args.margin
    output = export_markdown_to_pdf(text, target, options, base_dir=source.parent)
    _print(f"已导出：{output}（{output.stat().st_size} 字节）")
    return 0


def cmd_icon(context, args) -> int:
    """生成/更换程序图标（窗口图标，也是桌面快捷方式使用的图标）。"""
    from gwp.resources import app_icon as icon_module
    from gwp.resources import planet_icon

    if args.image:
        source = Path(args.image)
        try:
            ico = icon_module.install_image(source, size=int(args.size))
        except Exception as exc:  # noqa: BLE001
            _print(f"安装图标失败：{exc}")
            return 1
        _print(f"已用「{source.name}」生成图标：{ico}")
    else:
        style = args.style or planet_icon.DEFAULT_STYLE
        try:
            ico = icon_module.ensure_builtin_icon(style=style, force=bool(args.rebuild))
        except Exception as exc:  # noqa: BLE001
            _print(f"生成图标失败：{exc}")
            return 1
        _print(f"图标已就绪：{ico}（风格 {style}）")

    png = icon_module.icon_dir() / icon_module.PNG_NAME
    if png.is_file():
        _print(f"预览图：{png}")

    if args.preview:
        target = Path(args.preview)
        planet_icon.preview_sheet(target=target)
        _print(f"风格对比图：{target}")

    if args.shortcut:
        from PyQt6.QtWidgets import QApplication

        from gwp.services import shell_ops

        if QApplication.instance() is None:
            QApplication([])
        ok, message = shell_ops.create_desktop_shortcut()
        _print(("成功：" if ok else "失败：") + message)
        return 0 if ok else 1
    return 0


def cmd_key(context, args) -> int:
    """设置/查看 API Key 并立即测通。

    安全约定：不把 Key 当作命令行参数（否则会留在 shell 历史里），
    只支持从标准输入读取，或交互式隐藏输入。
    """
    provider_id = args.provider or context.ai.active_id
    adapter = context.ai.get(provider_id, refresh=True)
    if adapter is None:
        _print(f"找不到提供方：{provider_id}")
        return 1

    _print(f"提供方：{adapter.display_label}（{provider_id}）")
    _print(f"接口  ：{getattr(adapter, 'endpoint', '（网页版/本地程序，无接口地址）')}")

    if args.show:
        existing = context.config.api_key_for(provider_id)
        if existing:
            _print(f"当前已保存 Key：长度 {len(existing)}，前缀 {existing[:6]}…，后缀 …{existing[-4:]}")
        else:
            _print("当前未保存 Key。")
        return 0

    env_name = str(context.config.get(f"ai.providers.{provider_id}.api_key_env", "") or "")
    if env_name:
        _print(f"环境变量 {env_name} 优先级最高，若已设置会覆盖下面的值。")

    if args.clear:
        context.config.set_api_key(provider_id, "")
        _print("已清除该提供方的 Key。")
        return 0

    raw = sys.stdin.readline() if not sys.stdin.isatty() else input("请粘贴 API Key（输入不回显）：")
    api_key = (raw or "").strip()
    if not api_key:
        _print("没有读到 Key，已取消。")
        return 1

    context.config.set_api_key(provider_id, api_key)
    _print(f"已保存（长度 {len(api_key)}，前缀 {api_key[:6]}…）-> {context.paths.secrets_file}")

    if args.no_test:
        return 0

    _print("正在测试连接 ……")
    adapter = context.ai.get(provider_id, refresh=True)
    ok, message = adapter.test_connection()
    _print(("成功：" if ok else "失败：") + message)
    return 0 if ok else 1


def cmd_doctor(context, _args) -> int:
    """环境体检：路径、依赖、AI、数据概览。"""
    from gwp.services import dependencies

    _print("== Great White Planet 环境体检 ==")
    _print(f"项目根目录：{context.root}")
    _print(f"数据根目录：{context.paths.data_root}")
    _print(f"用户数据  ：{context.paths.user_data}")
    _print(f"软件数据  ：{context.paths.else_data}")
    _print(f"配置文件  ：{context.paths.config_file}（{'存在' if context.paths.config_file.exists() else '不存在'}）")
    _print(f"密钥文件  ：{context.paths.secrets_file}（{'存在' if context.paths.secrets_file.exists() else '不存在'}）")
    _print()
    _print("== 依赖 ==")
    _print(dependencies.summary())
    if dependencies.missing():
        _print(f"安装命令：{dependencies.install_command()}")
    _print()
    _print("== AI ==")
    for provider_id, label, ok, reason in context.ai.available():
        _print(f"[{'可用' if ok else '不可用'}] {label}（{provider_id}）" + ("" if ok else f"：{reason}"))
    _print()
    _print("== 数据 ==")
    subjects = context.library.subjects(refresh=True)
    _print(f"科目 {len(subjects)} 个，书目 {sum(item.book_count for item in subjects)} 本")
    for subject in subjects:
        _print(f"  · {subject.title}：{subject.book_count} 本 / {subject.file_count} 个文件")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gwp.cli",
        description="Great White Planet 命令行工具（批量生成总结、体检、导出 PDF）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="列出所有科目与书目").set_defaults(func=cmd_list)

    p = sub.add_parser("providers", help="查看 AI 提供方状态")
    p.add_argument("--test", action="store_true", help="顺便测试当前 AI 的连通性")
    p.set_defaults(func=cmd_providers)

    p = sub.add_parser("materials", help="预览某本书将要参与总结的资料")
    p.add_argument("--subject", required=True, help="科目文件夹名")
    p.add_argument("--book", required=True, help="书目文件夹名")
    p.set_defaults(func=cmd_materials)

    p = sub.add_parser("summary", help="生成学习总结")
    p.add_argument("--subject", help="科目文件夹名")
    p.add_argument("--book", help="书目文件夹名")
    p.add_argument("--all", action="store_true", help="处理全部书目")
    p.add_argument("--provider", help="指定 AI 提供方 id")
    p.set_defaults(func=cmd_summary)

    p = sub.add_parser("pdf", help="把 Markdown 导出为 PDF")
    p.add_argument("--file", required=True, help="源 Markdown 文件")
    p.add_argument("--out", help="输出 PDF 路径（默认与源文件同目录同名）")
    p.add_argument("--page-size", dest="page_size", help="A4/A5/B5/Letter/Legal")
    p.add_argument("--margin", type=float, help="页边距（毫米）")
    p.set_defaults(func=cmd_pdf)

    p = sub.add_parser("icon", help="生成或更换程序图标（大白星球的桌面快捷方式图标）")
    p.add_argument("--image", help="用这张图片作为图标（会居中裁成正方形并转成多分辨率 ico）")
    p.add_argument("--style", choices=list(planet_icon.STYLES), help="内置绘制风格")
    p.add_argument("--rebuild", action="store_true", help="强制重新生成内置图标")
    p.add_argument("--size", type=int, default=512, help="自定义图片的基准尺寸（默认 512）")
    p.add_argument("--preview", help="顺便输出一张风格对比图到指定路径")
    p.add_argument("--shortcut", action="store_true", help="生成图标后重建桌面快捷方式")
    p.set_defaults(func=cmd_icon)

    p = sub.add_parser(
        "key",
        help="设置 API Key 并立即测通（Key 从标准输入读取，不进命令行历史）",
    )
    p.add_argument("--provider", help="提供方 id（默认当前 AI）")
    p.add_argument("--show", action="store_true", help="只显示已保存 Key 的长度与首尾，便于核对")
    p.add_argument("--clear", action="store_true", help="清除该提供方已保存的 Key")
    p.add_argument("--no-test", action="store_true", help="只保存，不测试连接")
    p.set_defaults(func=cmd_key)

    sub.add_parser("doctor", help="环境体检").set_defaults(func=cmd_doctor)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    context = bootstrap([])
    try:
        return int(args.func(context, args) or 0)
    except KeyboardInterrupt:
        _print("\n已中断。")
        return 130
    except Exception as exc:  # noqa: BLE001 - 命令行需要给出可读错误
        _print(f"执行失败：{exc}")
        import logging

        logging.getLogger(__name__).exception("命令行执行失败")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
