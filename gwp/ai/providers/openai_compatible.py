"""OpenAI 兼容协议的提供方。

DeepSeek API、GPT API 以及绝大多数第三方兼容网关都使用同一套
``/chat/completions`` 协议，因此共用一个实现，只靠配置区分：

    {
      "type": "openai_compatible",
      "base_url": "https://api.deepseek.com",
      "path": "/chat/completions",
      "model": "deepseek-chat",
      "api_key_env": "DEEPSEEK_API_KEY"
    }

要接入新服务（通义、Kimi、本地 vLLM……），只需在 config.json 里再加一段配置，
不需要写新代码。
"""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
from pathlib import Path
from typing import Any

from gwp.ai.base import BaseAIAdapter, http_json, http_stream_lines, retry_call
from gwp.ai.registry import ProviderMeta, register_provider
from gwp.ai.types import (
    AIAuthError,
    AIError,
    ChatMessage,
    ChatOptions,
    ChunkHandler,
)
from gwp.core.config import Config

log = logging.getLogger(__name__)


class OpenAICompatibleAdapter(BaseAIAdapter):
    """任何兼容 OpenAI Chat Completions 协议的服务。"""

    provider_id = "openai_compatible"
    label = "OpenAI 兼容 API"
    kind = "api"

    # -- 元数据 ---------------------------------------------------------

    @classmethod
    def describe(cls) -> ProviderMeta:
        return ProviderMeta(
            provider_id=cls.provider_id,
            label=cls.label,
            kind="api",
            description=cls.description or "兼容 OpenAI /chat/completions 协议的服务",
            needs_api_key=True,
            needs_base_url=True,
            needs_model=True,
            supports_stream=True,
            supports_images=bool(getattr(cls, "supports_vision", False)),
        )

    def is_configured(self) -> tuple[bool, str]:
        if not self.setting("base_url"):
            return False, "未配置接口地址（base_url）"
        if not self.setting("model"):
            return False, "未配置模型名（model）"
        if not self.api_key:
            env = self.setting("api_key_env", "")
            hint = f"，或设置环境变量 {env}" if env else ""
            return False, f"未配置 API Key（请在 AI 设置里填写{hint}）"
        return True, ""

    def diagnose(self) -> tuple[bool, str]:
        """连通性自检，并把常见故障原因说清楚。

        覆盖实际最容易踩的坑：把 Key 配到了别的提供方、用了中转站却填官方地址、
        Key 被截断或带空格、额度用尽、以及"用浏览器验证根地址"导致的误判。
        """
        ok, reason = self.is_configured()
        if not ok:
            return False, reason

        try:
            reply = self.complete(
                [ChatMessage(role="user", content="回复两个字：正常")],
                ChatOptions(max_tokens=16, timeout=min(30, self._timeout(None))),
            )
        except AIAuthError as exc:
            return False, self._auth_hint(exc)
        except AIError as exc:
            return False, str(exc)
        except Exception as exc:  # noqa: BLE001
            return False, f"未预期的错误：{exc}"

        return True, (
            f"连接正常：{(reply or '').strip()[:40]}\n"
            f"接口：{self.endpoint}\n模型：{self.model}"
        )

    def _auth_hint(self, exc: Exception) -> str:
        """鉴权失败时给出可操作的排查清单。"""
        label = self.setting("label", self.label)
        lines = [
            f"鉴权失败：{exc}",
            "",
            "常见原因与排查：",
            f"1. Key 配错了提供方 —— 当前用的是「{label}」，确认 Key 来自这个服务商；",
            f"2. Key 不完整或带空格（当前长度 {len(self.api_key)}；"
            "DeepSeek 的 Key 以 sk- 开头，约 35 个字符）；",
            "3. 用浏览器打开 https://api.deepseek.com/ 会显示 Authentication Fails，"
            "这是官方设计如此，不代表 Key 失效；",
            "4. 用的是中转/聚合站账号：接口地址要改为该站提供的地址，不能填官方域名；",
            "5. 账号欠费或 Key 已被吊销，请到服务商控制台确认；",
            f"6. 模型名不匹配也可能报鉴权类错误，当前模型为 {self.model}。",
        ]
        return "\n".join(lines)

    # -- 请求构造 -------------------------------------------------------

    @property
    def endpoint(self) -> str:
        base = str(self.setting("base_url", "")).rstrip("/")
        path = str(self.setting("path", "/chat/completions") or "/chat/completions")
        if path.startswith("http"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return base + path

    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        extra = self.settings.get("extra_headers") or {}
        if isinstance(extra, dict):
            headers.update({str(k): str(v) for k, v in extra.items()})
        return headers

    def _payload(
        self,
        messages: list[ChatMessage],
        options: ChatOptions,
        stream: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": options.model or self.model,
            "messages": self._encode_messages(messages),
            "stream": bool(stream),
        }
        if options.temperature is not None:
            payload["temperature"] = float(options.temperature)
        if options.max_tokens:
            payload["max_tokens"] = int(options.max_tokens)
        payload.update(options.extra or {})
        # 部分网关要求 stream_options
        if stream and self.config.get("ai.stream_include_usage", False):
            payload["stream_options"] = {"include_usage": True}
        return payload

    def _encode_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        encoded: list[dict[str, Any]] = []
        for message in messages:
            if message.images and self._vision_enabled():
                content: list[dict[str, Any]] = []
                if message.content:
                    content.append({"type": "text", "text": message.content})
                for image_path in message.images:
                    encoded_image = self._encode_image(image_path)
                    if encoded_image:
                        content.append({"type": "image_url", "image_url": {"url": encoded_image}})
                encoded.append({"role": message.role, "content": content or message.content})
            else:
                item: dict[str, Any] = {"role": message.role, "content": message.content}
                encoded.append(item)
        return encoded

    def _vision_enabled(self) -> bool:
        if not self.settings.get("supports_vision"):
            return False
        return bool(self.config.get("ai.send_images", False))

    @staticmethod
    def _encode_image(image_path: str) -> str:
        try:
            path = Path(image_path)
            if not path.is_file():
                return ""
            mime = mimetypes.guess_type(path.name)[0] or "image/png"
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime};base64,{data}"
        except OSError:
            return ""

    # -- 调用 -----------------------------------------------------------

    def complete(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> str:
        prepared, opts = self._prepare(messages, options)
        payload = self._payload(prepared, opts, stream=False)
        timeout = self._timeout(opts)
        attempts = max(1, int(self.config.get("ai.max_retries", 2) or 1))

        data = retry_call(
            lambda: http_json(self.endpoint, payload, self._headers(), timeout=timeout),
            attempts=attempts,
        )
        return self._extract_text(data)

    def stream(
        self,
        messages: list[ChatMessage],
        options: ChatOptions | None = None,
        on_chunk: ChunkHandler | None = None,
    ) -> str:
        prepared, opts = self._prepare(messages, options)
        if not opts.stream:
            return self.complete(prepared, opts)

        payload = self._payload(prepared, opts, stream=True)
        timeout = self._timeout(opts)
        collected: list[str] = []

        try:
            for line in http_stream_lines(self.endpoint, payload, self._headers(), timeout=timeout):
                if line in ("[DONE]", "DONE"):
                    break
                delta = self._extract_delta(line)
                if delta:
                    collected.append(delta)
                    if on_chunk:
                        on_chunk(delta)
        except AIError:
            # 有些网关不支持流式；已经收到内容就不要重试，否则回退到一次性请求
            if collected:
                raise
            log.warning("流式请求失败，回退到非流式：%s", self.provider_id)
            return self.complete(prepared, opts)

        text = "".join(collected)
        if not text:
            # 服务端返回了空流：再试一次非流式
            return self.complete(prepared, opts)
        return text

    # -- 解析 -----------------------------------------------------------

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            # 有些服务把内容放在 output_text / content
            for key in ("output_text", "content", "text", "answer"):
                if isinstance(data.get(key), str):
                    return data[key]
            raise AIError(f"AI 返回中没有 choices 字段：{json.dumps(data, ensure_ascii=False)[:200]}")
        first = choices[0] or {}
        message = first.get("message") or {}
        content = message.get("content")
        if isinstance(content, list):
            parts = [part.get("text", "") for part in content if isinstance(part, dict)]
            content = "".join(parts)
        if content is None:
            content = first.get("text") or ""
        if message.get("reasoning_content") and not content:
            content = message["reasoning_content"]
        return str(content)

    @staticmethod
    def _extract_delta(line: str) -> str:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            return ""
        if not isinstance(data, dict):
            return ""
        if data.get("error"):
            error = data["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise AIAuthError(f"AI 服务返回错误：{message}")
        choices = data.get("choices") or []
        if not choices:
            return ""
        first = choices[0] or {}
        delta = first.get("delta") or {}
        content = delta.get("content")
        if content is None:
            content = first.get("text") or ""
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        return str(content or "")


# --------------------------------------------------------------------------
# 具体提供方：只是配置好的子类
# --------------------------------------------------------------------------

@register_provider
class DeepSeekAPIAdapter(OpenAICompatibleAdapter):
    """DeepSeek API（api.deepseek.com）。"""

    provider_id = "deepseek_api"
    label = "DeepSeek API"
    description = "DeepSeek 官方 API，兼容 OpenAI 协议"

    def __init__(self, config: Config | None = None, **overrides: Any) -> None:
        super().__init__(config, **overrides)
        defaults = {
            "base_url": "https://api.deepseek.com",
            "path": "/chat/completions",
            "model": "deepseek-chat",
            "api_key_env": "DEEPSEEK_API_KEY",
        }
        for key, value in defaults.items():
            self.settings.setdefault(key, value)
            if not self.settings.get(key):
                self.settings[key] = value


@register_provider
class GPTAPIAdapter(OpenAICompatibleAdapter):
    """GPT API（api.openai.com）。"""

    provider_id = "gpt_api"
    label = "GPT API"
    description = "OpenAI 官方 API，支持图片输入"

    def __init__(self, config: Config | None = None, **overrides: Any) -> None:
        super().__init__(config, **overrides)
        defaults = {
            "base_url": "https://api.openai.com",
            "path": "/v1/chat/completions",
            "model": "gpt-4o-mini",
            "api_key_env": "OPENAI_API_KEY",
        }
        for key, value in defaults.items():
            self.settings.setdefault(key, value)
            if not self.settings.get(key):
                self.settings[key] = value


@register_provider
class CustomAPIAdapter(OpenAICompatibleAdapter):
    """自定义的 OpenAI 兼容服务（本地 vLLM、第三方网关等）。"""

    provider_id = "custom_api"
    label = "自定义 API"
    description = "任何兼容 OpenAI 协议的第三方或本地服务"


__all__ = [
    "CustomAPIAdapter",
    "DeepSeekAPIAdapter",
    "GPTAPIAdapter",
    "OpenAICompatibleAdapter",
]
