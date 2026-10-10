"""AI 提供方集合。

新增一个提供方文件时，**不需要**在这里登记——``gwp.ai.registry.discover()`` 会用
``pkgutil`` 扫描本目录并自动导入，导入过程触发 ``@register_provider`` 注册。

下面这些导入是"为了副作用"（让默认提供方在包被导入时就完成注册），
同时也方便外部直接 ``from gwp.ai.providers import DeepSeekAPIAdapter``。
"""

from gwp.ai.providers import openai_compatible, web_bridge  # noqa: F401  触发子模块注册
from gwp.ai.providers.local_command import LocalCommandAdapter  # noqa: F401
from gwp.ai.providers.openai_compatible import (  # noqa: F401
    CustomAPIAdapter,
    DeepSeekAPIAdapter,
    GPTAPIAdapter,
    OpenAICompatibleAdapter,
)
from gwp.ai.providers.web_bridge import DeepSeekWebAdapter, GPTWebAdapter, WebBridgeAdapter  # noqa: F401

__all__ = [
    "CustomAPIAdapter",
    "DeepSeekAPIAdapter",
    "DeepSeekWebAdapter",
    "GPTAPIAdapter",
    "GPTWebAdapter",
    "LocalCommandAdapter",
    "OpenAICompatibleAdapter",
    "WebBridgeAdapter",
]
