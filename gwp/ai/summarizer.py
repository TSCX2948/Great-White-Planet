"""Summary 生成引擎。

对应需求文档第五、六节：

* 参与整合的资料：``Introduct.md`` + ``notebook`` + ``error-prone``（``book`` 不参与）；
* 不是简单概括，而是"整合 + 扩展"成一份完整学习文档；
* 输出文件名 ``<书名>_summary.md``，默认排在书目首位；
* 生成前先把上一版另存到 ``else data/summary_backup``（只留一版）。

本模块是**纯逻辑**（不认识 Qt），因此可以在命令行里单独测试；
界面通过回调拿到流式文本与进度。
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from gwp.ai.base import BaseAIAdapter
from gwp.ai.types import AIError, ChatMessage, ChatOptions
from gwp.core import constants as C
from gwp.core.config import Config
from gwp.data_manager import metadata as meta_io
from gwp.data_manager.models import Book
from gwp.data_manager.summary_backup import BackupManager
from gwp.services.document_reader import ExtractOptions, ExtractedDocument, extract

log = logging.getLogger(__name__)

ProgressCallback = Callable[["ProgressEvent"], None]
ChunkCallback = Callable[[str], None]
QuestionCallback = Any


@dataclass
class ProgressEvent:
    """进度事件。percent < 0 表示不确定进度（滚动条忙碌态）。"""

    message: str
    percent: int = -1
    detail: str = ""


@dataclass
class SummaryMaterial:
    """一份待整合的资料。"""

    path: Path
    source: str                 # intro | notebook | error-prone
    rel_path: str = ""
    text: str = ""
    kind: str = "text"
    reliable: bool = True
    included: bool = True
    notes: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def char_count(self) -> int:
        return len(self.text)

    @property
    def label(self) -> str:
        return {
            "intro": "简介",
            "notebook": "笔记",
            "error-prone": "易错题",
        }.get(self.source, self.source)


@dataclass
class SummaryResult:
    """生成结果。"""

    ok: bool
    summary_path: Path | None = None
    backup_path: Path | None = None
    text: str = ""
    material_count: int = 0
    char_count: int = 0
    chunks: int = 0
    provider: str = ""
    elapsed: float = 0.0
    error: str = ""
    skipped: list[SummaryMaterial] = field(default_factory=list)
    used_images: int = 0


# --------------------------------------------------------------------------

class Summarizer:
    """把一本书的零散资料整合成一份学习文档。"""

    def __init__(
        self,
        config: Config | None = None,
        library: Any = None,
        ai_manager: Any = None,
    ) -> None:
        self.config = config or Config.load()
        self.library = library
        self.ai_manager = ai_manager
        self.backups = BackupManager(self.config)

    # ------------------------------------------------------------------
    # 资料收集
    # ------------------------------------------------------------------

    #: 旧版本写进 config.json 的默认来源列表。
    #: 它长得和"用户自定义"一模一样，因此要单独识别出来当作"没自定义"，
    #: 否则日记类型永远拿不到自己的 my diary / else diary。
    LEGACY_DEFAULT_SOURCES = (C.INTRO_FILE, C.NOTEBOOK_FOLDER, C.ERROR_FOLDER)

    def source_spec(self, subject_type: str = "") -> list[tuple[str, Path]]:
        """返回 [(来源标签, 路径)]；路径可能是文件或目录。

        ``subject_type`` 决定默认来源：

        * 普通科目（自学课/校修课）：``Introduct.md`` + ``notebook`` + ``error-prone``；
        * **日记**：``Introduct.md`` + ``my diary`` + ``else diary``
          （没有教材也没有易错题）。

        配置里显式写了 ``summary.sources`` 时以配置为准（旧默认值除外），
        因此任何类型都能被用户手工调整。
        """
        if (subject_type or "") == C.SUBJECT_DIARY:
            default_dirs = list(C.DIARY_SOURCE_DIRS)
        else:
            default_dirs = [C.NOTEBOOK_FOLDER, C.ERROR_FOLDER]

        default_labels = {
            C.NOTEBOOK_FOLDER: "notebook",
            C.ERROR_FOLDER: "error-prone",
            C.DIARY_MINE_FOLDER: "my diary",
            C.DIARY_OTHERS_FOLDER: "else diary",
        }

        spec: list[tuple[str, Path]] = []
        configured = [str(item) for item in (self.config.get("summary.sources", []) or [])]
        if tuple(configured) == self.LEGACY_DEFAULT_SOURCES:
            configured = []                     # 旧默认值 -> 视为未自定义
        names = configured or [C.INTRO_FILE, *default_dirs]
        for name in names:
            if name == C.INTRO_FILE:
                spec.append(("intro", Path(C.INTRO_FILE)))
            elif name in default_labels:
                spec.append((default_labels[name], Path(name)))
            else:
                # 配置里写了别的目录，也照样支持（可扩展）
                spec.append((Path(name).name or name, Path(name)))
        return spec

    def resolve_sources(self, book: Book) -> list[tuple[str, Path]]:
        """把来源标签解析成 book 目录下的真实路径。"""
        # book 的父目录就是科目目录，直接从它的元数据里取类型
        subject_type = ""
        try:
            meta = meta_io.load_subject_meta(book.path.parent)
            subject_type = str(meta.get("subject_type") or "")
        except Exception:  # noqa: BLE001 - 拿不到类型时按普通科目处理
            subject_type = ""

        resolved: list[tuple[str, Path]] = []
        for label, relative in self.source_spec(subject_type):
            candidate = book.path / relative
            if label == "intro":
                # 简介文件可能被改名，优先用实际存在的那个
                if book.intro_path is not None:
                    resolved.append(("intro", book.intro_path))
                    continue
                for alias in (C.INTRO_FILE, "Introduce.md", "introduction.md", "Intro.md"):
                    if (book.path / alias).exists():
                        resolved.append(("intro", book.path / alias))
                        break
                continue
            if candidate.exists():
                resolved.append((label, candidate))
        return resolved

    def collect_materials(
        self,
        book: Book,
        on_progress: ProgressCallback | None = None,
    ) -> list[SummaryMaterial]:
        """收集并解析所有参与总结的文件。"""
        materials: list[SummaryMaterial] = []
        sources = self.resolve_sources(book)

        files: list[tuple[str, Path]] = []
        for label, path in sources:
            if path.is_file():
                files.append((label, path))
            elif path.is_dir():
                try:
                    for child in sorted(path.rglob("*")):
                        if child.is_file() and not child.name.startswith("."):
                            if child.name.endswith(".tmp"):
                                continue
                            files.append((label, child))
                except OSError:
                    log.exception("读取目录失败: %s", path)

        total = len(files)
        if on_progress:
            on_progress(ProgressEvent(f"正在读取资料：共 {total} 个文件", 5 if total else 100))

        exclusions = [str(name) for name in (self.config.get("summary.exclude_dirs", []) or [])]
        for index, (label, path) in enumerate(files, start=1):
            # 防御：无论如何都不让 book 目录参与总结
            if C.BOOK_FOLDER in exclusions and C.BOOK_FOLDER in path.parts:
                continue
            if on_progress and total:
                percent = 5 + int(35 * index / total)
                on_progress(ProgressEvent(f"读取中（{index}/{total}）", percent, path.name))

            image_dir = path.parent / f".{path.stem}_assets"
            image_target = None if path.suffix.lower() == ".md" else image_dir
            options = ExtractOptions.from_config(self.config, image_dir=image_target)
            options.max_chars = int(self.config.get("summary.max_input_chars", 200_000) or 200_000)
            document = extract(path, options)
            materials.append(self._material_from(label, path, book, document))
        return materials

    def _material_from(
        self,
        label: str,
        path: Path,
        book: Book,
        document: ExtractedDocument,
    ) -> SummaryMaterial:
        text = document.markdown or ""
        # 图片按 Markdown 相对路径写进 summary（summary 就在 book 目录里）
        image_count = 0
        if document.image_files:
            for image in document.image_files:
                try:
                    relative = image.relative_to(book.path).as_posix()
                except ValueError:
                    relative = image.as_posix()
                text = text.replace(image.as_posix(), relative)
                image_count += 1

        notes = list(document.notes)
        if document.error:
            notes.append(document.error)
        try:
            rel = path.relative_to(book.path).as_posix()
        except ValueError:
            rel = path.name
        return SummaryMaterial(
            path=path,
            source=label,
            rel_path=rel,
            text=text,
            kind=document.kind,
            reliable=document.reliable,
            included=bool(text.strip()),
            notes=notes,
            error=document.error,
        )

    # ------------------------------------------------------------------
    # 提示词组装
    # ------------------------------------------------------------------

    def build_context(self, materials: list[SummaryMaterial], book: Book) -> str:
        blocks: list[str] = []
        for material in materials:
            if not material.included:
                continue
            body = material.text.strip()
            if not body:
                continue
            flags = []
            if not material.reliable:
                flags.append("识别可靠性：低（已按原文/图片保留）")
            if material.notes:
                flags.append("；".join(material.notes))
            header = f"===== 资料来源：{material.label} / {material.rel_path} ====="
            if flags:
                header += "\n（" + " | ".join(flags) + "）"
            blocks.append(f"{header}\n{body}")
        return "\n\n".join(blocks)

    def _prompt(self, key: str, default: str) -> str:
        return str(self.config.get(f"prompts.{key}", default) or default)

    def _build_single_messages(
        self, book: Book, context: str, system_prompt: str | None = None
    ) -> list[ChatMessage]:
        template = self._prompt(
            "summary_user_template",
            "书目名称：{book}\n所属科目：{subject}\n\n以下是需要整合的全部资料：\n\n{materials}",
        )
        user_text = template.format(book=book.title, subject=book.subject_name, materials=context)
        system = (
            system_prompt
            if system_prompt is not None
            else self._prompt("summary_system", "") + self._uncertainty_rules()
        )
        return [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user_text),
        ]

    def _build_chunk_messages(
        self, book: Book, context: str, index: int, total: int,
        system_prompt: str | None = None,
    ) -> list[ChatMessage]:
        template = self._prompt(
            "chunk_user_template",
            "书目名称：{book}\n这是第 {index}/{total} 部分资料。\n\n{materials}",
        )
        user_text = template.format(book=book.title, index=index, total=total, materials=context)
        system = (
            system_prompt if system_prompt is not None
            else self._prompt("summary_chunk_system", "")
        )
        return [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user_text),
        ]

    def _build_merge_messages(
        self, book: Book, merged: str, system_prompt: str | None = None
    ) -> list[ChatMessage]:
        template = self._prompt(
            "merge_user_template",
            "书目名称：{book}\n所属科目：{subject}\n\n以下是各部分资料的提炼结果：\n\n{materials}",
        )
        user_text = template.format(book=book.title, subject=book.subject_name, materials=merged)
        system = (
            system_prompt if system_prompt is not None
            else self._prompt("summary_merge_system", "") + self._uncertainty_rules()
        )
        return [
            ChatMessage(role="system", content=system),
            ChatMessage(role="user", content=user_text),
        ]

    def _uncertainty_rules(self) -> str:
        rules = str(self.config.get("prompts.uncertainty_rules", "") or "").strip()
        return f"\n\n{rules}" if rules else ""

    # ------------------------------------------------------------------
    # 切块
    # ------------------------------------------------------------------

    def split_context(self, context: str) -> list[str]:
        """按配置的字符数切块，优先在段落/标题边界切开。"""
        limit = max(2000, int(self.config.get("summary.chunk_chars", 18000) or 18000))
        overlap = max(0, int(self.config.get("summary.chunk_overlap", 400) or 0))
        overlap = min(overlap, limit // 4)
        if len(context) <= limit:
            return [context]

        chunks: list[str] = []
        position = 0
        length = len(context)
        while position < length:
            end = min(position + limit, length)
            if end < length:
                window = context[position:end]
                # 依次尝试：空行 + 标题 / 空行 / 换行 / 中文句号
                for token in ("\n## ", "\n### ", "\n\n", "\n", "。", "；"):
                    cut = window.rfind(token)
                    if cut > limit * 0.5:
                        end = position + cut + len(token)
                        break
            chunks.append(context[position:end])
            if end >= length:
                break
            position = max(end - overlap, position + 1)
        return chunks

    # ------------------------------------------------------------------
    # 生成
    # ------------------------------------------------------------------

    def generate(
        self,
        book: Book,
        adapter: BaseAIAdapter | None = None,
        on_progress: ProgressCallback | None = None,
        on_chunk: ChunkCallback | None = None,
        question_handler: QuestionCallback | None = None,
        should_cancel: Any = None,
        materials: list[SummaryMaterial] | None = None,
        extra_instruction: str = "",
    ) -> SummaryResult:
        """生成 summary 并写盘。``adapter`` 为空时使用 AIManager 的兜底链。"""
        started = time.time()
        report = on_progress or (lambda event: None)

        report(ProgressEvent("正在收集资料……", 2))
        materials = materials if materials is not None else self.collect_materials(book, on_progress)

        included = [m for m in materials if m.included and m.text.strip()]
        skipped = [m for m in materials if not (m.included and m.text.strip())]
        if not included:
            return SummaryResult(
                ok=False,
                error="没有可用于总结的资料。请在 notebook（笔记）或 error-prone（易错题）中放入内容，"
                      "或在 Introduct.md 里写下学习目标。",
                skipped=skipped,
                material_count=len(materials),
            )

        context = self.build_context(included, book)
        if extra_instruction.strip():
            context += f"\n\n===== 用户额外要求 =====\n{extra_instruction.strip()}"
        report(ProgressEvent(f"已读取 {len(included)} 份资料，共 {len(context)} 字符", 40))

        try:
            text, chunks, provider = self._run_ai(
                book, context, adapter, report, on_chunk, question_handler, should_cancel
            )
        except Exception as exc:  # noqa: BLE001 - 统一转成结果对象，界面负责展示
            log.exception("生成 summary 失败")
            return SummaryResult(
                ok=False,
                error=str(exc),
                material_count=len(included),
                char_count=len(context),
                elapsed=time.time() - started,
                skipped=skipped,
            )

        if not text.strip():
            return SummaryResult(
                ok=False,
                error="AI 没有返回内容，请检查网络或更换 AI。",
                material_count=len(included),
                elapsed=time.time() - started,
                skipped=skipped,
            )

        report(ProgressEvent("正在写入文件……", 95))
        summary_path = self._resolve_summary_path(book)
        backup_path = self._write_summary(book, summary_path, text)

        result = SummaryResult(
            ok=True,
            summary_path=summary_path,
            backup_path=backup_path,
            text=text,
            material_count=len(included),
            char_count=len(context),
            chunks=chunks,
            provider=provider,
            elapsed=time.time() - started,
            skipped=skipped,
            used_images=sum(1 for m in included if m.kind == "pdf" and not m.reliable),
        )
        report(ProgressEvent("完成", 100))
        return result

    def _run_ai(
        self,
        book: Book,
        context: str,
        adapter: BaseAIAdapter | None,
        report: ProgressCallback,
        on_chunk: ChunkCallback | None,
        question_handler: QuestionCallback | None,
        should_cancel: Any,
        system_prompt: str | None = None,
        chunk_system_prompt: str | None = None,
        merge_system_prompt: str | None = None,
        task_label: str = "整合资料",
    ) -> tuple[str, int, str]:
        """按资料长度决定"一次整合"还是"分块提炼 + 合并"。返回 (文本, 块数, 提供方)。

        ``system_prompt`` / ``chunk_system_prompt`` / ``merge_system_prompt``
        用于替换默认提示词（日记的两套流程各自有自己的提示词）。
        """
        chunks = self.split_context(context)
        options = ChatOptions(
            temperature=float(self.config.get("ai.temperature", 0.3) or 0.3),
            max_tokens=int(self.config.get("ai.max_tokens", 8192) or 8192),
            stream=bool(self.config.get("ai.stream", True)),
        )

        def _chat(messages: list[ChatMessage], chunk_cb: ChunkCallback | None) -> tuple[str, str]:
            if adapter is not None:
                text = adapter.chat(
                    messages,
                    options,
                    on_chunk=chunk_cb,
                    question_handler=question_handler,
                    should_cancel=should_cancel,
                )
                return text, adapter.provider_id
            if self.ai_manager is None:
                raise AIError("没有可用的 AI 适配器。")
            text, provider_id = self.ai_manager.chat_with_fallback(
                messages,
                options,
                on_chunk=chunk_cb,
                question_handler=question_handler,
                should_cancel=should_cancel,
            )
            return text, provider_id

        if len(chunks) == 1:
            report(ProgressEvent(f"AI 正在{task_label}……", 55))
            text, provider = _chat(
                self._build_single_messages(book, context, system_prompt), on_chunk
            )
            return text, 1, provider

        # 长资料：先分块提炼，再合并
        refined: list[str] = []
        provider = ""
        for index, chunk in enumerate(chunks, start=1):
            percent = 40 + int(45 * (index - 1) / len(chunks))
            report(ProgressEvent(f"AI 正在提炼第 {index}/{len(chunks)} 部分……", percent))
            part, provider = _chat(
                self._build_chunk_messages(
                    book, chunk, index, len(chunks), chunk_system_prompt
                ),
                None if index < len(chunks) else on_chunk,
            )
            refined.append(f"----- 第 {index} 部分提炼结果 -----\n{part.strip()}")

        merged_input = "\n\n".join(refined)
        if len(merged_input) > int(self.config.get("summary.chunk_chars", 18000) or 18000) * 3:
            # 极端情况：合并输入本身过长，截断并提示
            limit = int(self.config.get("summary.chunk_chars", 18000) or 18000) * 3
            merged_input = merged_input[:limit] + "\n\n（后续内容因长度限制被截断）"
        report(ProgressEvent(f"AI 正在合并{task_label}……", 88))
        text, provider = _chat(
            self._build_merge_messages(book, merged_input, merge_system_prompt), on_chunk
        )
        return text, len(chunks), provider

    # ------------------------------------------------------------------
    # 写盘
    # ------------------------------------------------------------------

    def _resolve_summary_path(self, book: Book) -> Path:
        name = book.summary_path.name if book.summary_path else f"{book.name}{C.SUMMARY_SUFFIX}"
        return book.path / name

    # ------------------------------------------------------------------
    # 日记类型：两套独立的生成流程
    # ------------------------------------------------------------------

    def diary_sources(self, book: Book) -> list[SummaryMaterial]:
        """读 ``my diary`` 里的全部文件（AI 日记与思想总结都只吃这一份来源）。"""
        materials: list[SummaryMaterial] = []
        folder = book.path / C.DIARY_MINE_FOLDER
        if not folder.is_dir():
            return materials
        files = sorted(
            (p for p in folder.rglob("*") if p.is_file()),
            key=lambda p: p.name.lower(),
        )
        options = ExtractOptions(
            max_chars=int(self.config.get("summary.max_chars_per_file", 200000) or 200000)
        )
        for path in files:
            try:
                document = extract(path, options)
            except Exception as exc:  # noqa: BLE001 - 单个文件失败不影响其它
                log.warning("读取日记文件失败：%s（%s）", path, exc)
                continue
            text = document.markdown or ""
            notes = list(document.notes)
            if document.error:
                notes.append(document.error)
            materials.append(
                SummaryMaterial(
                    path=path,
                    source="my diary",
                    rel_path=path.name,
                    text=text,
                    kind=document.kind,
                    reliable=document.reliable,
                    included=bool(text.strip()),
                    notes=notes,
                    error=document.error,
                )
            )
        return materials

    def _diary_context(self, book: Book, materials: list[SummaryMaterial]) -> str:
        """把 my diary 拼成给 AI 的上下文，带上明确的日期来源信息。"""
        blocks: list[str] = []
        for material in materials:
            if not (material.included and material.text.strip()):
                continue
            blocks.append(
                f"===== 日记文件：{material.rel_path} =====\n{material.text.strip()}"
            )
        header = (
            f"日记本名称：{book.title}\n"
            f"来源目录：{C.DIARY_MINE_FOLDER}（共 {len(blocks)} 份文件）\n\n"
        )
        return header + "\n\n".join(blocks)

    def generate_diary(
        self,
        book: Book,
        mode: str = "thought",
        adapter: BaseAIAdapter | None = None,
        on_progress: ProgressCallback | None = None,
        on_chunk: ChunkCallback | None = None,
        question_handler: QuestionCallback | None = None,
        should_cancel: Any = None,
        extra_instruction: str = "",
    ) -> SummaryResult:
        """生成日记文档。

        ``mode="thought"`` -> 读 ``my diary`` 归纳思想，写入 ``AI summary/``；
        ``mode="book"``    -> 把 ``my diary`` 整合成格式统一的日记册，写入 ``AI diary/``。
        """
        started = time.time()
        report = on_progress or (lambda event: None)

        if mode not in ("thought", "book"):
            return SummaryResult(ok=False, error=f"未知的日记生成模式：{mode}")

        if mode == "thought":
            system_prompt = self._prompt(
                "diary_thought_system", C.DIARY_THOUGHT_SYSTEM_PROMPT
            )
            task_label = "归纳思想"
            target_dir = book.path / C.DIARY_AI_SUMMARY_FOLDER
            file_hint = "思想总结"
        else:
            system_prompt = self._prompt(
                "diary_book_system", C.DIARY_BOOK_SYSTEM_PROMPT
            )
            task_label = "整理日记"
            target_dir = book.path / C.DIARY_AI_DIARY_FOLDER
            file_hint = "日记"

        report(ProgressEvent("正在读取 my diary……", 5))
        materials = self.diary_sources(book)
        included = [m for m in materials if m.included and m.text.strip()]
        if not included:
            from gwp.services.document_reader import supported_extensions

            kinds = "、".join(sorted(supported_extensions()))
            return SummaryResult(
                ok=False,
                error=(
                    f"「{C.DIARY_MINE_FOLDER}」里没有可用的日记内容。\n\n"
                    f"请先把日记放进：{book.path / C.DIARY_MINE_FOLDER}\n"
                    f"支持的格式：{kinds}"
                ),
                skipped=materials,
                material_count=len(materials),
            )

        context = self._diary_context(book, included)
        if extra_instruction.strip():
            context += f"\n\n===== 用户额外要求 =====\n{extra_instruction.strip()}"
        report(
            ProgressEvent(
                f"已读取 {len(included)} 份日记，共 {len(context)} 字符", 30
            )
        )

        try:
            text, chunks, provider = self._run_ai(
                book, context, adapter, report, on_chunk, question_handler,
                should_cancel,
                system_prompt=system_prompt,
                chunk_system_prompt=system_prompt,
                merge_system_prompt=system_prompt,
                task_label=task_label,
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("生成日记文档失败（mode=%s）", mode)
            return SummaryResult(
                ok=False, error=str(exc), material_count=len(included),
                char_count=len(context), elapsed=time.time() - started,
            )

        if not text.strip():
            return SummaryResult(
                ok=False, error="AI 没有返回内容，请检查网络或更换 AI。",
                material_count=len(included), elapsed=time.time() - started,
            )

        report(ProgressEvent("正在写入文件……", 95))
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            output = target_dir / f"{book.name}_{file_hint}.md"
            backup = self._write_text_with_backup(output, text)
        except OSError as exc:
            return SummaryResult(
                ok=False, error=f"写入失败：{exc}", material_count=len(included),
                elapsed=time.time() - started,
            )

        result = SummaryResult(
            ok=True,
            summary_path=output,
            backup_path=backup,
            text=text,
            material_count=len(included),
            char_count=len(context),
            chunks=chunks,
            provider=provider,
            elapsed=time.time() - started,
        )
        report(ProgressEvent("完成", 100))
        return result

    def _write_text_with_backup(self, target: Path, text: str) -> Path | None:
        """原子写入并保留上一版（沿用总结的备份策略）。"""
        backup: Path | None = None
        if target.exists():
            try:
                backup = self._backup_file(target)
            except Exception:  # noqa: BLE001 - 备份失败不阻断生成
                log.warning("备份旧版本失败：%s", target, exc_info=True)
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, target)
        return backup

    def _backup_file(self, target: Path) -> Path | None:
        """把已有文件复制到 ``else data/summary_backup`` 下（按时间戳）。"""
        try:
            from gwp.core.paths import current as current_paths

            paths = current_paths()
            stamp = time.strftime("%Y%m%d-%H%M%S")
            folder = paths.backup_dir / target.parent.parent.name / target.parent.name / stamp
            folder.mkdir(parents=True, exist_ok=True)
            destination = folder / target.name
            shutil.copy2(target, destination)
            return destination
        except Exception:  # noqa: BLE001
            return None

    def _write_summary(self, book: Book, summary_path: Path, text: str) -> Path | None:
        """先备份上一版，再原子写入新内容。返回备份目录（没有则为 None）。"""
        backup_path: Path | None = None
        if summary_path.exists() and summary_path.stat().st_size > 0:
            backup = self.backups.save_previous(book.subject_name, book.name, summary_path)
            backup_path = backup.directory if backup else None

        content = text.strip() + "\n"
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = summary_path.with_suffix(summary_path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(summary_path)
        log.info("summary 已写入: %s（%s 字符）", summary_path, len(content))
        return backup_path

    # ------------------------------------------------------------------
    # 预览 / 统计
    # ------------------------------------------------------------------

    def preview(
        self,
        book: Book,
        on_progress: ProgressCallback | None = None,
    ) -> tuple[list[SummaryMaterial], str]:
        materials = self.collect_materials(book, on_progress)
        return materials, self.build_context(materials, book)

    def stats(self, book: Book) -> dict[str, int]:
        """不解析内容，只统计各来源的文件数与大小（用于书目页快速展示）。

        除了参与总结的来源，还会额外报告**不参与总结**的目录（作业、教材）的
        真实文件数 —— 否则界面上会显示成 0，让人以为文件丢了。
        """
        result = {"intro": 0, "notebook": 0, "error-prone": 0, "total": 0, "chars": 0}
        for label, path in self.resolve_sources(book):
            if path.is_file():
                result[label] = result.get(label, 0) + 1
                result["total"] += 1
            elif path.is_dir():
                try:
                    count = sum(1 for child in path.rglob("*") if child.is_file())
                except OSError:
                    count = 0
                result[label] = result.get(label, 0) + count
                result["total"] += count

        # 不参与总结的目录：单独统计，仅供界面显示
        for key in (C.HOMEWORK_FOLDER, C.BOOK_FOLDER):
            folder = book.path / key
            if not folder.is_dir():
                result.setdefault(key, 0)
                continue
            try:
                if key == C.HOMEWORK_FOLDER:
                    # 作业栏目在界面上是"一个作业一行"，所以这里也必须数**顶层条目**：
                    # 用 rglob 会把每个作业内部的 homework.json + 内容文件都算进来，
                    # 于是标签/概览显示的数字和表格行数对不上（用户报障的那个 bug）。
                    # 规则统一为：**这里报的数字 = 点进该栏目能看到几行**。
                    result[key] = sum(
                        1 for child in folder.iterdir()
                        if not child.name.startswith(".")
                    )
                else:
                    result[key] = sum(
                        1 for child in folder.rglob("*") if child.is_file()
                    )
            except OSError:
                result[key] = 0
        return result


__all__ = [
    "ProgressEvent",
    "SummaryMaterial",
    "SummaryResult",
    "Summarizer",
]
