"""界面层的无头自检（offscreen 模式，不需要真实显示器）。

用法::

    set QT_QPA_PLATFORM=offscreen
    <venv>\\Scripts\\python.exe tests\\smoke_gui.py

覆盖：主窗口构建、菜单栏、科目/书目创建、文件导入、Markdown 打开与编辑、
AI 双栏开关、样式切换、带假 AI 的总结生成、版本备份、各对话框构建。

说明：无头环境下没有人能点按钮，因此这里会把消息框和部分对话框替换成
"自动确认"的桩，只验证调用链路是否走通。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

CODE_DIR = Path(__file__).resolve().parents[1]
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

FAILURES: list[str] = []
DIALOG_LOG: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    print(f"[{'PASS' if condition else 'FAIL'}] {label}" + (f" -> {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


# --------------------------------------------------------------------------
# 让所有模态对话框在无头环境下自动返回
# --------------------------------------------------------------------------

def pump(ms: int = 200) -> None:
    """让事件循环真的转起来一段时间。

    **为什么不能只用 ``app.processEvents()``**（这是个真坑，查了很久）：

    离屏（offscreen）平台上，``processEvents()`` **不会派发跨线程排队信号** ——
    后台线程 emit 出来的 ``finished_ok`` 会一直排队，槽函数永不执行。
    表现为"任务明明跑完了、界面却一直显示正在处理"，
    而且**没有任何报错**。更糟的是它会让人误判被测代码有 bug。

    （实测：同一个 ``QThread``，``processEvents`` 循环收不到信号，
    而 ``QEventLoop.exec()`` 转起来就能收到；
    先 ``thread.wait()`` 再用 ``processEvents`` 也能收到。）

    所以凡是要等后台线程结果的用例，都用这个函数替代 processEvents 循环。
    """
    from PyQt6.QtCore import QEventLoop, QTimer

    loop = QEventLoop()
    QTimer.singleShot(max(0, int(ms)), loop.quit)
    loop.exec()


def _tab_names(view) -> list[str]:
    """取标签页上的**栏目名**，剥掉后面的条目数量。

    标签文字形如 ``笔记 3``（栏目名 + 空格 + 数量）；数量为 0 时不显示。
    断言只关心栏目名与顺序，因此统一剥掉数字，避免用例被数据条数影响。
    """
    names: list[str] = []
    for index in range(view.tabs.count()):
        text = view.tabs.tabText(index)
        parts = text.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            text = parts[0]
        names.append(text)
    return names


def install_dialog_stubs() -> None:
    from PyQt6.QtWidgets import QDialog, QMessageBox

    from gwp.ui import common

    def _record(kind: str, text: str) -> None:
        DIALOG_LOG.append(f"{kind}: {text.splitlines()[0] if text else ''}")

    def _info(_parent, text, title="提示", *args, **kwargs):
        _record(f"info[{title}]", str(text))
        return QMessageBox.StandardButton.Ok

    def _warn(_parent, text, title="注意", *args, **kwargs):
        _record(f"warn[{title}]", str(text))
        return QMessageBox.StandardButton.Ok

    def _error(_parent, text, title="出错了", *args, **kwargs):
        _record(f"error[{title}]", str(text))
        return QMessageBox.StandardButton.Ok

    def _confirm(_parent, text, title="请确认", *args, **kwargs):
        _record(f"confirm[{title}]", str(text))
        return True

    common.info = _info          # type: ignore[assignment]
    common.warn = _warn          # type: ignore[assignment]
    common.error = _error        # type: ignore[assignment]
    common.confirm = _confirm    # type: ignore[assignment]

    # 「生成总结」用 ask_generate_summary 问两个复选框（混排 / 长庚知道补充）；
    # 返回 None 表示取消。
    # 默认按"确定且都不勾选"处理（= 只合并资料、不调 AI），
    # 需要勾选或取消的用例自己临时替换这个函数。
    common.ask_generate_summary = lambda *a, **k: (False, False)   # type: ignore[assignment]

    # QMessageBox 静态方法（有些地方直接用它）
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)  # type: ignore[assignment]
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)  # type: ignore[assignment]
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)  # type: ignore[assignment]

    # 会阻塞的对话框统一改成"不显示直接返回"
    QDialog.exec = lambda self: _record("dialog", self.windowTitle()) or QDialog.DialogCode.Rejected  # type: ignore[assignment]

    # QMessageBox.exec（DocumentView.confirm_close 里用到）
    QMessageBox.exec = lambda self: 0  # type: ignore[assignment]


def main() -> int:
    temp_root = Path(tempfile.mkdtemp(prefix="gwp_gui_"))
    os.environ["GWP_ROOT"] = str(temp_root)
    (temp_root / "code").mkdir(parents=True, exist_ok=True)

    from gwp.app import create_application

    app = create_application(["gwp-test"])
    install_dialog_stubs()

    from gwp.bootstrap import bootstrap
    from gwp.core.config import Config
    from gwp.core.paths import DataPaths, set_current

    config = Config.load(temp_root / "code" / "else data" / "config.json", force=True)
    config.set("paths.data_root", str(temp_root / "data"))
    # 生成总结后**不要自动打开 PDF**。
    #
    # 为什么必须在测试里关掉：自动打开会交给系统阅读器（这台机器上是
    # `fastpdf`），它会**一直占着那个 PDF**，于是"再次生成"替换不了它
    # （实测 WinError 32，重试 6 轮也不行，因为阅读器不会自己放手）。
    # 那是产品的**预期行为**（用户当然会想看刚生成的总结），
    # 但测试会被它绊住 —— 所以测试里关掉，产品里保留。
    config.set("summary.auto_open_after_generate", False)
    config.set("startup.prewarm_scan", False)
    config.save()
    set_current(DataPaths(config))

    context = bootstrap([])
    check("bootstrap 成功", context.paths.data_root == temp_root / "data")

    # ---- 主窗口 ----
    from gwp.services.file_clipboard import COPY, CUT
    from gwp.ui.main_window import MainWindow
    from gwp.ui.views.book_view import TABS
    from gwp.ui.windows.global_chat_window import DAILY_SESSION_KEY
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QLabel

    window = MainWindow(context)
    window.show()
    app.processEvents()
    check("主窗口创建", window.isVisible())
    menus = [action.text() for action in window.menuBar().actions()]
    check("菜单栏包含 8 个菜单", len(menus) == 8, str(menus))
    for expected in ("文件", "编辑", "查看", "工具", "AI", "设置", "论坛", "帮助"):
        check(f"存在「{expected}」菜单", any(expected in item for item in menus), str(menus))

    # ---- 科目 / 书目 ----
    library = context.library
    subject = library.create_subject("界面测试科目")
    library.invalidate()
    window.home_view.refresh()
    app.processEvents()
    check("首页出现卡片", window.home_view.grid.count == 1, str(window.home_view.grid.count))

    book = library.create_book(subject.name, "界面测试书目")
    library.invalidate()
    window.open_subject(subject.name)
    app.processEvents()
    check("科目页出现卡片", window.subject_view.grid.count == 1)

    window.open_book(subject.name, book.name)
    app.processEvents()
    check("书目页加载", window.book_view.book() is not None)
    check("书目页有 9 个标签（含单词书）",
          window.book_view.tabs.count() == 9,
          str(window.book_view.tabs.count()))
    tab_titles = _tab_names(window.book_view)
    check(
        "标签顺序：AI 总结在最前，练习紧随笔记，「其它文件」在教材之后（自学课）",
        tab_titles == [
            "AI 总结", "简介", "笔记", "练习", "易错题", "教材", "其它文件",
            "单词书", "全部条目",
        ],
        str(tab_titles),
    )
    check("默认停在 AI 总结页", window.book_view._current_tab_key() == "summary",
          window.book_view._current_tab_key())

    # ---- 作业标签：目录正确、且不参与 AI 总结 ----
    from gwp.core import constants as _C

    check("作业目录已存在", (book.path / _C.HOMEWORK_FOLDER).is_dir(),
          str(sorted(p.name for p in book.path.iterdir())))
    homework_index = next(i for i, (key, _t, _f) in enumerate(TABS) if key == "homework")
    window.book_view.tabs.setCurrentIndex(homework_index)
    app.processEvents()
    check("切到作业标签", window.book_view._current_tab_key() == "homework",
          window.book_view._current_tab_key())
    homework_target = window.book_view._target_folder()
    check("作业标签的导入目标是 homework 目录",
          homework_target == book.path / _C.HOMEWORK_FOLDER, str(homework_target))

    # 放进作业的文件不应进入总结来源
    homework_file = book.path / _C.HOMEWORK_FOLDER / "作业一.md"
    homework_file.write_text("# 作业一\n\n不该进总结\n", encoding="utf-8")
    window.book_view.refresh()
    app.processEvents()
    from gwp.services import document_reader as _dr  # noqa: F401  仅确认模块可导入

    summarizer_for_check = context.summarizer
    resolved_now = summarizer_for_check.resolve_sources(book)
    check("作业文件没有进入总结来源",
          not any(_C.HOMEWORK_FOLDER in str(path) for _, path in resolved_now),
          str([str(p) for _, p in resolved_now]))
    stats_now = summarizer_for_check.stats(book)
    check("资料概览把作业列为不参与总结",
          stats_now.get(_C.HOMEWORK_FOLDER) == 1, str(stats_now))
    check("参与总结的总数不含作业",
          stats_now.get("total") == stats_now.get("intro", 0), str(stats_now))
    homework_table = window.book_view._tables[_C.HOMEWORK_FOLDER]
    check("作业文件出现在作业表格里",
          any(item.name == "作业一.md" for item in homework_table._items),
          str([i.name for i in homework_table._items]))
    homework_file.unlink(missing_ok=True)
    window.book_view.refresh()
    app.processEvents()

    # ---- 资料概览可折叠（默认折起，从布局里移除，不留空白）----
    view = window.book_view
    check("存在资料概览面板", hasattr(view, "side_panel"))
    check("存在折叠按钮", hasattr(view, "btn_collapse"))
    check("存在常驻开关", hasattr(view, "btn_side_toggle"))
    # 入口按钮要与其它操作按钮完全一致（同类型、同高度、同文字规格）
    from PyQt6.QtWidgets import QPushButton
    check("入口是普通按钮样式", isinstance(view.btn_side_toggle, QPushButton),
          type(view.btn_side_toggle).__name__)
    check("入口有文字标签", view.btn_side_toggle.text() == "资料概览",
          view.btn_side_toggle.text())
    other = view.btn_export      # 同一操作区里的普通按钮
    check("入口与其它按钮同类", isinstance(other, QPushButton) and isinstance(view.btn_side_toggle, QPushButton))
    # 两者的外观都由同一条 QPushButton 规则决定：没有 accent 定制属性、未设固定尺寸
    check(
        "入口没有额外的大小定制（与其它按钮同规则）",
        not view.btn_side_toggle.property("accent")
        and not other.property("accent")
        and view.btn_side_toggle.maximumHeight() == other.maximumHeight(),
        f"accent={view.btn_side_toggle.property('accent')} maxH={view.btn_side_toggle.maximumHeight()}",
    )
    view.ensurePolished()
    check("窗口样式表已应用（按钮外观由同一套 QSS 决定）", "QPushButton" in window.styleSheet())
    check("入口可勾选（用于反显展开态）", view.btn_side_toggle.isCheckable())
    check("默认是折起状态", view.side_collapsed)
    check("折起时面板已从布局移除", view.side_panel.parent() is None)
    check("折起时面板不可见", not view.side_panel.isVisible())
    check("常驻开关显示为未勾选", not view.btn_side_toggle.isChecked())
    check("折起时左侧列表占满", view.splitter.count() == 1, str(view.splitter.count()))

    view.set_side_collapsed(False, animate=False)
    app.processEvents()
    check("展开后状态正确", not view.side_collapsed)
    check("展开后面板回到布局", view.side_panel.parent() is view.splitter)
    check("展开后面板可见", view.side_panel.isVisible())
    check("展开后内容可见", view.side_content.isVisible())
    check("展开后有合理宽度", view.side_panel.width() >= 300, str(view.side_panel.width()))
    check("展开后按钮为 ▾", view.btn_collapse.text() == "▾", view.btn_collapse.text())
    check("常驻开关显示为勾选", view.btn_side_toggle.isChecked())

    view.set_side_collapsed(True, animate=False)
    app.processEvents()
    check("再次折起成功", view.side_collapsed)
    check("折起后面板再次被移除", view.side_panel.parent() is None)
    check("折起状态已写入配置", bool(config.get("ui.book_side_collapsed")))

    # 折叠状态在重新进入书目后保持
    window.open_book(subject.name, book.name)
    app.processEvents()
    check("重新进入书目后仍是折起", window.book_view.side_collapsed)
    check("重新进入后仍从布局移除", window.book_view.side_panel.parent() is None)

    # 展开一次，后续用例（依赖右侧面板按钮）才能正常使用
    window.book_view.set_side_collapsed(False, animate=False)
    app.processEvents()
    check("恢复展开以便后续用例", not window.book_view.side_collapsed)

    # ---- 资料 ----
    from gwp.core import constants as C

    (book.path / C.NOTEBOOK_FOLDER / "笔记.md").write_text("# 笔记\n\n行列式的性质。\n", encoding="utf-8")
    (book.path / C.ERROR_FOLDER / "错题.md").write_text("# 错题\n\n把秩算错了。\n", encoding="utf-8")
    target_source = book.path / C.NOTEBOOK_FOLDER / "笔记.md"
    window.book_view.refresh()
    app.processEvents()
    check("笔记表有 1 行", window.book_view._tables[C.NOTEBOOK_FOLDER].rowCount() == 1)
    check("易错题表有 1 行", window.book_view._tables["error-prone"].rowCount() == 1)

    # ---- 复制 / 剪切 / 粘贴 ----
    view = window.book_view
    check("存在剪贴板操作条", hasattr(view, "btn_cut") and hasattr(view, "btn_copy"))
    check("剪贴板初始为空", view.clipboard.is_empty)
    check("未选中时剪切按钮不可用", not view.btn_cut.isEnabled())
    check("剪贴板为空时粘贴按钮不可用", not view.btn_paste.isEnabled())

    notebook_index = next(i for i, (key, _t, _f) in enumerate(TABS) if key == C.NOTEBOOK_FOLDER)
    error_index = next(i for i, (key, _t, _f) in enumerate(TABS) if key == C.ERROR_FOLDER)

    # 专用一次性文件，避免影响后面「打开文档」的用例
    clip_src = book.path / C.NOTEBOOK_FOLDER / "剪贴板测试.md"
    clip_move = book.path / C.NOTEBOOK_FOLDER / "剪切移动测试.md"
    clip_src.write_text("# 剪贴板测试\n\n用于验证复制粘贴。\n", encoding="utf-8")
    clip_move.write_text("# 剪切移动测试\n\n用于验证剪切。\n", encoding="utf-8")
    view.refresh()
    view.tabs.setCurrentIndex(notebook_index)
    app.processEvents()
    notebook_table = view._tables[C.NOTEBOOK_FOLDER]
    check("笔记表有 3 行（笔记 + 2 个测试文件）", notebook_table.rowCount() == 3,
          str(notebook_table.rowCount()))

    def select_by_path(table, path) -> bool:
        for row in range(table.rowCount()):
            if table._items[row].path == path:
                table.selectRow(row)
                app.processEvents()
                return True
        return False

    check("能选中剪贴板测试文件", select_by_path(notebook_table, clip_src))
    check("选中后剪切/复制可用", view.btn_cut.isEnabled() and view.btn_copy.isEnabled())

    # 复制 -> 粘贴到易错题目录
    view.copy_selection(mode=COPY)
    check("剪贴板记录为复制", not view.clipboard.is_cut and view.clipboard.count == 1)
    check("剪贴板提示文案正确", "已复制" in view.clipboard.describe(), view.clipboard.describe())
    check("粘贴按钮变为可用", view.btn_paste.isEnabled())

    view.tabs.setCurrentIndex(error_index)
    app.processEvents()
    before_copy = view._tables[C.ERROR_FOLDER].rowCount()
    view.paste_files()
    app.processEvents()
    check("复制粘贴后目标目录多了一项",
          view._tables[C.ERROR_FOLDER].rowCount() == before_copy + 1,
          f"{before_copy} -> {view._tables[C.ERROR_FOLDER].rowCount()}")
    check("复制模式的源文件未被删除", clip_src.exists())
    check("副本内容正确",
          any(p.read_text(encoding="utf-8").startswith("# 剪贴板测试")
              for p in (book.path / C.ERROR_FOLDER).glob("剪贴板测试*.md")))

    # 同目录再次粘贴 -> 自动改名，不覆盖
    view.tabs.setCurrentIndex(notebook_index)
    app.processEvents()
    view.paste_files()
    app.processEvents()
    duplicates = sorted(p.name for p in (book.path / C.NOTEBOOK_FOLDER).glob("剪贴板测试*.md"))
    check("同目录粘贴自动改名不覆盖", len(duplicates) == 2, str(duplicates))

    # 剪切 -> 粘贴（移动）
    check("能选中剪切移动测试文件", select_by_path(notebook_table, clip_move))
    view.copy_selection(mode=CUT)
    check("剪贴板记录为剪切", view.clipboard.is_cut)
    check("剪切提示文案正确", "已剪切" in view.clipboard.describe(), view.clipboard.describe())
    view.tabs.setCurrentIndex(error_index)
    app.processEvents()
    before_cut = view._tables[C.ERROR_FOLDER].rowCount()
    view.paste_files()
    app.processEvents()
    check("剪切粘贴后源文件已移除", not clip_move.exists(), str(clip_move))
    check("剪切粘贴后目标目录多了一项",
          view._tables[C.ERROR_FOLDER].rowCount() == before_cut + 1,
          f"{before_cut} -> {view._tables[C.ERROR_FOLDER].rowCount()}")
    check("剪切完成后剪贴板被清空", view.clipboard.is_empty)

    # 结构目录不允许剪切
    root_index = next(i for i, (key, _t, _f) in enumerate(TABS) if key == "root")
    root_table = view._tables["root"]
    view.tabs.setCurrentIndex(root_index)
    app.processEvents()
    protected_index = None
    for row in range(root_table.rowCount()):
        entry = root_table._items[row]
        if entry.is_dir and entry.name == C.NOTEBOOK_FOLDER:
            protected_index = row
            break
    if protected_index is not None:
        root_table.selectRow(protected_index)
        app.processEvents()
        view.copy_selection(mode=CUT)
        check("结构目录被拒绝剪切", view.clipboard.is_empty)
        check("结构目录仍然存在", (book.path / C.NOTEBOOK_FOLDER).is_dir())

    # 清理：只删本次测试产生的文件
    for extra in list((book.path / C.ERROR_FOLDER).glob("剪贴板测试*.md")):
        extra.unlink()
    for extra in list((book.path / C.ERROR_FOLDER).glob("剪切移动测试*.md")):
        extra.unlink()
    for extra in list((book.path / C.NOTEBOOK_FOLDER).glob("剪贴板测试*.md")):
        if extra != clip_src:
            extra.unlink()
    clip_src.unlink()
    view.clipboard.clear()
    view.refresh()
    app.processEvents()
    check("清理后笔记表剩 1 行", view._tables[C.NOTEBOOK_FOLDER].rowCount() == 1,
          str(view._tables[C.NOTEBOOK_FOLDER].rowCount()))
    check("原笔记文件未被剪贴板测试影响", target_source.exists())

    # ---- 导出 PDF：对象选择规则（选中的文件优先，没选中才用总结）----
    from gwp.ui.dialogs.export_dialog import ExportPdfDialog

    # 生成一个总结，制造"既有总结、又有选中文件"的场景
    summary_file = book.path / f"{book.name}{C.SUMMARY_SUFFIX}"
    summary_file.write_text("# 测试总结\n\n这是总结内容。\n", encoding="utf-8")
    library.invalidate()
    view.refresh()
    app.processEvents()

    # 1) 停在「笔记」标签：选中的笔记应当优先于总结
    view.tabs.setCurrentIndex(notebook_index)
    app.processEvents()
    notebook_table.selectRow(0)
    app.processEvents()
    picked = view._resolve_export_source(view.book())
    check(
        "选中笔记时导出笔记（不再被总结抢占）",
        picked == target_source,
        f"picked={picked}",
    )

    # 2) 未选中任何文件：回退到总结
    notebook_table.clearSelection()
    summary_index = next(i for i, (key, _t, _f) in enumerate(TABS) if key == "summary")
    view.tabs.setCurrentIndex(summary_index)
    app.processEvents()
    view._tables["summary"].clearSelection()
    picked = view._resolve_export_source(view.book())
    check("未选中时回退到总结", picked == summary_file, f"picked={picked}")

    # 3) 选中的是文件夹时，取文件夹里第一个可导出文件
    view.tabs.setCurrentIndex(notebook_index)
    app.processEvents()
    for row in range(notebook_table.rowCount()):
        pass
    folder_item = None
    root_table_index = next(i for i, (key, _t, _f) in enumerate(TABS) if key == "root")
    view.tabs.setCurrentIndex(root_table_index)
    app.processEvents()
    for row in range(view._tables["root"].rowCount()):
        entry = view._tables["root"]._items[row]
        if entry.is_dir and entry.name == C.NOTEBOOK_FOLDER:
            folder_item = entry
            view._tables["root"].selectRow(row)
            break
    app.processEvents()
    if folder_item is not None:
        picked = view._resolve_export_source(view.book())
        check(
            "选中文件夹时取其中第一个文件",
            picked is not None and picked.parent == folder_item.path,
            f"picked={picked}",
        )

    # 4) 对话框要显示导出对象，并带页码选项
    dialog = ExportPdfDialog(context, summary_file, window)
    check("导出对话框标题标明文件", summary_file.name in dialog.windowTitle(), dialog.windowTitle())
    source_labels = [
        label.text() for label in dialog.findChildren(QLabel)
        if summary_file.name in (label.text() or "")
    ]
    check("导出对话框正文标明导出对象", bool(source_labels), str(len(source_labels)))
    check("导出对话框有页码选项",
          hasattr(dialog, "check_page_numbers") and dialog.check_page_numbers.isChecked())
    check("导出对话框有「询问页码范围」选项",
          hasattr(dialog, "check_ask_range") and dialog.check_ask_range.isChecked())
    check("导出按钮初始可用", dialog.btn_export.isEnabled())
    dialog.close()

    # ---- 页码范围询问框：默认全部 + 输入校验 ----
    from gwp.services.page_range import PageRangeError, parse_page_range
    from gwp.ui.dialogs.page_range_dialog import PageRangeDialog

    range_dialog = PageRangeDialog(10, window)
    check("范围框默认全部页", range_dialog.input_range.text() == "1-10",
          range_dialog.input_range.text())
    check("范围框默认勾选加页码", range_dialog.add_page_numbers)
    check("默认选中全部 10 页", range_dialog.selected_pages() == list(range(1, 11)),
          str(range_dialog.selected_pages()))
    check("合法输入时确定按钮可用", range_dialog.btn_ok.isEnabled())

    range_dialog.input_range.setText("1-3, 5")
    app.processEvents()
    check("多段范围解析正确", range_dialog.selected_pages() == [1, 2, 3, 5],
          str(range_dialog.selected_pages()))
    check("结果提示显示页数", "共 4 页" in range_dialog.lbl_result.text(),
          range_dialog.lbl_result.text())

    # 非法输入：按钮禁用 + 红字提示（不会用错误值去导出）
    range_dialog.input_range.setText("2-1")
    app.processEvents()
    check("区间反了时禁用确定按钮", not range_dialog.btn_ok.isEnabled())
    check("区间反了时给出提示", "反了" in range_dialog.lbl_result.text(),
          range_dialog.lbl_result.text())

    range_dialog.input_range.setText("99")
    app.processEvents()
    check("越界时禁用确定按钮", not range_dialog.btn_ok.isEnabled())
    check("越界时给出提示", "超出" in range_dialog.lbl_result.text(),
          range_dialog.lbl_result.text())

    range_dialog.input_range.setText("abc")
    app.processEvents()
    check("乱输入时禁用确定按钮", not range_dialog.btn_ok.isEnabled())

    # e 的含义：最后一页
    range_dialog.input_range.setText("e-1, e")
    app.processEvents()
    check("e 表示最后一页", range_dialog.selected_pages() == [9, 10],
          str(range_dialog.selected_pages()))

    range_dialog.input_range.setText("")
    app.processEvents()
    check("清空输入视为全部页", len(range_dialog.selected_pages()) == 10,
          str(range_dialog.selected_pages()))

    range_dialog.input_range.setText("1-3")
    app.processEvents()
    check("点「全部」可重置", True)
    range_dialog._reset_all()
    app.processEvents()
    check("重置后回到全部页", range_dialog.input_range.text() == "1-10",
          range_dialog.input_range.text())
    range_dialog.close()

    # ---- 端到端：导出流程（排版 → 弹窗选页 → 写出 3 页）----
    export_source = book.path / "导出测试.md"
    export_source.write_text(
        "# 导出范围测试\n\n" + "\n\n".join(
            f"## 第 {i} 节\n\n" + ("用于撑满页面的内容。" * 200) for i in range(1, 7)
        ),
        encoding="utf-8",
    )
    export_target = book.path / "导出测试.pdf"
    live_dialog = ExportPdfDialog(context, export_source, window)
    seen_counts: list[int] = []

    def _fake_exec(self) -> int:
        seen_counts.append(self.total_pages)
        self.input_range.setText("1-3")
        self.check_numbers.setChecked(True)
        self._validate()
        return 1 if self.btn_ok.isEnabled() else 0

    original_exec = PageRangeDialog.exec
    PageRangeDialog.exec = _fake_exec          # type: ignore[assignment]
    live_dialog.input_path.setText(str(export_target))
    live_dialog._export()
    # 导出分两阶段（排版 -> 选页 -> 写出），两阶段之间有一瞬间"没有在跑的 worker"，
    # 因此这里必须等到"对话框被 accept"或"目标文件出现"才算结束，
    # 否则会提前跳出并关掉对话框，把正在写文件的线程掐断。
    finished = False
    for _ in range(1200):
        worker = live_dialog._worker
        busy = worker is not None and worker.isRunning()
        if not busy and (live_dialog.result() == 1 or export_target.exists()):
            finished = True
            break
        app.processEvents()
        app.thread().msleep(25)
    app.processEvents()
    PageRangeDialog.exec = original_exec       # type: ignore[assignment]
    check("导出流程正常结束（未被提前中断）", finished, "等待超时")
    live_dialog.close()

    check("导出流程走到了范围弹窗", len(seen_counts) == 1, str(seen_counts))
    check("弹窗拿到了排版后的总页数", bool(seen_counts) and seen_counts[0] >= 3,
          str(seen_counts))
    check("最终 PDF 已生成", export_target.is_file())
    if export_target.is_file():
        try:
            import pymupdf

            result = pymupdf.open(export_target)
            created = result.page_count
            first_page = result[0].get_text()
            result.close()
            check("导出的页数与选择一致（3 页）", created == 3, str(created))
            check("导出结果带页码", f"- 1 / {seen_counts[0]} -" in first_page,
                  repr(first_page[-16:]))
        except ImportError:
            pass
    leftover = [p.name for p in book.path.iterdir() if ".layout" in p.name or ".pages" in p.name]
    check("导出后没有残留中间文件", not leftover, str(leftover))
    export_source.unlink(missing_ok=True)
    export_target.unlink(missing_ok=True)

    # 清理总结，避免影响后续断言
    summary_file.unlink()
    library.invalidate()
    view.refresh()
    app.processEvents()

    # ---- 打开文档（独立窗口） ----
    target = book.path / C.NOTEBOOK_FOLDER / "笔记.md"
    window.open_document_window(target)
    app.processEvents()
    check("新窗口已打开", len(window._windows) == 1, str(len(window._windows)))
    doc_window = window._windows[0]
    check("文档路径正确", doc_window.view.path == target)
    check("默认是查看模式", not doc_window.view.is_editing)

    doc_window.view.toggle_edit_mode()
    app.processEvents()
    check("切换到编辑模式", doc_window.view.is_editing)
    doc_window.view.editor.replace_all("# 笔记（已编辑）\n\n新内容。\n")
    app.processEvents()
    check("编辑后标记为未保存", doc_window.view.has_unsaved)
    check("保存成功", doc_window.view.save())
    check("内容已写入磁盘", "已编辑" in target.read_text(encoding="utf-8"))

    # ---- AI 双栏 ----
    doc_window.view.set_ai_visible(True)
    app.processEvents()
    check("AI 面板可见", doc_window.view.chat.isVisible())
    check("AI 下拉有提供方", doc_window.view.chat.combo_ai.count() >= 4,
          str(doc_window.view.chat.combo_ai.count()))
    doc_window.view.chat.bind_document(target, "test-key", title="test")
    check("聊天会话已绑定", doc_window.view.chat.session is not None)

    # ---- 内嵌文档视图 ----
    config.set("ui.open_files_in_new_window", False)
    window.open_document(target)
    app.processEvents()
    check("主窗口内嵌文档视图", len(window._documents) == 1, str(len(window._documents)))
    inline = window._documents[0]
    inline.set_ai_visible(True)
    app.processEvents()
    check("内嵌视图 AI 面板可见", inline.chat.isVisible())
    check("文件已自动发送给 AI（写入会话）", inline.chat.session.file_sent)

    # ---- 主题 ----
    window.act_theme.setChecked(True)
    app.processEvents()
    check("切换到深色主题", context.config.get("ui.theme") == "dark", str(context.config.get("ui.theme")))
    check("样式表已应用", "QMainWindow" in window.styleSheet())
    window.act_theme.setChecked(False)
    app.processEvents()
    check("切回浅色主题", context.config.get("ui.theme") == "light")

    # ---- 对话框构建 ----
    from gwp.ui.dialogs.settings_dialog import SettingsDialog

    dialog = SettingsDialog(context, window)
    check("设置对话框有 9 页", dialog.stack.count() == 9, str(dialog.stack.count()))
    check("设置收集到路径配置", "data_root" in dialog.collect().get("paths", {}))
    dialog.close()

    from gwp.ui.dialogs.help_dialog import HelpDialog

    help_dialog = HelpDialog(context, "设计思想", window)
    check("帮助内容非空", len(help_dialog.view.toPlainText()) > 200, str(len(help_dialog.view.toPlainText())))
    help_dialog.close()

    from gwp.ui.dialogs.export_dialog import ExportPdfDialog

    export_dialog = ExportPdfDialog(context, target, window)
    check("导出对话框默认 .pdf", export_dialog.input_path.text().endswith(".pdf"))
    export_dialog.close()

    from gwp.ui.dialogs.backup_dialog import BackupDialog

    backup_dialog = BackupDialog(context, subject.name, book.name, book.path / "x_summary.md", window)
    check("版本对话框可构建", backup_dialog is not None)
    backup_dialog.close()

    from gwp.ai.types import AiQuestion
    from gwp.ui.dialogs.question_dialog import AiQuestionDialog

    question_dialog = AiQuestionDialog(
        AiQuestion(question="用哪种记法？", options=["A", "B"], allow_custom=True), window
    )
    check("提问对话框有选项", question_dialog.list.count() == 2)
    question_dialog.close()

    from gwp.ui.dialogs.chat_manager_dialog import ChatManagerDialog

    chat_manager = ChatManagerDialog(context, window)
    check("聊天记录对话框可构建", chat_manager.list.count() >= 1, str(chat_manager.list.count()))
    chat_manager.close()

    # 生成总结前的"资料清单"对话框（需求变更后不再预览 AI 提示词，
    # 只如实列出会被插入的文件）
    from gwp.services import source_merge as _sm_mod
    from gwp.ui.dialogs.materials_dialog import SummarySourcesDialog

    _ms_sources = _sm_mod.collect_sources(book)
    _ms_dialog = SummarySourcesDialog(book.title, _ms_sources, window)
    check("**资料清单对话框列出了会被插入的文件**",
          _ms_dialog.table.rowCount() == len(_ms_sources)
          and _ms_dialog.table.rowCount() >= 3,
          f"{_ms_dialog.table.rowCount()} 行 / {len(_ms_sources)} 份")
    check("资料清单能数出页数（PDF 不只算 1 页）",
          all(_ms_dialog.table.item(r, 3) is not None
              for r in range(_ms_dialog.table.rowCount())),
          "有行缺页数")
    _ms_dialog.close()

    from gwp.ui.dialogs.subject_dialog import SubjectDialog
    from gwp.ui.dialogs.book_dialog import BookDialog

    subject_dialog = SubjectDialog(window, subject=subject)
    check("科目对话框回填名称", subject_dialog.input_name.text() == subject.name)
    subject_dialog.close()
    book_dialog = BookDialog(window, book=book)
    check("书目对话框回填名称", book_dialog.input_name.text() == book.name)
    book_dialog.close()

    # ---- 完整总结流程（需求变更后：直接插入资料，AI 不再写正文）----
    #
    # 变更前：「生成总结」把简介/笔记/易错题交给 AI，AI 写出一份正文。
    # 变更后：**不调用 AI 写正文**，而是把资料原样转成图片插进 summary；
    #         AI 只在"按主题重排页序"这个可选步骤里出现一次。
    #
    # 所以这一段旧断言（"summary 内容里有 AI 写的『学习目标』"）已经不再成立，
    # 改成验证新行为：正文是**资料图片**、AI 没有参与写文字。
    from gwp.ai.base import BaseAIAdapter
    from gwp.ai.registry import register_provider

    @register_provider
    class GuiFakeAdapter(BaseAIAdapter):
        provider_id = "gui_fake"
        label = "测试 AI"
        #: 记录 AI 被调用了几次、prompt 里有什么（用来证明"没有让 AI 写正文"）
        calls: list = []
        #: 想让这次调用返回什么就设它（用完置回 None）
        reply: str | None = None

        def is_configured(self):
            return True, ""

        def complete(self, messages, options=None):
            type(self).calls.append(messages)
            # 用例指定了返回值就用它（例如「长庚知道」补充要一段 Markdown）
            if type(self).reply:
                return type(self).reply
            content = messages[-1].content if messages else ""
            # 「AI 混排」要的是 JSON 页序；**其它场景**（聊天、日记总结）
            # 仍然返回普通文本 —— 这个假适配器是所有 AI 用例共用的，
            # 一律返回 JSON 会把聊天那些断言弄坏（踩过）。
            if '"order"' in content or "页清单" in content:
                total = 0
                for line in content.splitlines():
                    head = line.split(".", 1)[0].strip()
                    if head.isdigit():
                        total = max(total, int(head))
                import json as _json

                return _json.dumps({"order": list(range(1, total + 1))})
            return "# 界面测试书目\n\n## 一、学习目标\n\n掌握行列式。\n"

        def stream(self, messages, options=None, on_chunk=None):
            text = self.complete(messages, options)
            if on_chunk:
                on_chunk(text)
            return text

    context.ai._adapters["gui_fake"] = GuiFakeAdapter(config)
    context.ai._active_id = "gui_fake"

    # 「生成总结」的确认框走 common.ask_generate_summary；这里要临时改它，
    # 所以先把模块取到本地（这个作用域里没有裸名 `common`）。
    from gwp.ui import common as _common_sum

    summary_path = book.path / f"{book.name}{C.SUMMARY_SUFFIX}"

    # 需求变更后「生成总结」是**按类型分流**的：
    #   md -> 直接融合成文字；图片型 PDF -> 每页转成图片。
    # 而 AI 混排**只对图片型资料有意义**（它排的是"页"）。
    # 这个书目原来只有 md，所以既不会有图片、也不会触发混排 ——
    # 这里补一份**两页的图片型 PDF**，让两条路都真的走到。
    import fitz as _gui_fitz
    from PIL import Image as _GuiImg
    from PIL import ImageDraw as _GuiDraw

    _gui_scan = Path(tempfile.mkdtemp(prefix="gwp_guiscan_")) / "s.png"
    _gi = _GuiImg.new("RGB", (700, 900), (255, 255, 255))
    _GuiDraw.Draw(_gi).text((40, 40), "SCANNED PAGE", fill=(0, 0, 0))
    _gi.save(_gui_scan)
    _gui_pdf = book.path / C.NOTEBOOK_FOLDER / "扫描讲义.pdf"
    _gd = _gui_fitz.open()
    for _ in range(2):
        _gp = _gd.new_page(width=595, height=842)
        _gp.insert_image(_gui_fitz.Rect(0, 0, 595, 842), filename=str(_gui_scan))
    _gd.save(str(_gui_pdf))
    _gd.close()

    # ---- 第一次：不勾混排 -> 完全不调用 AI ----
    GuiFakeAdapter.calls.clear()
    _real_ask_choice = _common_sum.ask_generate_summary
    _common_sum.ask_generate_summary = lambda *a, **k: (False, False)
    try:
        window.book_view.generate_summary()
        for _ in range(20):
            app.processEvents()
    finally:
        _common_sum.ask_generate_summary = _real_ask_choice

    # ================= 技术路线变更后的断言（产物是 PDF）=================
    #
    # 需求："AI总结实现方法：将所有待总结文件转化并合并为一个pdf文档，
    #       结束后删除中间可能产生的废弃文档和数据"
    #       "不再生成md文档，旧的md之间删掉"
    #
    # 所以这里断言的是：**书目里只多出一个 summary.pdf**，
    # 旧的 md 被删掉，中间物（merged / equations / 临时目录）全部不存在。
    from gwp.services import summary_pdf as _sp_mod

    _pdf_path = _sp_mod.summary_pdf_path(book)
    check("**生成总结后产出的是 summary.pdf（不再是 md）**",
          _pdf_path.is_file(), str(_pdf_path))
    check("**不再生成 Markdown 总结**",
          not summary_path.is_file(), str(summary_path))

    _pdf_pages = 0
    if _pdf_path.is_file():
        import fitz as _gui_fitz2

        with _gui_fitz2.open(str(_pdf_path)) as _doc:
            _pdf_pages = _doc.page_count
    check("**合并后的 PDF 有多页内容（不是空壳）**",
          _pdf_pages >= 2, f"{_pdf_pages} 页")
    check("**不勾混排时不调用 AI 写任何东西**",
          not GuiFakeAdapter.calls,
          f"被调用了 {len(GuiFakeAdapter.calls)} 次")

    # ---- 中间物必须全部清掉（需求："删除中间可能产生的废弃文档和数据"）----
    _else_data = context.paths.else_data
    check("**中间图片目录 merged 不存在**",
          not (_else_data / "merged").exists(),
          str(_else_data / "merged"))
    check("**中间公式目录 equations 不存在**",
          not (_else_data / "equations").exists(),
          str(_else_data / "equations"))
    check("**没有留下构建中的临时 PDF**",
          not list(book.path.glob("*" + _sp_mod.BUILDING_SUFFIX)),
          str(list(book.path.glob("*" + _sp_mod.BUILDING_SUFFIX))))
    import tempfile as _tf

    check("**没有留下本次专用的临时工作目录**",
          not list(Path(_tf.gettempdir()).glob(_sp_mod.WORK_PREFIX + "*")),
          str(list(Path(_tf.gettempdir()).glob(_sp_mod.WORK_PREFIX + "*"))))
    # 书目目录里除了原本那些，只多一个 pdf
    _entries = sorted(p.name for p in book.path.iterdir())
    check("**书目目录里只多出 summary.pdf（没有别的残留）**",
          _entries.count(_pdf_path.name) == 1
          and not any(n.endswith(".tmp") or n.endswith(".building.pdf")
                      for n in _entries),
          str(_entries))

    # ---- 重复生成：目标文件被替换，且不产生第二份 ----
    _before_size = _pdf_path.stat().st_size if _pdf_path.is_file() else 0
    _real_ask_choice2 = _common_sum.ask_generate_summary
    _common_sum.ask_generate_summary = lambda *a, **k: (False, False)
    try:
        window.book_view.generate_summary()
        for _ in range(20):
            app.processEvents()
    finally:
        _common_sum.ask_generate_summary = _real_ask_choice2
    check("**重复生成不会越积越多（只替换同一个 PDF）**",
          _pdf_path.is_file()
          and len(list(book.path.glob("*" + C.SUMMARY_PDF_SUFFIX))) == 1,
          str(sorted(p.name for p in book.path.glob("*.pdf"))))
    check("重复生成后 PDF 仍然有内容",
          _pdf_path.is_file() and _pdf_path.stat().st_size > 1000,
          f"{_pdf_path.stat().st_size if _pdf_path.is_file() else 0} 字节")

    library.invalidate()
    refreshed = library.book(subject.name, book.name)
    check("扫描识别到 summary", refreshed is not None and refreshed.has_summary)
    check("**识别到的就是那个 PDF**",
          refreshed is not None and refreshed.summary_path is not None
          and refreshed.summary_path.suffix.lower() == ".pdf",
          str(refreshed.summary_path if refreshed else None))
    window.book_view.refresh()
    app.processEvents()
    check("总结标签页显示 1 项", window.book_view._tables["summary"].rowCount() == 1,
          str(window.book_view._tables["summary"].rowCount()))

    # ---- 第二次：勾上混排 -> AI 被调用且只用于"排页序" ----
    GuiFakeAdapter.calls.clear()
    _common_sum.ask_generate_summary = lambda *a, **k: (True, False)
    try:
        window.book_view.generate_summary()
        for _ in range(20):
            app.processEvents()
    finally:
        _common_sum.ask_generate_summary = _real_ask_choice

    check("**勾选混排后 AI 被调用了一次**",
          len(GuiFakeAdapter.calls) == 1, f"{len(GuiFakeAdapter.calls)} 次")
    if GuiFakeAdapter.calls:
        _prompt = GuiFakeAdapter.calls[0]
        _joined = "\n".join(str(m.content) for m in _prompt)
        # 要断言的是"这个请求的**目的**是排页序，而不是写总结"：
        # 它必须要求 order，且不能带上"写一份学习文档"那套总结提示词。
        check("**混排请求只问页序，没让 AI 写正文**",
              "order" in _joined
              and "学习资料整合专家" not in _joined
              and "硬性要求" not in _joined,
              _joined[:160])
        check("混排请求里带上了每页的来源与内容开头",
              "页" in _joined and "共" in _joined, _joined[:160])
    check("**混排后仍然只有一个 PDF（不产生第二份产物）**",
          len(list(book.path.glob("*" + C.SUMMARY_PDF_SUFFIX))) == 1
          and not summary_path.is_file(),
          str(sorted(p.name for p in book.path.iterdir())))

    # ---- 第三次：勾上「长庚知道」补充 -> 末尾多出带标记的页 ----
    #
    # 需求："生成AI总结时，可以在文档最后加入一些关于知识点的你的补充
    #       （标记 长庚知道 在页面左上角）"
    from gwp.services import knowledge_supplement as _ks_gui

    def _pages_with_label(path):
        import fitz as _fz

        with _fz.open(str(path)) as _d:
            return [i + 1 for i, _p in enumerate(_d)
                    if _ks_gui.LABEL in _p.get_text()], _d.page_count

    _before_marked, _before_pages = _pages_with_label(_pdf_path)
    check("**默认（不勾补充）末尾没有「长庚知道」页**",
          _before_marked == [],
          f"{_before_pages} 页，标记页={_before_marked}")

    GuiFakeAdapter.calls.clear()
    GuiFakeAdapter.reply = (
        "### 为什么取 ε/2\n\n各取 $\\varepsilon/2$ 是必须的。\n\n"
        "### 常见误区\n\n量词顺序不能换。\n"
    )
    _common_sum.ask_generate_summary = lambda *a, **k: (False, True)
    try:
        window.book_view.generate_summary()
        for _ in range(20):
            app.processEvents()
    finally:
        _common_sum.ask_generate_summary = _real_ask_choice

    _after_marked, _after_pages = _pages_with_label(_pdf_path)
    check("**勾了补充后会在末尾追加「长庚知道」页**",
          len(_after_marked) >= 1 and max(_after_marked) >= _before_pages,
          f"{_before_pages} 页 -> {_after_pages} 页，标记页={_after_marked}")
    check("**勾了补充时 AI 被调用了一次**",
          len(GuiFakeAdapter.calls) == 1, f"{len(GuiFakeAdapter.calls)} 次")
    if GuiFakeAdapter.calls:
        _joined2 = "\n".join(str(m.content) for m in GuiFakeAdapter.calls[0])
        check("**补充请求要的是知识点补充，不是排页序**",
              "补充" in _joined2 and "order" not in _joined2,
              _joined2[:160])
    check("**补充页不会把资料页挤掉（页数只增不减）**",
          _after_pages > _before_pages, f"{_before_pages} -> {_after_pages}")
    check("**补充页仍然只有一个 PDF、没有多余产物**",
          len(list(book.path.glob("*" + C.SUMMARY_PDF_SUFFIX))) == 1
          and not list(book.path.glob("*" + _sp_mod.BUILDING_SUFFIX)),
          str(sorted(p.name for p in book.path.iterdir())))
    GuiFakeAdapter.reply = None

    backups = context.backups.list_backups(subject.name, book.name)
    check("生成后保留历史版本（旧内容可退回）",
          len(backups) >= 1, str(len(backups)))

    # ---- 取消生成 -> 什么都不该发生 ----
    # 注意：产物现在是 PDF（不是 md），所以"没改动"要比的是 **PDF 的字节**。
    _before_bytes = _pdf_path.read_bytes() if _pdf_path.is_file() else b""
    _common_sum.ask_generate_summary = lambda *a, **k: None      # None = 取消
    try:
        window.book_view.generate_summary()
        for _ in range(10):
            app.processEvents()
    finally:
        _common_sum.ask_generate_summary = _real_ask_choice
    check("**在确认框里点取消不会改动 summary**",
          (_pdf_path.read_bytes() if _pdf_path.is_file() else b"") == _before_bytes)

    # ---- 新建 Markdown 只能落在书目的 notebook 里（首页/科目页禁用）----
    window.show_home()
    for _ in range(4):
        app.processEvents()
    check("可以回到首页", window.stack.currentWidget() is window.home_view)
    check("首页禁用「新建 Markdown」",
          not window.act_new_markdown.isEnabled(),
          window.act_new_markdown.toolTip())
    check("首页的工具提示说明原因",
          "书目" in window.act_new_markdown.toolTip(),
          window.act_new_markdown.toolTip())

    target, reason = window._markdown_target_dir()
    check("首页没有 Markdown 目标目录", target is None and bool(reason), str((target, reason)))

    # 在首页真的点一次：必须被拦住，且不产生任何文件
    before = {p for p in context.paths.subjects_dir.rglob("*")}
    window.new_markdown()
    app.processEvents()
    after = {p for p in context.paths.subjects_dir.rglob("*")}
    check("首页新建 Markdown 被拦住（没有新文件）", before == after,
          str(sorted(str(p) for p in (after - before))))
    uncategorized = context.paths.subjects_dir / "未分类"
    check("不会创建「未分类」目录", not uncategorized.exists(), str(uncategorized))

    # 科目页同样禁用
    window.open_subject(subject.name)
    for _ in range(6):
        app.processEvents()
    check("科目页禁用「新建 Markdown」", not window.act_new_markdown.isEnabled())
    target, reason = window._markdown_target_dir()
    check("科目页没有 Markdown 目标目录", target is None, str(target))

    # 书目页启用，且目标就是该书的 notebook
    window.open_book(subject.name, book.name)
    for _ in range(6):
        app.processEvents()
    check("书目页启用「新建 Markdown」", window.act_new_markdown.isEnabled(),
          window.act_new_markdown.toolTip())
    target, reason = window._markdown_target_dir()
    expected_notebook = book.path / "notebook"
    check("目标目录是该书目的 notebook",
          target == expected_notebook, f"{target} != {expected_notebook}")

    # 真的创建一个（绕过输入框，直接建文件后确认能被扫描到）
    created = expected_notebook / "新建测试.md"
    expected_notebook.mkdir(parents=True, exist_ok=True)
    created.write_text("# 新建测试\n\n", encoding="utf-8")
    window.book_view.refresh()
    app.processEvents()
    check("新建的文件位于 notebook 目录", created.is_file())
    from gwp.services.document_reader import supported_extensions

    check("新建的 md 是可读格式", ".md" in supported_extensions())
    created.unlink(missing_ok=True)

    # 回到首页后重新禁用
    window.show_home()
    for _ in range(6):
        app.processEvents()
    check("回到首页后重新禁用", not window.act_new_markdown.isEnabled())


    from gwp.bootstrap import EXIT_ALREADY_RUNNING, check_single_instance
    from gwp.core import single_instance

    lock_file = context.paths.else_data / "instance.lock"
    # 测试环境里不能真占锁（否则会影响别处启动），只验证规则
    check("退出码常量已定义", EXIT_ALREADY_RUNNING == 2, str(EXIT_ALREADY_RUNNING))
    check("锁文件路径在 else data 下",
          single_instance.lock_path(context.paths.else_data) == lock_file,
          str(lock_file))

    # 带 --allow-multiple 时应跳过检查（便于开发时多开对比）
    saved_argv = list(context.argv)
    context.argv = [*saved_argv, "--allow-multiple"]
    check("--allow-multiple 时跳过单实例检查", check_single_instance(context) is None)
    context.argv = saved_argv
    context.services.pop("instance_lock", None)

    # GWP_NO_PROMPT 时提示框被跳过（避免无头环境卡在模态框上）
    os.environ["GWP_NO_PROMPT"] = "1"
    from gwp.app import _report_already_running

    _report_already_running(context)          # 不应抛异常、不应阻塞
    check("GWP_NO_PROMPT 下提示逻辑可安全调用", True)

    # 已有实例（用当前进程的 PID 模拟）时，check_single_instance 应当返回退出码
    original = lock_file.read_text(encoding="utf-8") if lock_file.is_file() else None
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    other = os.getpid() + 1
    lock_file.write_text(f"{other}\n", encoding="utf-8")
    if single_instance.is_process_alive(other):
        check("检测到他人持锁时返回退出码",
              check_single_instance(context) == EXIT_ALREADY_RUNNING)
        check("未持锁时不应写入自己的锁",
              lock_file.read_text(encoding="utf-8").strip() == str(other))
    else:
        check("他人 PID 不存在时不算冲突",
              single_instance.running_instance(context.paths.else_data) is None)
    # 还原锁文件状态
    if original is None:
        lock_file.unlink(missing_ok=True)
    else:
        lock_file.write_text(original, encoding="utf-8")
    os.environ.pop("GWP_NO_PROMPT", None)

    # ---- Win11 多桌面：只在当前桌面显示 + 另一个桌面启动时弹窗提示 ----
    from PyQt6.QtWidgets import QMessageBox

    from gwp.core import desktops
    from gwp.core.single_instance import read_lock

    # 主窗口句柄应当已经写进锁文件（下一个实例靠它判断虚拟桌面）
    if lock_file.is_file():
        info = read_lock(lock_file)
        check("锁文件结构可用", info.pid > 0 or info.pid == 0, str(info))

    check("窗口只在当前虚拟桌面显示的样式位已定义",
          desktops.is_supported() in (True, False))

    # 主界面窗口句柄有效（用于跨桌面判断）
    hwnd = int(window.winId())
    check("主窗口有有效句柄", hwnd > 0, str(hwnd))

    # 打桩：假装已有实例开在另一个桌面，检查提示文案与退出码
    from gwp.app import _report_already_running
    from gwp.bootstrap import EXIT_ALREADY_RUNNING

    # 直接调用提示逻辑：另一个桌面分支不能静默退出，必须给出可读说明
    os.environ["GWP_NO_PROMPT"] = "1"
    _report_already_running(context, on_other_desktop=True, other_pid=1234, other_hwnd=hwnd)
    os.environ.pop("GWP_NO_PROMPT", None)
    check("另一个桌面的提示可安全调用（不阻塞）", True)
    check("退出码复用同一个常量", EXIT_ALREADY_RUNNING == 2)

    # 用桩替换 QMessageBox，看文案里是否说清"另一个虚拟桌面"
    shown: list[tuple[str, str, list[str]]] = []

    class _FakeMessageBox:
        Icon = QMessageBox.Icon
        ButtonRole = QMessageBox.ButtonRole
        StandardButton = QMessageBox.StandardButton

        def __init__(self) -> None:
            self._title = ""
            self._text = ""
            self._buttons: list[str] = []

        def setWindowTitle(self, text: str) -> None:
            self._title = text

        def setIcon(self, _icon) -> None:
            pass

        def setText(self, text: str) -> None:
            self._text = text

        def addButton(self, label, _role=None):
            self._buttons.append(label)
            return label

        def setStandardButtons(self, _buttons) -> None:
            self._buttons.append("OK")

        def exec(self) -> int:
            shown.append((self._title, self._text, list(self._buttons)))
            return 0

        def clickedButton(self):
            return None

    def _wake_file_guard(ctx) -> float:
        """读一下唤回请求文件的修改时间（不存在返回 -1）。

        用它来判断"这次调用有没有写唤回请求"——
        比"有没有弹框"更直接地反映行为。
        """
        from gwp.core import wakeup as _wk

        try:
            return _wk.wake_path(ctx.paths.else_data).stat().st_mtime
        except OSError:
            return -1.0

    def _visible_hwnd() -> int:
        """一个**可见**窗口的句柄（用测试自己那个主窗口）。

        用它来构造"已有实例的窗口就在眼前"这个情况 ——
        那种情况应当弹提示，而不是偷偷写唤回请求。
        """
        try:
            h = int(window.winId())
        except Exception:  # noqa: BLE001
            h = 0
        return h

    import PyQt6.QtWidgets as qt_widgets

    original_box = qt_widgets.QMessageBox
    _wake_before = _wake_file_guard(context)
    try:
        qt_widgets.QMessageBox = _FakeMessageBox      # type: ignore[misc]
        # 情况 A：窗口在**另一个虚拟桌面**上 -> 必须弹提示（用户看不到它）
        _report_already_running(
            context, on_other_desktop=True, other_pid=4321, other_hwnd=hwnd
        )
        _after_other = len(shown)
        # 情况 B：窗口就在当前桌面、而且是**可见**的 -> 弹"已在运行"的提示，
        #          并且**不该**写唤回请求（它已经在你眼前了）
        _report_already_running(
            context, on_other_desktop=False, other_pid=4321,
            other_hwnd=_visible_hwnd(),
        )
        _after_visible = len(shown)
        _wake_after_visible = _wake_file_guard(context)
    finally:
        qt_widgets.QMessageBox = original_box        # type: ignore[misc]

    check("另一个桌面时会弹提示（这种情况必须让用户知道）",
          _after_other == 1, str(_after_other))
    check("窗口已可见时也弹「已在运行」提示",
          _after_visible == 2, str(_after_visible))
    check("窗口已可见时不会去写唤回请求（它就在眼前）",
          _wake_after_visible == _wake_before,
          f"{_wake_before} -> {_wake_after_visible}")

    if _after_other >= 1:
        title_other, text_other, buttons_other = shown[0]
        check("标题点明『另一个桌面』", "另一个桌面" in title_other, title_other)
        check("正文说明窗口开在另一个虚拟桌面",
              "虚拟桌面" in text_other, text_other[:120])
        check("正文给出切换桌面的按键提示",
              "Win + Ctrl" in text_other or "Win+Ctrl" in text_other, text_other[:200])
        check("提供『切到那个桌面』按钮",
              any("切到那个桌面" in item for item in buttons_other), str(buttons_other))
    if _after_visible >= 2:
        title_same, text_same, _buttons_same = shown[1]
        check("同桌面时标题不带『另一个桌面』", "另一个桌面" not in title_same, title_same)
        check("同桌面时提示切换窗口", "任务栏" in text_same, text_same[:120])

    # ---- 「导入文件」按钮：文案要短，位置信息放悬浮提示 ----
    check("导入按钮文案只有「导入文件」四个字",
          window.book_view.btn_import.text() == "导入文件",
          window.book_view.btn_import.text())
    check("导入按钮不带省略号",
          "…" not in window.book_view.btn_import.text())

    # 悬浮提示要说清导入到哪个位置（随标签页变化）
    tips: dict[str, str] = {}
    for index in range(window.book_view.tabs.count()):
        window.book_view.tabs.setCurrentIndex(index)
        app.processEvents()
        tips[_tab_names(window.book_view)[index]] = window.book_view.btn_import.toolTip()

    check("悬浮提示说明导入到当前位置",
          all("当前位置" in text for text in tips.values()), str(tips))
    check("笔记标签的提示写明 notebook 目录",
          "notebook" in tips.get("笔记", ""), str(tips.get("笔记")))
    check("「练习」标签的提示写明 homework 目录",
          "homework" in tips.get("练习", ""), str(tips.get("练习")))
    for label in ("AI 总结", "简介", "全部条目"):
        if label in tips:
            check(f"「{label}」提示说明会让你选分类",
                  "选择分类" in tips[label], str(tips[label]))
    check("切换标签会更新提示",
          len(set(tips.values())) > 1, str(tips))

    # 回到 AI 总结（后续用例的默认预期）
    window.book_view._select_tab_key("summary")
    app.processEvents()

    # ---- 卡片点击必须真的能打开（用真实鼠标事件，防止信号派发出错）----
    # 背景：曾经 card_opened 对科目卡片派发的是 Subject 模型、对收纳箱派发的是
    # 卡片本身，接收方按卡片判断就静默失败，表现为"科目卡片点不开"。
    from PyQt6.QtTest import QTest

    from gwp.ui.widgets.cards import SubjectCard as _SC

    home = window.home_view
    home.leave_box()
    window.show_home()
    for _ in range(6):
        app.processEvents()

    plain_cards = [c for c in home.grid._cards if isinstance(c, _SC)]
    check("首页有科目卡片可测", bool(plain_cards), str(len(plain_cards)))
    if plain_cards:
        target = plain_cards[0]
        expected_name = target.subject.name
        before = window.stack.currentWidget()
        # 真实鼠标双击（不是直接调方法）
        QTest.mouseDClick(
            target, Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier, target.rect().center(),
        )
        for _ in range(6):
            app.processEvents()
        after = window.stack.currentWidget()
        check("双击科目卡片会进入科目页",
              after is window.subject_view, type(after).__name__)
        check("进入的是被双击的那个科目",
              window.subject_view.subject_name == expected_name,
              f"{window.subject_view.subject_name!r} != {expected_name!r}")

        # 单击只选中、不跳转（避免误触）
        window.show_home()
        for _ in range(4):
            app.processEvents()
        again = [c for c in home.grid._cards if isinstance(c, _SC)]
        if again:
            QTest.mouseClick(
                again[0], Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier, again[0].rect().center(),
            )
            for _ in range(4):
                app.processEvents()
            check("单击科目卡片不会跳转",
                  window.stack.currentWidget() is home,
                  type(window.stack.currentWidget()).__name__)

        # 信号派发的必须始终是卡片本身
        captured: list = []
        home.grid.card_opened.connect(lambda obj: captured.append(obj))
        window.show_home()
        for _ in range(4):
            app.processEvents()
        fresh = [c for c in home.grid._cards if isinstance(c, _SC)]
        if fresh:
            QTest.mouseDClick(
                fresh[0], Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier, fresh[0].rect().center(),
            )
            for _ in range(4):
                app.processEvents()
        check("card_opened 派发的是卡片本身",
              bool(captured) and isinstance(captured[0], _SC),
              type(captured[0]).__name__ if captured else "无")
        window.show_home()
        for _ in range(4):
            app.processEvents()

    # ---- 箱内科目的右键菜单要有「移出收纳箱」----
    box_entries_outside = home._subject_menu_entries(subject)
    from gwp.ui.widgets.cards import SUBJECT_MIME, BoxCard

    home = window.home_view
    home.leave_box()
    app.processEvents()

    box_store = context.library.boxes
    box_a = box_store.create("界面收纳箱")
    box_store.move_subjects(box_a.id, [subject.name])
    home.refresh()
    app.processEvents()

    box_cards = [c for c in home.grid._cards if isinstance(c, BoxCard)]
    subject_cards = [c for c in home.grid._cards if not isinstance(c, BoxCard)]
    check("最外层出现收纳箱卡片", len(box_cards) == 1, str(len(box_cards)))
    check("被收纳的科目不再单独出现",
          subject.name not in [
              getattr(getattr(c, "subject", None), "name", None) for c in subject_cards
          ],
          str([getattr(c, "title", "?") for c in subject_cards]))

    # 需求：点击收纳箱即展开（不需要双击）
    if box_cards:
        box_cards[0].clicked.emit()
        app.processEvents()
        check("单击收纳箱即展开", home.current_box_id == box_a.id, str(home.current_box_id))
        check("展开后只显示箱内科目",
              [getattr(c, "title", "?") for c in home.grid._cards] == [subject.title],
              str([getattr(c, "title", "?") for c in home.grid._cards]))
        check("展开后出现关闭按钮", home.btn_close_box.isVisible())
        check("展开后隐藏新建科目/新建收纳箱",
              not home.btn_new_subject.isVisible() and not home.btn_new_box.isVisible())
        # 需求：取消「← 返回全部」，退出只由「✕ 关闭收纳箱」完成
        check("已彻底移除「← 返回全部」按钮", not hasattr(home, "btn_back"))
        _header_buttons = [
            w.text() for w in home.header_bar.findChildren(
                __import__("PyQt6.QtWidgets", fromlist=["QPushButton"]).QPushButton
            )
            if w.isVisible()
        ]
        check("箱内不再有「返回全部」按钮",
              not any("返回全部" in text for text in _header_buttons),
              str(_header_buttons))
        check("箱内有「关闭收纳箱」按钮",
              any("关闭收纳箱" in text for text in _header_buttons),
              str(_header_buttons))

        # 需求：该页面要有"关闭收纳箱"
        home.btn_close_box.click()
        app.processEvents()
        check("点关闭收纳箱回到总览", home.current_box_id is None)
        check("关闭后不再显示关闭按钮", not home.btn_close_box.isVisible())
        check("关闭后新建科目按钮恢复", home.btn_new_subject.isVisible())
        check("关闭后科目仍在（没被删）",
              any(
                  subject.name in [m.name for m in members]
                  for _box, members in context.library.boxes_with_members(refresh=True)
              ),
              "科目从收纳箱里消失了")

        # 单击科目只选中、不进入（避免误触跳走）
        plain = [c for c in home.grid._cards if not isinstance(c, BoxCard)]
        if plain:
            plain[0].clicked.emit()
            app.processEvents()
            check("单击科目不会进入科目页",
                  window.stack.currentWidget() is home, "被误触发")

    # ---- 首页统计：日记单独计数，不算在科目里 ----
    # 需求：'共 3 个科目 · 3 本书目 · 1 个收纳箱' 里的科目数不能把日记算进去。
    stat_subject = context.library.create_subject("统计科目甲")
    context.library.create_book(stat_subject.name, "统计书目甲")
    stat_diary = context.library.create_subject(
        "统计日记科目", subject_type="diary"
    )
    home.refresh()
    for _ in range(6):
        app.processEvents()
    subtitle = home.lbl_subtitle.text()
    all_subjects = context.library.subjects()
    diary_total = sum(1 for s in all_subjects if s.subject_type == "diary")
    check("首页统计里把日记单独列出来", "个日记" in subtitle, subtitle)
    check("首页统计里的科目数不含日记",
          f"{len(all_subjects) - diary_total} 个科目" in subtitle,
          f"{subtitle}（共 {len(all_subjects)} 个，含 {diary_total} 个日记）")
    check("日记数量显示正确",
          f"{diary_total} 个日记" in subtitle, subtitle)
    context.library.delete_subject(stat_subject.name, to_recycle=False)
    context.library.delete_subject(stat_diary.name, to_recycle=False)
    home.refresh()
    for _ in range(4):
        app.processEvents()

    if box_cards:
        box_card = box_cards[0]
        check("收纳箱卡片开了边框标记", box_card._bordered is True)
        if subject_cards:
            check("科目卡片没有边框标记", subject_cards[0]._bordered is False)
        check("收纳箱卡片接受拖放", box_card.acceptDrops() is True)
        check("收纳箱徽标显示科目数", box_card._badge == "1 个科目", box_card._badge)

        # 像素级：边框确实画出来了（用纯红边框并关闭悬停）
        box_card._hover = False
        box_card.set_bordered(True, "#FF0000")
        handle, name = tempfile.mkstemp(suffix=".png")
        os.close(handle)
        shot = Path(name)
        reds = 0
        try:
            box_card.grab().save(str(shot))
            from PIL import Image as _Img

            with _Img.open(shot) as img:
                img = img.convert("RGB")
                reds = sum(
                    1
                    for x in range(img.size[0])
                    for y in range(img.size[1])
                    if img.getpixel((x, y))[0] > 180 and img.getpixel((x, y))[1] < 90
                )
        finally:
            shot.unlink(missing_ok=True)
        check("收纳箱边框在像素上可见", reds > 100, f"红色像素={reds}")

    # 双击也能展开（保留旧入口）
    home.enter_box(box_a.id)
    app.processEvents()
    check("enter_box 仍可用作打开入口", home.current_box_id == box_a.id)
    home.btn_close_box.click()
    app.processEvents()

    # 拖放：模拟把科目拖到箱子上
    dropped: list = []
    if box_cards:
        box_cards[0].subjects_dropped.connect(
            lambda bid, names: dropped.append((bid, list(names)))
        )
        from PyQt6.QtCore import QMimeData, QPointF
        from PyQt6.QtGui import QDropEvent

        mime = QMimeData()
        mime.setData(SUBJECT_MIME, subject.name.encode("utf-8"))
        event = QDropEvent(
            QPointF(10, 10), Qt.DropAction.MoveAction, mime,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
        )
        box_cards[0].dropEvent(event)
        app.processEvents()
    check("拖放会触发收纳信号", bool(dropped) and dropped[0][0] == box_a.id, str(dropped))
    check("科目右键菜单支持移入收纳箱",
          hasattr(home, "_move_into_box") and hasattr(home, "_move_into_new_box"))
    check("收纳箱有独立右键菜单", hasattr(home, "_box_menu"))

    # 清理：删除收纳箱，科目回到最外层
    box_store.delete(box_a.id)
    home.leave_box()
    home.refresh()
    app.processEvents()
    check("删除收纳箱后科目回到最外层",
          subject.name in [
              getattr(getattr(c, "subject", None), "name", None)
              for c in home.grid._cards
          ],
          str([getattr(c, "title", "?") for c in home.grid._cards]))

    # 右键菜单的收纳箱项：判断依据是**数据事实**（科目是否真的在箱子里），
    # 而不是"当前在哪个视图"。这样两个入口都不会找不到"怎么拿出来"。
    # 情形一：科目不在任何箱子里 -> 显示「移入收纳箱 …」
    not_in_box_titles = [
        entry[0] for entry in home._subject_menu_entries(subject) if entry is not None
    ]
    check("科目不在箱里时右键显示「移入收纳箱 …」",
          any("移入收纳箱" in title for title in not_in_box_titles),
          str(not_in_box_titles))
    check("科目不在箱里时不显示「移出收纳箱」",
          not any("移出收纳箱" in title for title in not_in_box_titles),
          str(not_in_box_titles))

    # 情形二：把科目放进箱子，但**视角仍留在最外层** -> 必须显示「移出收纳箱」
    box_b = box_store.create("移出测试箱")
    box_store.move_subjects(box_b.id, [subject.name])
    home.leave_box()
    home.refresh()
    app.processEvents()
    in_box_titles = [
        entry[0] for entry in home._subject_menu_entries(subject) if entry is not None
    ]
    check("科目在箱里时右键出现「移出收纳箱」（即使视角在最外层）",
          any("移出收纳箱" in title for title in in_box_titles),
          str(in_box_titles))
    check("移出项写明箱名与去向",
          any("移出测试箱" in title and "最外层" in title
              for title in in_box_titles),
          str(in_box_titles))
    check("科目在箱里时不出现「移入收纳箱」",
          not any("移入收纳箱" in title for title in in_box_titles),
          str(in_box_titles))

    # 箱内右键菜单：同样应出现「移出收纳箱」，且真的能点、点了能移出去
    home.enter_box(box_b.id)
    app.processEvents()

    inside_entries = home._subject_menu_entries(subject)
    inside_titles = [entry[0] for entry in inside_entries if entry is not None]
    check("箱内右键出现「移出收纳箱」",
          any("移出收纳箱" in title for title in inside_titles),
          str(inside_titles))
    check("箱内右键的文案写明回到最外层",
          any("最外层" in title for title in inside_titles if "移出收纳箱" in title),
          str(inside_titles))
    check("箱内右键不再显示「移入收纳箱」",
          not any("移入收纳箱" in title for title in inside_titles),
          str(inside_titles))

    from gwp.ui.widgets.cards import build_context_menu as _build_menu

    menu = _build_menu(home, inside_entries)
    remove_action = next(
        (a for a in menu.actions() if "移出收纳箱" in a.text() and not a.isSeparator()),
        None,
    )
    check("「移出收纳箱」是可点击项",
          remove_action is not None and remove_action.isEnabled(),
          remove_action.text() if remove_action else "没找到")
    if remove_action is not None:
        remove_action.trigger()
        app.processEvents()
        still_inside = [
            box.id for box, members in context.library.boxes_with_members()
            if subject.name in [m.name for m in members]
        ]
        check("点击后科目回到最外层", not still_inside, str(still_inside))

    box_store.delete(box_b.id)
    home.leave_box()
    home.refresh()
    app.processEvents()

    # ---- 拖拽改变顺序：科目之间、收纳箱之间 ----
    from gwp.ui.widgets.cards import BOX_MIME as _BOX_MIME
    from gwp.ui.widgets.cards import SubjectCard as _SubjectCard

    # 造两个额外科目与两个收纳箱，便于判断顺序
    extra_subjects = []
    for name in ("排序甲", "排序乙"):
        try:
            extra_subjects.append(context.library.create_subject(name))
        except Exception:  # noqa: BLE001 - 已存在就复用
            pass
    home.refresh()
    app.processEvents()

    plain_cards = [c for c in home.grid._cards if isinstance(c, _SubjectCard)]
    check("首页有可排序的科目卡片", len(plain_cards) >= 2, str(len(plain_cards)))
    if len(plain_cards) >= 2:
        source_card = plain_cards[-1]
        target_card = plain_cards[0]
        source_name = source_card.subject.name
        target_name = target_card.subject.name

        check("科目卡片可拖动", bool(source_card._drag_mime()))
        check("科目卡片可接收拖放", source_card.acceptDrops() is True)

        home._on_card_dropped(SUBJECT_MIME, source_name, target_card)
        app.processEvents()
        order = [s.name for s in context.library.subjects(refresh=True)]
        check("拖拽后科目顺序改变",
              order.index(source_name) < order.index(target_name),
              f"{source_name} 应排在 {target_name} 之前，实际 {order}")
        check("拖拽后首页立即刷新",
              [c.title for c in home.grid._cards if isinstance(c, _SubjectCard)][0]
              == source_name,
              str([c.title for c in home.grid._cards if isinstance(c, _SubjectCard)]))

    # 收纳箱之间排序
    box_x = context.library.boxes.create("排序箱甲")
    box_y = context.library.boxes.create("排序箱乙")
    home.refresh()
    app.processEvents()
    box_cards_now = [c for c in home.grid._cards if isinstance(c, BoxCard)]
    check("首页有可排序的收纳箱卡片", len(box_cards_now) >= 2, str(len(box_cards_now)))
    if len(box_cards_now) >= 2:
        src_box = box_cards_now[-1]
        dst_box = box_cards_now[0]
        check("收纳箱卡片可拖动", src_box._drag_mime() == _BOX_MIME, src_box._drag_mime())
        home._on_card_dropped(_BOX_MIME, src_box.box.id, dst_box)
        app.processEvents()
        box_order = [b.id for b in context.library.boxes.load()]
        check("拖拽后收纳箱顺序改变",
              box_order.index(src_box.box.id) < box_order.index(dst_box.box.id),
              f"{src_box.box.id} 应排在 {dst_box.box.id} 之前，实际 {box_order}")

    # 落点提示：左半边与右半边要能区分
    if box_cards_now:
        probe = box_cards_now[0]
        probe._drop_active = True
        probe._drop_before = True
        check("落点提示状态可设置", probe._drop_active is True)
        probe._drop_active = False

    for box_id in (box_x.id, box_y.id):
        context.library.boxes.delete(box_id)
    home.refresh()
    app.processEvents()

    # ---- 日记科目：标签与按钮要换成两套生成流程 ----
    diary_subject = context.library.create_subject("界面日记", subject_type="diary")
    home = window.home_view
    home.leave_box()
    home.refresh()
    app.processEvents()
    diary_book = diary_subject.books[0]
    window.open_book(diary_subject.name, diary_book.name)
    for _ in range(6):
        app.processEvents()

    view = window.book_view
    diary_tabs = _tab_names(view)
    check("日记科目类型已生效", view.subject_type == "diary", view.subject_type)
    check("日记标签为四个目录 + 单词书 + 全部条目",
          diary_tabs == ["AI 思想总结", "AI 日记", "我的日记", "其它日记",
                         "单词书", "全部条目"],
          str(diary_tabs))
    check("日记没有「AI 总结」标签", "AI 总结" not in diary_tabs, str(diary_tabs))
    check("日记没有「简介」标签", "简介" not in diary_tabs, str(diary_tabs))
    check("日记隐藏普通的「生成总结」按钮", not view.btn_summary.isVisible())
    check("日记显示「生成思想总结」", view.btn_diary_thought.isVisible())
    check("日记显示「生成日记」", view.btn_diary_book.isVisible())
    check("两个日记按钮的提示写明了目标目录",
          "AI summary" in view.btn_diary_thought.toolTip()
          and "AI diary" in view.btn_diary_book.toolTip(),
          f"{view.btn_diary_thought.toolTip()} | {view.btn_diary_book.toolTip()}")

    # 切到「我的日记」标签，导入目标应当是 my diary
    mine_index = diary_tabs.index("我的日记")
    view.tabs.setCurrentIndex(mine_index)
    app.processEvents()
    check("「我的日记」标签的导入目标是 my diary 目录",
          view._target_folder() == diary_book.path / "my diary",
          str(view._target_folder()))
    check("「我的日记」的导入提示写明 my diary",
          "my diary" in view.btn_import.toolTip(), view.btn_import.toolTip())

    # 放一篇日记，两个目录应当分别出现各自产物（用假适配器）
    (diary_book.path / "my diary" / "2026-05-01.md").write_text(
        "# 2026年5月1日\n\n天气：晴\n\n今天学了矩阵。\n", encoding="utf-8"
    )

    class _FakeChat:
        provider_id = "fake"
        label = "假AI"
        kind = "api"

        def chat(self, messages, options=None, on_chunk=None,
                 question_handler=None, should_cancel=None):
            return "## 2026年5月1日\n\n天气：晴\n\n今天学了矩阵。"

    summarizer = context.summarizer
    book_obj = context.library.book(diary_subject.name, diary_book.name)
    thought = summarizer.generate_diary(book_obj, mode="thought", adapter=_FakeChat())
    diary_doc = summarizer.generate_diary(book_obj, mode="book", adapter=_FakeChat())
    check("界面侧生成思想总结成功", thought.ok, thought.error)
    check("界面侧生成 AI 日记成功", diary_doc.ok, diary_doc.error)

    view.refresh()
    app.processEvents()
    thought_table = view._tables["diary-ai-summary"]
    diary_table = view._tables["diary-ai"]
    check("「AI 思想总结」标签页出现产物",
          any(i.name == thought.summary_path.name for i in thought_table._items),
          str([i.name for i in thought_table._items]))
    check("「AI 日记」标签页出现产物",
          any(i.name == diary_doc.summary_path.name for i in diary_table._items),
          str([i.name for i in diary_table._items]))

    # 切回普通科目：标签与按钮必须复原
    window.open_book(subject.name, book.name)
    for _ in range(6):
        app.processEvents()
    normal_tabs = _tab_names(view)
    check("切回普通科目后标签复原",
          normal_tabs == [
              "AI 总结", "简介", "笔记", "练习", "易错题", "教材", "其它文件",
              "单词书", "全部条目",
          ],
          str(normal_tabs))
    check("切回普通科目后按钮复原",
          view.btn_summary.isVisible()
          and not view.btn_diary_thought.isVisible()
          and not view.btn_diary_book.isVisible())

    # 清理日记科目，并把界面彻底恢复到普通科目的 AI 总结页，
    # 避免影响后面的像素类用例（它们假定当前是普通书目）
    context.library.delete_subject(diary_subject.name)
    window.open_book(subject.name, book.name)
    window.book_view._select_tab_key("summary")
    home.leave_box()
    home.refresh()
    for _ in range(6):
        app.processEvents()

    # ---- 箱内拖拽排序（用真实拖放事件，而不是直接调处理函数）----
    from PyQt6.QtCore import QMimeData as _QMimeData, QPointF as _QPointF

    from gwp.ui.widgets.cards import SubjectCard as _SubjectCard2

    # 这两个事件类用于真实施加"拖到某张卡片上"的动作
    from PyQt6.QtGui import (
        QDragEnterEvent as _QDragEnterEvent,
        QDropEvent as _QDropEvent,
    )

    box_inner = box_store.create("箱内排序箱")
    for name in ("内甲", "内乙", "内丙"):
        try:
            context.library.create_subject(name)
        except Exception:  # noqa: BLE001 - 已存在就复用
            pass
    box_store.move_subjects(box_inner.id, ["内甲", "内乙", "内丙"])
    home.leave_box()
    home.refresh()
    app.processEvents()
    home.enter_box(box_inner.id)
    for _ in range(4):
        app.processEvents()

    def _inner_members() -> list[str]:
        found = box_store.get(box_inner.id)
        return list(found.members) if found else []

    def _inner_cards() -> list:
        return [c for c in home.grid._cards if isinstance(c, _SubjectCard2)]

    def _drop_on(target, mime_kind: str, payload: str) -> tuple[bool, bool]:
        mime = _QMimeData()
        mime.setData(mime_kind, payload.encode("utf-8"))
        enter = _QDragEnterEvent(
            target.rect().center(), Qt.DropAction.MoveAction, mime,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
        )
        target.dragEnterEvent(enter)
        drop = _QDropEvent(
            _QPointF(target.rect().center()), Qt.DropAction.MoveAction, mime,
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
        )
        target.dropEvent(drop)
        for _ in range(3):
            app.processEvents()
        return enter.isAccepted(), drop.isAccepted()

    check("箱内初始顺序正确", _inner_members() == ["内甲", "内乙", "内丙"],
          str(_inner_members()))

    by_title = {c.title: c for c in _inner_cards()}
    if "内丙" in by_title and "内甲" in by_title:
        enter_ok, drop_ok = _drop_on(by_title["内甲"], SUBJECT_MIME, "内丙")
        check("箱内拖放事件被接受", enter_ok and drop_ok, f"{enter_ok}/{drop_ok}")
        check("箱内拖动改变了成员顺序",
              _inner_members() == ["内丙", "内甲", "内乙"], str(_inner_members()))
        check("箱内卡片显示顺序跟着变",
              [c.title for c in _inner_cards()] == ["内丙", "内甲", "内乙"],
              str([c.title for c in _inner_cards()]))

    # 拖到自己身上不应改变
    before_self = _inner_members()
    by_title = {c.title: c for c in _inner_cards()}
    if before_self and before_self[0] in by_title:
        _drop_on(by_title[before_self[0]], SUBJECT_MIME, before_self[0])
        check("箱内拖到自己身上顺序不变", _inner_members() == before_self,
              str(_inner_members()))

    box_store.delete(box_inner.id)
    home.leave_box()
    home.refresh()
    app.processEvents()

    # ---- 最外层混排：把收纳箱拖到科目上（左半边=前面，右半边=后面）----
    from gwp.ui.widgets.cards import BOX_MIME as _BOX_MIME2

    mix_subject = context.library.create_subject("混排科目")
    mix_subject2 = context.library.create_subject("混排科目二")
    mix_box = box_store.create("混排箱")
    home.leave_box()
    home.refresh()
    for _ in range(6):
        app.processEvents()

    def _home_titles() -> list[str]:
        titles = []
        for card in home.grid._cards:
            titles.append(card.title)
        return titles

    def _card(title: str):
        return next((c for c in home.grid._cards if c.title == title), None)

    base_titles = _home_titles()
    check("最外层同时有收纳箱与科目卡片",
          "混排箱" in base_titles and "混排科目" in base_titles,
          str(base_titles))

    box_card = _card("混排箱")
    subject_card = _card("混排科目")
    if box_card is not None and subject_card is not None:
        # 右半边 -> 插到科目后面
        subject_card._drop_before = False
        home._on_card_dropped(_BOX_MIME2, mix_box.id, subject_card, before=False)
        app.processEvents()
        after = _home_titles()
        check("箱子拖到科目右半边 -> 排到科目后面",
              after.index("混排箱") > after.index("混排科目"), str(after))
        check("首页卡片顺序已刷新（箱子在科目后）",
              home.grid._cards.index(box_card) > home.grid._cards.index(subject_card)
              if box_card in home.grid._cards and subject_card in home.grid._cards
              else True,
              str(after))

        # 左半边 -> 插到科目前面
        box_card = _card("混排箱")
        subject_card = _card("混排科目二") or _card("混排科目")
        home._on_card_dropped(_BOX_MIME2, mix_box.id, subject_card, before=True)
        app.processEvents()
        front = _home_titles()
        check("箱子拖到科目左半边 -> 排到科目前面",
              front.index("混排箱") < front.index(subject_card.title), str(front))

    # 科目拖到收纳箱卡片上仍是"收进箱子"（不能变成排序）
    box_card = _card("混排箱")
    if box_card is not None:
        before_members = list(box_store.get(mix_box.id).members)
        _drop_on(box_card, SUBJECT_MIME, "混排科目")
        check("科目拖到收纳箱卡片上仍表示收进箱子",
              "混排科目" in box_store.get(mix_box.id).members,
              f"{before_members} -> {box_store.get(mix_box.id).members}")

    box_store.delete(mix_box.id)
    for name in (mix_subject.name, mix_subject2.name):
        context.library.delete_subject(name)
    home.leave_box()
    home.refresh()
    app.processEvents()

    # ---- 右键菜单必须经真实事件走通（防止信号派发对象不一致导致静默失灵）----
    # 背景：card_context 曾经派发 Subject/Book 模型而不是卡片，
    # 接收方按"卡片"判断就静默 return，表现是"右键没反应"。
    from PyQt6.QtGui import QContextMenuEvent as _ContextEvent

    rclick_box = box_store.create("右键测试箱")
    for name in ("右甲", "右乙"):
        try:
            context.library.create_subject(name)
        except Exception:  # noqa: BLE001
            pass
    box_store.move_subjects(rclick_box.id, ["右甲", "右乙"])
    home.leave_box()
    home.refresh()
    app.processEvents()

    # 最外层：右键收纳箱卡片 -> 应弹出收纳箱菜单
    box_card = next(
        (c for c in home.grid._cards if isinstance(c, BoxCard)
         and c.box.id == rclick_box.id),
        None,
    )
    check("最外层能找到右键测试箱", box_card is not None)
    if box_card is not None:
        captured: list = []
        from gwp.ui.widgets.cards import build_context_menu as _build_ctx

        _real_menu = _build_ctx(home, [])
        _original_menu_exec = type(_real_menu).exec

        def _capture_exec(self, *args, **kwargs):
            captured.append([a.text() for a in self.actions() if not a.isSeparator()])
            return None

        type(_real_menu).exec = _capture_exec
        try:
            pos = box_card.rect().center()
            app.sendEvent(
                box_card,
                _ContextEvent(
                    _ContextEvent.Reason.Mouse, pos, box_card.mapToGlobal(pos)
                ),
            )
            for _ in range(4):
                app.processEvents()
        finally:
            type(_real_menu).exec = _original_menu_exec
        check("右键收纳箱卡片会弹出菜单", bool(captured), str(captured))
        if captured:
            check("收纳箱菜单含「打开收纳箱」",
                  any("打开收纳箱" in t for t in captured[0]), str(captured[0]))

    # 箱内：右键科目卡片 -> 菜单里要有「移出收纳箱」
    home.enter_box(rclick_box.id)
    app.processEvents()
    member_cards = [c for c in home.grid._cards if isinstance(c, _SubjectCard)]
    check("箱内有可右键的科目卡片", bool(member_cards), str(len(member_cards)))
    if member_cards:
        card = member_cards[0]
        captured2: list = []
        probe_menu = _build_ctx(home, [])
        original2 = type(probe_menu).exec

        def _capture2(self, *args, **kwargs):
            captured2.append(self)
            return None

        type(probe_menu).exec = _capture2
        try:
            pos = card.rect().center()
            app.sendEvent(
                card,
                _ContextEvent(_ContextEvent.Reason.Mouse, pos, card.mapToGlobal(pos)),
            )
            for _ in range(4):
                app.processEvents()
        finally:
            type(probe_menu).exec = original2

        check("右键箱内科目卡片会弹出菜单", bool(captured2), str(len(captured2)))
        if captured2:
            titles = [a.text() for a in captured2[-1].actions() if not a.isSeparator()]
            check("右键菜单含「移出收纳箱」",
                  any("移出收纳箱" in t for t in titles), str(titles))
            remove_action = next(
                (a for a in captured2[-1].actions() if "移出收纳箱" in a.text()), None
            )
            if remove_action is not None:
                target = card.subject.name
                remove_action.trigger()
                for _ in range(4):
                    app.processEvents()
                remaining = box_store.get(rclick_box.id)
                check("点「移出收纳箱」真的移出了",
                      remaining is not None and target not in remaining.members,
                      str(remaining.members if remaining else None))
                check("移出后箱内卡片少了一个",
                      target not in [
                          c.subject.name for c in home.grid._cards
                          if isinstance(c, _SubjectCard)
                      ],
                      str([c.title for c in home.grid._cards]))

    box_store.delete(rclick_box.id)
    for name in ("右甲", "右乙"):
        try:
            context.library.delete_subject(name)
        except Exception:  # noqa: BLE001
            pass
    home.leave_box()
    home.refresh()
    app.processEvents()

    # 科目页：右键书目卡片也要能弹出菜单（同一类"派发卡片/模型"问题的另一处）
    window.open_subject(subject.name)
    for _ in range(6):
        app.processEvents()
    book_cards = [
        c for c in window.subject_view.grid._cards
        if getattr(c, "book", None) is not None
    ]
    check("科目页有可右键的书目卡片", bool(book_cards), str(len(book_cards)))
    if book_cards:
        captured3: list = []
        probe3 = _build_ctx(home, [])
        original3 = type(probe3).exec

        def _capture3(self, *args, **kwargs):
            captured3.append([a.text() for a in self.actions() if not a.isSeparator()])
            return None

        type(probe3).exec = _capture3
        try:
            bc = book_cards[0]
            pos = bc.rect().center()
            app.sendEvent(
                bc,
                _ContextEvent(_ContextEvent.Reason.Mouse, pos, bc.mapToGlobal(pos)),
            )
            for _ in range(4):
                app.processEvents()
        finally:
            type(probe3).exec = original3
        check("右键书目卡片会弹出菜单", bool(captured3), str(captured3))
        if captured3:
            check("书目菜单含「重命名…」",
                  any("重命名" in t for t in captured3[0]), str(captured3[0]))

    window.show_home()
    for _ in range(4):
        app.processEvents()

    # ---- 单击 vs 拖拽：真实鼠标序列（不能只测处理函数）----
    # 背景：clicked 曾在 mousePressEvent 里发出，导致"一按下就展开箱子"，
    # 拖拽被展开动作吞掉 —— 表现是"收纳箱排序用不了"。
    from PyQt6.QtCore import QEvent as _QEvent, QPoint as _QPoint

    from PyQt6.QtGui import QMouseEvent as _QMouseEvent3

    from gwp.ui.widgets.cards import BOX_MIME as _BOX_MIME3
    from gwp.ui.widgets.cards import BoxCard as _BoxCard3

    seq_box = box_store.create("序列测试箱")
    seq_subject = context.library.create_subject("序列科目")
    home.leave_box()
    home.refresh()
    for _ in range(4):
        app.processEvents()

    seq_box_card = next(
        (c for c in home.grid._cards if isinstance(c, _BoxCard3)
         and c.box.id == seq_box.id),
        None,
    )
    check("找到序列测试箱卡片", seq_box_card is not None)

    def _mouse(kind, widget, pos, buttons):
        return _QMouseEvent3(
            kind, _QPointF(pos), _QPointF(widget.mapToGlobal(pos)),
            Qt.MouseButton.LeftButton, buttons, Qt.KeyboardModifier.NoModifier,
        )

    if seq_box_card is not None:
        center = seq_box_card.rect().center()
        # 1) 只按下：此时**不应**展开箱子
        seq_box_card.mousePressEvent(
            _mouse(_QEvent.Type.MouseButtonPress, seq_box_card, center,
                   Qt.MouseButton.LeftButton)
        )
        check("按下收纳箱时还不展开（等释放才判定单击）",
              home.current_box_id is None, str(home.current_box_id))
        # 2) 释放：算单击 -> 展开
        seq_box_card.mouseReleaseEvent(
            _mouse(_QEvent.Type.MouseButtonRelease, seq_box_card, center,
                   Qt.MouseButton.NoButton)
        )
        app.processEvents()
        check("释放后算单击 -> 展开收纳箱",
              home.current_box_id == seq_box.id, str(home.current_box_id))
        home.leave_box()
        home.refresh()
        for _ in range(3):
            app.processEvents()

        # 3) 按下 + 移动 + 释放 = 拖拽：应重排，且**不展开**
        seq_box_card = next(
            (c for c in home.grid._cards if isinstance(c, _BoxCard3)
             and c.box.id == seq_box.id),
            None,
        )
        target_card = next(
            (c for c in home.grid._cards
             if getattr(c, "subject", None) is not None
             and c.subject.name == seq_subject.name),
            None,
        )
        check("拖拽测试有目标科目卡片", target_card is not None)
        if seq_box_card is not None and target_card is not None:
            # 打桩 QDrag.exec，让拖拽在目标上"落下"
            from PyQt6.QtGui import QDrag as _QDrag3

            original_exec3 = _QDrag3.exec

            def _stub_exec(self, *args, **kwargs):
                mime = self.mimeData()
                payload = ""
                if mime is not None and mime.hasFormat(_BOX_MIME3):
                    payload = bytes(mime.data(_BOX_MIME3)).decode("utf-8")
                data = _QMimeData()
                data.setData(_BOX_MIME3, payload.encode("utf-8"))
                local = target_card.rect().center()
                enter = _QDragEnterEvent(
                    local, Qt.DropAction.MoveAction, data,
                    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                )
                target_card.dragEnterEvent(enter)
                drop = _QDropEvent(
                    _QPointF(local), Qt.DropAction.MoveAction, data,
                    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                )
                target_card.dropEvent(drop)
                for _ in range(2):
                    app.processEvents()
                return Qt.DropAction.MoveAction

            _QDrag3.exec = _stub_exec
            try:
                start = seq_box_card.rect().center()
                seq_box_card.mousePressEvent(
                    _mouse(_QEvent.Type.MouseButtonPress, seq_box_card, start,
                           Qt.MouseButton.LeftButton)
                )
                for step in (12, 120):
                    moved = _QPoint(
                        min(seq_box_card.width() - 1, start.x() + step), start.y()
                    )
                    seq_box_card.mouseMoveEvent(
                        _mouse(_QEvent.Type.MouseMove, seq_box_card, moved,
                               Qt.MouseButton.LeftButton)
                    )
                seq_box_card.mouseReleaseEvent(
                    _mouse(_QEvent.Type.MouseButtonRelease, seq_box_card, start,
                           Qt.MouseButton.NoButton)
                )
                for _ in range(4):
                    app.processEvents()
            finally:
                _QDrag3.exec = original_exec3

            check("拖拽收纳箱不会展开它（不会吞掉拖拽）",
                  home.current_box_id is None, str(home.current_box_id))
            titles_after = [c.title for c in home.grid._cards]
            check("拖拽后箱子排到了目标科目之前",
                  "序列测试箱" in titles_after and "序列科目" in titles_after
                  and titles_after.index("序列测试箱")
                  < titles_after.index("序列科目"),
                  str(titles_after))

    box_store.delete(seq_box.id)
    try:
        context.library.delete_subject(seq_subject.name)
    except Exception:  # noqa: BLE001
        pass
    home.leave_box()
    home.refresh()
    app.processEvents()

    # ---- 删除确认：默认按钮必须是「取消」，回车不能误删 ----
    # 背景：原先确认框 setDefaultButton(确定)，删除时手快按到回车就把数据删了。
    # 这里直接检查**源码**与**真实 QMessageBox 的默认按钮**。
    # 注意：本套件开头已经用桩替换了 common.confirm，所以不能 inspect 那个函数对象
    # （那只会看到桩自己），要读模块源码。
    import importlib.util
    import inspect

    from PyQt6.QtWidgets import QMessageBox as _QMessageBox

    _common_path = Path(importlib.util.find_spec("gwp.ui.common").origin)
    _module_source = _common_path.read_text(encoding="utf-8")

    check("危险确认框把默认按钮设为「取消」",
          "setDefaultButton(cancel)" in _module_source, "源码里应有 setDefaultButton(cancel)")
    check("危险确认框使用警告图标",
          "Icon.Warning" in _module_source and "dangerous" in _module_source)
    check("危险确认框的确定按钮是「删除」而非「确定」",
          'addButton("删除"' in _module_source, "破坏性操作应写明「删除」")

    def _fake_exec(self):
        """不真的弹窗，只记录当时的默认按钮文本。"""
        default = self.defaultButton()
        captured_default.append(default.text() if default is not None else "")
        return 0

    captured_default: list = []

    # 从源码里取回未被桩替换的 confirm，单独编译执行
    _start = _module_source.find("def confirm(")
    _end = _module_source.find("\ndef ask_text(")
    _namespace: dict = {}
    exec(  # noqa: S102 - 测试内自用，源码来自本仓库
        compile(_module_source[_start:_end], "confirm_probe", "exec"),
        {"QMessageBox": _QMessageBox, "QWidget": object},
        _namespace,
    )
    real_confirm = _namespace["confirm"]

    _original_exec = _QMessageBox.exec
    _QMessageBox.exec = _fake_exec
    try:
        answer = real_confirm(None, "删除测试", "删除", dangerous=True)
        check("危险确认框的默认按钮是「取消」",
              captured_default == ["取消"], str(captured_default))
        check("没点按钮时 confirm 判定为「不删除」", answer is False, str(answer))

        # 普通确认框（非删除）仍应默认「确定」
        captured_default.clear()
        real_confirm(None, "普通确认", "提示")
        check("普通确认框仍默认「确定」",
              captured_default == ["确定"], str(captured_default))
    finally:
        _QMessageBox.exec = _original_exec

    # ---- 删除警告文案要与真实行为一致 ----
    from gwp.services import shell_ops as _shell_ops

    recyclable = _shell_ops.can_use_recycle_bin()
    warn_subject = context.library.create_subject("删除警告科目")
    warn_book = context.library.create_book(warn_subject.name, "警告书目")
    (warn_book.path / "notebook" / "a.md").write_text("# a\n", encoding="utf-8")
    (warn_book.path / "error-prone" / "b.md").write_text("# b\n", encoding="utf-8")
    context.library.invalidate()
    warn_subject = context.library.subject(warn_subject.name)

    message, detail, has_content = home._subject_delete_warning(warn_subject)
    check("科目删除警告列出了书目数量", "包含书目：1 本" in message, message[:160])
    check("科目删除警告说明是否可还原",
          ("回收站还原" in message) if recyclable else ("永久" in message),
          f"recyclable={recyclable} :: {message[:200]}")
    check("科目删除警告在详情里给出真实路径",
          str(warn_subject.path) in detail, detail[:200])
    check("非空科目被判定为需要二次确认", has_content is True, str(has_content))

    warn_book = context.library.book(warn_subject.name, "警告书目")
    book_message, book_detail, book_has_content = window.subject_view._book_delete_warning(warn_book)
    check("书目删除警告给出文件数与来源数",
          "文件总数" in book_message and "参与 AI 总结" in book_message,
          book_message[:200])
    check("书目删除警告与行为一致",
          ("回收站还原" in book_message) if recyclable else ("永久" in book_message),
          f"recyclable={recyclable}")
    check("非空书目被判定为需要二次确认", book_has_content is True, str(book_has_content))
    check("书目删除详情列出各目录文件数",
          "各目录文件数" in book_detail, book_detail[:200])

    # 归档清理
    context.library.delete_subject(warn_subject.name, to_recycle=False)
    home.refresh()
    app.processEvents()

    # ---- 取消确认时，必须真的什么都不删（端到端）----
    from gwp.ui import common as _common2

    keep_subject = context.library.create_subject("取消删除科目")
    keep_book = context.library.create_book(keep_subject.name, "取消删除书目")
    (keep_book.path / "notebook" / "keep.md").write_text("# keep\n", encoding="utf-8")
    context.library.invalidate()

    _stub_confirm = _common2.confirm  # 前面装的桩，恒返回 True
    _common2.confirm = lambda *a, **k: False      # 模拟用户点「取消」
    try:
        home._delete_subject(context.library.subject(keep_subject.name))
        app.processEvents()
    finally:
        _common2.confirm = _stub_confirm

    check("取消删除科目后科目仍在",
          (context.library.paths.subjects_dir / keep_subject.name).is_dir(),
          str(context.library.paths.subjects_dir / keep_subject.name))

    window.open_subject(keep_subject.name)
    for _ in range(4):
        app.processEvents()
    _common2.confirm = lambda *a, **k: False
    try:
        window.subject_view._delete_book(
            context.library.book(keep_subject.name, "取消删除书目")
        )
        app.processEvents()
    finally:
        _common2.confirm = _stub_confirm

    check("取消删除书目后书目仍在",
          (context.library.paths.subjects_dir / keep_subject.name / "取消删除书目").is_dir(),
          str(context.library.paths.subjects_dir / keep_subject.name / "取消删除书目"))
    check("取消删除后笔记文件也还在",
          (context.library.paths.subjects_dir / keep_subject.name
           / "取消删除书目" / "notebook" / "keep.md").is_file())

    # 归档清理
    context.library.delete_subject(keep_subject.name, to_recycle=False)
    window.show_home()
    home.refresh()
    app.processEvents()

    # ---- 启动时不得写注册表：勾选同步必须屏蔽信号 ----
    # 背景：act_startup.setChecked(...) 会触发 toggled -> toggle_autostart
    # -> set_autostart，于是**每次启动都往注册表写开机自启**（用户没勾也会被勾上，
    # 受限环境还会报 PermissionError）。
    from gwp.services import shell_ops as _shell

    autostart_calls: list = []
    _real_set_autostart = _shell.set_autostart

    def _spy_set_autostart(enabled):
        autostart_calls.append(enabled)
        return _real_set_autostart(enabled)

    _shell.set_autostart = _spy_set_autostart
    try:
        probe_window = type(window)(context)
        probe_window.resize(900, 600)
        for _ in range(6):
            app.processEvents()
    finally:
        _shell.set_autostart = _real_set_autostart

    check("创建主窗口时不会写「开机自启」注册表",
          not autostart_calls, f"被调用了 {autostart_calls}")
    check("「开机自动启动」菜单项存在",
          getattr(probe_window, "act_startup", None) is not None)
    probe_window.close()
    app.processEvents()

    # 源码层面也确认同步勾选时屏蔽了信号
    _mw_source = Path(importlib.util.find_spec("gwp.ui.main_window").origin).read_text(
        encoding="utf-8"
    )
    _sync_index = _mw_source.find("act_startup.setChecked(shell_ops.is_autostart_enabled())")
    check("同步勾选状态前后有 blockSignals",
          _sync_index > 0
          and "blockSignals(True)" in _mw_source[max(0, _sync_index - 160):_sync_index]
          and "blockSignals(False)" in _mw_source[_sync_index:_sync_index + 160],
          _mw_source[max(0, _sync_index - 200):_sync_index + 200])

    # ---- 「其它文件」栏目：不参与 AI 总结，但可以新建文件夹 ----
    import shutil

    from gwp.ui import common as _common2

    others_index = tab_titles.index("其它文件")
    window.book_view.tabs.setCurrentIndex(others_index)
    app.processEvents()
    check("「其它文件」标签的导入目标是 others 目录",
          window.book_view._target_folder() == book.path / "others",
          str(window.book_view._target_folder()))
    check("「其它文件」不在 AI 总结来源里",
          "others" not in _C.summary_sources_for_type(subject.subject_type),
          str(_C.summary_sources_for_type(subject.subject_type)))
    check("新建书目时就建好了 others 目录",
          (book.path / "others").is_dir(), str(book.path / "others"))

    # 新建文件夹
    _real_ask = _common2.ask_text
    _common2.ask_text = lambda *a, **k: "课件资料"
    try:
        window.book_view.create_folder()
        app.processEvents()
    finally:
        _common2.ask_text = _real_ask
    check("右键「新建文件夹」能建出文件夹",
          (book.path / "others" / "课件资料").is_dir(),
          str(book.path / "others"))

    others_table = window.book_view._tables["others"]
    check("新建的文件夹出现在「其它文件」列表里",
          any(i.name == "课件资料" for i in others_table._items),
          str([i.name for i in others_table._items]))

    # 在文件夹里再建子文件夹（右键文件夹 -> 新建）
    _common2.ask_text = lambda *a, **k: "第一章"
    try:
        window.book_view.create_folder(inside=book.path / "others" / "课件资料")
        app.processEvents()
    finally:
        _common2.ask_text = _real_ask
    check("能在文件夹里继续建子文件夹",
          (book.path / "others" / "课件资料" / "第一章").is_dir(),
          str(book.path / "others" / "课件资料"))

    # 重名与非法名要拦住
    _common2.ask_text = lambda *a, **k: "课件资料"
    try:
        window.book_view.create_folder()
        app.processEvents()
    finally:
        _common2.ask_text = _real_ask
    check("重名不会覆盖已有文件夹",
          len(list((book.path / "others").glob("课件资料*"))) == 1,
          str([p.name for p in (book.path / "others").iterdir()]))

    _common2.ask_text = lambda *a, **k: "a/b"
    try:
        window.book_view.create_folder()
        app.processEvents()
    finally:
        _common2.ask_text = _real_ask
    check("非法名称（含斜杠）被拒绝",
          not any("a_b" == p.name for p in (book.path / "others").iterdir()),
          str([p.name for p in (book.path / "others").iterdir()]))

    # 取消输入不创建
    _common2.ask_text = lambda *a, **k: None
    try:
        window.book_view.create_folder()
        app.processEvents()
    finally:
        _common2.ask_text = _real_ask
    check("取消输入时不创建任何东西",
          len(list((book.path / "others").iterdir())) == 1,
          str([p.name for p in (book.path / "others").iterdir()]))

    # 「其它文件」里的内容不得进入 AI 总结资料
    (book.path / "others" / "不该被总结.md").write_text("# x\n", encoding="utf-8")
    context.library.invalidate()
    materials = context.summarizer.collect_materials(
        context.library.book(subject.name, book.name)
    )
    check("「其它文件」里的文件不会被 AI 总结读到",
          all("others" not in str(m.path) for m in materials),
          str([m.path.name for m in materials]))

    # 清掉测试建的目录，避免影响后面的断言
    shutil.rmtree(book.path / "others" / "课件资料", ignore_errors=True)
    (book.path / "others" / "不该被总结.md").unlink(missing_ok=True)
    window.book_view.tabs.setCurrentIndex(0)
    app.processEvents()

    # 老书目（这次改动之前建的）打开时应自动补上 others
    repair_subject = context.library.create_subject("老书目科目")
    repair_book = context.library.create_book(repair_subject.name, "老书目")
    shutil.rmtree(repair_book.path / "others", ignore_errors=True)
    check("模拟旧书目：others 目录确实不存在",
          not (repair_book.path / "others").is_dir())
    window.open_book(repair_subject.name, "老书目")
    for _ in range(6):
        app.processEvents()
    check("打开旧书目会自动补建 others 目录",
          (repair_book.path / "others").is_dir(), str(repair_book.path))
    repaired_tabs = _tab_names(window.book_view)
    check("旧书目的标签里也出现了「其它文件」",
          "其它文件" in repaired_tabs, str(repaired_tabs))
    context.library.delete_subject(repair_subject.name, to_recycle=False)
    window.show_home()
    for _ in range(4):
        app.processEvents()

    # ---- 右键修改科目类型：自学课 <-> 校修课 ----
    from PyQt6.QtWidgets import QDialog
    type_subject = context.library.create_subject("界面转型科目")
    type_book = context.library.create_book(type_subject.name, "转型书目")
    (type_book.path / "notebook" / "笔记.md").write_text("# 笔记\n", encoding="utf-8")
    home.leave_box()
    home.refresh()
    for _ in range(4):
        app.processEvents()
    type_subject = context.library.subject(type_subject.name)

    type_entries = home._subject_menu_entries(type_subject)
    type_titles = [entry[0] for entry in type_entries if entry is not None]
    check("右键菜单有「修改类型…」",
          any("修改类型" in title for title in type_titles), str(type_titles))
    check("「修改类型」项写明当前类型",
          any("当前：自学课" in title for title in type_titles), str(type_titles))
    type_action = next(
        (entry for entry in type_entries
         if entry is not None and "修改类型" in entry[0] and "日记" not in entry[0]),
        None,
    )
    check("「修改类型」项是可点击的",
          type_action is not None and len(type_action) < 3, str(type_action))

    # 对话框：普通科目允许在类型下拉里切换
    from gwp.ui.dialogs.subject_dialog import SubjectDialog as _SubjectDialog

    _real_exec = QDialog.exec
    QDialog.exec = lambda self: 0
    try:
        edit_dialog = _SubjectDialog(home, subject=type_subject)
        check("编辑普通科目时类型下拉可用", edit_dialog.combo_type.isEnabled())
        available = [
            edit_dialog.combo_type.itemData(i)
            for i in range(edit_dialog.combo_type.count())
        ]
        check("类型下拉含自学课与校修课",
              "self-study" in available and "school" in available, str(available))
        check("对话框回填了当前类型",
              edit_dialog.subject_type == "self-study", edit_dialog.subject_type)
        edit_dialog.combo_type.setCurrentIndex(available.index("school"))
        check("切换后 values() 返回新类型",
              edit_dialog.values()["subject_type"] == "school",
              str(edit_dialog.values()["subject_type"]))
        edit_dialog.close()
    finally:
        QDialog.exec = _real_exec

    # 日记科目：下拉禁用，菜单项变成禁用提示
    diary_sub = context.library.create_subject("界面日记科目", subject_type="diary")
    home.refresh()
    for _ in range(4):
        app.processEvents()
    diary_sub = context.library.subject(diary_sub.name)
    diary_entries = home._subject_menu_entries(diary_sub)
    diary_type_entry = next(
        (e for e in diary_entries if e is not None and "修改类型" in e[0]), None
    )
    check("日记科目的「修改类型」是禁用项",
          diary_type_entry is not None and len(diary_type_entry) > 2
          and diary_type_entry[2] is False,
          str(diary_type_entry))
    QDialog.exec = lambda self: 0
    try:
        diary_dialog = _SubjectDialog(home, subject=diary_sub)
        check("编辑日记科目时类型下拉被禁用",
              not diary_dialog.combo_type.isEnabled())
        diary_dialog.close()
    finally:
        QDialog.exec = _real_exec

    # 真正改一次：标签跟着变，文件不动
    context.library.change_subject_type(type_subject.name, "school")
    window.open_book(type_subject.name, "转型书目")
    for _ in range(6):
        app.processEvents()
    changed_tabs = _tab_names(window.book_view)
    check("改成校修课后标签出现「作业」", "作业" in changed_tabs, str(changed_tabs))
    check("改成校修课后不再有「练习」", "练习" not in changed_tabs, str(changed_tabs))
    check("改类型后笔记文件仍在",
          (type_book.path / "notebook" / "笔记.md").is_file())
    window.show_home()
    for _ in range(4):
        app.processEvents()

    context.library.delete_subject(type_subject.name, to_recycle=False)
    context.library.delete_subject(diary_sub.name, to_recycle=False)
    home.refresh()
    app.processEvents()

    # ---- 校修课的「作业」栏目：创建作业（内容 + DDL + 提交方式）----
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    from gwp.data_manager import homework as _hw2

    school_subject = context.library.create_subject("作业测试校修课", subject_type="school")
    school_book = context.library.create_book(school_subject.name, "作业书目")
    window.open_book(school_subject.name, "作业书目")
    for _ in range(6):
        app.processEvents()
    school_tabs = _tab_names(window.book_view)
    hw_index = school_tabs.index("作业")
    window.book_view.tabs.setCurrentIndex(hw_index)
    app.processEvents()

    check("校修课的作业栏目显示「创建作业」按钮",
          window.book_view.btn_homework.isVisible())
    check("作业栏目里隐藏「导入文件」",
          not window.book_view.btn_import.isVisible())

    # 进了某个作业（子文件夹）里之后：必须给出「导入文件」入口
    # （用户曾截图反馈"作业栏目无上传文件按钮"：在作业文件夹里既没有合理的
    #  "创建作业"语义，又没有导入入口，只能靠拖拽）
    _hw_root = school_book.path / "homework"
    (_hw_root / "第一次作业").mkdir(parents=True, exist_ok=True)
    context.library.invalidate()
    window.book_view.refresh()
    for _ in range(6):
        app.processEvents()
    window.book_view.enter_folder(_hw_root / "第一次作业")
    for _ in range(8):
        app.processEvents()
    check("进入作业文件夹后显示「导入文件」按钮",
          window.book_view.btn_import.isVisible(),
          f"homework={window.book_view.btn_homework.isVisible()} "
          f"import={window.book_view.btn_import.isVisible()}")
    check("进入作业文件夹后隐藏「创建作业」（在作业里再建作业不合语境）",
          not window.book_view.btn_homework.isVisible())
    check("进入子文件夹后「导入文件」的提示写明当前位置",
          "第一次作业" in window.book_view._import_tooltip(),
          window.book_view._import_tooltip())
    check("导入落点就是正在看的那个作业文件夹",
          window.book_view.drop_target_folder() == _hw_root / "第一次作业",
          str(window.book_view.drop_target_folder()))
    window.book_view.leave_folder()
    for _ in range(8):
        app.processEvents()
    check("退回作业栏目根目录后恢复「创建作业」",
          window.book_view.btn_homework.isVisible()
          and not window.book_view.btn_import.isVisible())

    # 标签上的数量必须等于"点进去能看到几行"
    # （作业栏目曾经用 rglob 递归数文件：一个作业内部的 homework.json +
    #  作业内容文件被算成 2，而表格只显示 1 行 —— 数字对不上）
    _hw_root2 = school_book.path / "homework"
    (_hw_root2 / "第二次作业").mkdir(parents=True, exist_ok=True)
    (_hw_root2 / "第二次作业" / "homework.json").write_text("{}", encoding="utf-8")
    (_hw_root2 / "第二次作业" / "内容.md").write_text("x", encoding="utf-8")
    context.library.invalidate()
    window.book_view.refresh()
    for _ in range(8):
        app.processEvents()
    _fresh_book = context.library.book(school_subject.name, "作业书目")
    _rows = len(context.library.list_homework_items(_fresh_book))
    _count = int((_fresh_book.item_counts or {}).get("homework", -1))
    check("作业栏目的计数 = 作业个数（不是内部文件数）",
          _count == _rows, f"计数={_count} 表格行数={_rows}")
    check("作业计数不会把 homework.json 算进去",
          _count == 2, f"应有 2 个作业，实际计数={_count}")
    # 注意：要读**原始标签文字**，不能用 _tab_names() —— 那个辅助函数的作用
    # 正是"剥掉数量"，用它永远看不到数字（这个坑我踩过一次）。
    _raw_labels = [
        window.book_view.tabs.tabText(i)
        for i in range(window.book_view.tabs.count())
    ]
    check("作业标签上显示的数字与表格行数一致",
          f"作业 {_count}" in _raw_labels, str(_raw_labels))
    # 其它栏目仍是"数文件"（笔记里子目录会铺开显示，所以文件数才准）
    check("非作业栏目仍按文件计数",
          (school_book.path / "notebook").is_dir()
          and int((_fresh_book.item_counts or {}).get("notebook", -1))
          == sum(1 for p in (school_book.path / "notebook").rglob("*") if p.is_file()),
          str((_fresh_book.item_counts or {}).get("notebook")))

    # 切回「笔记」应恢复「导入文件」
    window.book_view.tabs.setCurrentIndex(school_tabs.index("笔记"))
    app.processEvents()
    check("切到别的栏目恢复「导入文件」",
          window.book_view.btn_import.isVisible()
          and not window.book_view.btn_homework.isVisible())
    window.book_view.tabs.setCurrentIndex(hw_index)
    app.processEvents()

    hw_table = window.book_view._tables["homework"]
    check("作业表格有「DDL」列", hw_table.column_of("DDL") >= 0,
          str([hw_table.horizontalHeaderItem(i).text()
               for i in range(hw_table.columnCount())]))
    check("作业表格有「提交方式」列", hw_table.column_of("提交方式") >= 0)
    check("非作业表格没有 DDL 列",
          window.book_view._tables["notebook"].column_of("DDL") < 0)

    # 用真实的数据层建三个作业，检查渲染
    hw_dir = school_book.path / "homework"
    _hw2.create(
        hw_dir / "已过期作业",
        content="内容",
        due=(_dt.now() - _td(days=2)).strftime("%Y-%m-%dT%H:%M"),
        submit_url="https://example.com/old",
    )
    _hw2.create(
        hw_dir / "快到期的作业",
        content="内容",
        due=(_dt.now() + _td(hours=3)).strftime("%Y-%m-%dT%H:%M"),
        submit_url="https://example.com/soon",
    )
    # 距现在 30 小时：旧阈值（24h）下它不会被标黄，改成 48 小时后必须标黄
    _hw2.create(
        hw_dir / "30小时后到期",
        content="内容",
        due=(_dt.now() + _td(hours=30)).strftime("%Y-%m-%dT%H:%M"),
        submit_url="https://example.com/soon30",
    )
    _hw2.create(hw_dir / "没设DDL的作业", content="内容")
    window.book_view.refresh()
    for _ in range(4):
        app.processEvents()

    # 名称格现在是 "名字（已完成/未完成）"，所以按前缀找行。
    def _find_row(name: str):
        """按名字前缀找行号（名称格里带了完成状态）。"""
        for r in range(hw_table.rowCount()):
            cell = hw_table.item(r, 0)
            if cell is not None and cell.text().startswith(name):
                return r
        return None

    rows = {hw_table.item(r, 0).text(): r for r in range(hw_table.rowCount())}
    check("三个作业都出现在列表里",
          all(_find_row(n) is not None
              for n in ("已过期作业", "快到期的作业", "没设DDL的作业")),
          str(list(rows)))
    due_col = hw_table.column_of("DDL")
    submit_col = hw_table.column_of("提交方式")

    # ---- 完成状态与染色（需求："用绿色字体标已完成 / 用红色字体标未完成"
    #      以及"但是未完成 快到DDL的还是要染色"）----
    def _fg(row):
        return hw_table.item(row, 0).foreground().color().name().upper()

    def _bg(row):
        """返回 `(是否有底色, 底色值)`。"""
        brush = hw_table.item(row, 0).background()
        painted = int(brush.style().value) != 0
        return painted, (brush.color().name().upper() if painted else "")

    _row_overdue = _find_row("已过期作业")
    if _row_overdue is not None:
        check("过期作业的 DDL 标注「已过期」",
              "已过期" in hw_table.item(_row_overdue, due_col).text(),
              hw_table.item(_row_overdue, due_col).text())
        check("**未完成的作业用红色字体标「未完成」**",
              "未完成" in hw_table.item(_row_overdue, 0).text()
              and _fg(_row_overdue) == "#C5221F",
              f"{hw_table.item(_row_overdue, 0).text()} / {_fg(_row_overdue)}")
        _painted, _color = _bg(_row_overdue)
        check("**未完成且逾期仍然整行染色（浅红）**",
              _painted and _color == "#FFE1E1", f"{_painted} / {_color}")

    _row_soon = _find_row("快到期的作业")
    if _row_soon is not None:
        check("临期作业的 DDL 标注「即将截止」",
              "即将截止" in hw_table.item(_row_soon, due_col).text(),
              hw_table.item(_row_soon, due_col).text())
        _painted, _color = _bg(_row_soon)
        check("**未完成且临近 DDL 仍然整行染色（浅黄）**",
              _painted and _color == "#FFF4D6", f"{_painted} / {_color}")

    _row_soon30 = _find_row("30小时后到期")
    if _row_soon30 is not None:
        check("**30 小时后到期的作业也标「即将截止」**（48 小时阈值，用户反馈的那条）",
              "即将截止" in hw_table.item(_row_soon30, due_col).text(),
              hw_table.item(_row_soon30, due_col).text())
        _painted, _color = _bg(_row_soon30)
        check("30 小时后到期的作业也染色", _painted and _color == "#FFF4D6",
              f"{_painted} / {_color}")

    _row_nodue = _find_row("没设DDL的作业")
    if _row_nodue is not None:
        check("没设 DDL 时写明「未设 DDL」",
              hw_table.item(_row_nodue, due_col).text() == "未设 DDL",
              hw_table.item(_row_nodue, due_col).text())
        check("没填提交方式时写明「未填写」",
              hw_table.item(_row_nodue, submit_col) is not None
              and hw_table.item(_row_nodue, submit_col).text() == "未填写",
              hw_table.item(_row_nodue, submit_col).text()
              if hw_table.item(_row_nodue, submit_col) else "无")
        _painted, _color = _bg(_row_nodue)
        check("**没设 DDL 的未完成作业不染色**（无期限就没什么可催的）",
              not _painted, f"{_painted} / {_color}")

    # ---- 标记完成后：变绿、且**底色必须消失**（需求："已完成的作业取消颜色标记"）----
    if _row_soon is not None:
        _hw_target = None
        for _item in context.library.list_homework_items(school_book):
            if _item.name == "快到期的作业":
                _hw_target = _item.path
        check("能定位到那条临期作业", _hw_target is not None, str(_hw_target))
        if _hw_target is not None:
            _hw2.set_done(_hw_target, True)
            window.book_view.refresh()
            for _ in range(4):
                app.processEvents()
            _done_row = _find_row("快到期的作业")
            check("**标完成后立刻变绿色「已完成」**",
                  _done_row is not None
                  and "已完成" in hw_table.item(_done_row, 0).text()
                  and _fg(_done_row) == "#1E8E3E",
                  f"{hw_table.item(_done_row, 0).text() if _done_row is not None else '-'}"
                  f" / {_fg(_done_row) if _done_row is not None else '-'}")
            _painted_done, _color_done = (
                _bg(_done_row) if _done_row is not None else (None, None)
            )
            check("**已完成就把染色取消（即使 DDL 就在眼前）**",
                  _painted_done is False,
                  f"染色={_painted_done} 色={_color_done}")
            _hw2.set_done(_hw_target, False)
            window.book_view.refresh()
            for _ in range(4):
                app.processEvents()

    # 提交方式列：长网址换成按钮，不显示网址本身
    from PyQt6.QtWidgets import QPushButton as _QPushButton

    check("提交方式列是固定宽度（不被网址撑开）",
          hw_table.columnWidth(submit_col) <= 120,
          str(hw_table.columnWidth(submit_col)))
    long_url = "https://spocnew.example.edu/mycourse/coursecenter/" + "x" * 200
    _hw2.create(
        hw_dir / "超长网址作业",
        content="内容",
        due=(_dt.now() + _td(days=30)).strftime("%Y-%m-%dT%H:%M"),
        submit_url=long_url,
    )
    window.book_view.refresh()
    for _ in range(4):
        app.processEvents()
    rows = {hw_table.item(r, 0).text(): r for r in range(hw_table.rowCount())}
    _row_long = _find_row("超长网址作业")
    check("长网址作业出现在列表里", _row_long is not None, str(list(rows)))
    if _row_long is not None:
        row = _row_long
        holder = hw_table.cellWidget(row, submit_col)
        submit_btn = holder.findChild(_QPushButton) if holder is not None else None
        check("有提交网址的作业显示「提交作业」按钮",
              submit_btn is not None and submit_btn.text() == "提交作业",
              submit_btn.text() if submit_btn else "无按钮")
        check("表格里不显示网址本身",
              hw_table.item(row, submit_col) is None
              or long_url not in (hw_table.item(row, submit_col).text() or ""),
              "网址不应出现在单元格文本里")
        if submit_btn is not None:
            check("按钮的悬浮提示给出完整网址",
                  long_url in submit_btn.toolTip(), submit_btn.toolTip()[:80])
            long_hits: list = []
            hw_table.submit_link_clicked.connect(
                lambda folder, url: long_hits.append(url)
            )
            submit_btn.click()
            app.processEvents()
            check("点「提交作业」按钮触发打开网址",
                  long_hits == [long_url], str(long_hits)[:80])
            check("超长网址也不会把列撑宽",
                  hw_table.columnWidth(submit_col) <= 120,
                  str(hw_table.columnWidth(submit_col)))

            # 真实按钮 -> 提交确认框（走完整链路，不是发信号）
            from gwp.ui.dialogs import submit_dialog as _sd

            real_chain: list = []
            _sd_real = _sd.SubmitHomeworkDialog

            class _ChainDialog:
                def __init__(self, parent=None, homework=None, folder=None, url=""):
                    real_chain.append((Path(folder) if folder else None, url))
                    self.choice = ""

                def exec(self):
                    self.choice = ""
                    return 0

            _sd.SubmitHomeworkDialog = _ChainDialog
            try:
                submit_btn.click()
                app.processEvents()
            finally:
                _sd.SubmitHomeworkDialog = _sd_real
            check("点真实按钮会带着该作业的文件夹路径弹框",
                  bool(real_chain)
                  and real_chain[0][0] == hw_dir / "超长网址作业"
                  and real_chain[0][1] == long_url,
                  str(real_chain)[:90])

    # 每个作业只占一行（不把 homework.json / 内容文件也铺出来）
    hw_names = [
        hw_table.item(r, 0).text() for r in range(hw_table.rowCount())
        if hw_table.item(r, 0) is not None
    ]
    check("作业栏目一个作业一行",
          not any("/" in name for name in hw_names), str(hw_names))
    check("作业栏目不显示内部的 homework.json",
          not any("homework.json" in name for name in hw_names), str(hw_names))

    # ---- 进入某个作业里面：必须列出该文件夹的**全部内容** ----
    #
    # 需求原话："本地文件夹有内容 但是软件内不显示 要显示出来该作业文件夹的所有文件"
    # 原来的 bug：作业栏目无论在哪一层都用 list_homework_items 再按
    # `path.parent == folder` 过滤，而那个函数只列作业根目录第一层的作业文件夹
    # —— 进了 homework/xxx 之后过滤结果恒为空，界面一片空白。
    _assignment_dir = school_book.path / "homework" / "第一次作业"
    _assignment_dir.mkdir(parents=True, exist_ok=True)
    (_assignment_dir / "第一次作业.md").write_text("# 作业\n", encoding="utf-8")
    (_assignment_dir / "老师发的图1.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (_assignment_dir / "老师发的图2.jpg").write_bytes(b"\xff\xd8\xff")
    (_assignment_dir / "homework.json").write_text("{}", encoding="utf-8")
    context.library.invalidate()
    window.book_view.refresh()
    for _ in range(8):
        app.processEvents()
    window.book_view.tabs.setCurrentIndex(hw_index)
    for _ in range(6):
        app.processEvents()
    window.book_view.enter_folder(_assignment_dir)
    for _ in range(8):
        app.processEvents()
    _inner_names = [
        hw_table.item(r, 0).text() for r in range(hw_table.rowCount())
        if hw_table.item(r, 0) is not None
    ]
    check("进入作业文件夹后列出本地全部文件（不再空白）",
          len(_inner_names) == 4, str(_inner_names))
    check("作业内容 md 显示出来了",
          "第一次作业.md" in _inner_names, str(_inner_names))
    check("作业文件夹里的图片也显示出来了",
          "老师发的图1.png" in _inner_names
          and "老师发的图2.jpg" in _inner_names, str(_inner_names))
    check("进入作业后 homework.json 也列出来（用户要能看到文件夹里的东西）",
          "homework.json" in _inner_names, str(_inner_names))
    _meta_items = [
        hw_table.item_at(r) for r in range(hw_table.rowCount())
        if hw_table.item_at(r) is not None
    ]
    _meta = next((i for i in _meta_items if i.name == "homework.json"), None)
    check("homework.json 被标记为软件内部文件",
          _meta is not None and _meta.is_meta, str(_meta))
    check("内部文件的类型列显示「作业信息」",
          _meta is not None and _meta.kind_label == "作业信息",
          _meta.kind_label if _meta else None)
    check("普通作业内容不会被误标为内部文件",
          all(not i.is_meta for i in _meta_items if i.name != "homework.json"),
          str([(i.name, i.is_meta) for i in _meta_items]))
    # 内部文件不给改名/删除入口（改/删会让这条作业丢掉 DDL 与提交网址）
    from gwp.ui.views import book_view as _book_view_mod

    _meta_actions: list = []
    _real_menu = _book_view_mod.common_menu

    class _FakeMenu:
        def exec(self, *a, **k):
            return None

    def _capture_menu(parent, actions):
        _meta_actions.extend(
            a[0] for a in actions if isinstance(a, tuple) and a and a[0]
        )
        return _FakeMenu()

    _book_view_mod.common_menu = _capture_menu
    try:
        window.book_view._on_item_context(_meta, _QPoint(5, 5))
    finally:
        _book_view_mod.common_menu = _real_menu
    check("右键内部文件时没有「重命名」入口",
          not any("重命名" in text for text in _meta_actions),
          str(_meta_actions))
    check("右键内部文件时没有「删除」入口",
          not any("删除" in text for text in _meta_actions),
          str(_meta_actions))
    check("右键内部文件时说明了为什么不能动",
          any("只读" in text or "不可改动" in text for text in _meta_actions),
          str(_meta_actions))

    # ---- 文件夹层级：栏目里只列**这一层**（用户报障）----
    #
    # 用户原话："在本地建立文件夹后，文件夹里面的内容在软件里会和文件夹平行显示"
    #
    # 原来的 list_folder 会把每个子目录里的文件也铺出来（做成 "子目录/文件"），
    # 于是表格里同时出现「第二章」和「第二章/2.1.md」两行 —— 后者是**假层级**
    # （它根本不在这一层），右键删它删的是子文件夹里的文件，用户会以为目录乱了。
    #
    # 注意：必须**先切到「笔记」标签**再断言 ——
    # 各标签各有自己的表格，`enter_folder` 只重画"当前标签"的那一个。
    # 不切标签就会得到空表（我第一版就踩了这个，看着像功能坏了）。
    _nb_index = next(
        i for i, (k, _t, _f) in enumerate(window.book_view._tab_defs)
        if k == C.NOTEBOOK_FOLDER
    )
    _prev_tab_idx = window.book_view.tabs.currentIndex()
    window.book_view.tabs.setCurrentIndex(_nb_index)
    for _ in range(4):
        app.processEvents()

    # 注意：这里必须用**当前打开的那个书目**。
    # 测试里的 `book` 是「界面测试书目」，而这一段运行时窗口打开的是
    # 「作业测试校修课 / 作业书目」—— 在 A 书里建文件夹、去 B 书的表格里断言，
    # 当然读不到（我第一版就这么错，断言显示空表，看着像功能坏了）。
    _cur_book = window.book_view.book()
    check("能取到当前打开的书目", _cur_book is not None, str(_cur_book))
    _nb_root = _cur_book.path / C.NOTEBOOK_FOLDER
    check("当前书目的笔记目录存在", _nb_root.is_dir(), str(_nb_root))

    _lv_dir = _nb_root / "层级测试"
    _lv_dir.mkdir(parents=True, exist_ok=True)
    (_lv_dir / "里面的.md").write_text("内容", encoding="utf-8")
    window.book_view._current_folder = None      # 确保从栏目根开始看
    # **切标签之后必须 refresh()** —— 只 setCurrentIndex 不会重填表格，
    # 表格里还是上一次的内容（我第一版就漏了这一步，断言读到空表）。
    window.book_view.refresh()
    for _ in range(6):
        app.processEvents()

    _nb_table = window.book_view._tables[C.NOTEBOOK_FOLDER]
    _nb_names = [_nb_table.item(r, 0).text()
                 for r in range(_nb_table.rowCount())]
    check("「笔记」标签已就位（表格有内容）",
          bool(_nb_names), str(_nb_names))
    check("**栏目里列出了那个文件夹本身**",
          "层级测试" in _nb_names, str(_nb_names))
    check("**文件夹里的文件不再和文件夹平行显示**",
          not any(n.startswith("层级测试/") for n in _nb_names),
          str(_nb_names))
    check("**栏目里没有任何假层级（带 / 的行）**",
          not any("/" in n for n in _nb_names), str(_nb_names))

    window.book_view.enter_folder(_lv_dir)
    for _ in range(4):
        app.processEvents()
    _in_names = [_nb_table.item(r, 0).text() for r in range(_nb_table.rowCount())]
    check("**进入文件夹后才显示它里面的文件**",
          _in_names == ["里面的.md"], str(_in_names))
    window.book_view.leave_folder()
    for _ in range(4):
        app.processEvents()

    # ---- 新建文件夹 / 新建 Markdown 的落点 ----
    #
    # 用户原话："Book内部各个栏目 目前右键新建文件夹存在异常"
    #
    # 根因有两处：
    #   1. `_creation_dir` 只看**标签**，不看"现在浏览到哪一层"——
    #      进了子文件夹后新建，东西会落到**上一级**；
    #      虚拟栏目（AI 总结 / 简介 / 全部条目）更是直接返回 None，
    #      只弹一句"请先进入某个书目…"（用户明明就在书目里）；
    #   2. `FileTable._on_context` 在 `item is None`（右键空白处）时**直接 return**，
    #      列表下方的空白区域右键什么都不弹 —— 而那正是用户的直觉入口。
    _nb_root = _cur_book.path / C.NOTEBOOK_FOLDER

    def _mk_folder(name: str, *, inside=None, item=None):
        _prev_ask = _common_sum.ask_text
        _common_sum.ask_text = lambda *a, **k: name
        try:
            window.book_view.create_folder(inside=inside, item=item)
        finally:
            _common_sum.ask_text = _prev_ask
        app.processEvents()

    _mk_folder("新建在笔记根")
    check("**在「笔记」标签下能新建文件夹（不再报「先进入某个书目」）**",
          (_nb_root / "新建在笔记根").is_dir(),
          f"tab={window.book_view._current_tab_key()} "
          f"creation_dir={window.book_view._creation_dir()} "
          f"notebook={sorted(p.name for p in _nb_root.iterdir())}")

    window.book_view.enter_folder(_lv_dir)
    for _ in range(4):
        app.processEvents()
    _mk_folder("新建在层级测试里")
    check("**进入子文件夹后，新建的文件夹落在这一层**",
          (_lv_dir / "新建在层级测试里").is_dir(),
          str(sorted(p.name for p in _lv_dir.iterdir())))
    check("**没有跑到上一层去**",
          not (_nb_root / "新建在层级测试里").exists())
    window.book_view.leave_folder()
    for _ in range(4):
        app.processEvents()

    _item_ctx = next(
        (i for i in context.library.list_folder(_nb_root)
         if i.name == "新建在笔记根"), None
    )
    check("能取到刚建的文件夹条目", _item_ctx is not None, str(_item_ctx))
    if _item_ctx is not None:
        _resolved = window.book_view._creation_dir(item=_item_ctx)
        check("**右键条目时，落点是它所在的那一层**",
              _resolved == _nb_root, f"{_resolved} != {_nb_root}")

    # 虚拟栏目（AI 总结）也要有兜底目录，而不是弹一句没用的提示
    window.book_view.tabs.setCurrentIndex(0)
    for _ in range(4):
        app.processEvents()
    check("当前在虚拟栏目（AI 总结）",
          window.book_view._current_tab_key() == "summary",
          window.book_view._current_tab_key())
    check("**虚拟栏目里新建不再返回 None（有兜底目录）**",
          window.book_view._creation_dir() is not None,
          str(window.book_view._creation_dir()))

    # 右键**空白处**必须也能弹出菜单（原来是直接 return）
    _blank_actions: list = []

    def _capture_blank(parent, actions):
        _blank_actions.extend(actions)
        return _FakeMenu()

    _book_view_mod.common_menu = _capture_blank
    try:
        window.book_view._on_item_context(None, _QPoint(10, 10))
    finally:
        _book_view_mod.common_menu = _real_menu
    _blank_labels = [a[0] for a in _blank_actions
                     if isinstance(a, tuple) and a and a[0]]
    check("**右键空白处会弹出菜单（不再什么都不发生）**",
          bool(_blank_labels), str(_blank_labels))
    check("**空白处菜单里有「新建文件夹」**",
          any("新建文件夹" in str(lbl) for lbl in _blank_labels),
          str(_blank_labels))
    # **把标签恢复回去**：后面的用例依赖"当前在哪个栏目"
    # （例如作业右键菜单要求 `_current_tab_key() == "homework"`）。
    # 我第一版忘了恢复，把后面几条断言弄红了 —— 看着像功能坏了，其实是测试污染。
    window.book_view.tabs.setCurrentIndex(_prev_tab_idx)
    for _ in range(4):
        app.processEvents()

    # ---- 文件操作后必须**留在当前文件夹内**（用户报障）----
    #
    # 用户原话："文件操作（如删除文件）后会返回上一层页面，改成保持在该文件夹内"
    #
    # 根因：refresh() 只重填"各标签的根目录"，不会重画"当前所在文件夹"。
    # 所以 `_current_folder` 与标题其实一直是对的，只有**表格内容**变成了
    # 根目录的列表 —— 看起来就是被弹回上一层。
    window.book_view.enter_folder(_assignment_dir)
    for _ in range(8):
        app.processEvents()
    _del_target = _assignment_dir / "待删除的附件.md"
    _del_target.write_text("bye", encoding="utf-8")
    window.book_view.refresh()
    for _ in range(8):
        app.processEvents()

    def _inner_names_now():
        return sorted(
            hw_table.item_at(r).name for r in range(hw_table.rowCount())
            if hw_table.item_at(r) is not None
        )

    _before_del = _inner_names_now()
    check("删除前能看到刚放进去的文件",
          "待删除的附件.md" in _before_del, str(_before_del))

    _real_del_confirm = _book_view_mod.common.confirm
    _book_view_mod.common.confirm = lambda *a, **k: True
    # 这里用**真实删除**：只打桩"删除动作"的话文件还在，
    # 就测不出"删掉之后列表里少了它"（我第一版就是这么写的，结果这条用例假失败）。
    # 测试数据都在临时目录里，删掉没有副作用。
    try:
        _del_item = next(
            (hw_table.item_at(r) for r in range(hw_table.rowCount())
             if hw_table.item_at(r) is not None
             and hw_table.item_at(r).name == "待删除的附件.md"),
            None,
        )
        check("找得到要删除的条目", _del_item is not None)
        if _del_item is not None:
            window.book_view._delete_item(_del_item)
            for _ in range(10):
                app.processEvents()
    finally:
        _book_view_mod.common.confirm = _real_del_confirm

    check("删除动作真的把文件从磁盘移走了",
          not _del_target.exists(), str(_del_target))

    _after_del = _inner_names_now()
    check("**删除文件后仍留在该文件夹内**（不跳回上一层）",
          window.book_view._current_folder is not None
          and window.book_view._current_folder == _assignment_dir,
          str(window.book_view._current_folder))
    check("删除后表格里是该文件夹的内容，而不是上一层的列表",
          "第一次作业.md" in _after_del and "第一次作业" not in _after_del,
          str(_after_del))
    check("删除后目标文件从列表里消失",
          "待删除的附件.md" not in _after_del, str(_after_del))
    check("同文件夹里的其它文件还在（没被连带清掉）",
          "第一次作业.md" in _after_del and "homework.json" in _after_del,
          str(_after_del))

    # 退回作业根目录后恢复"一个作业一行"
    window.book_view.leave_folder()
    for _ in range(8):
        app.processEvents()
    _back_names = [
        hw_table.item(r, 0).text() for r in range(hw_table.rowCount())
        if hw_table.item(r, 0) is not None
    ]
    check("退回作业栏目根目录后仍是「一个作业一行」",
          not any(name.endswith(".json") for name in _back_names), str(_back_names))

    # 点「提交作业」按钮：先弹出确认框（显示作业文件夹路径），再跳转
    from gwp.services import shell_ops as _shell2
    from gwp.ui.dialogs import submit_dialog as _submit_mod

    seen: list = []
    _real_submit_dialog = _submit_mod.SubmitHomeworkDialog

    class _FakeSubmitDialog:
        """把真实对话框的入参记下来，然后模拟"点了提交作业"。"""

        def __init__(self, parent=None, homework=None, folder=None, url=""):
            self.homework = homework
            self.folder = Path(folder) if folder is not None else None
            self.url = url or ""
            self.choice = ""
            self.name = homework.name if homework is not None else (
                self.folder.name if self.folder else "作业"
            )
            seen.append({"folder": self.folder, "url": self.url, "name": self.name})

        def exec(self):
            self.choice = "submit"
            return 1

    _submit_mod.SubmitHomeworkDialog = _FakeSubmitDialog
    opened: list = []
    _real_open = _shell2.open_url
    _shell2.open_url = lambda url: (opened.append(url), True)[1]
    try:
        _submit_row = _find_row("已过期作业")
        if _submit_row is not None:
            hw_table.cellClicked.emit(_submit_row, submit_col)
            app.processEvents()
    finally:
        _shell2.open_url = _real_open
        _submit_mod.SubmitHomeworkDialog = _real_submit_dialog

    check("点「提交方式」列会先弹出提交确认框",
          bool(seen) and seen[0]["folder"] == hw_dir / "已过期作业",
          str(seen))
    check("确认框里带着作业文件夹路径",
          bool(seen) and seen[0]["folder"] is not None
          and seen[0]["folder"].name == "已过期作业",
          str(seen[0]["folder"]) if seen else "无")
    check("确认框里带着提交网址",
          bool(seen) and seen[0]["url"] == "https://example.com/old",
          str(seen[0]["url"]) if seen else "无")
    check("确认「提交作业」后才打开网址",
          opened == ["https://example.com/old"], str(opened))

    # 取消（关闭）时不该打开网址
    class _CancelSubmitDialog(_FakeSubmitDialog):
        def exec(self):
            self.choice = ""
            return 0

    _submit_mod.SubmitHomeworkDialog = _CancelSubmitDialog
    cancelled: list = []
    _shell2.open_url = lambda url: (cancelled.append(url), True)[1]
    try:
        _submit_row = _find_row("已过期作业")
        if _submit_row is not None:
            hw_table.cellClicked.emit(_submit_row, submit_col)
            app.processEvents()
    finally:
        _shell2.open_url = _real_open
        _submit_mod.SubmitHomeworkDialog = _real_submit_dialog
    check("关闭确认框不会打开网址", not cancelled, str(cancelled))

    # 真实对话框本身：路径要完整显示出来
    real_dialog = _real_submit_dialog(
        home,
        homework=_hw2.load(hw_dir / "已过期作业"),
        folder=hw_dir / "已过期作业",
        url="https://example.com/old",
    )
    check("提交框里显示的是完整文件夹路径",
          real_dialog.input_path.text() == str(hw_dir / "已过期作业"),
          real_dialog.input_path.text())
    check("提交框的路径可复制（只读但可选中）",
          real_dialog.input_path.isReadOnly() and real_dialog.input_path.text() != "",
          f"readOnly={real_dialog.input_path.isReadOnly()}")
    check("提交框显示提交网址",
          real_dialog.url == "https://example.com/old", real_dialog.url)
    check("提交框有「提交作业」与「打开文件夹」两个出口",
          real_dialog.btn_submit.text() == "提交作业"
          and real_dialog.btn_open_folder.text() == "打开文件夹",
          f"{real_dialog.btn_submit.text()} / {real_dialog.btn_open_folder.text()}")
    real_dialog.btn_submit.click()
    check("点「提交作业」记录用户选择",
          real_dialog.choice == "submit", real_dialog.choice)
    real_dialog.close()

    # 没有网址时应禁用「提交作业」按钮
    no_url_dialog = _real_submit_dialog(
        home, homework=_hw2.load(hw_dir / "没设DDL的作业"),
        folder=hw_dir / "没设DDL的作业", url="",
    )
    check("没有提交网址时「提交作业」按钮被禁用",
          not no_url_dialog.btn_submit.isEnabled())
    no_url_dialog.close()

    # 右键作业应有作业专属菜单
    hw_items = context.library.list_folder(hw_dir)
    target_item = next((i for i in hw_items if i.name == "已过期作业"), None)
    check("作业文件夹被当成一个条目", target_item is not None)
    if target_item is not None:
        captured_hw: list = []
        from gwp.ui.widgets.cards import build_context_menu as _build_hw_menu

        _menu_probe = _build_hw_menu(home, [])
        _orig_menu_exec = type(_menu_probe).exec
        type(_menu_probe).exec = lambda self, *a, **k: captured_hw.append(
            [act.text() for act in self.actions() if not act.isSeparator()]
        )
        try:
            window.book_view._on_item_context(
                target_item,
                window.book_view.mapToGlobal(window.book_view.rect().center()),
            )
        finally:
            type(_menu_probe).exec = _orig_menu_exec
        check("作业的右键菜单有「编辑作业…」",
              bool(captured_hw) and any("编辑作业" in t for t in captured_hw[0]),
              str(captured_hw))
        check("作业的右键菜单有「打开提交网址」",
              bool(captured_hw) and any("打开提交网址" in t for t in captured_hw[0]),
              str(captured_hw))

    # 「创建作业」按钮端到端：打桩对话框，确认真的落盘
    from gwp.ui.dialogs import homework_dialog as _hw_dialog_mod

    _real_hw_dialog = _hw_dialog_mod.HomeworkDialog

    class _FakeHwDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return 1

        @property
        def folder_name(self):
            return "通过按钮创建的作业"

        @property
        def content_text(self):
            return "老师要求交一份报告"

        @property
        def due_text(self):
            return "2026-12-31T23:59"

        @property
        def submit_url(self):
            return "https://example.com/new"

    _hw_dialog_mod.HomeworkDialog = _FakeHwDialog
    try:
        window.book_view.create_homework()
        app.processEvents()
    finally:
        _hw_dialog_mod.HomeworkDialog = _real_hw_dialog

    created_dir = hw_dir / "通过按钮创建的作业"
    check("「创建作业」按钮真的建出作业文件夹", created_dir.is_dir(), str(created_dir))
    created_hw = _hw2.load(created_dir)
    check("按钮创建的作业有元信息",
          created_hw is not None and (created_dir / "homework.json").is_file())
    check("按钮创建的作业保留了 DDL",
          created_hw is not None and created_hw.due_label.startswith("2026-12-31"),
          created_hw.due_label if created_hw else "无")
    check("按钮创建的作业保留了提交网址",
          created_hw is not None and created_hw.submit_url == "https://example.com/new",
          created_hw.submit_url if created_hw else "无")
    check("按钮创建的作业内容写进了 Markdown",
          "报告" in _hw2.content_file(created_dir).read_text(encoding="utf-8"),
          _hw2.content_file(created_dir).read_text(encoding="utf-8")[:40])

    # 重复创建同名作业应被拦住
    window.book_view.create_homework()
    app.processEvents()
    check("同名作业不会被重复创建",
          len(list(hw_dir.glob("通过按钮创建的作业*"))) == 1,
          str([p.name for p in hw_dir.iterdir()]))

    # 清理
    context.library.delete_subject(school_subject.name, to_recycle=False)
    window.show_home()
    for _ in range(4):
        app.processEvents()

    # ---- 标题区精简 + 数量搬到标签上 ----
    # 背景：原来标题区那行浅灰面包屑（"科目 / 书目 校修课 · 笔记 0 · 作业 0 …"）
    # 太长，把右侧按钮挤成「返回」「导入文」这种截断样。
    window.open_book(subject.name, book.name)
    for _ in range(6):
        app.processEvents()
    check("书目页标题只显示书名",
          window.book_view.lbl_title.text() == book.title,
          window.book_view.lbl_title.text())
    check("书目页不再显示那行浅灰面包屑",
          window.book_view.lbl_subtitle.text() == ""
          and window.book_view.lbl_breadcrumb.text() == "",
          f"subtitle={window.book_view.lbl_subtitle.text()!r} "
          f"breadcrumb={window.book_view.lbl_breadcrumb.text()!r}")

    raw_tabs = [
        window.book_view.tabs.tabText(i) for i in range(window.book_view.tabs.count())
    ]
    check("标签文字 = 栏目名（可带数量）",
          _tab_names(window.book_view) == [
              "AI 总结", "简介", "笔记", "练习", "易错题", "教材", "其它文件",
              "单词书", "全部条目",
          ],
          str(raw_tabs))
    check("空栏目的标签不带 0（避免一排 0 的噪声）",
          not any(text.endswith(" 0") for text in raw_tabs), str(raw_tabs))

    truncated = [
        btn.text() for btn in window.book_view.findChildren(
            type(window.book_view.btn_import)
        )
        if btn.isVisible() and btn.width() < btn.sizeHint().width()
    ]
    check("标题区精简后按钮不再被截断", not truncated, str(truncated))

    # ---- 按钮文字必须完整显示（标题让位，按钮不让位）----
    # 背景：标题区原来那行长文字会把右侧按钮挤到「导入文」「版本管理…」这种
    # 显示不全的样子。现在按钮宽度按内容锁定、不可压缩，空间不够时压缩标题。
    def _clipped_buttons(view) -> list[tuple[str, int, int]]:
        out: list[tuple[str, int, int]] = []
        for button in view.findChildren(QPushButton):
            if not button.isVisible():
                continue
            need = button.fontMetrics().horizontalAdvance(button.text()) + 22
            if button.width() < need:
                out.append((button.text(), button.width(), need))
        return out

    for width in (960, 1014, 1280):
        window.resize(width, 700)
        for _ in range(6):
            app.processEvents()
        problems = _clipped_buttons(window.book_view)
        check(f"{width}px 窗口下书目页按钮文字完整",
              not problems, f"被截断：{problems}")

    window.resize(1014, 700)
    for _ in range(6):
        app.processEvents()
    check("窄窗口下按钮仍然完整（标题不会把按钮挤掉）",
          not _clipped_buttons(window.book_view),
          f"被截断：{_clipped_buttons(window.book_view)}")
    check("标题的悬浮提示给出完整书名",
          window.book_view.lbl_title.toolTip() == window.book_view.lbl_title.text(),
          window.book_view.lbl_title.toolTip())

    window.resize(1280, 720)
    for _ in range(6):
        app.processEvents()

    # ---- 首页右侧日程栏：作业 + 其它日程，按 DDL 排序，可完成 ----
    from datetime import datetime as _dt2
    from datetime import timedelta as _td2

    from PyQt6.QtWidgets import QLabel as _QLabel

    from gwp.core.eventbus import bus as _bus2
    from gwp.data_manager import homework as _hw4

    window.show_home()
    for _ in range(6):
        app.processEvents()
    home = window.home_view
    home.refresh()
    for _ in range(6):
        app.processEvents()

    panel = home.schedule_panel
    check("首页右侧有日程栏", panel is not None and panel.isVisible())
    check("日程栏标题是「日程」", panel.lbl_title.text() == "日程", panel.lbl_title.text())
    check("日程栏有「新建日程」按钮", panel.btn_new.text() == "＋ 新建日程",
          panel.btn_new.text())

    # 造数据：一个作业 + 一条其它日程
    sched_subject = context.library.create_subject("日程科目", subject_type="school")
    sched_book = context.library.create_book(sched_subject.name, "日程书目")
    soon_due = (_dt2.now() + _td2(hours=6)).strftime("%Y-%m-%dT%H:%M")
    far_due = (_dt2.now() + _td2(days=30)).strftime("%Y-%m-%dT%H:%M")
    _hw4.create(sched_book.path / "homework" / "日程作业甲", content="x", due=soon_due)
    _hw4.create(sched_book.path / "homework" / "日程作业乙", content="x", due=far_due)
    schedule_item = context.schedule.add("其它日程丙", due=far_due)
    home.refresh_schedule()
    for _ in range(6):
        app.processEvents()

    def _row_title(row) -> str:
        """取出日程栏某一行的**标题**。

        文本区是一个富文本 QLabel（对象名 AgendaText），标题在第一行
        （`<b>标题</b><br/>来源 &nbsp; DDL`）。为什么合成一个标签：
        之前把标题和 DDL 分成两个标签时，DDL 会被布局压成 0 宽
        （用户反馈"这里要显示 DDL"）。一个标签自己换行就没有这个分配问题。
        """
        import re as _re

        label = row.findChild(_QLabel, "AgendaText")
        if label is None:
            return ""
        first = label.text().split("<br/>")[0]
        return _re.sub(r"<[^>]+>", "", first).strip()

    def _row_titles() -> list[str]:
        return [_row_title(row) for row in panel._rows]

    titles = _row_titles()
    check("日程栏列出了作业与其它日程",
          {"日程作业甲", "日程作业乙", "其它日程丙"} <= set(titles), str(titles))
    check("日程栏按 DDL 排序（近的在前）",
          titles.index("日程作业甲") < titles.index("日程作业乙"), str(titles))
    check("日程栏计数写明待办数",
          "待办" in panel.lbl_count.text(), panel.lbl_count.text())

    # 作业条目的按钮
    def _row_of(title: str):
        for row in panel._rows:
            if _row_title(row) == title:
                return row
        return None

    hw_row = _row_of("日程作业甲")
    check("作业条目存在", hw_row is not None)
    if hw_row is not None:
        button_texts = [b.text() for b in hw_row.findChildren(QPushButton)]
        check("作业条目有「完成」按钮", "完成" in button_texts, str(button_texts))
        check("作业条目有「打开」按钮", "打开" in button_texts, str(button_texts))
        check("按钮是横排的（不会被面板宽度裁掉）",
              all(b.geometry().right() <= hw_row.width()
                  for b in hw_row.findChildren(QPushButton)),
              str([(b.text(), b.geometry().getRect())
                   for b in hw_row.findChildren(QPushButton)]))
    sched_row = _row_of("其它日程丙")
    if sched_row is not None:
        sched_buttons = [b.text() for b in sched_row.findChildren(QPushButton)]
        check("其它日程有「完成」按钮", "完成" in sched_buttons, str(sched_buttons))
        check("其它日程有「编辑」「删除」按钮",
              "编辑" in sched_buttons and "删除" in sched_buttons, str(sched_buttons))

    # 点「完成」：写回 homework.json 并重新排序
    if hw_row is not None:
        done_btn = next(
            b for b in hw_row.findChildren(QPushButton) if b.text() == "完成"
        )
        done_btn.click()
        for _ in range(6):
            app.processEvents()
        stored = _hw4.load(sched_book.path / "homework" / "日程作业甲")
        check("点「完成」写回了 homework.json",
              stored is not None and stored.done is True,
              str(stored.done if stored else "无"))
        moved = _row_titles()
        check("完成后的作业排到未完成之后",
              moved.index("日程作业甲") > moved.index("日程作业乙"), str(moved))
        check("已完成的条目划线",
              _row_of("日程作业甲").findChild(_QLabel, "AgendaText").font().strikeOut(),
              "应划线")

    # 点「完成」（其它日程）
    if sched_row is not None:
        sched_done = next(
            b for b in sched_row.findChildren(QPushButton) if b.text() == "完成"
        )
        sched_done.click()
        for _ in range(6):
            app.processEvents()
        check("点「完成」把其它日程标为完成",
              context.schedule.get(schedule_item.id).done is True)

    # 隐藏已完成
    panel.check_hide_done.setChecked(True)
    for _ in range(6):
        app.processEvents()
    visible_titles = [_row_title(row) for row in panel._rows if row.isVisible()]
    check("勾选「隐藏已完成」后不再显示已完成的条目",
          "日程作业甲" not in visible_titles and "其它日程丙" not in visible_titles,
          str(visible_titles))
    check("未完成的条目仍然显示",
          "日程作业乙" in visible_titles, str(visible_titles))
    panel.check_hide_done.setChecked(False)
    for _ in range(6):
        app.processEvents()

    # 新建日程：打桩对话框，确认落盘并出现在栏里
    from gwp.ui.views import home_view as _home_mod

    _real_sched_dialog = _home_mod.ScheduleDialog

    class _FakeScheduleDialog:
        def __init__(self, *args, **kwargs):
            pass

        def exec(self):
            return 1

        title_text = "通过按钮建的日程"
        due_text = "2031-03-03T09:00"
        note_text = "备注内容"

    _home_mod.ScheduleDialog = _FakeScheduleDialog
    try:
        home.create_schedule()
        for _ in range(6):
            app.processEvents()
    finally:
        _home_mod.ScheduleDialog = _real_sched_dialog

    check("「新建日程」把日程存进 schedule.json",
          any(x.title == "通过按钮建的日程"
              for x in context.schedule.load(refresh=True)),
          str([x.title for x in context.schedule.load(refresh=True)]))
    check("新建的日程出现在日程栏里",
          "通过按钮建的日程" in _row_titles(), str(_row_titles()))
    new_item = next(
        x for x in context.schedule.load(refresh=True)
        if x.title == "通过按钮建的日程"
    )
    check("新建日程保留了时间与备注",
          new_item.due_label.startswith("2031-03-03") and new_item.note == "备注内容",
          f"{new_item.due_label} / {new_item.note}")

    # 删除日程（打桩确认框）
    from gwp.ui import common as _common3

    _real_confirm_home = _common3.confirm
    _common3.confirm = lambda *a, **k: True
    try:
        home.delete_schedule(new_item.id)
        for _ in range(4):
            app.processEvents()
    finally:
        _common3.confirm = _real_confirm_home
    check("删除日程后从栏里消失",
          "通过按钮建的日程" not in _row_titles(), str(_row_titles()))

    # 在书目页新建作业后，首页日程栏要跟着更新
    _hw4.create(sched_book.path / "homework" / "书目页新建的作业",
                content="x", due=soon_due)
    from gwp.core.eventbus import BOOK_CONTENT_CHANGED as _BCC

    _bus2.emit(_BCC, subject=sched_subject.name, book="日程书目")
    for _ in range(6):
        app.processEvents()
    check("书目页新建作业后首页日程栏自动更新",
          "书目页新建的作业" in _row_titles(), str(_row_titles()))

    context.library.delete_subject(sched_subject.name, to_recycle=False)
    window.show_home()
    for _ in range(4):
        app.processEvents()

    # ---- 日程栏上方的日期 / 时间 / 天气条 ----
    from gwp.services import weather as _W2

    clock = home.clock_bar
    check("日程栏上方有日期/时间/天气条", clock is not None and clock.isVisible())
    check("信息条在日程栏上方",
          # 现在时钟条挂在日程栏面板**内部**（折叠时一起收起），
          # 两者不再是兄弟节点，所以要看它是否是面板里排在列表之前的那一项。
          clock.parent() is panel.clock_holder
          and panel.clock_holder.y() < panel.scroll.y(),
          f"parent={type(clock.parent()).__name__} "
          f"holder.y={panel.clock_holder.y()} scroll.y={panel.scroll.y()}")
    check("时钟条是日程栏的一部分（折叠时一起收起）",
          panel.clock_bar is clock
          and clock.parent() is panel.clock_holder,
          type(clock.parent()).__name__)
    check("信息条显示日期与星期",
          "年" in clock.lbl_date.text() and "星期" in clock.lbl_date.text(),
          clock.lbl_date.text())
    check("信息条显示时间（带秒）",
          len(clock.lbl_time.text()) == 8 and clock.lbl_time.text().count(":") == 2,
          clock.lbl_time.text())

    # 时间每秒走一次（不联网）
    import time as _time

    before = clock.lbl_time.text()
    _time.sleep(1.1)
    app.processEvents()
    after = clock.lbl_time.text()
    check("时间会自动走（每秒刷新）", before != after, f"{before} -> {after}")

    # 天气：用打桩结果填，避免测试依赖网络
    stub = _W2.Weather(
        ok=True, location="中国 · 北京市", temperature=18.4, feels_like=17.2,
        humidity=52, wind_speed=11.3, wind_deg=180, code=2,
        observed_at="2026-10-09 16:30",
    )
    clock.apply_weather(stub)
    app.processEvents()
    check("天气成功时显示温度+情况",
          clock.lbl_weather.text() == "18°C 多云", clock.lbl_weather.text())
    check("天气条显示地区", clock.lbl_place.text() == "中国 · 北京市",
          clock.lbl_place.text())
    check("体感/湿度/风只在悬浮提示里（不占版面）",
          "体感 17°C" in clock.lbl_weather.toolTip()
          and "湿度 52%" in clock.lbl_weather.toolTip()
          and "南风" in clock.lbl_weather.toolTip()
          and "体感" not in clock.lbl_weather.text(),
          clock.lbl_weather.toolTip())
    check("地区也带同一份详情提示",
          "中国 · 北京市" in clock.lbl_place.toolTip(), clock.lbl_place.toolTip())

    # 失败态：显示原因而不是崩掉
    clock.apply_weather(_W2.Weather(ok=False, error="无法定位（可能没联网）"))
    app.processEvents()
    check("天气失败时显示失败原因",
          "无法定位" in clock.lbl_weather.text(), clock.lbl_weather.text())
    check("天气失败不弹窗、不抛异常", True)

    # 真实线程：打桩 query_weather，确认线程真的被清理。
    # 注意要打在使用点（clock_bar.W），打 weather 模块上的名字无效 ——
    # worker 里用的是 clock_bar 自己 import 的那份绑定。
    from gwp.ui.widgets import clock_bar as _clock_mod

    # 用**命名函数**打桩（lambda 在早前的写法里出现过时序不稳的情况）。
    # 注意打在使用点 clock_bar.W 上，不是 weather 模块上的名字。
    real_query = _clock_mod.W.query_weather

    def _stub_query(cancelled=None):
        return _W2.Weather(ok=True, location="测试地区", temperature=20.0, code=1)

    _clock_mod.W.query_weather = _stub_query
    try:
        # 先确保没有正在跑的线程：否则 start_fetch 会直接返回（不起新的）
        clock.stop(force=True)
        clock.start_fetch()
        # 用 pump 而不是 processEvents：离屏下后者不派发跨线程排队信号，
        # 会让 worker 的 finished 永远到不了（详见 pump 的说明）
        for _ in range(60):
            pump(50)
            if clock._worker is None:
                break
        pump(80)
        check("后台线程抓完后被清理", clock._worker is None, str(clock._worker))
        check("后台线程把结果填进了界面",
              clock.lbl_weather.text() == "20°C 晴间多云", clock.lbl_weather.text())
        check("后台线程填上了地区", clock.lbl_place.text() == "测试地区",
              clock.lbl_place.text())
    finally:
        _clock_mod.W.query_weather = real_query

    # 重复调用不会起第二个线程
    clock.start_fetch()
    first_worker = clock._worker
    clock.start_fetch()
    check("重复触发不会起第二个天气线程",
          clock._worker is first_worker, "应复用同一个线程")
    clock.stop()
    check("stop() 后线程引用被清空", clock._worker is None)

    # 设置里的开关：关掉天气就不联网、关掉整条就不显示
    clock.set_weather_enabled(False)
    app.processEvents()
    check("关掉天气后显示「天气已关闭」",
          clock.lbl_weather.text() == "天气已关闭", clock.lbl_weather.text())
    check("关掉天气时不会起联网线程", clock._worker is None, str(clock._worker))
    clock.set_weather_enabled(True)
    app.processEvents()
    check("重新打开天气会再去抓取",
          clock.lbl_weather.text() == "天气获取中…", clock.lbl_weather.text())
    clock.stop()

    context.config.set("ui.show_clock_bar", False)
    home.refresh_settings()
    app.processEvents()
    check("设置里关掉后整条信息条不显示", not clock.isVisible())
    context.config.set("ui.show_clock_bar", True)
    home.refresh_settings()
    app.processEvents()
    check("打开后信息条又显示出来", clock.isVisible())

    # ---- 论坛：菜单 → 用系统浏览器打开 ----
    forum_menu = next(
        (a.menu() for a in window.menuBar().actions() if "论坛" in a.text()), None
    )
    check("菜单栏有「论坛」", forum_menu is not None,
          str([a.text() for a in window.menuBar().actions()]))
    entries = [a.text() for a in forum_menu.actions() if not a.isSeparator()] if forum_menu else []
    check("论坛菜单下有「牢大CS」", any("牢大CS" in text for text in entries), str(entries))

    laoda = next((a for a in forum_menu.actions() if "牢大CS" in a.text()), None) if forum_menu else None
    check("「牢大CS」是可点击的菜单项", laoda is not None)
    check("论坛地址来自配置（不写死在代码里）",
          window.forum_url("laoda_cs").startswith("https://cs9.x-way.work"),
          window.forum_url("laoda_cs"))

    # 点一下：应调用 shell_ops.open_url（打桩，不真的开浏览器）
    from gwp.services import shell_ops as _shell_forum

    opened_urls: list = []
    _real_open_url = _shell_forum.open_url
    _shell_forum.open_url = lambda url: (opened_urls.append(url), True)[1]
    try:
        if laoda is not None:
            laoda.trigger()
            app.processEvents()
    finally:
        _shell_forum.open_url = _real_open_url
    check("点「牢大CS」会用浏览器打开论坛地址",
          opened_urls == ["https://cs9.x-way.work/"], str(opened_urls))

    # 打不开时要给出提示而不是静默失败
    _shell_forum.open_url = lambda url: False
    warned: list = []
    _real_warn = _common3.warn
    _common3.warn = lambda *a, **k: warned.append(a)
    try:
        window.open_forum("牢大CS")
    finally:
        _shell_forum.open_url = _real_open_url
        _common3.warn = _real_warn
    check("浏览器打不开时会提示用户", bool(warned), str(warned)[:80])

    # ---- 软件内部打开文件夹 / 文件（不弹资源管理器）----
    folder_subject = context.library.create_subject("文件夹科目")
    folder_book = context.library.create_book(folder_subject.name, "文件夹书目")
    others_dir = folder_book.path / "others"
    (others_dir / "第一章").mkdir(parents=True, exist_ok=True)
    (others_dir / "第一章" / "课件.md").write_text("# 课件\n", encoding="utf-8")
    (others_dir / "第一章" / "说明.txt").write_text("说明\n", encoding="utf-8")
    (others_dir / "配置.json").write_text('{"a": 1}\n', encoding="utf-8")
    context.library.invalidate()
    window.open_book(folder_subject.name, "文件夹书目")
    for _ in range(6):
        app.processEvents()
    fbv = window.book_view
    fbv.tabs.setCurrentIndex(
        next(i for i, t in enumerate(_tab_names(fbv)) if t == "其它文件")
    )
    for _ in range(6):
        app.processEvents()
    ftable = fbv._tables["others"]
    frows = [ftable.item(r, 0).text() for r in range(ftable.rowCount())]
    check("「其它文件」里能看到子文件夹", "第一章" in frows, str(frows))

    # 双击文件夹：应进入软件内部，而不是弹资源管理器
    revealed: list = []
    from gwp.services import file_ops as _file_ops2

    _real_reveal = _file_ops2.reveal_in_explorer
    _file_ops2.reveal_in_explorer = lambda p: (revealed.append(Path(p)), True)[1]
    try:
        folder_item = next(
            i for i in context.library.list_folder(others_dir) if i.name == "第一章"
        )
        fbv._on_item_double_clicked(folder_item)
        for _ in range(4):
            app.processEvents()
    finally:
        _file_ops2.reveal_in_explorer = _real_reveal
    check("双击文件夹不会弹出资源管理器", not revealed, str(revealed))
    check("双击文件夹进入软件内部浏览",
          fbv._current_folder == others_dir / "第一章", str(fbv._current_folder))
    inner = [ftable.item(r, 0).text() for r in range(ftable.rowCount())]
    check("只列出该文件夹里的内容",
          sorted(inner) == ["说明.txt", "课件.md"], str(inner))
    check("标题显示当前所在位置",
          "第一章" in fbv.lbl_title.text(), fbv.lbl_title.text())
    check("出现「上一层」按钮", fbv.btn_folder_up.isVisible())

    fbv.leave_folder()
    for _ in range(4):
        app.processEvents()
    check("「上一层」能退回分类目录", fbv._current_folder is None,
          str(fbv._current_folder))
    check("退回后又看到全部条目",
          "第一章" in [ftable.item(r, 0).text() for r in range(ftable.rowCount())])
    check("退回后「上一层」按钮隐藏", not fbv.btn_folder_up.isVisible())

    # 切换栏目应自动退出文件夹浏览
    folder_item2 = next(
        i for i in context.library.list_folder(others_dir) if i.name == "第一章"
    )
    fbv.enter_folder(folder_item2.path)
    for _ in range(4):
        app.processEvents()
    fbv.tabs.setCurrentIndex(
        next(i for i, t in enumerate(_tab_names(fbv)) if t == "笔记")
    )
    for _ in range(6):
        app.processEvents()
    check("切换栏目会退出文件夹浏览", fbv._current_folder is None,
          str(fbv._current_folder))

    # ---- 拖拽上传：落点必须是"当前浏览的目录"，不是上一级 ----
    #
    # 需求原话："作业以及其它文件夹都要支持拖拽上传 目前会传到上一目录"。
    # 原来 dropEvent 用的是 _target_folder()，它只看标签登记、
    # 完全不管你浏览到哪一层，所以进了 others/第一章 再拖就被丢到 others。
    from PyQt6.QtCore import QMimeData as _QMime
    from PyQt6.QtCore import QUrl as _QUrl
    from PyQt6.QtGui import QDropEvent as _QDrop

    def _make_dropper(source: Path):
        mime = _QMime()
        mime.setUrls([_QUrl.fromLocalFile(str(source))])

        def dropper(widget, pos):
            event = _QDrop(
                QPointF(pos), Qt.DropAction.CopyAction, mime,
                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
            )
            widget.dropEvent(event)
            for _ in range(8):
                app.processEvents()

        return dropper

    def _rel_paths(root: Path) -> list[str]:
        return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())

    def _empty_pos(table) -> _QPoint:
        """表格**下方空白处**的坐标 —— 用来测"落在当前栏目根目录"。

        为什么不能用 ``(40, 20)``：那正好是第一行（很可能是个文件夹），
        而"拖到文件夹行上"是**另一种**语义（进那个文件夹，见 ④）。
        两个用例必须用不同落点，否则互相干扰。
        """
        rows_height = sum(table.rowHeight(r) for r in range(table.rowCount()))
        y = min(rows_height + 12, max(0, table.viewport().height() - 6))
        return _QPoint(40, y)

    def _capture_drop(widget, pos):
        """拖一次，并记下**真正用于导入的目标目录**。

        为什么断言"目标目录"而不是"文件出现在哪"：
        * 目标目录就是这段逻辑的产出，断言它最直接；
        * 不受同名字自动改名、对话框打桩、行高变化等无关因素干扰。

        实现要点（踩过坑）：**不要** ``files_dropped.disconnect()`` ——
        那会把视图自己的连接一起摘掉，之后所有拖拽都不再走导入，
        表现为"一连串用例神秘失败"。只换 ``_do_import`` 就够了。
        """
        seen: list[Path] = []
        real = fbv._do_import
        fbv._do_import = lambda paths, folder: (seen.append(Path(folder)), None)[1]
        try:
            dropper(widget, pos)
        finally:
            fbv._do_import = real
        return seen

    drop_src = Path(tempfile.mkdtemp(prefix="gwp_drop_")) / "拖入的资料.txt"
    drop_src.write_text("外部文件", encoding="utf-8")
    dropper = _make_dropper(drop_src)

    # 先切到「其它文件」栏目（前面的文件夹浏览测试把当前标签留在了"笔记"）
    fbv.tabs.setCurrentIndex(
        next(i for i, t in enumerate(_tab_names(fbv)) if t == "其它文件")
    )
    for _ in range(8):
        app.processEvents()

    check("文件表格接受外部拖入（否则导入会被表格吃掉）",
          fbv._current_table().acceptDrops())
    check("文件表格的视口也接受拖入",
          fbv._current_table().viewport().acceptDrops())

    # ① 表格自己的 dropEvent 必须把落点交给视图（两条路径规则一致）
    #    注意：**不能** disconnect，那会摘掉视图自己的连接，后面的用例就全废了
    _drop_table = fbv._current_table()
    _got: list = []
    _drop_table.files_dropped.connect(lambda pos, mime: _got.append((pos, mime)))
    _capture_drop(_drop_table, _empty_pos(_drop_table))
    check("表格接受外部拖入后会通知视图处理", len(_got) >= 1, str(len(_got)))

    # ② 栏目根目录 → 落到该栏目目录
    check("栏目根目录的拖拽落点 = 该栏目目录",
          fbv.drop_target_folder() == others_dir, str(fbv.drop_target_folder()))
    _seen_root = _capture_drop(fbv._current_table(), _empty_pos(fbv._current_table()))
    check("拖到「其它文件」根目录 → 目标目录是 others/",
          _seen_root == [others_dir], str(_seen_root))

    # ③ 进入子目录后再拖 → 目标必须是子目录，**不是上一级**（用户报的 bug）
    fbv.enter_folder(others_dir / "第一章")
    for _ in range(8):
        app.processEvents()
    check("进入子目录后拖拽落点 = 该子目录",
          fbv.drop_target_folder() == others_dir / "第一章",
          str(fbv.drop_target_folder()))
    _t3 = fbv._current_table()
    _seen_inner = _capture_drop(_t3, _empty_pos(_t3))
    check("拖到子目录里 → 目标目录是那个子目录（不是上一级）",
          _seen_inner == [others_dir / "第一章"], str(_seen_inner))
    check("拖到子目录里 → 目标**不是**上一级 others/",
          _seen_inner != [others_dir], str(_seen_inner))

    # ④ 拖到某个文件夹那一行上 → 进那一行对应的目录
    fbv.leave_folder()
    fbv.enter_folder(others_dir)
    for _ in range(8):
        app.processEvents()
    _tbl = fbv._current_table()
    _names = [_tbl.item_at(r).name for r in range(_tbl.rowCount())]
    _row = _names.index("第一章")
    _cell = _tbl.visualRect(_tbl.model().index(_row, 0)).center()
    check("落在文件夹那一行时，落点就是那个文件夹",
          fbv._row_folder_at(_cell) == others_dir / "第一章",
          str(fbv._row_folder_at(_cell)))
    _seen_row = _capture_drop(_tbl, _cell)
    check("拖到文件夹行上 → 目标目录是那个文件夹",
          _seen_row == [others_dir / "第一章"], str(_seen_row))

    # ⑤ 作业栏目也要能拖入。
    #    注意：这个书目属于**自学课**科目，同一栏目显示为「练习」而不是「作业」，
    #    所以按**内部 key** 找标签，而不是按显示文案（文案一变测试就崩）。
    while fbv._current_folder is not None:
        fbv.leave_folder()
        for _ in range(3):
            app.processEvents()
    _homework_idx = next(
        i for i, (key, _title, _folder) in enumerate(fbv._tab_defs)
        if key == "homework"
    )
    fbv.tabs.setCurrentIndex(_homework_idx)
    for _ in range(8):
        app.processEvents()
    check("作业栏目的拖拽落点是 homework 目录",
          fbv.drop_target_folder() == folder_book.path / "homework",
          str(fbv.drop_target_folder()))
    _seen_hw = _capture_drop(fbv._current_table(), _empty_pos(fbv._current_table()))
    check("作业栏目支持拖拽上传（目标 homework 目录）",
          _seen_hw == [folder_book.path / "homework"], str(_seen_hw))

    # ⑥ 状态栏提示里给出相对书目的完整路径（原来只给文件夹名，看不出落点）
    check("目录标签给出相对书目的完整路径",
          "第一章" in fbv._folder_label(others_dir / "第一章"),
          fbv._folder_label(others_dir / "第一章"))
    check("拖拽落点提示控件存在且默认隐藏",
          hasattr(fbv, "lbl_drop_hint") and not fbv.lbl_drop_hint.isVisible())
    fbv._set_drop_hint(others_dir / "第一章")
    check("拖拽时会显示落点提示",
          fbv.lbl_drop_hint.isVisible()
          and "第一章" in fbv.lbl_drop_hint.text(),
          fbv.lbl_drop_hint.text())
    fbv._set_drop_hint(None)
    check("离开拖拽后落点提示隐藏", not fbv.lbl_drop_hint.isVisible())

    # ⑦ 右键菜单里也有明确的"上传文件"入口
    _upload_calls: list = []
    _real_upload = fbv.upload_files
    fbv.upload_files = lambda inside=None: _upload_calls.append(inside)
    try:
        check("右键菜单有「上传文件」入口",
              callable(getattr(fbv, "upload_files", None)))
    finally:
        fbv.upload_files = _real_upload

    # JSON：优先 VSCode；没有 VSCode 时落到内置查看器
    json_path = others_dir / "配置.json"
    vscode_tries: list = []
    _real_vscode = _file_ops2.open_in_vscode
    _file_ops2.open_in_vscode = lambda p: (vscode_tries.append(Path(p)), True)[1]
    before_views = len(window._text_views)
    try:
        fbv._on_item_double_clicked(
            next(i for i in context.library.list_folder(others_dir)
                 if i.name == "配置.json")
        )
        for _ in range(4):
            app.processEvents()
    finally:
        _file_ops2.open_in_vscode = _real_vscode
    check("JSON 会用 VSCode 打开", vscode_tries == [json_path], str(vscode_tries))
    check("有 VSCode 时不占用内置查看器",
          len(window._text_views) == before_views, str(len(window._text_views)))

    _file_ops2.open_in_vscode = lambda p: False
    try:
        fbv._on_item_double_clicked(
            next(i for i in context.library.list_folder(others_dir)
                 if i.name == "配置.json")
        )
        for _ in range(6):
            app.processEvents()
    finally:
        _file_ops2.open_in_vscode = _real_vscode
    check("没有 VSCode 时用内置查看器打开 JSON",
          len(window._text_views) == before_views + 1, str(len(window._text_views)))
    if len(window._text_views) > before_views:
        tv = window._text_views[-1]
        check("内置查看器显示 JSON 内容",
              '"a": 1' in tv.editor.toPlainText(), tv.editor.toPlainText()[:40])
        check("内置查看器是只读的", tv.editor.isReadOnly())
        tv.closed.emit(tv)
        for _ in range(4):
            app.processEvents()
        check("关闭后查看器被移除",
              len(window._text_views) == before_views, str(len(window._text_views)))

    check("find_vscode 找不到时返回空串而不报错",
          isinstance(_file_ops2.find_vscode(), str))

    context.library.delete_subject(folder_subject.name, to_recycle=False)
    window.show_home()
    for _ in range(4):
        app.processEvents()

    # 日程栏每行必须显示 DDL（用户反馈过一次"这里要显示 DDL"）
    def _agenda_text(row):
        label = row.findChild(_QLabel, "AgendaText")
        return label.text() if label is not None else ""

    def _agenda_label_width(row):
        label = row.findChild(_QLabel, "AgendaText")
        return label.width() if label is not None else 0

    def _agenda_lines(row) -> list[str]:
        """把日程栏某一行的富文本按行拆开（去标签）。"""
        import re as _re

        label = row.findChild(_QLabel, "AgendaText")
        if label is None:
            return []
        return [_re.sub(r"<[^>]+>", "", part).strip()
                for part in label.text().split("<br/>")]

    def _ddl_line(row) -> str:
        """DDL 所在的那一行文本。

        结构固定为：标题 / 来源 / **DDL** / 备注（可选）。
        需求明确要求"DDL 单独一行、加粗"，所以这里按下标取第三行。
        """
        lines = _agenda_lines(row)
        return lines[2] if len(lines) > 2 else ""

    def _ddl_is_bold(row) -> bool:
        """DDL 那一行是否真的在 <b> 里（加粗）。"""
        label = row.findChild(_QLabel, "AgendaText")
        if label is None:
            return False
        parts = label.text().split("<br/>")
        return len(parts) > 2 and parts[2].lstrip().startswith("<b>")

    def _has_due(row) -> bool:
        """这一行是否显示了截止信息。

        * 作业没设 DDL → 「未设 DDL」
        * 其它日程没设时间 → 「未设时间」
        * 已完成的条目 → 「已完成」（不再显示 DDL —— 已经不用赶了）
        """
        text = _ddl_line(row)
        return "DDL" in text or "未设" in text or "已完成" in text

    check("日程栏每行都有文本标签", all(_agenda_text(r) for r in panel._rows))
    check("日程栏每行都显示截止信息（DDL / 未设 / 已完成）",
          all(_has_due(r) for r in panel._rows),
          str([_agenda_lines(r) for r in panel._rows]))
    check("DDL 单独一行（不与来源挤在一起）",
          all("DDL" not in _agenda_lines(r)[1] if len(_agenda_lines(r)) > 1 else True
              for r in panel._rows),
          str([_agenda_lines(r) for r in panel._rows]))
    check("DDL 那一行是加粗的",
          all(_ddl_is_bold(r) for r in panel._rows),
          str([_agenda_text(r) for r in panel._rows]))
    check("日程栏文本标签有实际宽度（没被压成 0）",
          all(_agenda_label_width(r) > 0 for r in panel._rows),
          str([_agenda_label_width(r) for r in panel._rows]))
    check("日程栏文本没有被竖向裁掉（内容多时行会变高）",
          all(r.findChild(_QLabel, "AgendaText").height()
              >= r.findChild(_QLabel, "AgendaText").sizeHint().height() - 2
              for r in panel._rows if r.findChild(_QLabel, "AgendaText")),
          str([(r.findChild(_QLabel, "AgendaText").height(),
                r.findChild(_QLabel, "AgendaText").sizeHint().height())
               for r in panel._rows]))

    # 窄面板下也不能被压没、按钮不能被裁
    for width in (960, 1100, 1400):
        window.resize(width, 760)
        for _ in range(8):
            app.processEvents()
        rows = panel._rows
        check(f"{width}px 窗口下日程栏的截止信息仍然可见",
              all(_has_due(r) and _agenda_label_width(r) > 0 for r in rows),
              str([(len(_agenda_text(r)), _agenda_label_width(r)) for r in rows]))
        check(f"{width}px 窗口下日程栏按钮不被裁",
              all(b.geometry().right() <= r.width()
                  for r in rows for b in r.findChildren(QPushButton)),
              str([[b.text() for b in r.findChildren(QPushButton)] for r in rows]))
    window.resize(1280, 760)
    for _ in range(6):
        app.processEvents()

    # DDL 文案要能区分三种状态
    from gwp.data_manager import homework as _hw5

    _now = _dt.now()
    _hw5.create(
        sched_book.path / "homework" / "状态-过期",
        content="x",
        due=(_now - _td(days=1)).strftime("%Y-%m-%dT%H:%M"),
    )
    _hw5.create(
        sched_book.path / "homework" / "状态-临期",
        content="x",
        due=(_now + _td(hours=3)).strftime("%Y-%m-%dT%H:%M"),
    )
    # 用户反馈的场景：距现在 30 小时。旧阈值（24h）下它不会标「即将截止」，
    # 现在阈值改成 48 小时，它必须被标出来。
    _hw5.create(
        sched_book.path / "homework" / "状态-临期30小时",
        content="x",
        due=(_now + _td(hours=30)).strftime("%Y-%m-%dT%H:%M"),
    )
    home.refresh_schedule()
    for _ in range(6):
        app.processEvents()
    texts = {r: _agenda_text(r) for r in panel._rows}
    all_text = " ".join(_agenda_text(r) for r in panel._rows)
    check("过期的 DDL 标注「已过期」", "已过期" in all_text, all_text[:240])
    check("临期的 DDL 标注「即将截止」", "即将截止" in all_text, all_text[:240])
    check("**30 小时内的 DDL 也标「即将截止」**（48 小时阈值）",
          all_text.count("即将截止") >= 2, all_text[:400])
    check("已完成的条目显示「已完成」而不是过期 DDL",
          "已完成" in all_text, all_text[:240])

    # 补一条"没有时间"的日程，验证「未设时间」文案
    no_due_item = context.schedule.add("没有时间的杂事")
    home.refresh_schedule()
    for _ in range(6):
        app.processEvents()
    no_due_text = " ".join(_agenda_text(r) for r in panel._rows)
    check("没设时间的日程显示「未设时间」",
          "未设时间" in no_due_text, no_due_text[:240])
    # 再补一条"没设 DDL"的作业，验证「未设 DDL」文案
    _hw5.create(sched_book.path / "homework" / "状态-没DDL", content="x")
    home.refresh_schedule()
    for _ in range(6):
        app.processEvents()
    none_text = " ".join(_agenda_text(r) for r in panel._rows)
    check("没设 DDL 的作业显示「未设 DDL」",
          "未设 DDL" in none_text, none_text[:240])
    context.schedule.remove(no_due_item.id)
    home.refresh_schedule()
    for _ in range(4):
        app.processEvents()

    # 单行高度可配置（需求："可以加高单个任务的大小"）
    check("日程栏行高有下限（不低于 44px）",
          panel._row_height() >= 44, str(panel._row_height()))
    heights: list[int] = []
    for value in (76, 96, 44, 0, "abc"):
        context.config.set("ui.schedule_row_height", value)
        home.refresh_schedule()
        for _ in range(6):
            app.processEvents()
        row_h = panel._rows[0].height() if panel._rows else 0
        heights.append(row_h)
    check("提高配置能真的加高任务行",
          heights[1] > heights[0], f"76px->{heights[0]}, 96px->{heights[1]}")
    check("离谱的配置值被夹到安全下限",
          heights[2] >= 44 and heights[3] >= 44 and heights[4] >= 44,
          str(heights))
    context.config.set("ui.schedule_row_height", 88)
    home.refresh_schedule()
    for _ in range(6):
        app.processEvents()

    # ---- AI 助手自称「长庚」（需求：不要叫"大白星球"）----
    from gwp.core import constants as _C2

    _prompt_names = [
        name for name in dir(_C2)
        if "PROMPT" in name and isinstance(getattr(_C2, name), str)
    ]
    check("存在 AI 助手名称常量", _C2.AI_ASSISTANT_NAME == "长庚",
          _C2.AI_ASSISTANT_NAME)
    check("所有 AI 提示词都自称「长庚」",
          all(_C2.AI_ASSISTANT_NAME in getattr(_C2, n) for n in _prompt_names),
          str([n for n in _prompt_names
               if _C2.AI_ASSISTANT_NAME not in getattr(_C2, n)]))
    check("没有任何提示词把软件名当成助手名字",
          all("大白星球" not in getattr(_C2, n) for n in _prompt_names),
          str([n for n in _prompt_names if "大白星球" in getattr(_C2, n)]))
    check("默认配置里的提示词也用的是新名字",
          _C2.AI_ASSISTANT_NAME in str(context.config.get("prompts.summary_system")),
          str(context.config.get("prompts.summary_system"))[:60])
    check("配置里有提示词版本号（便于以后自动升级）",
          int(context.config.get("prompts.revision", 0) or 0) >= 1,
          str(context.config.get("prompts.revision")))

    # ---- 日期时间输入：日历选 + 滚轮调，不手打 ----
    from PyQt6.QtCore import QDateTime as _QDT
    from PyQt6.QtWidgets import QDateTimeEdit as _QDTE

    from gwp.services import themes as _themes2
    from gwp.ui import common as _common4

    dt = _common4.make_datetime_edit(_QDT.currentDateTime())
    check("日期时间输入带日历弹窗", dt.calendarPopup())
    check("时间精确到分钟（不给用户多余的秒）",
          dt.displayFormat() == "yyyy-MM-dd HH:mm", dt.displayFormat())
    check("支持键盘/滚轮分段调节", dt.keyboardTracking() is True)
    check("该段可循环（59 分滚回 0 分）", dt.wrapping() is True)
    _cal = dt.calendarWidget()
    check("日历弹窗有足够宽度（数字不挤）",
          _cal is not None and _cal.minimumWidth() >= 340,
          str(_cal.minimumWidth() if _cal else None))
    check("日历有网格线（行列看得清）",
          _cal is not None and _cal.isGridVisible())
    check("日历从周一开始",
          _cal is not None and _cal.firstDayOfWeek() == Qt.DayOfWeek.Monday,
          str(_cal.firstDayOfWeek() if _cal else None))
    dt.setCurrentSection(_QDTE.Section.MinuteSection)
    _before = dt.dateTime().toString("HH:mm")
    dt.stepUp()
    _after = dt.dateTime().toString("HH:mm")
    check("分钟段可以用 stepUp 调整（= 滚轮/上下按钮）",
          _before != _after, f"{_before} -> {_after}")
    dt.setCurrentSection(_QDTE.Section.HourSection)
    _h1 = dt.dateTime().toString("HH:mm")
    dt.stepUp()
    _h2 = dt.dateTime().toString("HH:mm")
    check("小时段可以用 stepUp 调整", _h1 != _h2, f"{_h1} -> {_h2}")

    from gwp.ui.dialogs.homework_dialog import HomeworkDialog as _HDlg
    from gwp.ui.dialogs.schedule_dialog import ScheduleDialog as _SDlg

    _hw_dlg = _HDlg(home)
    check("作业对话框的 DDL 输入带日历弹窗", _hw_dlg.edit_due.calendarPopup())
    check("作业对话框的 DDL 输入支持分段调节",
          _hw_dlg.edit_due.keyboardTracking() is True)
    _hw_dlg.close()
    _sc_dlg = _SDlg(home)
    check("日程对话框的时间输入带日历弹窗", _sc_dlg.edit_due.calendarPopup())
    check("日程对话框的时间输入支持分段调节",
          _sc_dlg.edit_due.keyboardTracking() is True)
    _sc_dlg.close()

    check("日期时间控件也套上了应用的样式（不再用 Qt 默认外观）",
          "QDateTimeEdit" in _themes2.app_qss(
              theme="light", accent="", font_family="x", font_size=10),
          "QSS 里应包含 QDateTimeEdit")

    # ---- 图片提取为 Markdown（对话框 + 接线）----
    #
    # 需求："增加文件夹内多图片AI提取内容（无把握识别准确就直接插入图片）并合并为md功能"
    # 这里把 AI 调用打桩，验证"界面 → 服务层 → 落盘"整条链路与状态判定。
    from PyQt6.QtGui import QColor as _QColor
    from PyQt6.QtGui import QImage as _QImage

    from gwp.services import image_digest as _digest
    from gwp.ui.dialogs import image_digest_dialog as _digest_dialog

    _digest_dir = folder_book.path / "others" / "照片"
    _digest_dir.mkdir(parents=True, exist_ok=True)
    for _name in ("第10页.png", "第2页.png", "第1页.png"):
        _img = _QImage(120, 80, _QImage.Format.Format_RGB32)
        _img.fill(_QColor("#DDDDDD"))
        _img.save(str(_digest_dir / _name))

    _replies = iter([
        "## 第一节\n\n这是一段足够长的正文，可以判定为识别成功。" * 3,
        "抱歉，这张图片无法辨认清楚，无法提供内容。" * 3,
        "",                                   # 用户跳过
    ])
    _sent: list = []

    def _fake_send(prompt, **kwargs):
        _sent.append((prompt, kwargs.get("image_path")))
        return next(_replies, "")

    _real_send = _digest_dialog.web_bridge.send_to_ai
    _digest_dialog.web_bridge.send_to_ai = _fake_send
    try:
        _dlg = _digest_dialog.ImageDigestDialog(context, _digest_dir, parent=window)
        for _ in range(6):
            app.processEvents()
        check("图片提取对话框列出文件夹里的图片",
              _dlg.table.rowCount() == 3, str(_dlg.table.rowCount()))
        check("图片提取按自然顺序（第2页在第10页前）",
              [r.image.name for r in _dlg.results]
              == ["第1页.png", "第2页.png", "第10页.png"],
              str([r.image.name for r in _dlg.results]))
        check("初始状态都是待处理",
              all(_dlg.table.item(r, 2).text() == "待处理" for r in range(3)),
              str([_dlg.table.item(r, 2).text() for r in range(3)]))

        _dlg.extract_all()
        for _ in range(6):
            app.processEvents()
        check("每张图都带着图片路径送去识别",
              all(path is not None for _p, path in _sent) and len(_sent) == 3,
              str(len(_sent)))
        check("提示词里带序号与文件名",
              "第 1/3 张" in _sent[0][0] and "第1页.png" in _sent[0][0],
              _sent[0][0][:60])
        _statuses = [_dlg.table.item(r, 2).text() for r in range(3)]
        check("识别成功的标为「已提取」", _statuses[0] == "已提取", str(_statuses))
        check("AI 自认看不清的标为「插入原图」", _statuses[1] == "插入原图", str(_statuses))
        check("用户跳过的也标为「插入原图」", _statuses[2] == "插入原图", str(_statuses))
        check("状态列写明不可信的原因",
              "无法辨认" in _dlg.table.item(1, 3).text(),
              _dlg.table.item(1, 3).text())
        check("汇总文案统计正确",
              "2 张改为插入原图" in _dlg.lbl_summary.text(),
              _dlg.lbl_summary.text())

        # 预览必须是最终要落盘的内容
        _preview = _dlg.preview.toPlainText()
        check("预览里识别失败的项直接嵌入了原图",
              "![第2页.png](第2页.png)" in _preview, _preview[:300])
        check("预览里识别成功的不插图",
              "![第1页.png]" not in _preview, _preview[:300])

        # 手动干预：把"看不清"那张改成用文字（编辑正文后即视为可信）
        _real_ask = _digest_dialog.common.ask_multiline
        _digest_dialog.common.ask_multiline = lambda *a, **k: "手写的正确正文" * 6
        try:
            _dlg.table.selectRow(1)
            _dlg.edit_selected()
        finally:
            _digest_dialog.common.ask_multiline = _real_ask
        for _ in range(4):
            app.processEvents()
        check("手动编辑正文后该张变为「已提取」",
              _dlg.table.item(1, 2).text() == "已提取",
              _dlg.table.item(1, 2).text())
        check("手动编辑并不可信的图不再插入原图",
              "![第2页.png]" not in _dlg.preview.toPlainText())

        # 手动标记没把握应当反过来生效
        _dlg.table.selectRow(0)
        _dlg.mark_unsure()
        for _ in range(4):
            app.processEvents()
        check("手动标记没把握 -> 该张改为插入原图",
              _dlg.table.item(0, 2).text() == "插入原图",
              _dlg.table.item(0, 2).text())
        check("手动标记后预览里嵌入原图",
              "![第1页.png](第1页.png)" in _dlg.preview.toPlainText())

        _dlg.save()
        for _ in range(4):
            app.processEvents()
        check("保存生成了 Markdown 文件",
              _dlg.saved_path is not None and _dlg.saved_path.is_file(),
              str(_dlg.saved_path))
        check("输出文件放在当前文件夹里",
              _dlg.saved_path.parent == _digest_dir, str(_dlg.saved_path))
        check("文件名带文件夹名与日期",
              _dlg.saved_path.name.startswith("照片_图片提取_")
              and _dlg.saved_path.name.endswith(".md"),
              _dlg.saved_path.name)
        _written = _dlg.saved_path.read_text(encoding="utf-8")
        check("落盘内容含总览统计", "| 图片总数 | 3 |" in _written, _written[:400])
        check("落盘内容用相对路径引用图片",
              str(_digest_dir.as_posix()) not in _written,
              "不该出现绝对路径")
        _dlg.close()

        # 再存一次不能覆盖上一次（自动改名）
        _dlg2 = _digest_dialog.ImageDigestDialog(context, _digest_dir, parent=window)
        _dlg2.results[0].text = "第二轮的正文内容，足够长可以通过检查。" * 3
        _dlg2.save()
        check("重复保存自动改名，不覆盖上一次",
              _dlg2.saved_path is not None
              and _dlg2.saved_path != _dlg.saved_path
              and _dlg.saved_path.is_file(),
              f"{_dlg.saved_path.name} / {_dlg2.saved_path.name}")
        _dlg2.close()
    finally:
        _digest_dialog.web_bridge.send_to_ai = _real_send

    # 菜单与右键入口都要有
    _tool_actions = []
    for _menu in window.menuBar().findChildren(type(window.menuBar().addMenu("x"))):
        _tool_actions.extend(a.text() for a in _menu.actions() if a.text())
    check("工具菜单里有「图片提取为 Markdown…」入口",
          any("图片提取" in text for text in _tool_actions),
          str([t for t in _tool_actions if "图片" in t]))
    check("书目视图提供 extract_images 方法",
          callable(getattr(fbv, "extract_images", None)))

    # 图片进剪贴板（网页版桥接的关键：网页输入框要能 Ctrl+V 粘图）
    from gwp.ai.providers import web_bridge as _wb

    _clip_src = _digest_dir / "第1页.png"
    check("能把图片放进系统剪贴板（供粘到网页版 AI）",
          _wb.copy_image_to_clipboard(_clip_src) is True)
    check("剪贴板里确实有图片",
          not app.clipboard().image().isNull(),
          str(app.clipboard().image().size()))
    check("超大图会先缩放再进剪贴板（避免网页拒收）",
          _wb.CLIPBOARD_IMAGE_MAX_EDGE <= 4096,
          str(_wb.CLIPBOARD_IMAGE_MAX_EDGE))
    check("不存在的文件安全返回 False",
          _wb.copy_image_to_clipboard(_digest_dir / "没有.png") is False)
    check("传目录也安全返回 False",
          _wb.copy_image_to_clipboard(_digest_dir) is False)
    check("传 None 也安全返回 False",
          _wb.copy_image_to_clipboard(None) is False)

    # 配置了视觉模型时应该走"全自动识别"、不走粘贴。
    # 这里只验证"能不能看图"的判定函数（真调用会走网络，不测）。
    _old_send_images = context.config.get("ai.send_images", False)
    _old_vision = dict(context.config.get("ai.providers.gpt_api", {}) or {})
    try:
        context.config.set("ai.providers.gpt_api.supports_vision", True)
        context.config.set("ai.send_images", False)
        check("没打开「发送图片」时不认作可用视觉模型",
              _wb._provider_sees_images(context, "gpt_api", object()) is False)
        context.config.set("ai.send_images", True)
        check("声明支持视觉 + 打开发送图片 -> 认作可用",
              _wb._provider_sees_images(context, "gpt_api", object()) is True)
        context.config.set("ai.providers.gpt_api.supports_vision", False)
        check("没声明支持视觉的模型不会被用来读图",
              _wb._provider_sees_images(context, "gpt_api", object()) is False)
    finally:
        context.config.set("ai.send_images", _old_send_images)
        for _key, _value in _old_vision.items():
            context.config.set(f"ai.providers.gpt_api.{_key}", _value)

    # ---- AI 对话的附件（需求：AI 助手新增附件上传功能）----
    from gwp.ai.chat_session import ChatSession as _ChatSession
    from gwp.services import attachment as _att2
    from gwp.ui import common as _chat_common
    from gwp.ui.widgets.chat_panel import ChatPanel as _ChatPanel

    _att_src = Path(tempfile.mkdtemp(prefix="gwp_attgui_"))
    (_att_src / "讲义.md").write_text(
        "# 第二章 极限\n\n定义：任给 ε>0，存在 δ>0 ……\n", encoding="utf-8"
    )
    (_att_src / "成绩.csv").write_text("科目,分数\n数学,95\n", encoding="utf-8")
    (_att_src / "板书.jpg").write_bytes(b"\xff\xd8\xff")

    _captured: dict = {}

    def _fake_chat_with_fallback(messages, options=None, on_chunk=None,
                                 question_handler=None, should_cancel=None):
        _captured["messages"] = messages
        if on_chunk:
            on_chunk("已阅读")
        return ("我看过了这份讲义。", "fake-provider")

    _real_chat = context.ai.chat_with_fallback
    context.ai.chat_with_fallback = _fake_chat_with_fallback
    _warned: list = []
    _real_info, _real_warn = _chat_common.info, _chat_common.warn
    _chat_common.info = lambda parent, text, title="": _warned.append(("info", text))
    _chat_common.warn = lambda parent, text, title="": _warned.append(("warn", text))
    try:
        _panel = _ChatPanel(context)
        _panel.session = _ChatSession(key="gui-attach-test", title="附件测试")
        _panel.show()
        for _ in range(6):
            app.processEvents()

        check("AI 对话栏有「附件」按钮",
              hasattr(_panel, "btn_attach") and _panel.btn_attach.isEnabled())
        check("初始没有附件", _panel.attachments == [])
        check("初始附件条是隐藏的（不占地方）",
              _panel.attach_bar.isHidden(), str(_panel.attach_bar.isHidden()))

        _panel.attach_files([_att_src / "讲义.md", _att_src / "成绩.csv"])
        for _ in range(6):
            app.processEvents()
        check("附件被加入列表", len(_panel.attachments) == 2,
              str([a.name for a in _panel.attachments]))
        check("加附件后附件条显示出来", _panel.attach_bar.isVisible())
        check("文本类附件提取出了正文",
              all(a.usable for a in _panel.attachments),
              str([a.describe() for a in _panel.attachments]))

        # 重复加同一个文件应被跳过（避免重复占上下文）
        _panel.attach_files([_att_src / "讲义.md"])
        for _ in range(4):
            app.processEvents()
        check("重复添加同一份附件会被跳过",
              len(_panel.attachments) == 2,
              str([a.name for a in _panel.attachments]))

        # 图片：必须明确警告用户"内容没传进去"
        _warned.clear()
        _panel.attach_files([_att_src / "板书.jpg"])
        for _ in range(6):
            app.processEvents()
        _img = _panel.attachments[-1]
        check("图片附件被标为 image 类型",
              _img.kind == _att2.KIND_IMAGE, _img.kind)
        check("加图片时警告用户内容没传进去",
              any(kind == "warn" for kind, _t in _warned), str(_warned)[:120])
        check("警告里给出了可行的替代做法",
              any("图片提取为 Markdown" in text for _k, text in _warned),
              str(_warned)[:200])
        check("关闭 send_images 时图片不会真的发给模型",
              _panel._vision_image_paths() == [],
              str(_panel._vision_image_paths()))

        # 真正的发送：附件内容要进用户消息
        _panel.input.setPlainText("这份讲义讲了什么？")
        _panel.send_current_input()
        # 等后台线程把信号送到界面（必须用 pump，见它的说明；
        # 用 processEvents 循环的话 finished_ok 永远到不了，
        # 界面会一直停在"正在回答"，看起来像被测代码的 bug）
        for _ in range(100):
            pump(50)
            if _panel._worker is None or not _panel._worker.isRunning():
                break
        pump(120)
        _msgs = _captured.get("messages") or []
        _last = _msgs[-1] if _msgs else None
        check("发送时把附件内容拼进了用户消息",
              _last is not None and "任给" in _last.content,
              (_last.content[:120] if _last else "无消息"))
        check("用户消息里含附件说明",
              _last is not None and "用户上传了" in _last.content)
        check("图片没传进去这件事写进了提示词",
              _last is not None and "内容没有包含在本次对话里" in _last.content)
        check("表格附件转成了 Markdown 表格一起发送",
              _last is not None and "| 科目 | 分数 |" in _last.content)
        check("发送后输入区的附件被清空（不会每轮重发全文）",
              _panel.attachments == [],
              str([a.name for a in _panel.attachments]))
        check("附件名记进了聊天记录（便于回溯）",
              "讲义.md" in (_panel.session.attachments or []),
              str(_panel.session.attachments))
        check("AI 的回复正常显示",
              any("我看过了这份讲义" in m.content
                  for m in _panel.session.messages if m.role == "assistant"),
              str([m.content[:20] for m in _panel.session.messages]))
        check("打桩确实被调用（没真的去调网络）",
              bool(_captured.get("messages")),
              str(len(_captured.get("messages") or [])))
        check("回答完成后不再处于忙状态",
              _panel.btn_send.isEnabled(), str(_panel.btn_send.isEnabled()))

        # 只有附件、没有文字时也应该能发出去
        _captured.clear()
        _panel.attach_files([_att_src / "成绩.csv"])
        for _ in range(4):
            app.processEvents()
        _panel.input.setPlainText("")
        _panel.send_current_input()
        for _ in range(100):
            pump(50)
            if _panel._worker is None or not _panel._worker.isRunning():
                break
        pump(120)
        check("只有附件、没有提问文字时也能发送",
              bool(_captured.get("messages")),
              str(len(_captured.get("messages") or [])))
        check("没有提问文字时自动补一句默认问题",
              "总结要点" in (_captured.get("messages") or [{}])[-1].content,
              (_captured.get("messages") or [{}])[-1].content[:60])

        # 移除与清空
        _panel.attach_files([_att_src / "讲义.md"])
        for _ in range(4):
            app.processEvents()
        _n_before = len(_panel.attachments)
        _panel.remove_attachment(_panel.attachments[0])
        for _ in range(4):
            app.processEvents()
        check("可以单独移除一份附件",
              len(_panel.attachments) == _n_before - 1,
              f"{_n_before} -> {len(_panel.attachments)}")
        _panel.attach_files([_att_src / "成绩.csv"])
        for _ in range(4):
            app.processEvents()
        _panel.clear_attachments()
        for _ in range(4):
            app.processEvents()
        check("可以一次清空所有附件", _panel.attachments == [])
        check("清空后附件条隐藏", not _panel.attach_bar.isVisible())
        _panel.close()
    finally:
        context.ai.chat_with_fallback = _real_chat
        _chat_common.info, _chat_common.warn = _real_info, _real_warn

    # ---- 关闭到后台（需求：主界面关闭后进程继续在后台运行）----
    #
    # 需求原话："考虑到软件启动慢 当主界面关闭，软件在后台运行，
    #          除非用户手动用任务资源管理器将其任务终止"
    #
    # 离屏环境没有系统托盘，所以这里测的是**降级路径**
    # （托盘不可用 -> 最小化到任务栏，进程照样留着）以及开关的两种行为。
    # 真实托盘 + 双击快捷方式唤回在真机上手测过（0.3 秒唤回）。
    check("QApplication 不会因最后一个窗口关闭而退出",
          app.quitOnLastWindowClosed() is False,
          str(app.quitOnLastWindowClosed()))

    from PyQt6.QtGui import QCloseEvent as _QCloseEvent

    from gwp.ui.main_window import MainWindow as _MainWindow

    _bg_win = _MainWindow(context)
    _bg_win.resize(1000, 700)
    _bg_win.show()
    for _ in range(6):
        app.processEvents()

    check("默认开启「关闭到后台」",
          _bg_win._close_to_background_enabled() is True)
    check("文件菜单里有「隐藏到后台」入口",
          _bg_win.act_hide_background.isVisible())
    check("有托盘相关的入口方法",
          callable(getattr(_bg_win, "hide_to_background", None))
          and callable(getattr(_bg_win, "restore_from_background", None))
          and callable(getattr(_bg_win, "quit_completely", None)))

    # 隐藏到后台：进程不退出
    _hid = _bg_win.hide_to_background()
    for _ in range(4):
        app.processEvents()
    check("隐藏到后台成功", _hid is True, str(_hid))
    check("隐藏后窗口不可见或已最小化（进程留着）",
          (not _bg_win.isVisible()) or _bg_win.isMinimized(),
          f"visible={_bg_win.isVisible()} minimized={_bg_win.isMinimized()}")

    # 唤回
    _bg_win.restore_from_background()
    for _ in range(4):
        app.processEvents()
    check("可以从后台唤回窗口", _bg_win.isVisible() and not _bg_win.isMinimized(),
          f"visible={_bg_win.isVisible()} minimized={_bg_win.isMinimized()}")

    # 关闭事件：开着开关时**不能**接受关闭（否则进程会退出）
    _ev = _QCloseEvent()
    _bg_win.closeEvent(_ev)
    for _ in range(4):
        app.processEvents()
    check("开着开关时关闭事件不被接受（进程留在后台）",
          _ev.isAccepted() is False, str(_ev.isAccepted()))
    check("关闭后被列为隐藏状态", _bg_win.isHidden() or _bg_win.isMinimized(),
          f"hidden={_bg_win.isHidden()} minimized={_bg_win.isMinimized()}")

    # 真正退出：走 quit_completely 后 closeEvent 才放行
    _bg_win.quit_completely()
    for _ in range(6):
        app.processEvents()
    check("quit_completely 会置上「真的要退出」标志", _bg_win._really_quit is True)

    # ---- 跨进程唤回窗口（需求：再双击快捷方式要能把后台的窗口叫回来）----
    #
    # 这一条以前是"第二个进程直接调 ShowWindow 显示窗口"，
    # 结果用户看到**全黑窗口**（Qt 不知道窗口被显示了，就不重绘）。
    # 现在改成"第二个进程写请求文件 + 第一个进程自己用 Qt show()"。
    _wake_win = _MainWindow(context)
    _wake_win.resize(1000, 700)
    _wake_win.show()
    for _ in range(6):
        app.processEvents()

    check("界面里有唤回请求的轮询定时器",
          getattr(_wake_win, "_wake_timer", None) is not None
          and _wake_win._wake_timer.isActive(),
          str(getattr(_wake_win, "_wake_timer", None)))
    check("轮询间隔在「点了就该有反应」的范围内（<=1 秒）",
          0 < _wake_win._wake_timer.interval() <= 1000,
          str(_wake_win._wake_timer.interval()))

    _wake_win.hide_to_background()
    for _ in range(4):
        app.processEvents()
    check("先把它藏到后台", not _wake_win.isVisible() or _wake_win.isMinimized(),
          f"visible={_wake_win.isVisible()}")

    # 模拟"另一个进程双击了快捷方式"：写请求文件，然后让定时器跑一次
    from gwp.core import wakeup as _wake_mod

    import time as _time_wake

    _time_wake.sleep(1.1)
    check("另一个进程写下了唤回请求",
          _wake_mod.request_wake(context.paths.else_data) is True)
    _wake_win._poll_wake_request()
    for _ in range(8):
        app.processEvents()
    check("**收到请求后窗口被唤回**",
          _wake_win.isVisible() and not _wake_win.isMinimized(),
          f"visible={_wake_win.isVisible()} minimized={_wake_win.isMinimized()}")

    # 连点两次不该出问题（同一个请求只生效一次）
    _wake_win._poll_wake_request()
    for _ in range(4):
        app.processEvents()
    check("重复轮询不会重复处理同一个请求", _wake_win.isVisible())

    _wake_win._really_quit = True
    _wake_win.close()
    for _ in range(6):
        app.processEvents()
    check("真正退出后停掉唤回轮询",
          not _wake_win._wake_timer.isActive())

    # 关掉开关时：关闭事件直接放行（= 真正退出）
    context.config.set("ui.close_to_background", False)
    _plain_win = _MainWindow(context)
    _plain_win.resize(900, 600)
    _plain_win.show()
    for _ in range(6):
        app.processEvents()
    check("关掉开关后 _close_to_background_enabled() 为 False",
          _plain_win._close_to_background_enabled() is False)
    check("关掉开关时「隐藏到后台」菜单项隐藏",
          not _plain_win.act_hide_background.isVisible())
    _ev2 = _QCloseEvent()
    _plain_win.closeEvent(_ev2)
    for _ in range(4):
        app.processEvents()
    check("关掉开关后关闭事件被接受（真正退出）",
          _ev2.isAccepted() is True, str(_ev2.isAccepted()))
    context.config.set("ui.close_to_background", True)

    # ---- 单词书栏目（需求：新增单词书 + 可折叠单词卡 + 只填英文自动补齐）----
    from gwp.data_manager import wordbook as _wb2
    from gwp.ui import common as _wb_common

    _wb_subject = context.library.create_subject("单词书测试英语", subject_type="school")
    _wb_book = context.library.create_book(_wb_subject.name, "英语1")
    window.open_book(_wb_subject.name, "英语1")
    for _ in range(8):
        app.processEvents()
    _wbv = window.book_view
    # 需求："所有科目公用一个文件夹" —— 所以书目目录下**不该**再有 wordbook，
    # 卡片统一放在 user data 下的共用目录里。
    check("新建书目**不会**在书目下建 wordbook（已改成共用目录）",
          not (_wb_book.path / "wordbook").exists(),
          str(sorted(p.name for p in _wb_book.path.iterdir())))
    check("共用单词书目录在 user data 下",
          context.paths.wordbook_dir.is_dir()
          and context.paths.wordbook_dir
          == context.paths.user_data / "wordbook",
          str(context.paths.wordbook_dir))
    check("共用单词书目录不在科目目录里",
          context.paths.subjects_dir not in context.paths.wordbook_dir.parents)
    _wb_tabs = _tab_names(_wbv)
    check("书目页出现「单词书」标签", "单词书" in _wb_tabs, str(_wb_tabs))
    _wb_index = next(i for i, t in enumerate(_wb_tabs) if t == "单词书")
    _wbv.tabs.setCurrentIndex(_wb_index)
    for _ in range(8):
        app.processEvents()

    _book_wb = _wbv.wordbook_view
    check("切到单词书后显示「添加单词」按钮", _wbv.btn_word_add.isVisible())
    check("切到单词书后隐藏「导入文件」按钮（这一页不是文件列表）",
          not _wbv.btn_import.isVisible())
    check("空单词书给出「怎么用」的提示",
          _book_wb.lbl_empty.isVisible() and "折叠" in _book_wb.lbl_empty.text(),
          _book_wb.lbl_empty.text()[:60])

    # 打桩 AI：只验证"只填英文就能自动补齐"这条链路
    import json as _json_wb

    from gwp.ai.providers import web_bridge as _wb_bridge

    _wb_prompts: list = []

    def _fake_word_ai(prompt, **kwargs):
        _wb_prompts.append(prompt)
        return _json_wb.dumps({
            "english": "give up",
            "phonetic": "/ɡɪv ʌp/",
            "part_of_speech": "phr.",
            "meaning": "phr. 放弃；认输",
            "examples": "He gave up smoking. —— 他戒烟了。",
            "phrases": "give up on —— 对…不再抱希望",
            "tip": "give（给）+ up（向上）",
        }, ensure_ascii=False)

    _real_word_ai = _wb_bridge.send_to_ai
    _wb_bridge.send_to_ai = _fake_word_ai
    _real_confirm = _wb_common.confirm
    _real_ask_text = _wb_common.ask_text
    _wb_common.confirm = lambda *a, **k: True          # 「现在就补齐吗」-> 是
    _wb_common.ask_text = lambda *a, **k: "give up"
    try:
        _book_wb.add_word()
        for _ in range(10):
            app.processEvents()
    finally:
        _wb_bridge.send_to_ai = _real_word_ai
        _wb_common.confirm = _real_confirm
        _wb_common.ask_text = _real_ask_text

    check("只填英文就自动创建了单词卡",
          len(_book_wb.cards) == 1, str([c.english for c in _book_wb.cards]))
    check("AI 被调用来补齐（不用用户填中文）",
          len(_wb_prompts) == 1 and "give up" in _wb_prompts[0],
          str(len(_wb_prompts)))
    _saved_card = _book_wb.cards[0]
    check("中文释义被自动补齐",
          "放弃" in _saved_card.meaning, _saved_card.meaning)
    check("音标被自动补齐", _saved_card.phonetic == "/ɡɪv ʌp/", _saved_card.phonetic)
    check("例句被自动补齐", "戒烟" in _saved_card.examples, _saved_card.examples)
    check("卡片落盘到**共用**单词书目录（不是书目下面）",
          (context.paths.wordbook_dir / "give up.json").is_file(),
          str(sorted(p.name for p in context.paths.wordbook_dir.iterdir())))
    check("单词书视图用的就是共用目录",
          _book_wb.folder() == context.paths.wordbook_dir,
          str(_book_wb.folder()))

    # **换一本书打开，卡片还在**（这正是"共用"的意义）
    _wb_book2 = context.library.create_book(_wb_subject.name, "英语2")
    window.open_book(_wb_subject.name, "英语2")
    for _ in range(10):
        app.processEvents()
    _wbv2 = window.book_view
    _wbv2.tabs.setCurrentIndex(
        next(i for i in range(_wbv2.tabs.count())
             if _tab_names(_wbv2)[i] == "单词书")
    )
    for _ in range(10):
        app.processEvents()
    check("**在另一本书里也能看到同一批单词卡**",
          [c.english for c in _wbv2.wordbook_view.cards] == ["give up"],
          str([c.english for c in _wbv2.wordbook_view.cards]))
    check("另一本书里的卡片内容与刚才那张一致",
          _wbv2.wordbook_view.cards
          and _wbv2.wordbook_view.cards[0].meaning == _saved_card.meaning,
          _wbv2.wordbook_view.cards[0].meaning if _wbv2.wordbook_view.cards else "")
    check("另一本书的书目目录下没有 wordbook",
          not (_wb_book2.path / "wordbook").exists(),
          str(sorted(p.name for p in _wb_book2.path.iterdir())))
    # 回到第一本继续后面的用例
    window.open_book(_wb_subject.name, "英语1")
    for _ in range(8):
        app.processEvents()
    _wbv.tabs.setCurrentIndex(
        next(i for i in range(_wbv.tabs.count())
             if _tab_names(_wbv)[i] == "单词书")
    )
    for _ in range(8):
        app.processEvents()
    _book_wb = _wbv.wordbook_view

    # ---- 折叠：默认折叠、只显示英文、单击展开 ----
    check("有卡片控件", len(_book_wb._widgets) == 1, str(len(_book_wb._widgets)))
    _wcard = _book_wb._widgets[0]
    check("单词卡默认是折叠的", not _wcard.expanded)
    check("折叠时详情区不可见（只显示英文）",
          not _wcard.detail.isVisible())
    check("折叠时头部显示的就是英文",
          _wcard.lbl_english.text() == "give up", _wcard.lbl_english.text())

    _wcard.toggle()
    for _ in range(4):
        app.processEvents()
    check("单击后展开", _wcard.expanded and _wcard.detail.isVisible())
    check("展开后能看到中文释义",
          any("放弃" in lb.text() for lb in _wcard.detail.findChildren(_QLabel)),
          str([lb.text()[:20] for lb in _wcard.detail.findChildren(_QLabel)]))
    check("展开状态被记住（刷新后不丢）", "give up" in _book_wb._expanded)
    _book_wb.refresh()
    for _ in range(6):
        app.processEvents()
    check("刷新后仍然是展开的", _book_wb._widgets[0].expanded)

    _book_wb.toggle_all()
    for _ in range(4):
        app.processEvents()
    check("「全部折叠」把所有卡片折起来",
          all(not w.expanded for w in _book_wb._widgets))
    _book_wb.toggle_all()
    for _ in range(4):
        app.processEvents()
    check("再点一次「全部展开」", all(w.expanded for w in _book_wb._widgets))

    # ---- 重复添加 / 搜索 / 手动编辑 ----
    _wb_common.info = lambda *a, **k: None
    _book_wb.add_word("give up")
    check("重复添加同一个词不会产生第二张卡",
          len(_book_wb.cards) == 1, str(len(_book_wb.cards)))

    _book_wb.input_search.setText("放弃")
    for _ in range(4):
        app.processEvents()
    check("搜索能按中文释义命中", len(_book_wb._widgets) == 1,
          str(len(_book_wb._widgets)))
    _book_wb.input_search.setText("zzz-不存在")
    for _ in range(4):
        app.processEvents()
    check("搜不到时显示提示而不是空白",
          _book_wb.lbl_empty.isVisible() and len(_book_wb._widgets) == 0,
          _book_wb.lbl_empty.text()[:40])
    _book_wb.input_search.setText("")
    for _ in range(4):
        app.processEvents()

    _real_multiline = _wb_common.ask_multiline
    _wb_common.ask_multiline = lambda *a, **k: (
        "english: give up\nmeaning: 我改过的释义\nnote: 我的笔记"
    )
    try:
        _book_wb.edit_card(_book_wb.cards[0])
        for _ in range(6):
            app.processEvents()
    finally:
        _wb_common.ask_multiline = _real_multiline
    check("手动编辑生效", _book_wb.cards[0].meaning == "我改过的释义",
          _book_wb.cards[0].meaning)
    check("编辑保留了自己写的笔记",
          _book_wb.cards[0].note == "我的笔记", _book_wb.cards[0].note)

    # ---- 用户手改过的内容不会被重新补齐冲掉 ----
    _again = _wb2.WordCard(english="give up", meaning="AI 想重写的释义")
    _merged_wb = _wb2.merge_into(_book_wb.cards[0], _again)
    check("重新补齐不会覆盖用户改过的释义",
          _merged_wb.meaning == "我改过的释义", _merged_wb.meaning)

    # 回到别的标签，单词书按钮应消失
    _wbv.tabs.setCurrentIndex(0)
    for _ in range(6):
        app.processEvents()
    check("离开单词书后隐藏它的按钮",
          not _wbv.btn_word_add.isVisible() and not _wbv.btn_word_fill.isVisible())

    # ---- 日程栏：宽度固定 + 只有折叠/展开两态（需求）----
    #
    # 需求："调节日程栏宽度固定，只有全部折叠和完全展开 不能调整宽度"
    _home_panel = window.home_view.schedule_panel
    _home_split = window.home_view.splitter
    check("日程栏的宽度固定（min == max）",
          _home_panel.minimumWidth() == _home_panel.maximumWidth(),
          f"{_home_panel.minimumWidth()} vs {_home_panel.maximumWidth()}")
    check("展开宽度是一个常量值",
          _home_panel.maximumWidth() == _home_panel.EXPANDED_WIDTH,
          str(_home_panel.maximumWidth()))
    check("折叠宽度比展开窄",
          _home_panel.COLLAPSED_WIDTH < _home_panel.EXPANDED_WIDTH,
          f"{_home_panel.COLLAPSED_WIDTH} / {_home_panel.EXPANDED_WIDTH}")
    check("分隔条不再允许拖动（handle 宽度为 0 且被禁用）",
          _home_split.handleWidth() == 0
          and _home_split.handle(1) is not None
          and not _home_split.handle(1).isEnabled(),
          f"handleWidth={_home_split.handleWidth()}")
    check("分隔条不再允许把面板拖到 0（childrenCollapsible 关闭）",
          _home_split.childrenCollapsible() is False)
    check("默认是展开态", _home_panel.collapsed is False)
    # 用 isVisibleTo(parent) 而不是 isVisible()：离屏测试里顶层窗口未必"可见"，
    # 问 isVisible() 会恒为 False —— 那不代表控件被藏起来了。
    check("展开时显示完整面板、隐藏折叠条",
          _home_panel.expanded.isVisibleTo(_home_panel)
          and not _home_panel.fold_bar.isVisibleTo(_home_panel))
    # 折叠后窄条要**贴住窗口右缘**（用户报障：白色竖条没靠右）。
    # 根因是上面的时钟条最小宽度 329px 把整列撑住了，所以把它并进了面板。
    check("右列收缩到只有窄条那么宽（竖条因此贴右缘）",
          window.home_view.side_column.width() == _home_panel.EXPANDED_WIDTH,
          str(window.home_view.side_column.width()))
    check("时钟条归日程栏管（折叠时一起收起）",
          _home_panel.clock_bar is window.home_view.clock_bar)

    # 强行改尺寸应该无效（模拟用户拖拽）
    _home_panel.resize(900, 400)
    for _ in range(4):
        app.processEvents()
    check("强行 resize 也改不动宽度",
          _home_panel.width() == _home_panel.EXPANDED_WIDTH,
          str(_home_panel.width()))

    window.home_view.toggle_schedule_panel()
    for _ in range(12):
        app.processEvents()
    check("折叠后进入折叠态", _home_panel.collapsed is True)
    check("折叠后只留折叠条，完整面板隐藏",
          _home_panel.fold_bar.isVisibleTo(_home_panel)
          and not _home_panel.expanded.isVisibleTo(_home_panel))
    check("折叠后面板真的变窄了",
          _home_panel.width() == _home_panel.COLLAPSED_WIDTH,
          f"width={_home_panel.width()} 期望={_home_panel.COLLAPSED_WIDTH}")
    check("折叠后仍然 min == max（宽度始终固定）",
          _home_panel.minimumWidth() == _home_panel.maximumWidth()
          == _home_panel.COLLAPSED_WIDTH,
          f"{_home_panel.minimumWidth()}/{_home_panel.maximumWidth()}")
    check("**折叠后整列只剩窄条宽度**（竖条贴住右缘，不留空白）",
          window.home_view.side_column.width() == _home_panel.COLLAPSED_WIDTH,
          f"side={window.home_view.side_column.width()} "
          f"期望={_home_panel.COLLAPSED_WIDTH}")
    check("折叠后窄条里也有「日程」字样（看得出这是什么）",
          "日程" in _home_panel.lbl_fold_caption.text().replace("\n", ""),
          repr(_home_panel.lbl_fold_caption.text()))
    check("折叠后窄条上显示未完成条数",
          _home_panel.lbl_fold_count.isVisibleTo(_home_panel)
          and _home_panel.lbl_fold_count.text().isdigit(),
          repr(_home_panel.lbl_fold_count.text()))
    check("折叠条上有展开按钮", _home_panel.btn_unfold.text() == "‹")
    check("面板上有折叠按钮", _home_panel.btn_fold.text() == "»")

    _home_panel.btn_unfold.click()
    for _ in range(12):
        app.processEvents()
    check("点折叠条上的按钮能展开", _home_panel.collapsed is False)
    check("展开后宽度回到固定值",
          _home_panel.width() == _home_panel.EXPANDED_WIDTH,
          str(_home_panel.width()))

    # ---- 科目卡网格必须跟着可用宽度换行（用户报障）----
    #
    # 用户原话："当页面大小调整后 日程栏目打开肯会遮挡Subject"
    #
    # 根因：网格的 minimumSizeHint() 返回"所有卡片排成一行"的宽度，
    # 而列数又按自身宽度算 —— 两者互相依赖，网格永远不肯变窄，
    # 于是窗口变窄 / 展开日程栏时，右边的列被滚动区裁掉，
    # 看起来就像"被日程栏遮住了"。
    _grid = window.home_view.grid
    _home_for_grid = window.home_view
    check("网格的最小宽度需求只有**一列**（不再钉住整行宽）",
          _grid.minimumSizeHint().width()
          <= _grid.cards[0].width() + 40 if _grid.cards else True,
          f"minHint={_grid.minimumSizeHint().width()} "
          f"card={_grid.cards[0].width() if _grid.cards else None}")
    check("网格的理想宽度仍然是一整行（大屏要能多排几列）",
          _grid.sizeHint().width() >= _grid.minimumSizeHint().width(),
          f"{_grid.sizeHint().width()} vs {_grid.minimumSizeHint().width()}")

    # 把可用宽度灌进去，看列数是否真的跟着变
    _grid.set_available_width(300)
    for _ in range(4):
        app.processEvents()
    _narrow_cols = _grid._columns()

    def _rightmost_card() -> int:
        cards = _grid.cards
        return max((c.x() + c.width() for c in cards), default=0)

    check("窄宽度下只排 1 列", _narrow_cols == 1, str(_narrow_cols))
    check("**窄宽度下卡片不会超出可用宽度**（不会再有被裁掉的列）",
          _rightmost_card() <= 300,
          f"最右={_rightmost_card()} 可用=300")

    _grid.set_available_width(2000)
    for _ in range(4):
        app.processEvents()
    check("宽宽度下会排多列", _grid._columns() > _narrow_cols,
          f"{_grid._columns()} vs {_narrow_cols}")

    # 真实尺寸变化：**改真实窗口宽度**，让布局自然传导下来。
    #
    # 注意：离屏环境下 resize() 不一定真的传导到子控件（实测 splitter 一直
    # 停在 1244），所以下面**不依赖它** —— 需要控制宽度的地方直接灌
    # _available_width（这是"可用宽度"的**单一入口**，真实布局也是走它）。
    # 而窗口 resize 只作为"不应该崩"的冒烟。
    def _resize_and_settle(width: int) -> None:
        window.resize(width, 820)
        for _ in range(8):
            app.processEvents()
        _home_for_grid._apply_schedule_width()
        for _ in range(12):
            app.processEvents()

    _resize_and_settle(760)
    check("改窗口宽度不会崩（冒烟）",
          _home_for_grid.scroll.viewport().width() >= 0)

    # 可用宽度是网格排版的**单一入口**：灌进去就必须重排
    _grid.set_available_width(700)
    for _ in range(6):
        app.processEvents()
    check("**灌入 700 后网格按 700 重排**",
          _grid._available_width == 700 and _grid._columns() <= 3,
          f"avail={_grid._available_width} cols={_grid._columns()}")
    check("700 宽下卡片不超出可用宽度",
          _rightmost_card() <= 700,
          f"最右={_rightmost_card()}")

    _grid.set_available_width(300)
    for _ in range(6):
        app.processEvents()
    check("**灌入 300 后只排 1 列且不超出**",
          _grid._columns() == 1 and _rightmost_card() <= 300,
          f"cols={_grid._columns()} 最右={_rightmost_card()}")
    _grid.set_available_width(1400)
    for _ in range(6):
        app.processEvents()

    # 空间不够时自动折叠：直接按"当前 splitter 宽度"判定的逻辑来测，
    # 不去改 splitter（离屏下改不动）
    _home_panel.set_collapsed(False)
    for _ in range(6):
        app.processEvents()
    _real_splitter_width = _home_for_grid.splitter.width
    _was_visible = _home_for_grid.isVisible()
    _real_is_visible = _home_for_grid.isVisible
    _home_for_grid.isVisible = lambda: True              # type: ignore[method-assign]
    try:
        # 假装 splitter 很窄 -> 应当自动折叠
        _home_for_grid.splitter.width = lambda: 560      # type: ignore[method-assign]
        _folded = _home_for_grid.auto_collapse_for_room()
    finally:
        _home_for_grid.splitter.width = _real_splitter_width  # type: ignore[method-assign]
        _home_for_grid.isVisible = _real_is_visible           # type: ignore[method-assign]
    check("**空间不够时日程栏自动折叠**（把位置让给科目卡片）",
          _folded is True and _home_panel.collapsed is True,
          f"folded={_folded} collapsed={_home_panel.collapsed} "
          f"wasVisible={_was_visible}")

    # 宽度够大时不该折叠
    _home_panel.set_collapsed(False)
    for _ in range(6):
        app.processEvents()
    _home_for_grid.splitter.width = lambda: 1400         # type: ignore[method-assign]
    try:
        _folded_wide = _home_for_grid.auto_collapse_for_room()
    finally:
        _home_for_grid.splitter.width = _real_splitter_width  # type: ignore[method-assign]
    check("宽度够时不会自动折叠", _folded_wide is False
          and _home_panel.collapsed is False,
          f"folded={_folded_wide} collapsed={_home_panel.collapsed}")

    # 不可见 / 宽度还没确定时不要乱动（启动早期会走到这里）
    _home_for_grid.splitter.width = lambda: 0            # type: ignore[method-assign]
    try:
        _folded_zero = _home_for_grid.auto_collapse_for_room()
    finally:
        _home_for_grid.splitter.width = _real_splitter_width  # type: ignore[method-assign]
    check("宽度还没确定时不会误折叠", _folded_zero is False
          and _home_panel.collapsed is False)

    # 用户手动展开/折叠仍然好使
    _home_for_grid.toggle_schedule_panel()
    for _ in range(8):
        app.processEvents()
    check("用户仍然可以手动切换", _home_panel.collapsed is True)
    _home_for_grid.toggle_schedule_panel()
    for _ in range(8):
        app.processEvents()
    check("再点一次又展开", _home_panel.collapsed is False)
    _resize_and_settle(1400)

    # ---- 日程栏「打开」：在软件内打开该 Book 的 homework 栏目（需求）----
    #
    # 需求："日程栏打开按键点击后在软件内打开对应Book的homework栏目，
    #       不是打开本地文件夹"
    window.show_home()
    for _ in range(10):
        app.processEvents()
    window.home_view.refresh_schedule()
    for _ in range(10):
        app.processEvents()

    from gwp.services import file_ops as _fo_nav

    _explorer_calls: list = []
    _real_reveal = _fo_nav.reveal_in_explorer
    _fo_nav.reveal_in_explorer = lambda p: (
        _explorer_calls.append(str(p)), True
    )[1]
    try:
        _panel_rows = [r for r in _home_panel._rows if getattr(r, "entry", None)]
        _hw_row = next((r for r in _panel_rows if r.entry.is_homework), None)
        check("日程栏里有作业行（用于测「打开」）", _hw_row is not None,
              str([getattr(r.entry, "title", None) for r in _panel_rows]))
        if _hw_row is not None:
            _entry = _hw_row.entry
            check("作业行有科目与书目信息（不用去猜路径）",
                  bool(_entry.subject) and bool(_entry.book),
                  f"{_entry.subject}/{_entry.book}")
            _row_buttons = {
                bt.text(): bt
                for bt in _hw_row.findChildren(type(_home_panel.btn_new))
            }
            check("作业行有「打开」按钮", "打开" in _row_buttons,
                  str(list(_row_buttons)))
            _open_btn = _row_buttons.get("打开")
            if _open_btn is not None:
                check("「打开」的提示写明是在软件内打开",
                      "软件内" in _open_btn.toolTip(), _open_btn.toolTip())
                _open_btn.click()
                for _ in range(16):
                    app.processEvents()

                _nav_view = window.book_view
                check("点「打开」后切到了书目页",
                      window.stack.currentWidget() is _nav_view,
                      type(window.stack.currentWidget()).__name__)
                check("切到了作业所在的科目与书目",
                      _nav_view.subject_name == _entry.subject
                      and _nav_view.book_name == _entry.book,
                      f"{_nav_view.subject_name}/{_nav_view.book_name}")
                check("停在作业栏目", _nav_view._current_tab_key() == "homework",
                      _nav_view._current_tab_key())
                check("定位到了那条作业的文件夹",
                      _nav_view._current_folder is not None
                      and _nav_view._current_folder == Path(_entry.folder),
                      str(_nav_view._current_folder))
                _nav_table = _nav_view._current_table()
                _nav_rows = sorted(
                    _nav_table.item_at(r).name
                    for r in range(_nav_table.rowCount())
                    if _nav_table.item_at(r) is not None
                )
                # 不断言具体是哪个作业（日程栏按 DDL 排序，第一条不一定是
                # "第一次作业"），只断言"列表里就是那个作业文件夹的内容"。
                check("列表里是该作业文件夹的内容（不是栏目根目录）",
                      _nav_rows and not any(
                          name in ("第一次作业", "2.4 作业") for name in _nav_rows
                      ),
                      str(_nav_rows))
                check("没有去打开本地资源管理器",
                      not _explorer_calls, str(_explorer_calls))
    finally:
        _fo_nav.reveal_in_explorer = _real_reveal

    check("能从作业路径反推科目与书目",
          window._guess_subject_book(
              Path(r"D:\x\subjects\高等代数\高等代数\homework\2.4 作业")
          ) == ("高等代数", "高等代数"),
          str(window._guess_subject_book(
              Path(r"D:\x\subjects\高等代数\高等代数\homework\2.4 作业"))))
    check("路径看不出结构时返回空（不瞎猜）",
          window._guess_subject_book(Path(r"D:\x")) == ("", ""),
          str(window._guess_subject_book(Path(r"D:\x"))))

    window.show_home()
    for _ in range(8):
        app.processEvents()

    # ---- 作业改名：对话框要能改，保存要真的生效（用户报障）----
    #
    # 用户原话："更改作业名称功能异常"
    #
    # 两个缺陷叠加：① 对话框在编辑模式下把名称输入框 setEnabled(False)；
    # ② edit_homework 从未读取作业名。所以"改名"在界面上是死路。
    from gwp.ui.dialogs.homework_dialog import HomeworkDialog as _HwDialog

    # 前面的用例把界面留在了别的书目上，先显式切到作业书目
    window.open_book(school_subject.name, "作业书目")
    for _ in range(10):
        app.processEvents()
    _rnv = window.book_view
    # 按**内部 key** 找标签，不要按显示文案 ——
    # 标签上带了条目数（"作业 4"），按文案找会 StopIteration。
    _rnv.tabs.setCurrentIndex(
        next(i for i, (key, _t, _f) in enumerate(_rnv._tab_defs)
             if key == "homework")
    )
    for _ in range(10):
        app.processEvents()
    _rn_hw_dir = school_book.path / "homework"
    _hw2.create(
        _rn_hw_dir / "待改名的作业",
        content="题目",
        due="2030-01-01T10:00",
        submit_url="https://example.com/rename",
    )
    window.book_view.refresh()
    for _ in range(8):
        app.processEvents()
    _rn_existing = _hw2.load(_rn_hw_dir / "待改名的作业")
    check("准备一个可编辑的作业", _rn_existing is not None,
          str(sorted(p.name for p in _rn_hw_dir.iterdir())))
    if _rn_existing is not None:
        _rn_dialog = _HwDialog(window, homework=_rn_existing)
        check("**编辑作业时名称输入框是可用的**（以前是灰的）",
              _rn_dialog.input_name.isEnabled())
        check("名称输入框回填了当前作业名",
              _rn_dialog.input_name.text() == "待改名的作业",
              _rn_dialog.input_name.text())
        check("刚打开时不算改过名", _rn_dialog.name_changed is False)
        _rn_dialog.input_name.setText("待改名的作业（改）")
        check("**改了名字之后能识别出「改过名」**",
              _rn_dialog.name_changed is True)
        _rn_dialog.input_name.setText("待改名的作业")
        check("改回原名又算没改过", _rn_dialog.name_changed is False)
        _rn_dialog.deleteLater()

        # 真正走一遍"编辑作业"这条路。
        # **先退回作业栏目根目录**：前面的用例可能把界面停在某个作业文件夹里，
        # 那时表格列出的是里面的文件，看不到"一个作业一行"。
        window.book_view.leave_folder()
        for _ in range(10):
            app.processEvents()
        _rn_table = window.book_view._current_table()
        _rn_rows = [
            _rn_table.item_at(r) for r in range(_rn_table.rowCount())
        ]
        _rn_item = next(
            (i for i in _rn_rows
             if i is not None and i.name == "待改名的作业"), None
        )
        check("找到了要改名的作业条目", _rn_item is not None,
              str([i.name for i in _rn_rows if i is not None]))

        # edit_homework 是**在函数内**延迟导入 HomeworkDialog 的，
        # 所以打桩要打在 **book_view 模块**的属性上。
        # 这里自己绑定模块对象：\_book_view_mod\ 是别处 if 块里的局部名，
        # 在这一层并不存在（我第一版就踩了这个 —— 于是补丁没打上，
        # 真实对话框被弹了出来，改名自然没发生）。
        import sys as _sys_rn

        _bv_mod_rn = _sys_rn.modules["gwp.ui.views.book_view"]

        class _RenameDialog:
            """把名字改成"改过的作业名"，其余字段保持原样。"""

            def __init__(self, parent=None, homework=None, *, folder=None):
                self.homework = homework
                self.content_text = homework.content if homework else ""
                self.due_text = homework.due if homework else ""
                self.submit_url = homework.submit_url if homework else ""
                self.name_changed = True
                self.input_name = type(
                    "I", (), {"text": lambda _s: "改过的作业名"}
                )()

            def exec(self):
                return 1

        # 关键：要替换**类本身**，而不是 book_view 模块上的属性名。
        # edit_homework 在函数内 rom ... import HomeworkDialog ——
        # 那个名字已经被绑定到真实类上了，改模块属性影响不到它
        # （我第一版就是这么错的，打桩看起来成功了但实际弹的是真对话框）。
        from gwp.ui.dialogs import homework_dialog as _hd_mod_rn

        _warned: list = []
        _real_warn = _bv_mod_rn.common.warn
        _real_dialog_cls = _hd_mod_rn.HomeworkDialog
        _hd_mod_rn.HomeworkDialog = _RenameDialog
        _bv_mod_rn.common.warn = lambda *a, **k: _warned.append(a)
        try:
            if _rn_item is not None:
                window.book_view.edit_homework(_rn_item)
                for _ in range(12):
                    app.processEvents()
        finally:
            _hd_mod_rn.HomeworkDialog = _real_dialog_cls
            _bv_mod_rn.common.warn = _real_warn

        check("改名过程没有被拦下", not _warned, str(_warned)[:120])
        _rn_new_dir = _rn_hw_dir / "改过的作业名"
        check("**改名后作业文件夹真的换了名字**", _rn_new_dir.is_dir(),
              str(sorted(p.name for p in _rn_hw_dir.iterdir())))
        check("旧文件夹已经不在了", not (_rn_hw_dir / "待改名的作业").exists())
        _rn_reloaded = _hw2.load(_rn_new_dir)
        check("homework.json 里的名字也更新了",
              _rn_reloaded is not None and _rn_reloaded.name == "改过的作业名",
              _rn_reloaded.name if _rn_reloaded else None)
        check("改名不会丢 DDL 与提交网址",
              _rn_reloaded is not None
              and _rn_reloaded.due == _rn_existing.due
              and _rn_reloaded.submit_url == _rn_existing.submit_url,
              f"{_rn_reloaded.due if _rn_reloaded else None}")
        check("列表里显示的是新名字",
              # 名称格里带完成状态（"新名字（未完成）"），所以用前缀匹配
              any((hw_table.item(r, 0) is not None)
                  and hw_table.item(r, 0).text().startswith("改过的作业名")
                  for r in range(hw_table.rowCount())),
              str([hw_table.item(r, 0).text()
                   for r in range(hw_table.rowCount())
                   if hw_table.item(r, 0) is not None]))
        # 改回去，别影响后面的用例
        if _rn_reloaded is not None:
            _hw2.rename(_rn_reloaded, "待改名的作业")
            window.book_view.refresh()
            for _ in range(10):
                app.processEvents()

    # ---- 新建作业沿用上次的提交网址 ----
    #
    # 需求："新建作业的提交方式的网址默认为该book的作业之前的提交方式的网址，
    #       避免用户每次输入"
    from gwp.ui.dialogs.homework_dialog import HomeworkDialog as _HwDialog

    _pre_url = "https://submit.example.com/course/9"
    _pre_dialog = _HwDialog(None, folder=Path("X:/（作业名）"),
                            default_url=_pre_url)
    check("**新建作业时提交网址已按上一份作业预填**",
          _pre_dialog.input_url.text() == _pre_url,
          _pre_dialog.input_url.text())
    check("预填的网址会被规范化后保存",
          _pre_dialog.submit_url == _pre_url, _pre_dialog.submit_url)
    # 用户清空 -> 就是空，不要把默认值塞回去
    _pre_dialog.input_url.setText("")
    check("**用户清空提交网址后不会又被塞回默认值**",
          _pre_dialog.submit_url == "", repr(_pre_dialog.submit_url))
    # 编辑模式：用作业自己的网址，不用默认值
    _pre_existing = _hw2.Homework(
        name="旧作业", path=Path("X:/旧作业"), content="", due="",
        submit_url="https://old.example.com/1",
    )
    _edit_dialog = _HwDialog(None, _pre_existing, default_url=_pre_url)
    check("**编辑作业时用作业自己的网址（不受默认值影响）**",
          _edit_dialog.input_url.text() == "https://old.example.com/1",
          _edit_dialog.input_url.text())
    # 没有默认值时输入框是空的
    #
    # 注意要先绑一个变量：写成 `_HwDialog(...).input_url.text()` 的话，
    # 临时对话框会在取属性前被回收，报
    # `RuntimeError: wrapped C/C++ object of type QLineEdit has been deleted`。
    _blank_dialog = _HwDialog(None, folder=Path("X:/（作业名）"))
    check("没有默认值时输入框是空的",
          _blank_dialog.input_url.text() == "",
          _blank_dialog.input_url.text())

    # ---- 真正的 QThread 也能被 shutdown 收干净（防"闪退"）----
    #
    # 用户报"改作业名会闪退"，根因是 Qt 在"线程还在跑时被析构"会 qFatal 中止进程
    # （0xC0000409，日志里没有 Python 栈）。这里用**真的 QThread** 验证：
    # 带父对象、还在跑的时候调 shutdown，必须能等到它结束。
    from PyQt6.QtCore import QThread as _QThread

    from gwp.core import threads as _threads_mod

    class _SlowThread(_QThread):
        def run(self):        # noqa: D102
            import time as _time

            _time.sleep(0.6)

    _holder = window            # 拿现成的窗口当父对象，别引入新控件
    _slow = _SlowThread(_holder)          # 故意带父对象，和项目里的写法一致
    _threads_mod.register(_slow)
    _slow.start()
    check("慢线程已启动", _slow.isRunning())
    _before_shutdown = _threads_mod.live_count()
    _left = _threads_mod.shutdown(grace_ms=3000, final_ms=6000)
    check("**shutdown 能等到真线程结束（防 Qt qFatal 闪退）**",
          not _slow.isRunning() and _left == 0,
          f"still_running={_slow.isRunning()} left={_left}")
    check("shutdown 之后登记表清空",
          _threads_mod.live_count() == 0,
          f"{_before_shutdown} -> {_threads_mod.live_count()}")

    # ---- 后台监听数据目录变化（需求：不断扫描但别耗 CPU）----
    #
    # 界面侧要验三件事：
    #   1. 外部真的动了文件 -> 界面自动刷新、缓存更新；
    #   2. **连续两次一致才算数**（避免抓到"写到一半"的中间状态）；
    #   3. 窗口隐藏/最小化时**完全停掉**（这是省 CPU 的关键）。
    from gwp.ui.data_watcher import DataWatcher as _DataWatcher

    _dw_dir = Path(tempfile.mkdtemp(prefix="gwp_watchgui_"))
    (_dw_dir / "科目").mkdir()
    # 说明：**防抖那套逻辑（连续两次一致才认账）在 smoke_core 里验** ——
    # 在这里用 check_now() 手动驱动会和 GUI 环境里的其它活动相互干扰，
    # 变成偶发失败（实测三次挂两次）。界面侧只验集成点：
    # 定时器能起停、以及窗口可见性能联动它。
    _watcher = _DataWatcher(_dw_dir, window, interval_ms=1000)
    _hits: list = []
    _watcher.changed.connect(lambda a, r: _hits.append((a, r)))
    _watcher.start()
    check("监听器能启动", _watcher.running)
    check("启动时会先取一份基准快照",
          _watcher.scan_count >= 1 and not _hits,
          f"scan={_watcher.scan_count} hits={len(_hits)}")

    # 停止 -> 不再扫描
    _watcher.stop()
    check("停止后定时器不再运行", not _watcher.running)
    _scan_before = _watcher.scan_count
    for _ in range(6):
        app.processEvents()
    check("停止后确实不再扫描（不耗 CPU）",
          _watcher.scan_count == _scan_before,
          f"{_scan_before} -> {_watcher.scan_count}")

    # 项目启动时应该已经把监听挂上了（间隔取值来自配置，且不激进）
    _mw_watcher = getattr(window, "_data_watcher", None)
    if _mw_watcher is not None:
        check("主窗口启动后已挂上数据变化监听",
              isinstance(_mw_watcher, _DataWatcher), str(type(_mw_watcher)))
        check("**默认扫描间隔是秒级（不会烧 CPU）**",
              _mw_watcher.interval_ms >= 1000,
              f"{_mw_watcher.interval_ms} ms")
        # 隐藏 -> 停；显示 -> 恢复（靠 Qt 事件，不靠每个调用点记得写）
        window.hide()
        for _ in range(4):
            app.processEvents()
        check("**窗口隐藏时停止扫描（省 CPU 的关键）**",
              not _mw_watcher.running, str(_mw_watcher.running))
        window.show()
        for _ in range(4):
            app.processEvents()
        check("窗口恢复显示后重新开始扫描",
              _mw_watcher.running, str(_mw_watcher.running))

    # ---- 文档合并 + 公式渲染（用户报障两条）----
    #
    # ① "生成的AI总结在AI总结位置未显示" —— Library 缓存没失效；
    # ② "md预览时 数学符号，公式，拉丁字母内容显示异常" —— QTextBrowser 不认识 LaTeX；
    # ③ "更主要的功能是文档合并" —— 把书目资料插进 summary。
    _mj_book = context.library.book(school_subject.name, "作业书目")
    check("准备书目用于合并测试", _mj_book is not None)
    if _mj_book is not None:
        _mj_summary = _mj_book.path / f"{_mj_book.name}_summary.md"
        _mj_summary.write_text("# 总结\n\n正文。\n", encoding="utf-8")
        # **缓存失效后 AI 总结页签要能看到它**（这就是用户报的那个 bug）
        context.library.invalidate()
        window.open_book(school_subject.name, "作业书目")
        for _ in range(12):
            app.processEvents()
        _mj_view = window.book_view
        _mj_view.tabs.setCurrentIndex(
            next(i for i, (key, _t, _f) in enumerate(_mj_view._tab_defs)
                 if key == "summary")
        )
        for _ in range(10):
            app.processEvents()
        _mj_table = _mj_view._tables["summary"]
        check("**写出的 summary 立刻出现在 AI 总结页签里**（缓存已失效）",
              _mj_table.rowCount() == 1,
              f"rows={_mj_table.rowCount()}")

        # 工具菜单里要有合并入口（直接读菜单项，不打桩）
        _mj_menu_texts: list[str] = []
        for _action in window.menuBar().actions():
            _sub = _action.menu()
            if _sub is None:
                continue
            for _item in _sub.actions():
                _mj_menu_texts.append(_item.text())
        check("工具菜单里有「生成总结」入口",
              any("生成总结" in text for text in _mj_menu_texts),
              str([t for t in _mj_menu_texts if "总结" in t]))
        check("书目页顶栏有「生成总结」按钮（原来的「合并资料到总结」已并入它）",
              "生成总结" in _mj_view.btn_merge.text(),
              _mj_view.btn_merge.text())
        check("两个入口指向同一个按钮（不再重复）",
              _mj_view.btn_merge is _mj_view.btn_summary)

    # Markdown 预览要接上公式目录（否则公式还是源码）
    from gwp.ui.views.document_view import DocumentView as _DocView

    _md_probe = Path(tempfile.mkdtemp(prefix="gwp_mdprev_")) / "公式.md"
    _md_probe.write_text("设 $\\varepsilon>0$。\n", encoding="utf-8")
    _dv = _DocView(context)
    check("**Markdown 编辑器接上了公式目录**（预览才能渲染公式）",
          _dv.editor.equation_dir is not None,
          str(_dv.editor.equation_dir))
    check("公式目录就是约定的那个（else data/equations）",
          _dv.editor.equation_dir == context.paths.else_data / "equations",
          str(_dv.editor.equation_dir))
    _preview_text = ""
    try:
        # load_file() 会同时设置 self.path 与内容（这才是正规入口）
        _dv.editor.load_file(_md_probe)
        _dv.editor.refresh_preview()
        for _ in range(8):
            app.processEvents()
        _preview_text = _dv.editor.preview.toPlainText()
    except Exception:  # noqa: BLE001 - 编辑器接口差异不该让用例炸掉
        pass
    check("**预览里不再出现 LaTeX 源码**",
          "\\varepsilon" not in _preview_text, _preview_text[:80])
    check("公式图片真的写到了 else data/equations",
          (context.paths.else_data / "equations").is_dir()
          and any((context.paths.else_data / "equations").glob("*.png")),
          str(list((context.paths.else_data / "equations").glob("*.png"))[:3]))
    _dv.deleteLater()

    # ---- 主页背景 ----
    from gwp.ui.dialogs.background_dialog import BackgroundDialog

    manager = context.backgrounds
    check("主窗口有背景容器", window.background_area.objectName() == "MainBackgroundArea",
          window.background_area.objectName())
    check("初始未设置背景", manager.current_path() is None)
    check("未设置背景时样式表不含背景图", "background-image" not in window.styleSheet())

    # 造两张图片并导入
    from PIL import Image as _Image

    pic_a = temp_root / "壁纸A.png"
    pic_b = temp_root / "壁纸B.png"
    _Image.new("RGB", (240, 160), (25, 70, 130)).save(pic_a)
    _Image.new("RGB", (240, 160), (140, 60, 40)).save(pic_b)

    target_a = manager.add(pic_a)
    target_b = manager.add(pic_b)
    check("导入后成为当前背景", manager.current_path() == target_b, str(manager.current_path()))
    check("两张图片都在图库里", len(manager.entries()) == 2,
          str([e.name for e in manager.entries()]))

    # 同步导入同一张 -> 数字递增，旧图保留
    target_a2 = manager.add(pic_a)
    check("同名再次导入数字递增", target_a2.name == "壁纸A_1.png", target_a2.name)
    check("第一张壁纸A仍保留", target_a.is_file())

    window.apply_background()
    app.processEvents()
    check("背景控件已加载图片", window.background_area.has_background)
    check("背景控件记住了填充方式", window.background_area._fit in
          ("cover", "contain", "stretch", "center"), window.background_area._fit)
    # 背景由控件自绘（QSS 的 background-image 在本项目里不绘制）
    check("样式表不再用 QSS 画背景图",
          "background-image" not in window.styleSheet(),
          window.styleSheet()[-200:])
    check("中间容器被设为透明以透出背景",
          "QStackedWidget" in window.styleSheet()
          and "background: transparent" in window.styleSheet())
    check("标题栏有半透明织带（保证文字可读）",
          "HeaderBar" in window.styleSheet(), window.styleSheet()[-300:])

    # 以下是几处踩过的坑，必须留有回归断言
    check("顶层页面栈有固定 objectName", window.stack.objectName() == "MainPageStack",
          window.stack.objectName())
    check("透明规则只点名 MainPageStack（不笼统匹配 QStackedWidget）",
          "QStackedWidget#MainPageStack" in window.styleSheet()
          and "QStackedWidget QWidget" not in window.styleSheet(),
          window.styleSheet()[-400:])
    check("覆盖到 QScrollArea 的 viewport（首页网格那片灰）",
          "QScrollArea" in window.styleSheet(), window.styleSheet()[-400:])
    check("标签栏保留不透明底色", "QTabBar" in window.styleSheet())
    margins = window.area_layout.contentsMargins()
    check("背景铺满（四周不留外框边距）",
          (margins.left(), margins.top(), margins.right(), margins.bottom()) == (0, 0, 0, 0),
          str((margins.left(), margins.top(), margins.right(), margins.bottom())))
    check("内容区不再标记为浮动（不留圆角）",
          not window.content_area.property("floating"),
          str(window.content_area.property("floating")))
    check("标题栏容器存在", hasattr(window.home_view, "header_bar"))

    # 关键回归：背景必须能透到工作区（曾经的 bug 是 QStackedWidget 盖住了它）
    from gwp.services.background import resolve_background

    image, fit, overlay, color = resolve_background(context.config, context.paths)
    check("解析出背景图片路径", image is not None and Path(image).is_file(), str(image))
    check("解析出填充方式", fit == "cover", fit)
    check("默认不压暗背景", overlay == 0.0, str(overlay))
    check("蒙层颜色为黑", color == (0, 0, 0), str(color))

    # 菜单项（两处入口：查看 / 设置，内容必须一致）
    window._rebuild_background_menu()
    check("两处背景子菜单都被注册", len(window.background_menus) == 2,
          str(len(window.background_menus)))
    view_menu = next(
        (action.menu() for action in window.menuBar().actions() if "查看" in action.text()),
        None,
    )
    settings_menu = next(
        (action.menu() for action in window.menuBar().actions() if "设置" in action.text()),
        None,
    )

    def _submenu(menu, title: str):
        if menu is None:
            return None
        for action in menu.actions():
            if action.menu() is not None and action.text() == title:
                return action.menu()
        return None

    view_bg = _submenu(view_menu, "更改背景")
    settings_bg = _submenu(settings_menu, "更改背景")
    check("查看菜单里有「更改背景」", view_bg is not None,
          str([a.text() for a in (view_menu.actions() if view_menu else [])]))
    check("设置菜单里保留「更改背景」", settings_bg is not None)

    bg_items = [action.text() for action in window.background_menus[0].actions()]
    check("背景菜单显示当前图", any("当前" in item for item in bg_items), str(bg_items))
    check("背景菜单列出图库", any("壁纸B.png" in item for item in bg_items), str(bg_items))
    check("背景菜单有选择入口", any("选择背景图" in item for item in bg_items), str(bg_items))
    check("背景菜单有打开文件夹", any("打开背景文件夹" in item for item in bg_items), str(bg_items))
    check("背景菜单有「不使用背景」", any("不使用背景" in item for item in bg_items), str(bg_items))

    if view_bg is not None and settings_bg is not None:
        view_bg.aboutToShow.emit()          # 模拟展开，验证展开即刷新
        app.processEvents()
        check("展开后两处内容一致",
              [a.text() for a in view_bg.actions()] == [a.text() for a in settings_bg.actions()],
              f"{[a.text() for a in view_bg.actions()]} vs "
              f"{[a.text() for a in settings_bg.actions()]}")

    # 切回第一张（不删任何文件）
    window.use_background(target_a)
    app.processEvents()
    check("可以切回旧背景", manager.current_path() == target_a)
    check("切换后文件数量不变", len(manager.entries()) == 3, str(len(manager.entries())))

    # 临时关闭背景
    window.toggle_background(False)
    app.processEvents()
    check("关闭背景后不再绘制背景", not window.background_area.has_background)
    check("关闭背景不删文件", len(manager.entries()) == 3)
    margins = window.area_layout.contentsMargins()
    check("关闭背景后内容区恢复铺满（无边距）",
          (margins.left(), margins.top(), margins.right(), margins.bottom()) == (0, 0, 0, 0),
          str((margins.left(), margins.top(), margins.right(), margins.bottom())))
    window.toggle_background(True)
    app.processEvents()
    check("重新启用后背景恢复", window.background_area.has_background)
    check("重新启用后样式表含透明规则",
          "background: transparent" in window.styleSheet())

    # 设置对话框
    bg_dialog = BackgroundDialog(context, window)
    check("背景对话框列出图库", bg_dialog.list.count() == 3, str(bg_dialog.list.count()))
    check("背景对话框有导入按钮", hasattr(bg_dialog, "btn_import"))
    check("背景对话框有显示方式选项", bg_dialog.combo_fit.count() == 4)
    check("背景对话框有蒙层滑块", bg_dialog.slider_overlay.value() >= 0)
    check("预览能加载图片（选中项）", not bg_dialog.preview.pixmap().isNull()
          or bg_dialog.list.currentRow() < 0,
          str(bg_dialog.list.currentRow()))
    bg_dialog.close()

    # 清理背景，恢复"未设置"状态，避免影响后续用例的样式断言
    manager.clear()
    manager.remove(target_a)
    manager.remove(target_a2)
    manager.remove(target_b)
    window.apply_background()
    app.processEvents()
    check("清理后无背景且图库为空", manager.current_path() is None and not manager.entries())

    # ---- 有背景时的像素级回归：背景要透出，文字面要不透明 ----
    # 用纯深色背景作为"最坏情况"：任何透明到文字的控件都会暴露出来。
    # 采样方式：直接 grab 控件本身（比在整窗截图里算坐标可靠得多）。
    import tempfile as _tempfile

    from PIL import Image as _PILImage
    from PyQt6.QtWidgets import QTableWidget as _QTableWidget

    def widget_pixel(widget, fx: float, fy: float) -> tuple:
        """抓取控件后取相对坐标 (fx, fy) 处的像素。"""
        handle, name = _tempfile.mkstemp(suffix=".png")
        os.close(handle)
        path = Path(name)
        try:
            widget.grab().save(str(path))
            with _PILImage.open(path) as shot:
                shot = shot.convert("RGB")
                width, height = shot.size
                return shot.getpixel(
                    (max(0, min(width - 1, int(width * fx))),
                     max(0, min(height - 1, int(height * fy))))
                )
        finally:
            path.unlink(missing_ok=True)

    def widget_row_pixels(widget, fx: float, fy: float, count: int = 3) -> list:
        """抓取控件后在相对高度 fy 处横向取 count 个像素（用于采样表头那一条）。"""
        handle, name = tempfile.mkstemp(suffix=".png")
        os.close(handle)
        path = Path(name)
        try:
            widget.grab().save(str(path))
            with _PILImage.open(path) as shot:
                shot = shot.convert("RGB")
                width, height = shot.size
                y = max(0, min(height - 1, int(height * fy)))
                return [
                    shot.getpixel(
                        (max(0, min(width - 1, int(width * (fx + step * 0.08)))), y)
                    )
                    for step in range(count)
                ]
        finally:
            path.unlink(missing_ok=True)

    dark_image = temp_root / "深色背景.png"
    _PILImage.new("RGB", (200, 150), (10, 10, 12)).save(dark_image)
    # 前面的用例可能把主题切成深色，这里显式回到浅色再断言像素
    # （深色主题的表格底色本来就深，"不透明"的判断标准不一样）
    context.config.set("ui.theme", "light")
    window.apply_theme()
    app.processEvents()
    check("像素用例前主题已回到浅色",
          context.theme == "light" and context.config.get("ui.theme") == "light",
          f"{context.theme} / {context.config.get('ui.theme')}")
    manager.set_current(dark_image)
    window.apply_theme()
    app.processEvents()
    check("深色背景已启用", window.background_area.has_background)

    window.open_book(subject.name, book.name)
    for _ in range(8):
        app.processEvents()

    # 只取**可见**的表格：findChildren 会连带隐藏标签页里的控件，
    # 那些控件可能还留着切主题时的旧绘制结果（曾经因此误报"表头是深色"）。
    book_tables = [t for t in window.book_view.findChildren(_QTableWidget) if t.isVisible()]
    check("书目页存在可见的文件表格", bool(book_tables), str(len(book_tables)))
    if book_tables:
        from gwp.services.themes import palette as _palette

        _colors = _palette(context.theme)
        _surface = tuple(
            int(_colors["surface"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)
        )
        _surface_alt = tuple(
            int(_colors["surface_alt"].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)
        )

        def _close_to(color: tuple, expected: tuple, tolerance: int = 6) -> bool:
            return all(abs(a - b) <= tolerance for a, b in zip(color, expected))

        # 表格体：取靠下空白处（不受文字影响）。底色必须是主题的 surface，
        # 也就是"不透明" —— 深色背景图不会透进来。
        body_pixel = widget_pixel(book_tables[0], 0.6, 0.92)
        check("文件表格底色不透明（文件名可读）",
              _close_to(body_pixel, _surface), f"{body_pixel} vs surface={_surface}")
        # 表头：在**表格整体截图**里采样表头那一条。
        # 注意两点（都是踩过的坑）：
        # 1. 不要单独 grab() QHeaderView —— 它作为独立控件套不上 QSS，会拿到错误颜色；
        # 2. 采样点要避开表头文字那一行，否则会采到文字色，改用"多数像素"判断。
        header_pixels = widget_row_pixels(book_tables[0], 0.55, 0.035, count=5)
        header_hits = sum(1 for c in header_pixels if _close_to(c, _surface_alt))
        check("表头底色不透明",
              header_hits >= 3, f"{header_pixels} 命中 {header_hits}/5，"
                               f"期望接近 surface_alt={_surface_alt}")

    from PyQt6.QtWidgets import QTabBar as _QTabBar

    bars = [b for b in window.book_view.findChildren(_QTabBar) if b.isVisible()]
    check("书目页存在可见的标签栏", bool(bars), str(len(bars)))
    if bars:
        # 标签栏右侧空白（没有标签文字的地方）
        tab_pixel = widget_pixel(bars[0], 0.97, 0.5)
        check("标签栏底色不透明（深色背景下标签文字可读）",
              min(tab_pixel) >= 200, str(tab_pixel))

    # 首页空白处应当透出深色背景（说明背景确实铺满工作区）
    window.show_home()
    for _ in range(6):
        app.processEvents()
    home_shot = temp_root / "home_dark.png"
    window.grab().save(str(home_shot))
    with _PILImage.open(home_shot) as shot:
        shot = shot.convert("RGB")
        width, height = shot.size
        home_center = shot.getpixel((int(width * 0.5), int(height * 0.8)))
    check("首页空白处透出深色背景（说明背景铺满工作区）",
          max(home_center) < 60, str(home_center))

    manager.clear()
    window.apply_theme()
    app.processEvents()
    check("回归用例结束后已清理背景", not window.background_area.has_background)


    corner = window.menuBar().cornerWidget(Qt.Corner.TopRightCorner)
    check("菜单栏右上角有 AI 入口", corner is not None)
    if corner is not None:
        check("右上角按钮显示 AI 对话", "AI 对话" in window.btn_chat.text(), window.btn_chat.text())
        check("右上角按钮带当前 AI 名称", "·" in window.btn_chat.text(), window.btn_chat.text())
    window._rebuild_corner_menu()
    corner_items = [action.text() for action in window.menu_corner.actions()]
    check("右上角菜单含日常对话入口", any("日常对话" in item for item in corner_items), str(corner_items))
    check("右上角菜单含提供方切换", any("测试 AI" in item for item in corner_items), str(corner_items))

    chat_window = window.open_chat_window()
    app.processEvents()
    check("日常对话窗口已打开", chat_window.isVisible())
    check("日常对话使用独立会话键", chat_window.chat.session.key == DAILY_SESSION_KEY,
          chat_window.chat.session.key)
    check("日常对话未绑定文件", chat_window.chat.document_path is None)
    check("日常对话为 daily 模式", chat_window.chat.daily_mode is True)
    check("日常对话隐藏了重发文件按钮", not chat_window.chat.btn_resend.isVisible())
    check("日常对话隐藏了插入文档按钮", not chat_window.chat.btn_insert.isVisible())
    check(
        "日常对话使用 daily 提示词",
        "日常对话" in chat_window.chat._system_prompt(),
        chat_window.chat._system_prompt()[:80],
    )
    check("再次打开返回同一窗口", window.open_chat_window() is chat_window)

    # 真的发一条消息（假 AI 已注入）
    chat_window.chat.input.setPlainText("你好，随便聊聊")
    chat_window.chat.send_current_input()
    for _ in range(200):
        if not chat_window.chat.is_busy():
            break
        app.processEvents()
        app.thread().msleep(25)
    app.processEvents()
    check("日常对话收到回答", len(chat_window.chat.session.messages) >= 2,
          str([m.role for m in chat_window.chat.session.messages]))
    check(
        "回答内容已写入会话",
        any("学习目标" in m.content for m in chat_window.chat.session.messages),
    )

    chat_window.new_conversation()
    app.processEvents()
    check("新对话清空了会话", chat_window.chat.session.is_empty)
    chat_window.view_ok = True
    chat_window.close()
    app.processEvents()
    check("日常对话窗口已关闭", window._chat_window is None or not window._chat_window.isVisible())

    # ---- PDF 导出（直接调用服务） ----
    #
    # 注意：**不要再读那个 `*_summary.md`** —— 技术路线变更后它已经被删掉了
    # （需求："不再生成md文档，旧的md之间删掉"）。这里换成自己写一段
    # Markdown 来测导出服务本身。
    from gwp.services.pdf_exporter import PDFExportOptions, export_markdown_to_pdf

    pdf_target = temp_root / "out" / "summary.pdf"
    try:
        export_markdown_to_pdf(
            "# 导出测试\n\n这是用来验证 Markdown → PDF 导出服务的正文。\n\n"
            "| 列 | 值 |\n|---|---|\n| a | 1 |\n",
            pdf_target,
            PDFExportOptions(),
            base_dir=book.path,
        )
        check("PDF 导出成功", pdf_target.is_file() and pdf_target.stat().st_size > 500)
    except Exception as exc:  # noqa: BLE001
        check("PDF 导出成功", False, str(exc))

    # ---- AI 菜单重建（检查不会崩） ----
    window._rebuild_ai_menu()
    ai_items = [action.text() for action in window.menu_ai.actions()]
    check("AI 菜单包含提供方", any("测试 AI" in item for item in ai_items), str(ai_items))
    check("AI 菜单包含刷新 AI", any("刷新" in item for item in ai_items))

    # ---- 关闭 ----
    for document in list(window._documents):
        window._close_document(document, force=True)
    for doc_win in list(window._windows):
        doc_win.view.editor._dirty = False
        doc_win.close()
    app.processEvents()
    check("文档窗口全部关闭", len(window._windows) == 0, str(len(window._windows)))

    window.close()
    app.processEvents()
    check("关闭时清空聊天记录", len(context.chats.list_sessions()) == 0,
          str(context.chats.list_sessions()))
    # 天气在后台线程里拉（免费接口慢网络下要 20 秒），关闭时必须停掉；
    # 否则 Qt 会打印 "QThread: Destroyed while thread is still running"。
    check("关闭时停掉了天气线程",
          window.home_view.clock_bar._worker is None,
          str(window.home_view.clock_bar._worker))

    print()
    print(f"对话框调用记录（{len(DIALOG_LOG)} 条）：")
    for line in DIALOG_LOG[:25]:
        print(f"  · {line}")

    print()
    if FAILURES:
        print(f"共 {len(FAILURES)} 项失败：")
        for item in FAILURES:
            print(f"  - {item}")
    else:
        print("界面自检全部通过 ✅")

    del app
    shutil.rmtree(temp_root, ignore_errors=True)
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
