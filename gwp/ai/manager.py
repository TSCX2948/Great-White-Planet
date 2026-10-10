"""AI 门面：当前提供方、切换、刷新、失败自动兜底。

界面只和 :class:`AIManager` 打交道，不直接创建适配器。
要新增一个 AI 后端，只需要在 ``gwp/ai/providers/`` 加一个文件 + 一段配置，
本模块与界面都无需修改。
"""

from __future__ import annotations

import logging
from typing import Any

from gwp.ai import registry
from gwp.ai.base import BaseAIAdapter
from gwp.ai.types import AIError, AIUnavailableError, ChatMessage, ChatOptions
from gwp.core.config import Config
from gwp.core.eventbus import AI_FALLBACK, AI_PROVIDER_CHANGED, bus

log = logging.getLogger(__name__)


class AIManager:
    """管理"当前 AI"以及失败后的兜底链。"""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.load()
        self._adapters: dict[str, BaseAIAdapter] = {}
        self._active_id: str = str(self.config.get("ai.active_provider", "") or "")
        registry.discover()

    # ------------------------------------------------------------------
    # 提供方列表
    # ------------------------------------------------------------------

    def provider_ids(self) -> list[str]:
        """配置里启用的提供方（保持配置顺序，界面菜单按此顺序展示）。"""
        configured = self.config.get("ai.providers", {}) or {}
        enabled = [pid for pid, node in configured.items() if (node or {}).get("enabled", True)]
        known = registry.provider_ids()
        # 配置里还没登记、但代码里存在的提供方也列出来（方便升级后自动出现）
        for pid in known:
            if pid not in enabled and pid not in configured:
                enabled.append(pid)
        return enabled

    def available(self) -> list[tuple[str, str, bool, str]]:
        """返回 (provider_id, 显示名, 是否可用, 不可用原因) 列表。"""
        result = []
        for provider_id in self.provider_ids():
            adapter = self.get(provider_id)
            if adapter is None:
                continue
            ok, reason = adapter.is_configured()
            result.append((provider_id, adapter.display_label, ok, reason))
        return result

    def get(self, provider_id: str, refresh: bool = False) -> BaseAIAdapter | None:
        """取得（并缓存）某个提供方的实例。"""
        if provider_id in self._adapters and not refresh:
            return self._adapters[provider_id]
        try:
            adapter = registry.create(provider_id, config=self.config)
        except AIError as exc:
            log.warning("创建 AI 提供方失败 %s: %s", provider_id, exc)
            return None
        self._adapters[provider_id] = adapter
        return adapter

    # ------------------------------------------------------------------
    # 当前提供方
    # ------------------------------------------------------------------

    @property
    def active_id(self) -> str:
        if not self._active_id:
            candidates = self.provider_ids()
            self._active_id = candidates[0] if candidates else ""
        return self._active_id

    def active(self) -> BaseAIAdapter | None:
        adapter = self.get(self.active_id)
        if adapter is None:
            # 当前配置的提供方不存在（例如配置被删）：退回第一个可用项
            for provider_id in self.provider_ids():
                candidate = self.get(provider_id)
                if candidate and candidate.is_configured()[0]:
                    self.set_active(provider_id, notify=False)
                    return candidate
        return adapter

    def set_active(self, provider_id: str, notify: bool = True) -> bool:
        adapter = registry.get_class(provider_id)
        if adapter is None:
            raise AIError(f"未知的 AI 提供方：{provider_id}")
        self._active_id = provider_id
        self.config.set("ai.active_provider", provider_id)
        self.config.save()
        if notify:
            bus.emit(AI_PROVIDER_CHANGED, provider_id=provider_id)
        log.info("当前 AI 切换为: %s", provider_id)
        return True

    def refresh(self, provider_id: str | None = None) -> tuple[bool, str]:
        """刷新 AI（重建适配器实例并做一次连通性自检）。"""
        target = provider_id or self.active_id
        adapter = self.get(target, refresh=True)
        if adapter is None:
            return False, f"无法加载 AI 提供方：{target}"
        ok, reason = adapter.is_configured()
        if not ok:
            return False, reason
        return adapter.test_connection()

    def invalidate(self) -> None:
        """配置变化后清空实例缓存。"""
        self._adapters.clear()

    # ------------------------------------------------------------------
    # 兜底链
    # ------------------------------------------------------------------

    def fallback_chain(self, exclude: str = "") -> list[str]:
        chain = list(self.config.get("ai.fallback_chain", []) or [])
        if not chain:
            chain = [pid for pid in self.provider_ids() if pid != exclude]
        result: list[str] = []
        for pid in chain:
            if pid and pid != exclude and pid not in result:
                result.append(pid)
        for pid in self.provider_ids():
            if pid != exclude and pid not in result:
                result.append(pid)
        return result

    def resolve_with_fallback(self, exclude: str = "") -> tuple[BaseAIAdapter | None, str]:
        """找一个当前可用的 AI。返回 (适配器, 提示信息)。"""
        for provider_id in self.fallback_chain(exclude=exclude):
            if provider_id == self.active_id and not exclude:
                continue
            adapter = self.get(provider_id)
            if adapter is None:
                continue
            ok, _reason = adapter.is_configured()
            if ok:
                return adapter, provider_id
        return None, ""

    def chat_with_fallback(
        self,
        messages: list[ChatMessage],
        options: ChatOptions | None = None,
        on_chunk: Any = None,
        question_handler: Any = None,
        should_cancel: Any = None,
    ) -> tuple[str, str]:
        """按"当前 AI → 兜底链"的顺序尝试对话。

        返回 ``(回答, 实际使用的 provider_id)``；主 AI 失败时会通过事件总线
        发出 :data:`AI_FALLBACK`，界面据此弹窗提示用户。
        """
        errors: list[str] = []
        primary = self.active()
        order: list[tuple[BaseAIAdapter, str]] = []
        if primary is not None:
            order.append((primary, self.active_id))
        fallback, fallback_id = self.resolve_with_fallback(exclude=self.active_id)
        if fallback is not None:
            order.append((fallback, fallback_id))

        if not order:
            raise AIUnavailableError(
                "没有任何可用的 AI。请在「AI → AI 设置」里配置 DeepSeek / GPT 的 API Key，"
                "或配置本地 AI 命令。"
            )

        for index, (adapter, provider_id) in enumerate(order):
            ok, reason = adapter.is_configured()
            if not ok:
                errors.append(f"{adapter.display_label}：{reason}")
                continue
            try:
                answer = adapter.chat(
                    messages,
                    options,
                    on_chunk=on_chunk,
                    question_handler=question_handler,
                    should_cancel=should_cancel,
                )
                if index > 0 and self.config.get("ai.notify_on_fallback", True):
                    bus.emit(
                        AI_FALLBACK,
                        from_provider=self.active_id,
                        to_provider=provider_id,
                        to_label=adapter.display_label,
                        reason="；".join(errors[-1:]),
                    )
                return answer, provider_id
            except AIUnavailableError as exc:
                errors.append(f"{adapter.display_label}：{exc}")
                continue
            except AIError as exc:
                errors.append(f"{adapter.display_label}：{exc}")
                log.warning("AI 调用失败(%s)：%s", provider_id, exc)
                continue

        raise AIUnavailableError("AI 调用失败：\n" + "\n".join(errors))

    # ------------------------------------------------------------------

    def describe_active(self) -> str:
        adapter = self.active()
        if adapter is None:
            return "未配置"
        ok, reason = adapter.is_configured()
        return adapter.display_label if ok else f"{adapter.display_label}（不可用：{reason}）"


__all__ = ["AIManager"]
