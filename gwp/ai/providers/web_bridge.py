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
    allow_paste: bool = True,
) -> str:
    """把一段提示词（可选带一张图片）送进 AI，返回回答。

    **这是界面层统一应该调用的入口**，别直接碰 provider：

    * 若配置的提供方支持**直接看图片**（`supports_vision` 且 `ai.send_images`
      打开），就直接调用它，**完全不需要用户粘贴**；
    * 否则走**网页版桥接**：图片与提示词进剪贴板 → 打开网页 →
      弹窗让用户粘贴回答。

    这样"以后填了视觉模型密钥"时，同一段界面代码自动变成全自动，
    不用改任何界面 —— 这是把"能力判断"收在一个函数里的好处。

    ``allow_paste=False`` 时**绝不走网页版桥接**（不复制剪贴板、不开浏览器、
    不弹粘贴框），直连拿不到就返回空串。

    为什么需要这个开关：这个函数现在会被**后台线程**调用（见
    ``ui/views/wordbook_view.py`` 的补齐任务）。而"让用户粘贴"要建
    QMessageBox —— **在非 GUI 线程里建控件是不允许的**，Qt 会直接中止进程。
    批量补齐时更糟：N 张卡会开 N 个浏览器窗口、弹 N 个框。
    所以后台任务一律传 ``allow_paste=False``；需要手工粘贴的场景
    （单张、用户主动触发）仍留在 GUI 线程里跑。
    """
    text = (prompt or "").strip()
    if not text and image_path is None:
        return ""
    # ---- ① 优先：**直接调用 API**（全自动，零粘贴）----
    #
    # 需求（用户原话）："单词卡那里，你用API问AI，不要让用户自己问"
    #
    # 这里原来**只给带图片的请求**开了直连通道，纯文本一律掉进下面的
    # "网页版桥接" ② —— 于是单词卡补齐、日记合并这类**纯文字**任务，
    # 即使用户已经配好了 API Key，也还是被要求自己去网页问一遍再粘回来。
    # 那显然不对：能直连就直连。
    #
    # 现在的判据：
    #
    # * **带图片** -> 只有"声明支持视觉 + 用户允许发图"的提供方才直连
    #   （发图有隐私含义，必须显式开启，见 _provider_sees_images）；
    # * **纯文本** -> 任何**已配置好**的提供方都可以直连 ——
    #   文本没有额外隐私含义，而且用户既然填了 Key 就是想让软件去问。
    #
    # 直连失败（没有可用提供方、网络出错等）才退回 ②，
    # 这样"没配 AI"的用户仍然有手工这条路可走。
    if context is not None:
        try:
            reply = _call_direct(
                context, text,
                provider_id=provider_id,
                image_path=image_path,
            )
        except Exception:  # noqa: BLE001 - 直连失败就退回桥接
            log.warning("直连 AI 失败，退回网页版桥接", exc_info=True)
            reply = ""
        if reply:
            return reply

    # ---- ② 兜底：网页版桥接（剪贴板 + 用户粘贴）----
    from gwp.ui import common

    log.debug("走网页版桥接：text=%r has_image=%s", text[:40], image_path is not None)
    if not allow_paste:
        # 调用方明确要求"不许手工粘贴"（后台线程、批量任务）。
        # 直连都没拿到回答，这里只能返回空串，由调用方按失败处理。
        log.warning("直连失败且调用方禁止手工粘贴，本次跳过：%r", text[:40])
        return ""
    if not common.has_gui():
        # 没有真正的 QApplication：**绝不能建任何控件**（Qt 会直接中止进程）。
        # 这种情况只会出现在无界面的调用里（脚本、自检），
        # 那时"让用户粘贴"本来也无从谈起，返回空串让调用方按失败处理。
        log.warning("没有界面可用，无法让用户粘贴 AI 回答（已跳过）")
        return ""

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


def _call_direct(
    context,
    text: str,
    *,
    provider_id: str = "",
    image_path=None,
) -> str:
    """直接调用 API 拿回答；拿不到就返回空串（由调用方决定要不要兜底）。

    **不抛异常之外的判断**：没有可用提供方、或提供方没配好，都返回空串。
    这样调用方的逻辑很简单："有回答就用，没有就走桥接"。
    """
    from gwp.ai.types import ChatMessage

    manager = getattr(context, "ai", None)
    if manager is None:
        return ""

    # 带图片时先确认"这个提供方真的能看图 + 用户允许发图"；
    # 纯文本则只需要"提供方已配置好"。
    for candidate_id in _direct_candidates(context, provider_id):
        if image_path is not None:
            provider = manager.get(candidate_id)
            if provider is None:
                continue
            if not _provider_sees_images(context, candidate_id, provider):
                continue
        elif not _provider_ready(context, candidate_id):
            continue

        message = ChatMessage(role="user", content=text)
        if image_path is not None:
            message = ChatMessage(role="user", content=text,
                                  images=[str(image_path)])
        try:
            reply, used = manager.chat_with_fallback([message])
        except Exception:  # noqa: BLE001 - 换下一个候选
            log.debug("直连 %s 失败，尝试下一个", candidate_id, exc_info=True)
            continue
        reply = str(reply or "").strip()
        if reply:
            log.info("已直接调用 API（%s）拿到回答，无需用户手工粘贴", used)
            return reply
    return ""


def _direct_candidates(context, provider_id: str) -> list[str]:
    """按优先级列出"可以直接调用"的提供方 id。

    顺序：调用方指定的 -> 当前启用的 -> 兜底链。
    与 :func:`_vision_candidates` 同一套顺序，只是这里**纯文本也能用**。
    """
    return _vision_candidates(context, provider_id)


def _provider_ready(context, provider_id: str) -> bool:
    """这个提供方现在能不能直接调用（纯文本）。

    判据只有一条：**它能自己说自己配好了**（``is_configured()`` 返回 True）。
    不额外要求"用户显式允许" —— 文本请求没有发图那种隐私含义，
    而且用户既然在设置里填了 API Key，本来就期望软件自己去问。
    """
    try:
        manager = getattr(context, "ai", None)
        provider = manager.get(provider_id) if manager is not None else None
        if provider is None:
            return False
        ok, _reason = provider.is_configured()
        return bool(ok)
    except Exception:  # noqa: BLE001
        return False


def has_direct_provider(context, provider_id: str = "") -> bool:
    """现在有没有能**直接调用**的 AI（不用手工粘贴）。

    界面层用它来分工：

    * 有 -> 可以让**后台线程**去补齐（``allow_paste=False``）；
    * 没有 -> 只能留在 GUI 线程走"复制提示词 + 粘贴回答"。

    这个判断**不发起任何网络请求**，只问各提供方 ``is_configured()``，
    所以可以随手调用。
    """
    if context is None:
        return False
    try:
        for candidate_id in _direct_candidates(context, provider_id):
            if _provider_ready(context, candidate_id):
                return True
    except Exception:  # noqa: BLE001
        return False
    return False


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
