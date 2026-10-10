"""本地 AI 提供方：调用本机已有的命令行 AI 程序。

用途（对应 need.md 第 6 条）：当 GPT / DeepSeek 不可用时，自动改用本地的
"天禧 AI" 之类程序，并弹窗提示用户。

配置示例（config.json）::

    "tianxi_local": {
      "type": "local_command",
      "enabled": true,
      "command": "tianxi --chat",
      "workdir": "D:/Tools/tianxi",
      "timeout": 180,
      "prompt_mode": "stdin",        // stdin | arg
      "output_mode": "stdout",       // stdout
      "system_prefix": "以下是系统要求："
    }

程序约定：从 stdin 读到全部提示词后，把回答写到 stdout。
如果本机程序接口不同，只需改这里的实现或再写一个新的适配器，其它模块无需改动。
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from gwp.ai.base import BaseAIAdapter
from gwp.ai.registry import ProviderMeta, register_provider
from gwp.ai.types import (
    AIConfigError,
    AIError,
    AINetworkError,
    ChatMessage,
    ChatOptions,
    ChunkHandler,
)

log = logging.getLogger(__name__)


@register_provider
class LocalCommandAdapter(BaseAIAdapter):
    """调用本地命令行程序作为 AI 后端（离线兜底）。"""

    provider_id = "tianxi_local"
    label = "本地天禧 AI"
    kind = "local"

    @classmethod
    def describe(cls) -> ProviderMeta:
        return ProviderMeta(
            provider_id=cls.provider_id,
            label=cls.label,
            kind="local",
            description="调用本机安装的命令行 AI 程序，作为断网/无 Key 时的兜底",
            needs_command=True,
            supports_stream=False,
        )

    def is_configured(self) -> tuple[bool, str]:
        command = str(self.setting("command", "") or "").strip()
        if not command:
            return False, "未配置本地命令（command）。请在 AI 设置里填写，例如 tianxi --chat"
        executable = self._executable()
        if executable is None:
            return False, f"找不到可执行文件：{command.split()[0]}（请确认已安装并加入 PATH）"
        return True, ""

    # ------------------------------------------------------------------

    def _executable(self) -> str | None:
        command = str(self.setting("command", "") or "").strip()
        if not command:
            return None
        head = command.split()[0].strip('"')
        if os.path.isabs(head) and os.path.exists(head):
            return head
        return shutil.which(head)

    def build_prompt(self, messages: list[ChatMessage]) -> str:
        system_parts = [m.content for m in messages if m.role == "system" and m.content]
        lines: list[str] = []
        prefix = str(self.setting("system_prefix", "") or "")
        if system_parts:
            lines.append((prefix + "\n" if prefix else "") + "\n\n".join(system_parts))
            lines.append("")
        for message in messages:
            if message.role == "system":
                continue
            speaker = {"user": "用户", "assistant": "助手"}.get(message.role, message.role)
            if message.content:
                lines.append(f"{speaker}：{message.content}")
        lines.append("助手：")
        return "\n".join(lines)

    # ------------------------------------------------------------------

    def complete(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> str:
        ok, reason = self.is_configured()
        if not ok:
            raise AIConfigError(reason)

        prepared, opts = self._prepare(messages, options)
        prompt = self.build_prompt(prepared)
        command = str(self.setting("command", "")).strip()
        workdir = str(self.setting("workdir", "") or "") or None
        timeout = int(self.setting("timeout", self._timeout(opts)) or self._timeout(opts))
        mode = str(self.setting("prompt_mode", "stdin") or "stdin")

        args = command if mode == "arg" else None
        if args:
            args = f'{command} "{prompt}"'

        try:
            process = subprocess.run(  # noqa: S603 - 命令由用户显式配置
                args if args else command,
                shell=True,
                input=None if args else prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                cwd=workdir or None,
            )
        except subprocess.TimeoutExpired as exc:
            raise AINetworkError(f"本地 AI 超时（>{timeout}s），可在 AI 设置里调大超时。") from exc
        except OSError as exc:
            raise AIConfigError(f"无法启动本地 AI：{exc}") from exc

        if process.returncode != 0:
            detail = (process.stderr or "").strip()[:300]
            raise AIError(f"本地 AI 退出码 {process.returncode}：{detail or '（无错误输出）'}")

        answer = (process.stdout or "").strip()
        if not answer:
            raise AIError("本地 AI 没有输出任何内容，请检查命令行参数。")
        return answer

    def stream(
        self,
        messages: list[ChatMessage],
        options: ChatOptions | None = None,
        on_chunk: ChunkHandler | None = None,
    ) -> str:
        text = self.complete(messages, options)
        if on_chunk and text:
            step = 200
            for index in range(0, len(text), step):
                on_chunk(text[index:index + step])
        return text


__all__ = ["LocalCommandAdapter"]
