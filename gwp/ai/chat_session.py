"""AI 聊天记录：会话模型与持久化。

需求文档第七节的规则：
* 首次在文件中打开 AI：自动发送当前文件；
* 关闭 AI：保存聊天记录；
* 关闭软件：清除所有 AI 聊天记录。

因此聊天记录存放在 ``else data/chats``（非用户数据），并提供一个"清空"入口。
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from gwp.ai.types import ChatMessage
from gwp.core.config import Config
from gwp.core.paths import DataPaths, current as current_paths

log = logging.getLogger(__name__)


@dataclass
class ChatSession:
    """一个文档（或书目）的聊天会话。"""

    key: str                                    # 稳定标识，例如 "高代/数学分析/notebook/a.md"
    title: str = ""
    provider: str = ""
    document_path: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: list[ChatMessage] = field(default_factory=list)
    file_sent: bool = False                     # 是否已经自动发送过当前文件
    attachments: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    # -- 消息操作 -------------------------------------------------------

    def add(self, role: str, content: str, images: list[str] | None = None, **meta) -> ChatMessage:
        message = ChatMessage(role=role, content=content, images=list(images or []), meta=meta)
        self.messages.append(message)
        self.updated_at = time.time()
        return message

    def clear(self) -> None:
        self.messages.clear()
        self.file_sent = False
        self.updated_at = time.time()

    def remove_last(self, count: int = 1) -> None:
        for _ in range(max(0, count)):
            if self.messages:
                self.messages.pop()
        self.updated_at = time.time()

    @property
    def is_empty(self) -> bool:
        return not self.messages

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "title": self.title,
            "provider": self.provider,
            "document_path": self.document_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "file_sent": self.file_sent,
            "attachments": self.attachments,
            "meta": self.meta,
            "messages": [m.to_dict() for m in self.messages],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChatSession":
        return cls(
            key=str(data.get("key", "")),
            title=str(data.get("title", "")),
            provider=str(data.get("provider", "")),
            document_path=str(data.get("document_path", "")),
            created_at=float(data.get("created_at") or time.time()),
            updated_at=float(data.get("updated_at") or time.time()),
            messages=[ChatMessage.from_dict(item) for item in data.get("messages", [])],
            file_sent=bool(data.get("file_sent", False)),
            attachments=list(data.get("attachments") or []),
            meta=dict(data.get("meta") or {}),
        )


class ChatStore:
    """聊天记录的磁盘存储。文件名由 key 的哈希决定，避免非法路径字符。"""

    def __init__(self, config: Config | None = None, paths: DataPaths | None = None) -> None:
        self.config = config or Config.load()
        self.paths = paths or current_paths()

    @property
    def directory(self) -> Path:
        return self.paths.chat_dir

    def _file_for(self, key: str) -> Path:
        import hashlib

        digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
        return self.directory / f"{digest}.json"

    def load(self, key: str) -> ChatSession:
        path = self._file_for(key)
        if not path.exists():
            return ChatSession(key=key)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            session = ChatSession.from_dict(data)
            session.key = key
            return session
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("聊天记录读取失败（已忽略）: %s (%s)", path, exc)
            return ChatSession(key=key)

    def save(self, session: ChatSession) -> Path | None:
        if not self.config.get("ai.persist_chat_on_close", True):
            return None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self._file_for(session.key)
            payload = json.dumps(session.to_dict(), ensure_ascii=False, indent=2)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, path)
            return path
        except OSError:
            log.exception("聊天记录保存失败: %s", session.key)
            return None

    def delete(self, key: str) -> bool:
        path = self._file_for(key)
        try:
            if path.exists():
                path.unlink()
                return True
        except OSError:
            log.exception("删除聊天记录失败: %s", path)
        return False

    def list_sessions(self) -> list[dict]:
        if not self.directory.exists():
            return []
        items = []
        for file in self.directory.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                items.append(
                    {
                        "key": data.get("key", ""),
                        "title": data.get("title", ""),
                        "provider": data.get("provider", ""),
                        "updated_at": float(data.get("updated_at") or 0),
                        "message_count": len(data.get("messages") or []),
                        "file": file,
                    }
                )
            except (OSError, json.JSONDecodeError):
                continue
        items.sort(key=lambda item: item["updated_at"], reverse=True)
        return items

    def clear_all(self, keep_days: int = 0) -> int:
        """清空聊天记录。keep_days > 0 时只删除更早的记录。返回删除数量。"""
        if not self.directory.exists():
            return 0
        cutoff = time.time() - keep_days * 86400 if keep_days > 0 else None
        removed = 0
        for file in self.directory.glob("*.json"):
            try:
                if cutoff is not None and file.stat().st_mtime >= cutoff:
                    continue
                file.unlink()
                removed += 1
            except OSError:
                continue
        # 清掉可能残留的临时文件
        for tmp in self.directory.glob("*.tmp"):
            try:
                tmp.unlink()
            except OSError:
                pass
        log.info("已清除 %s 个聊天记录文件", removed)
        return removed

    def clear_all_force(self) -> None:
        shutil.rmtree(self.directory, ignore_errors=True)


def session_key(*parts: str) -> str:
    """由若干路径片段拼出一个稳定的会话键。"""
    cleaned = [str(part).replace("\\", "/").strip("/") for part in parts if part]
    return "/".join(cleaned) or uuid.uuid4().hex


__all__ = ["ChatSession", "ChatStore", "session_key"]
