"""网页版 AI 桥接提供方（DeepSeek 网页版 / GPT 网页版）。

为什么这样做
------------
需求文档要求支持"DeepSeek 网页版"和"GPT 网页版"。在不引入浏览器自动化
（Playwright/Selenium 之类，易被网站改版破坏、体积大）的前提下，本适配器采用
**剪贴板 + 浏览器桥接**：

1. 把整理好的提示词写入系统剪贴板；
2. 打开对应的官网；
3. 用户在网页里粘贴提问，得到回答后回到软件的弹窗里粘贴回答（或直接把回答
   粘回聊天输入框）。

这样既满足"用网页版干活"的需求，又不会因为网站改版而失效。
如果后续希望全自动，只需要新增一个 ``type: web_automation`` 的适配器，
本文件无需改动——这正是可插拔结构的用处。
"""

from __future__ import annotations

import logging
import webbrowser
from gwp.ai.base import BaseAIAdapter
from gwp.ai.registry import ProviderMeta, register_provider
from gwp.ai.types import AIUnavailableError, ChatMessage, ChatOptions, ChunkHandler

log = logging.getLogger(__name__)


class WebBridgeAdapter(BaseAIAdapter):
    """把对话交给浏览器里的官方网页版，通过剪贴板往返。"""

    provider_id = "web_bridge"
    label = "网页版 AI"
    kind = "web"

    def is_configured(self) -> tuple[bool, str]:
        if not self.setting("url"):
            return False, "未配置网页地址（url）"
        return True, ""

    # -- 提示词整理 -----------------------------------------------------

    def build_prompt(self, messages: list[ChatMessage]) -> str:
        """把消息列表压成一段适合粘贴到聊天框的文本。"""
        system_parts = [m.content for m in messages if m.role == "system" and m.content]
        body_parts: list[str] = []
        for message in messages:
            if message.role == "system":
                continue
            speaker = {"user": "我", "assistant": "AI", "tool": "工具"}.get(message.role, message.role)
            if message.content:
                body_parts.append(f"【{speaker}】\n{message.content}")
            if message.images:
                body_parts.append("【附件图片】\n" + "\n".join(message.images))

        chunks: list[str] = []
        if system_parts:
            chunks.append("【系统要求】\n" + "\n\n".join(system_parts))
        chunks.extend(body_parts)
        return "\n\n".join(chunks).strip()

    # -- 调用 -----------------------------------------------------------

    def complete(self, messages: list[ChatMessage], options: ChatOptions | None = None) -> str:
        prepared, opts = self._prepare(messages, options)
        prompt = self.build_prompt(prepared)
        url = str(self.setting("url", ""))

        reply_callback = None
        if opts.extra:
            reply_callback = opts.extra.get("web_reply_callback")

        copied = False
        if self.setting("auto_paste", True):
            copied = copy_to_clipboard(prompt)
        try:
            webbrowser.open(url)
        except Exception as exc:  # noqa: BLE001 - 打不开浏览器不该让整个流程崩溃
            log.warning("打开浏览器失败: %s", exc)

        if reply_callback is None:
            raise AIUnavailableError(
                "已把提示词复制到剪贴板并打开{label}。\n"
                "请在网页中粘贴提问，然后把回答粘贴回聊天输入框。\n"
                "（若希望全自动，请在 AI 设置中改用 API 方式）".format(
                    label=self.setting("label", self.label)
                )
            )

        hint = "提示词已复制到剪贴板。" if copied else "请手动复制下面的提示词。"
        answer = reply_callback(prompt, f"{hint}\n已打开：{url}")
        if not answer:
            raise AIUnavailableError("未收到网页版的回答内容。")
        if self.settings.get("stream_simulate", True) and opts.stream:
            # 模拟流式输出，界面观感一致
            step = 80
            for index in range(0, len(answer), step):
                if opts.extra.get("on_chunk"):
                    opts.extra["on_chunk"](answer[index:index + step])
        return answer

    def stream(
        self,
        messages: list[ChatMessage],
        options: ChatOptions | None = None,
        on_chunk: ChunkHandler | None = None,
    ) -> str:
        opts = options or ChatOptions()
        opts.extra = dict(opts.extra or {})
        if on_chunk:
            opts.extra["on_chunk"] = on_chunk
        return self.complete(messages, opts)


