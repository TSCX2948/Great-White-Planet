"""科目页：显示该科目下的所有书目卡片。

点击科目后进入（需求文档第四节），书目同样完全来自扫描。
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QPoint, pyqtSignal
from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from gwp.bootstrap import AppContext
from gwp.data_manager.models import Book, Subject
from gwp.ui import common
from gwp.ui.dialogs.book_dialog import BookDialog
from gwp.ui.views.base_view import BaseView
from gwp.ui.widgets.cards import BookCard, CardGrid, build_context_menu

log = logging.getLogger(__name__)


class SubjectView(BaseView):
    """一个科目下的书目列表。"""

    book_opened = pyqtSignal(str, str)        # 科目名, 书目名
    back_requested = pyqtSignal()

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(context, parent)
        self.subject_name = ""

        self.add_action("← 返回首页", self.back_requested.emit, tooltip="回到科目总览")
        self.add_action("＋ 新建书目", self.create_book, accent=True)
        self.add_action("打开文件夹", self._reveal_subject)
        self.add_action("刷新", self.refresh)
        self.enable_search("搜索书目…")

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(12)

        self.grid = CardGrid()
        self.grid.card_opened.connect(self._open_book)
        self.grid.card_context.connect(self._book_menu)
        container_layout.addWidget(self.grid)

        self.empty_hint = QLabel("这个科目下还没有书目。点击「＋ 新建书目」创建第一本。")
        self.empty_hint.setObjectName("EmptyHint")
        self.empty_hint.setWordWrap(True)
        container_layout.addWidget(self.empty_hint)
        container_layout.addStretch(1)

        self.scroll.setWidget(container)
        self.body.addWidget(self.scroll, 1)

    # ==================================================================

    def show_subject(self, subject_name: str) -> None:
        self.subject_name = subject_name
        self.search.clear()
        self.refresh()

    def on_shown(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        subject = self.context.library.subject(self.subject_name)
        if subject is None:
            self.set_title("科目不存在", "它可能已经被删除或重命名")
            self.grid.set_cards([])
            self.empty_hint.setVisible(True)
            return

        keyword = self.search.text().strip().lower()
        books = list(subject.books)
        if keyword:
            books = [
                book for book in books
                if keyword in book.title.lower() or keyword in book.name.lower()
            ]

        cards = [
            BookCard(
                book,
                width=int(self.context.config.get("ui.card.width", 196) or 196),
                height=int(self.context.config.get("ui.card.height", 124) or 124),
                radius=int(self.context.config.get("ui.card.radius", 14) or 14),
            )
            for book in books
        ]
        self.grid.set_cards(cards)
        self.set_title(
            subject.title,
            f"{subject.book_count} 本书目 · {subject.file_count} 个文件 · {subject.size_label}",
            "按右键可以重命名、删除、移动书目",
        )
        self.empty_hint.setVisible(not books)
        self.empty_hint.setText(
            "没有匹配的书目。" if keyword else "这个科目下还没有书目。点击「＋ 新建书目」创建第一本。"
        )

    def _on_search(self, _text: str) -> None:
        self.refresh()

    # ==================================================================

    def create_book(self) -> None:
        subject = self.context.library.subject(self.subject_name)
        if subject is None:
            common.warn(self, "科目不存在，请先返回首页刷新。")
            return
        dialog = BookDialog(self, subject_name=subject.name)
        if not dialog.exec():
            return
        values = dialog.values()
        try:
            book = self.context.library.create_book(
                subject.name, values["name"], description=values["description"]
            )
            if values.get("color"):
                self.context.library.update_book(subject.name, book.name, color=values["color"])
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "新建书目失败")
            return
        self.refresh()
        self.status_message.emit(f"已创建书目：{book.title}")
        self.book_opened.emit(subject.name, book.name)

    def _open_book(self, card) -> None:
        """双击书目卡片 -> 打开书目。

        ``card_opened`` 统一派发**卡片本身**，因此这里从卡片上取书目；
        也兼容直接传入 ``Book``（早期用法）。
        """
        book = getattr(card, "book", None) or card
        if book is not None and getattr(book, "name", None):
            self.book_opened.emit(self.subject_name, book.name)

    def _book_menu(self, card, global_pos: QPoint) -> None:
        """右键书目卡片。

        ``card_context`` 统一派发**卡片本身**，因此这里先从卡片上取书目；
        也兼容直接传入 ``Book``（历史用法），避免"收到卡片却当模型用"而静默失灵。
        """
        book = getattr(card, "book", None) or card
        if book is None or not getattr(book, "name", None):
            return
        other_subjects = [
            subject for subject in self.context.library.subjects()
            if subject.name != self.subject_name
        ]
        menu = build_context_menu(
            self,
            [
                ("打开", lambda: self.book_opened.emit(self.subject_name, book.name)),
                None,
                ("重命名…", lambda: self._rename_book(book)),
                ("编辑说明/颜色…", lambda: self._edit_book(book)),
                ("置顶/取消置顶", lambda: self._toggle_pin(book)),
                None,
                ("补齐标准目录结构", lambda: self._repair(book)),
                ("在资源管理器中打开", lambda: self._reveal_book(book)),
                None,
                ("移动到其它科目…", lambda: self._move_book(book, other_subjects)) if other_subjects
                else ("移动到其它科目（无其它科目）", lambda: None),
                None,
                ("删除书目…", lambda: self._delete_book(book)),
            ],
        )
        menu.exec(global_pos)

    # -- 操作 -----------------------------------------------------------

    def _rename_book(self, book: Book) -> None:
        dialog = BookDialog(self, book=book)
        if not dialog.exec():
            return
        values = dialog.values()
        try:
            if values["name"] != book.name:
                renamed = self.context.library.rename_book(
                    self.subject_name, book.name, values["name"]
                )
                target = renamed.name
            else:
                target = book.name
            self.context.library.update_book(
                self.subject_name, target, description=values["description"], color=values["color"]
            )
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "保存失败")
            return
        self.refresh()
        self.status_message.emit(f"已保存书目：{values['name']}")

    def _edit_book(self, book: Book) -> None:
        self._rename_book(book)

    def _toggle_pin(self, book: Book) -> None:
        self.context.library.update_book(self.subject_name, book.name, pinned=not book.pinned)
        self.refresh()

    def _repair(self, book: Book) -> None:
        try:
            created = self.context.library.ensure_book_layout(self.subject_name, book.name)
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "补齐目录失败")
            return
        if created:
            common.info(self, "已补齐：" + "、".join(created), "补齐目录")
        else:
            common.info(self, "目录结构已经是完整的。", "补齐目录")
        self.refresh()

    def _reveal_book(self, book: Book) -> None:
        from gwp.services import file_ops

        file_ops.reveal_in_explorer(book.path)

    def _reveal_subject(self) -> None:
        from gwp.services import file_ops

        subject = self.context.library.subject(self.subject_name)
        if subject is not None:
            file_ops.reveal_in_explorer(subject.path)

    def _move_book(self, book: Book, targets: list[Subject]) -> None:
        from PyQt6.QtWidgets import QInputDialog

        names = [subject.title for subject in targets]
        choice, ok = QInputDialog.getItem(self, "移动书目", f"把「{book.title}」移动到：", names, 0, False)
        if not ok or not choice:
            return
        target = targets[names.index(choice)]
        try:
            self.context.library.move_book(self.subject_name, book.name, target.name)
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "移动失败")
            return
        self.refresh()
        self.status_message.emit(f"已移动到：{target.title}")

    def _book_delete_warning(self, book: Book) -> tuple[str, str, bool]:
        """拼出删除书目的警告文案，返回 ``(主文案, 详细信息, 是否非空)``。

        文案与真实行为保持一致：能进回收站才说"可还原"，否则明确说"永久删除"。
        """
        from gwp.services import shell_ops

        counts = dict(book.item_counts or {})
        total_files = sum(counts.values())
        sources = book.summary_source_count
        has_content = bool(total_files)

        recyclable = shell_ops.can_use_recycle_bin()
        if recyclable:
            outcome = "删除后会移入系统回收站，可从回收站还原。"
        else:
            outcome = "⚠ 当前**无法使用回收站**，删除后将**永久丢失、无法还原**。"

        message = "\n".join(
            [
                f"确定要删除书目「{book.title}」吗？",
                "",
                f"所在科目：{self.subject_name}",
                f"文件总数：约 {total_files} 个"
                + (f"（其中参与 AI 总结的笔记/易错题 {sources} 份）" if sources else ""),
                "",
                outcome,
            ]
        )
        detail = "\n".join(
            [
                f"书目目录：{book.path}",
                "各目录文件数："
                + (
                    "、".join(f"{key} {value}" for key, value in sorted(counts.items()))
                    or "（空）"
                ),
                f"已生成的总结：{book.summary_label}",
            ]
        )
        return message, detail, has_content

    def _delete_book(self, book: Book) -> None:
        if bool(self.context.config.get("ui.confirm_on_delete", True)):
            message, detail, has_content = self._book_delete_warning(book)
            # dangerous=True：默认按钮是「取消」，直接回车不会误删
            if not common.confirm(
                self, message, "删除书目", dangerous=True, detail=detail
            ):
                return
            if has_content:
                if not common.confirm(
                    self,
                    f"「{book.title}」里有约 {sum(book.item_counts.values())} 个文件，"
                    "删除后它们会一起消失。\n\n真的要删除吗？",
                    "再次确认删除",
                    dangerous=True,
                ):
                    return
        try:
            self.context.library.delete_book(self.subject_name, book.name, to_recycle=True)
        except Exception as exc:  # noqa: BLE001
            common.error(self, str(exc), "删除失败")
            return
        self.refresh()
        self.status_message.emit(f"已删除书目：{book.title}")


__all__ = ["SubjectView"]
