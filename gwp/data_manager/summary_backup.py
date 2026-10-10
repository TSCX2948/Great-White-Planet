"""Summary 版本管理：只保留“上一版”。

需求文档第六节：
* summary 更新时保存上一版；
* 新旧替换；
* 只保留一个上一版本（兼顾安全性与存储空间）。

落盘位置::

    else data/summary_backup/<科目>/<书目>/<时间戳>/<原文件名>
    else data/summary_backup/<科目>/<书目>/<时间戳>/backup.json

``backup_keep`` 配置项控制在保留几个历史目录（默认 1）。设为 0 表示关闭备份。
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from gwp.core.config import Config
from gwp.core.paths import DataPaths, current as current_paths

log = logging.getLogger(__name__)


@dataclass
class BackupRecord:
    """一个历史版本目录。"""

    directory: Path
    file: Path | None
    created_at: str
    book: str
    subject: str
    size: int = 0
    note: str = ""

    @property
    def created_label(self) -> str:
        return self.created_at.replace("T", " ")[:19] if self.created_at else self.directory.name

    @property
    def size_label(self) -> str:
        size = float(self.size)
        for unit in ("B", "KB", "MB"):
            if size < 1024 or unit == "MB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} MB"


class BackupManager:
    """管理 ``else data/summary_backup`` 下的历史版本。"""

    def __init__(self, config: Config | None = None, paths: DataPaths | None = None) -> None:
        self.config = config or Config.load()
        self.paths = paths or current_paths()

    # ------------------------------------------------------------------

    @property
    def keep(self) -> int:
        try:
            return max(0, int(self.config.get("summary.backup_keep", 1)))
        except (TypeError, ValueError):
            return 1

    def book_backup_dir(self, subject: str, book: str) -> Path:
        return self.paths.backup_book_dir(subject, book)

    def save_previous(
        self,
        subject: str,
        book: str,
        summary_file: Path,
        note: str = "",
    ) -> BackupRecord | None:
        """在覆盖 summary 之前调用：把当前文件另存为一个历史版本。

        返回保存的记录；``backup_keep=0`` 或文件不存在时返回 None。
        """
        if self.keep <= 0:
            return None
        if not summary_file.exists():
            return None

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target_dir = self.book_backup_dir(subject, book) / stamp
        # 同一秒内重复生成时避免撞名
        index = 1
        while target_dir.exists():
            target_dir = self.book_backup_dir(subject, book) / f"{stamp}_{index}"
            index += 1
        target_dir.mkdir(parents=True, exist_ok=True)

        target_file = target_dir / summary_file.name
        try:
            shutil.copy2(summary_file, target_file)
        except OSError:
            log.exception("备份 summary 失败: %s", summary_file)
            return None

        record_meta = {
            "subject": subject,
            "book": book,
            "original_name": summary_file.name,
            "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "size": target_file.stat().st_size,
            "note": note,
        }
        (target_dir / "backup.json").write_text(
            json.dumps(record_meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log.info("已保存上一版 summary: %s", target_dir)
        self.prune(subject, book)
        return BackupRecord(
            directory=target_dir,
            file=target_file,
            created_at=record_meta["created_at"],
            book=book,
            subject=subject,
            size=record_meta["size"],
            note=note,
        )

    def list_backups(self, subject: str, book: str) -> list[BackupRecord]:
        """按时间倒序列出该书目的历史版本。"""
        root = self.book_backup_dir(subject, book)
        if not root.is_dir():
            return []
        records: list[BackupRecord] = []
        for child in root.iterdir():
            if not child.is_dir():
                continue
            meta = {}
            meta_file = child / "backup.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    meta = {}
            files = [
                p for p in child.iterdir()
                if p.is_file() and p.name != "backup.json"
            ]
            main = files[0] if files else None
            records.append(
                BackupRecord(
                    directory=child,
                    file=main,
                    created_at=meta.get("created_at", ""),
                    book=meta.get("book", book),
                    subject=meta.get("subject", subject),
                    size=int(meta.get("size") or (main.stat().st_size if main else 0)),
                    note=meta.get("note", ""),
                )
            )
        records.sort(key=lambda r: r.directory.name, reverse=True)
        return records

    def latest(self, subject: str, book: str) -> BackupRecord | None:
        records = self.list_backups(subject, book)
        return records[0] if records else None

    def has_backup(self, subject: str, book: str) -> bool:
        return self.latest(subject, book) is not None

    def prune(self, subject: str, book: str) -> int:
        """只保留最近 ``keep`` 个版本，返回删除数量。"""
        keep = self.keep
        records = self.list_backups(subject, book)
        removed = 0
        for record in records[keep:]:
            try:
                shutil.rmtree(record.directory, ignore_errors=True)
                removed += 1
            except OSError:
                log.warning("删除旧备份失败: %s", record.directory)
        return removed

    def restore(
        self,
        subject: str,
        book: str,
        summary_file: Path,
        record: BackupRecord | None = None,
        keep_current: bool = True,
    ) -> bool:
        """把某个历史版本恢复为当前 summary。

        keep_current=True 时，会先把当前的 summary 另存为一个新版本，
        这样"恢复"操作本身也可以被撤销。

        注意：备份目录可能已经被新的生成操作挤掉（只保留一版），
        因此这里会校验文件确实存在；若指定版本已消失，自动改用当前最新的一版。
        """
        target = record or self.latest(subject, book)
        if target is None or target.file is None or not target.file.exists():
            # 指定的版本已被清理，退回当前最新版本
            latest = self.latest(subject, book)
            if latest is None or latest.file is None or not latest.file.exists():
                log.warning("没有可恢复的备份: %s/%s", subject, book)
                return False
            target = latest

        summary_file = Path(summary_file)
        if keep_current and summary_file.exists() and summary_file.stat().st_size > 0:
            # 先把当前版本存起来，但不要因为新增备份而把要恢复的版本挤掉
            self.save_previous(subject, book, summary_file, note="恢复前的自动备份")
            if not target.file.exists():
                latest = self.latest(subject, book)
                if latest is None or latest.file is None:
                    return False
                target = latest

        summary_file.parent.mkdir(parents=True, exist_ok=True)
        if target.file is None or not target.file.exists():
            return False
        shutil.copy2(target.file, summary_file)
        log.info("已恢复 summary: %s <- %s", summary_file, target.file)
        return True

    def read_backup_text(self, record: BackupRecord) -> str:
        if record.file is None or not record.file.exists():
            return ""
        try:
            return record.file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def delete_all(self, subject: str, book: str) -> None:
        shutil.rmtree(self.book_backup_dir(subject, book), ignore_errors=True)