def copy_to_clipboard(text: str) -> bool:
    """把文本放进系统剪贴板。优先用 Qt（界面进程内），否则退回 Windows clip 命令。"""
    if not text:
        return False
    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.clipboard().setText(text)
            return True
    except Exception:  # noqa: BLE001 - 非 GUI 环境（例如测试）时忽略
        pass
    try:
        import subprocess

        process = subprocess.run(
            ["clip"], input=text.encode("utf-16-le"), check=False, timeout=10, shell=False
        )
        return process.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


#: 图片进剪贴板前的最长边上限。
#: 手机拍的课件照片动辄 4000px/8MB，整张塞进剪贴板会让部分网页版
#: 拒收或上传极慢；缩到 2048 对"看清文字"完全够用。
CLIPBOARD_IMAGE_MAX_EDGE = 2048


def copy_image_to_clipboard(path) -> bool:
    """把一张图片放进系统剪贴板，供用户直接粘到网页版 AI 的输入框。

    网页版 AI 的输入框接受"粘贴图片"，所以这是"图片也能走网页版桥接"的关键。

    实现细节（都踩过）：

    * **同时提供 PNG 与原始格式两种剪贴板数据**：只放 DIB 时，大部分浏览器
      能收，但个别应用会失败；PNG 是最通用的中间格式。
    * **必须拿到剪贴板的"所有权"**：``setImage`` 默认可能会在某些平台上
      延迟取值，这里显式传 ``QClipboard.Mode.Clipboard`` 并确保返回前
      不释放 QImage（用局部变量持有到函数结束即可）。
    * **超大图先缩放**：见 :data:`CLIPBOARD_IMAGE_MAX_EDGE`。
    * 失败一律返回 ``False``，由调用方提示用户"手动拖图"，不要抛异常。

    返回是否成功放入剪贴板。
    """
    if not path:
        return False
    try:
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QGuiApplication, QImage

        app = QGuiApplication.instance()
        if app is None:
            return False
        image = QImage(str(path))
        if image.isNull():
            return False
        longest = max(image.width(), image.height())
        if longest > CLIPBOARD_IMAGE_MAX_EDGE:
            image = image.scaled(
                CLIPBOARD_IMAGE_MAX_EDGE,
                CLIPBOARD_IMAGE_MAX_EDGE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        clipboard = app.clipboard()
        if clipboard is None:
            return False
        clipboard.setImage(image)
        # 回读一次确认真的写进去了（某些平台 setImage 后立刻读会是空）
        return not clipboard.image().isNull()
    except Exception:  # noqa: BLE001 - 剪贴板失败不该让整个流程崩溃
        log.warning("把图片放入剪贴板失败：%s", path, exc_info=True)
        return False


def send_to_ai(
    prompt: str,
    *,
    provider_id: str = "",
    url: str = "",
    image_path=None,
    context=None,
    parent=None,
    title: str = "网页版 AI",
    open_browser: bool = True,
) -> str:
    """把一段提示词（可选带一张图片）送进 AI，返回回答。

    **这是界面层统一应该调用的入口**，别直接碰 provider：

    * 若配置的提供方支持**直接看图片**（`supports_vision` 且 `ai.send_images`
      打开），就直接调用它，**完全不需要用户粘贴**；
    * 否则走**网页版桥接**：图片与提示词进剪贴板 → 打开网页 →
      弹窗让用户粘贴回答。

    这样"以后填了视觉模型密钥"时，同一段界面代码自动变成全自动，
    不用改任何界面 —— 这是把"能力判断"收在一个函数里的好处。
    """
    text = (prompt or "").strip()
    if not text and image_path is None:
        return ""
    # ---- ① 优先：能直接看图的提供方（全自动，零粘贴）----
    if image_path is not None and context is not None:
        try:
            from gwp.ai.types import ChatMessage

            manager = getattr(context, "ai", None)
            if manager is not None:
                for candidate_id in _vision_candidates(context, provider_id):
                    provider = manager.get(candidate_id)      # AIManager 的取用接口
                    if provider is None:
                        continue
                    if not _provider_sees_images(context, candidate_id, provider):
                        continue
                    reply, _used = manager.chat_with_fallback(
                        [ChatMessage(role="user", content=text,
                                     images=[str(image_path)])],
                    )
                    if reply and str(reply).strip():
                        log.info("图片已由 %s 直接识别（无需手工粘贴）", candidate_id)
                        return str(reply).strip()
        except Exception:  # noqa: BLE001 - 直连失败就退回桥接
            log.warning("直连视觉模型失败，退回网页版桥接", exc_info=True)

    # ---- ② 兜底：网页版桥接（剪贴板 + 用户粘贴）----
    from gwp.ui import common

    image_copied = False
    if image_path is not None:
        image_copied = copy_image_to_clipboard(image_path)
    prompt_copied = copy_to_clipboard(text) if text else False

    target = url or _web_url(context, provider_id)
    if open_browser and target:
        try:
            import webbrowser

            webbrowser.open(target)
        except Exception:  # noqa: BLE001
            log.warning("打开浏览器失败：%s", target, exc_info=True)

    if image_path is not None:
        if image_copied:
            hint = ("图片**已复制到剪贴板**：在网页里点输入框按 Ctrl+V 粘贴图片，\n"
                    "然后粘贴下面的提示词（也已复制，可直接 Ctrl+V）。")
        else:
            hint = (f"**没能把图片放进剪贴板**。请手动把这张图拖进网页：\n"
                    f"{image_path}")
    else:
        hint = ("提示词已复制到剪贴板。" if prompt_copied
                else "请手动复制下面的提示词。")
    if target:
        hint += f"\n已打开：{target}"

    return common.ask_paste_reply(
        parent, title=title, prompt=text, hint=hint,
    )


def _vision_candidates(context, provider_id: str) -> list[str]:
    """按优先级列出"可能能看图"的提供方 id。"""
    order: list[str] = []
    if provider_id:
        order.append(provider_id)
    active = str(getattr(context, "config", None).get("ai.active_provider", "")
                 if getattr(context, "config", None) is not None else "")
    if active and active not in order:
        order.append(active)
    try:
        chain = context.config.get("ai.fallback_chain", []) or []
    except Exception:  # noqa: BLE001
        chain = []
    for name in chain:
        if name not in order:
            order.append(str(name))
    return order


def _provider_sees_images(context, provider_id: str, provider) -> bool:
    """这个提供方现在能不能直接收图片。

    两个条件都要满足：
    1. 它**声明**支持视觉（``supports_vision``）；
    2. 用户**允许发送图片**（``ai.send_images``）—— 发图有隐私含义，
       必须由用户显式开启，不能悄悄发。
    """
    try:
        config = context.config
        setting = config.get(f"ai.providers.{provider_id}", {}) or {}
        if not bool(setting.get("supports_vision")):
            return False
        return bool(config.get("ai.send_images", False))
    except Exception:  # noqa: BLE001
        return False


def _web_url(context, provider_id: str) -> str:
    """取网页版提供方的地址（用于打开浏览器）。"""
    try:
        if provider_id:
            setting = context.config.get(f"ai.providers.{provider_id}", {}) or {}
            if setting.get("url"):
                return str(setting["url"])
        for name in ("deepseek_web", "gpt_web"):
            setting = context.config.get(f"ai.providers.{name}", {}) or {}
            if setting.get("url"):
                return str(setting["url"])
    except Exception:  # noqa: BLE001
        pass
    return ""


@register_provider
class DeepSeekWebAdapter(WebBridgeAdapter):
    """DeepSeek 网页版（chat.deepseek.com）。"""

    provider_id = "deepseek_web"
    label = "DeepSeek 网页版"
    description = "打开 DeepSeek 官网，用剪贴板在网页与软件之间传递内容"

    @classmethod
    def describe(cls) -> ProviderMeta:
        return ProviderMeta(
            provider_id=cls.provider_id,
            label=cls.label,
            kind="web",
            description=cls.description,
            needs_url=True,
            supports_stream=False,
        )


@register_provider
class GPTWebAdapter(WebBridgeAdapter):
    """GPT 网页版（chatgpt.com）。"""

    provider_id = "gpt_web"
    label = "GPT 网页版"
    description = "打开 ChatGPT 官网，用剪贴板在网页与软件之间传递内容"

    @classmethod
    def describe(cls) -> ProviderMeta:
        return ProviderMeta(
            provider_id=cls.provider_id,
            label=cls.label,
            kind="web",
            description=cls.description,
            needs_url=True,
            supports_stream=False,
        )


__all__ = ["DeepSeekWebAdapter", "GPTWebAdapter", "WebBridgeAdapter", "copy_to_clipboard"]
