"""AI 层的数据结构与异常。

这一层刻意不认识 Qt、也不认识 HTTP 库：
适配器只负责"把消息发给某个 AI，把回答拿回来"，具体怎么发由子类决定。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


# --------------------------------------------------------------------------
# 异常
# --------------------------------------------------------------------------

class AIError(Exception):
    """AI 调用失败的基类。message 会直接展示给用户，请写中文。"""


class AIConfigError(AIError):
    """配置缺失（例如没有填 API Key、没有配置本地命令）。"""


class AINetworkError(AIError):
    """网络不可达、超时、DNS 失败等。"""


class AIAuthError(AIError):
    """鉴权失败（Key 无效、额度不足）。"""


class AIRateLimitError(AIError):
    """被限流或服务端过载。"""


class AIUnavailableError(AIError):
    """该提供方当前不可用（网页版需要人工操作、外部程序不存在等）。"""


# --------------------------------------------------------------------------
# 消息
# --------------------------------------------------------------------------

@dataclass
class ChatMessage:
    """一条对话消息。``images`` 用于多模态（本地图片路径列表）。"""

    role: str                       # system | user | assistant
    content: str
    images: list[str] = field(default_factory=list)
    name: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.name:
            data["name"] = self.name
        if self.meta:
            data["meta"] = self.meta
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatMessage":
        return cls(
            role=str(data.get("role", "user")),
            content=str(data.get("content", "")),
            images=list(data.get("images") or []),
            name=str(data.get("name", "")),
            meta=dict(data.get("meta") or {}),
        )


@dataclass
class ChatOptions:
    """单次调用的参数，缺省时由配置填充。"""

    model: str = ""
    temperature: float | None = None
    max_tokens: int | None = None
    stream: bool | None = None
    timeout: int | None = None
    system: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# --------------------------------------------------------------------------
# 提问机制（需求文档第七节：AI 不确定时弹窗询问用户）
# --------------------------------------------------------------------------

@dataclass
class AiQuestion:
    """AI 抛给用户的问题。"""

    question: str
    options: list[str] = field(default_factory=list)
    allow_custom: bool = True
    context: str = ""

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AiQuestion | None":
        question = str(payload.get("question") or payload.get("q") or "").strip()
        if not question:
            return None
        options = payload.get("options") or payload.get("choices") or []
        if isinstance(options, str):
            options = [options]
        options = [str(item) for item in options if str(item).strip()]
        return cls(
            question=question,
            options=options,
            allow_custom=bool(payload.get("allow_custom", True)),
            context=str(payload.get("context", "")),
        )


#: 界面层实现的回调：接收问题，返回用户答案（返回 None 表示用户取消）
QuestionHandler = Callable[[AiQuestion], "str | None"]
#: 流式增量回调
ChunkHandler = Callable[[str], None]


class ChatCancelled(AIError):
    """用户主动中断了本次回答。"""
