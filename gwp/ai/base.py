"""AI 适配器基类、提问块解析器、HTTP 工具。

子类只需要实现 :meth:`BaseAIAdapter.complete`（或 :meth:`stream`），
其余（提问交互、重试、异常归一化、配置读取）都由基类处理。
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any, Iterator

from gwp.ai.types import (
    AIAuthError,
    AIConfigError,
    AIError,
    AINetworkError,
    AIRateLimitError,
    AiQuestion,
    ChatCancelled,
    ChatMessage,
    ChatOptions,
    ChunkHandler,
    QuestionHandler,
)
from gwp.core.config import Config

log = logging.getLogger(__name__)


# ==========================================================================
# 提问块解析
# ==========================================================================

FENCE_OPEN = "```gwp:ask"
FENCE_CLOSE = "```"
COMMENT_OPEN = "<!--GWP:ASK"
COMMENT_CLOSE = "-->"


class QuestionBlockParser:
    """从流式文本中识别 AI 的提问块。

    支持两种写法（提示词里会教给 AI）::

        ```gwp:ask
        {"question": "这里的符号是内积还是外积？", "options": ["内积", "外积"], "allow_custom": true}
        ```

        <!--GWP:ASK {"question": "..."} -->

    块之前的所有文字会作为普通回答输出；块本身变成 :class:`AiQuestion`。
    只有**完整**的块才会被识别，因此流式输出中间态不会误触发。

    用法::

        parser = QuestionBlockParser()
        for delta in stream:
            text, questions = parser.feed(delta)      # 增量：只吐安全部分
            on_chunk(text)
            for payload in questions: ...
        text, questions = parser.finish()             # 收尾：吐干净
    """

    def __init__(self, max_buffer: int = 400_000) -> None:
        self.buffer = ""
        self.consumed = 0          # 缓冲区中已经吐出过的前缀长度
        self.max_buffer = max_buffer

    # -- 主接口 ---------------------------------------------------------

    def feed(self, text: str) -> tuple[str, list[dict[str, Any]]]:
        """喂入增量文本，返回 (可安全显示的文本, 已完成的提问块)。"""
        self.buffer += text
        return self._drain(final=False)

    def finish(self, text: str = "") -> tuple[str, list[dict[str, Any]]]:
        """结束一轮：把剩余内容全部吐出（未闭合的提问块按普通文本处理）。"""
        self.buffer += text
        return self._drain(final=True)

    # -- 内部实现 -------------------------------------------------------

    def _drain(self, final: bool) -> tuple[str, list[dict[str, Any]]]:
        questions: list[dict[str, Any]] = []
        while True:
            found = self._find_open()
            if found is None:
                # 没有提问块：吐出安全前缀（保留可能是标记开头的一小截）
                limit = len(self.buffer) if final else self._safe_limit()
                piece = self.buffer[self.consumed:limit]
                self.consumed = limit
                return piece, questions

            start, open_len = found
            if start > self.consumed:
                # 标记之前还有正文，先吐出去
                piece = self.buffer[self.consumed:start]
                self.consumed = start
                return piece, questions

            is_fence = self.buffer.startswith(FENCE_OPEN)
            closing = FENCE_CLOSE if is_fence else COMMENT_CLOSE
            end = self.buffer.find(closing, open_len)
            if end < 0 and not final:
                return "", questions      # 块还没结束，继续等
            if end < 0:
                # 始终没闭合：当作普通文本
                piece = self.buffer[self.consumed:]
                self.consumed = len(self.buffer)
                return piece, questions

            payload_text = self.buffer[open_len:end].strip().lstrip("\n")
            payload = _parse_json_object(payload_text)
            if payload is not None:
                questions.append(payload)
            else:
                # JSON 不合法：保留原文，不要把内容吞掉
                questions.append({"question": payload_text.strip(), "options": [], "allow_custom": True})
            self.consumed = end + len(closing)
            self._compact()

    def _safe_limit(self) -> int:
        """返回可安全吐出的缓冲区长度（末尾可能是标记开头，先留着）。"""
        limit = len(self.buffer)
        for marker in (FENCE_OPEN, COMMENT_OPEN):
            for size in range(min(len(marker) - 1, limit - self.consumed), 0, -1):
                if self.buffer.endswith(marker[:size]):
                    limit = len(self.buffer) - size
                    break
        return max(limit, self.consumed)

    def _compact(self) -> None:
        """丢掉已经消费掉的前缀，避免缓冲区无限增长。"""
        if self.consumed > 4096:
            self.buffer = self.buffer[self.consumed:]
            self.consumed = 0
        if len(self.buffer) > self.max_buffer:
            self.buffer = self.buffer[-self.max_buffer:]
            self.consumed = 0

    def _find_open(self) -> tuple[int, int] | None:
        fenced = self.buffer.find(FENCE_OPEN, self.consumed)
        comment = self.buffer.find(COMMENT_OPEN, self.consumed)
        candidates: list[tuple[int, int]] = []
        if fenced >= 0:
            candidates.append((fenced, len(FENCE_OPEN)))
        if comment >= 0:
            candidates.append((comment, len(COMMENT_OPEN)))
        return min(candidates) if candidates else None


def _parse_json_object(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        pass
    # 容错：从混杂文本里抠出第一个 {...}
    start = text.find("{")
    end = text.rfind("}")
    if 0 <= start < end:
        try:
            data = json.loads(text[start:end + 1])
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None
    return None


# ==========================================================================
# HTTP 工具（只用标准库，便于在没有第三方依赖的环境里运行）
# ==========================================================================

class HttpError(AIError):
    def __init__(self, message: str, status: int = 0, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body


def http_json(
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 120,
    method: str = "POST",
) -> dict[str, Any]:
    """发送 JSON 请求并解析 JSON 响应。异常统一转成 AIError 子类。"""
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json")
    request.add_header("User-Agent", "GreatWhitePlanet/1.0")
    for key, value in (headers or {}).items():
        if value:
            request.add_header(key, str(value))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
        raise _http_error_to_ai(exc.code, body, str(exc)) from exc
    except urllib.error.URLError as exc:
        raise AINetworkError(f"网络连接失败：{exc.reason}") from exc
    except TimeoutError as exc:
        raise AINetworkError(f"请求超时（{timeout}s），请检查网络或调大超时时间。") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AIError(f"AI 返回了无法解析的内容：{raw[:200]}") from exc
    if not isinstance(parsed, dict):
        raise AIError("AI 返回的数据格式不是对象")
    return parsed


def http_stream_lines(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
    timeout: int = 180,
) -> Iterator[str]:
    """发送请求并按行产出 SSE 数据（自动去掉 ``data: `` 前缀）。"""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "text/event-stream")
    request.add_header("User-Agent", "GreatWhitePlanet/1.0")
    for key, value in (headers or {}).items():
        if value:
            request.add_header(key, str(value))

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            for raw_line in response:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                if line.startswith("data:"):
                    line = line[5:].strip()
                yield line
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
        raise _http_error_to_ai(exc.code, body, str(exc)) from exc
    except urllib.error.URLError as exc:
        raise AINetworkError(f"网络连接失败：{exc.reason}") from exc
    except TimeoutError as exc:
        raise AINetworkError(f"请求超时（{timeout}s）") from exc


def _http_error_to_ai(status: int, body: str, fallback: str) -> AIError:
    detail = _extract_error_message(body) or fallback
    if status in (401, 403):
        return AIAuthError(f"鉴权失败（HTTP {status}）：{detail}")
    if status == 404:
        return AIConfigError(f"接口地址不存在（HTTP 404）：{detail}")
    if status == 429:
        return AIRateLimitError(f"请求过于频繁或额度用尽（HTTP 429）：{detail}")
    if status >= 500:
        return AINetworkError(f"AI 服务端错误（HTTP {status}）：{detail}")
    return AIError(f"请求失败（HTTP {status}）：{detail}")


def _extract_error_message(body: str) -> str:
    if not body:
        return ""
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body[:300]
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error)[:300]
        if isinstance(error, str):
            return error[:300]
        for key in ("message", "msg", "detail"):
            if data.get(key):
                return str(data[key])[:300]
    return body[:300]


# ==========================================================================
# 适配器基类
# ==========================================================================

class BaseAIAdapter(ABC):
    """所有 AI 提供方的基类。

    子类至少要实现 :meth:`complete`；如果能流式输出就覆盖 :meth:`stream`。
    """

    #: 唯一标识，必须与 config.json 中 ``ai.providers`` 的键一致
    provider_id: str = "base"
    #: 界面显示名（可被配置覆盖）
    label: str = "AI"
    #: api | web | local
    kind: str = "api"
    description: str = ""

    def __init__(self, config: Config | None = None, **overrides: Any) -> None:
        self.config = config or Config.load()
        self.settings: dict[str, Any] = dict(self.config.get(f"ai.providers.{self.provider_id}", {}) or {})
        self.settings.update(overrides)
        self.api_key = self.config.api_key_for(self.provider_id)

    # -- 元数据 ---------------------------------------------------------

    @classmethod
    def describe(cls) -> "ProviderMeta":
        from gwp.ai.registry import ProviderMeta

        return ProviderMeta(
            provider_id=cls.provider_id,
            label=cls.label,
            kind=cls.kind,
            description=cls.description or (cls.__doc__ or "").strip().splitlines()[0]
            if cls.__doc__ else cls.description,
        )

    # -- 可用性 ---------------------------------------------------------

    def is_configured(self) -> tuple[bool, str]:
        """返回 (是否可用, 不可用原因)。界面用它决定是否允许切换。"""
        return True, ""

    def test_connection(self) -> tuple[bool, str]:
        """连通性自检（菜单里的「刷新 AI」与设置里的「测试连接」都会调用）。

        子类如果实现了 :meth:`diagnose`，优先用它——这样可以给出更有针对性的排查提示。
        """
        diagnose = getattr(self, "diagnose", None)
        if callable(diagnose):
            try:
                return diagnose()
            except AIError as exc:
                return False, str(exc)
            except Exception as exc:  # noqa: BLE001
                return False, f"未预期的错误：{exc}"

        try:
            text = self.complete(
                [ChatMessage(role="user", content="回复两个字：正常")],
                ChatOptions(max_tokens=16, timeout=min(30, int(self.setting("timeout", 30) or 30))),
            )
            return True, f"连接正常：{(text or '').strip()[:40]}"
        except AIError as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001
            return False, f"未预期的错误：{exc}"

    # -- 配置辅助 -------------------------------------------------------

    def setting(self, key: str, default: Any = None) -> Any:
        value = self.settings.get(key, None)
        return default if value in (None, "") else value

    @property
    def model(self) -> str:
        return str(self.setting("model", ""))

    @property
    def display_label(self) -> str:
        label = str(self.setting("label", "") or self.label)
        model = self.model
        return f"{label}（{model}）" if model else label

    def _timeout(self, options: ChatOptions | None = None) -> int:
        if options and options.timeout:
            return int(options.timeout)
        return int(self.config.get("ai.request_timeout", 180) or 180)

    def _prepare(
        self,
        messages: list[ChatMessage],
        options: ChatOptions | None,
    ) -> tuple[list[ChatMessage], ChatOptions]:
        opts = options or ChatOptions()
        if opts.temperature is None:
            opts.temperature = float(self.config.get("ai.temperature", 0.3) or 0.3)
        if opts.max_tokens is None:
            opts.max_tokens = int(self.config.get("ai.max_tokens", 8192) or 8192)
        if opts.stream is None:
            opts.stream = bool(self.config.get("ai.stream", True))
        if not opts.model:
            opts.model = self.model
        prepared = list(messages)
        if opts.system and not any(m.role == "system" for m in prepared):
            prepared.insert(0, ChatMessage(role="system", content=opts.system))
        return prepared, opts

    # -- 核心接口 -------------------------------------------------------

    @abstractmethod
    def complete(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> str:
        """一次性返回完整回答。"""

    def stream(
        self,
        messages: list[ChatMessage],
        options: ChatOptions | None = None,
        on_chunk: ChunkHandler | None = None,
    ) -> str:
        """默认实现：不支持流式时退化为一次性返回，再整体回调一次。"""
        text = self.complete(messages, options)
        if on_chunk and text:
            on_chunk(text)
        return text

    # -- 带提问交互的对话（推荐入口） -----------------------------------

    def chat(
        self,
        messages: list[ChatMessage],
        options: ChatOptions | None = None,
        on_chunk: ChunkHandler | None = None,
        question_handler: QuestionHandler | None = None,
        should_cancel: Any = None,
        max_questions: int = 6,
    ) -> str:
        """发起一次对话；如果 AI 抛出提问块，就交给 ``question_handler`` 询问用户，
        把用户回答追加进对话后继续，直到得到正式回答。

        与 :meth:`stream` 的区别是：这里会把 ``gwp:ask`` 块从可见文本中剥离，
        变成界面上的弹窗提问，用户回答后自动继续下一轮。
        """
        conversation = list(messages)
        collected: list[str] = []

        def _cancel_check() -> bool:
            return bool(callable(should_cancel) and should_cancel())

        for _round in range(max(1, max_questions)):
            parser = QuestionBlockParser()
            asked: list[dict[str, Any]] = []

            def _emit(text: str) -> None:
                if text:
                    collected.append(text)
                    if on_chunk:
                        on_chunk(text)

            def _on_delta(delta: str) -> None:
                if _cancel_check():
                    raise ChatCancelled("已取消")
                text, questions = parser.feed(delta)
                _emit(text)
                asked.extend(questions)

            raw = self.stream(conversation, options, _on_delta)
            tail_text, tail_questions = parser.finish()
            _emit(tail_text)
            asked.extend(tail_questions)

            if not asked:
                return "".join(collected)

            if question_handler is None:
                raise AIConfigError(
                    "AI 需要向你确认信息（提出了问题），但当前界面没有提供提问入口。"
                )

            conversation.append(ChatMessage(role="assistant", content=raw or "".join(collected)))
            collected.clear()
            for payload in asked:
                question = AiQuestion.from_payload(payload)
                if question is None:
                    continue
                reply = question_handler(question)
                if reply is None:
                    raise ChatCancelled("用户取消了本次回答")
                conversation.append(ChatMessage(role="user", content=f"【用户回答】{reply}"))

        raise AIError(f"AI 连续提问超过 {max_questions} 次，已停止。请检查提示词或手动补充信息。")

    # -- 工具 -----------------------------------------------------------

    @staticmethod
    def _messages_to_dicts(messages: list[ChatMessage]) -> list[dict[str, Any]]:
        return [m.to_dict() for m in messages if m.content or m.images]

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__} id={self.provider_id}>"


def retry_call(func, attempts: int = 2, delay: float = 1.0, on_retry=None):
    """给网络调用加重试：只对可重试错误重试（限流/网络）。"""
    last: Exception | None = None
    for index in range(max(1, attempts)):
        try:
            return func()
        except (AIRateLimitError, AINetworkError) as exc:
            last = exc
            if index < attempts - 1:
                if on_retry:
                    on_retry(index + 1, exc)
                time.sleep(delay * (index + 1))
                continue
            raise
    if last:
        raise last
