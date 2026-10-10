"""扫描缓存：加速启动（需求文档第十三节：提前完成文件扫描，减少等待）。

缓存只保存**轻量元数据**（科目列表与每个科目目录的 mtime），
用于判断"自上次扫描以来目录有没有变过"。缓存失效或损坏时自动回退到完整扫描，
不会影响正确性。
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from gwp.core.paths import DataPaths, current as current_paths

log = logging.getLogger(__name__)

CACHE_VERSION = 1


class ScanCache:
    def __init__(self, paths: DataPaths | None = None) -> None:
        self.paths = paths or current_paths()
        self.file = self.paths.cache_dir / "scan_cache.json"
        self._data: dict = {"version": CACHE_VERSION, "subjects": {}, "saved_at": 0}
        self.load()

    # ------------------------------------------------------------------

    def load(self) -> None:
        if not self.file.exists():
            return
        try:
            data = json.loads(self.file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("version") == CACHE_VERSION:
                self._data = data
        except (OSError, json.JSONDecodeError):
            log.debug("扫描缓存不可用，忽略: %s", self.file)

    def save(self) -> None:
        try:
            self.file.parent.mkdir(parents=True, exist_ok=True)
            self._data["saved_at"] = time.time()
            tmp = self.file.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self.file)
        except OSError:
            log.debug("写入扫描缓存失败: %s", self.file)

    # ------------------------------------------------------------------

    def subject_signature(self, subject_dir: Path) -> float:
        try:
            return subject_dir.stat().st_mtime
        except OSError:
            return 0.0

    def is_fresh(self, subject_dir: Path) -> bool:
        entry = self._data.get("subjects", {}).get(subject_dir.name)
        if not entry:
            return False
        return abs(float(entry.get("mtime", 0)) - self.subject_signature(subject_dir)) < 0.001

    def record(self, subject_dir: Path, book_count: int, file_count: int, size: int) -> None:
        self._data.setdefault("subjects", {})[subject_dir.name] = {
            "mtime": self.subject_signature(subject_dir),
            "books": book_count,
            "files": file_count,
            "size": size,
            "scanned_at": time.time(),
        }

    def drop(self, subject_name: str) -> None:
        self._data.get("subjects", {}).pop(subject_name, None)

    def clear(self) -> None:
        self._data = {"version": CACHE_VERSION, "subjects": {}, "saved_at": 0}

    def summary(self) -> dict:
        subjects = self._data.get("subjects", {})
        return {
            "subject_count": len(subjects),
            "book_count": sum(int(v.get("books", 0)) for v in subjects.values()),
            "saved_at": self._data.get("saved_at", 0),
        }
