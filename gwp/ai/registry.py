"""提供方注册表：AI 适配器的自动发现机制。

新增一个 AI 只需要：

1. 在 ``gwp/ai/providers/`` 下新建一个 ``.py`` 文件；
2. 继承 :class:`BaseAIAdapter` 并加上 ``@register_provider``；
3. 在 ``config.json`` 的 ``ai.providers`` 里加一段同名配置（可选，缺省会用类里的默认值）。

不需要修改任何已有文件——这就是"可插拔"的含义。
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import pkgutil
import sys
from pathlib import Path
from typing import Any, Type, TypeVar

from gwp.ai.types import AIError
from gwp.core.config import Config

log = logging.getLogger(__name__)

_registry: dict[str, Type["BaseAIAdapter"]] = {}
_discovered = False

T = TypeVar("T", bound="BaseAIAdapter")


# --------------------------------------------------------------------------
# 元数据
# --------------------------------------------------------------------------

class ProviderMeta:
    """适配器的自我描述，UI 用它自动生成配置界面。"""

    def __init__(
        self,
        provider_id: str,
        label: str,
        kind: str = "api",                 # api | web | local
        description: str = "",
        needs_api_key: bool = False,
        needs_base_url: bool = False,
        needs_model: bool = False,
        needs_command: bool = False,
        needs_url: bool = False,
        supports_stream: bool = True,
        supports_images: bool = False,
        default_config: dict[str, Any] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.label = label
        self.kind = kind
        self.description = description
        self.needs_api_key = needs_api_key
        self.needs_base_url = needs_base_url
        self.needs_model = needs_model
        self.needs_command = needs_command
        self.needs_url = needs_url
        self.supports_stream = supports_stream
        self.supports_images = supports_images
        self.default_config = default_config or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.provider_id,
            "label": self.label,
            "kind": self.kind,
            "description": self.description,
            "needs_api_key": self.needs_api_key,
            "needs_base_url": self.needs_base_url,
            "needs_model": self.needs_model,
            "needs_command": self.needs_command,
            "needs_url": self.needs_url,
            "supports_stream": self.supports_stream,
            "supports_images": self.supports_images,
        }


# --------------------------------------------------------------------------
# 注册
# --------------------------------------------------------------------------

def register_provider(adapter_cls: Type[T]) -> Type[T]:
    """类装饰器：把适配器登记到注册表。"""
    provider_id = getattr(adapter_cls, "provider_id", "") or adapter_cls.__name__.lower()
    _registry[provider_id] = adapter_cls
    log.debug("注册 AI 提供方: %s -> %s", provider_id, adapter_cls.__name__)
    return adapter_cls


def discover(force: bool = False) -> dict[str, Type["BaseAIAdapter"]]:
    """导入 ``gwp/ai/providers`` 下所有模块，触发注册。"""
    global _discovered
    if _discovered and not force:
        return dict(_registry)
    import gwp.ai.providers as providers_pkg

    for module_info in pkgutil.iter_modules(providers_pkg.__path__):
        if module_info.name.startswith("_"):
            continue
        full_name = f"{providers_pkg.__name__}.{module_info.name}"
        try:
            importlib.import_module(full_name)
        except Exception:  # noqa: BLE001 - 单个提供方出错不应导致整个软件不可用
            log.exception("加载 AI 提供方失败: %s", full_name)
    _discovered = True
    return dict(_registry)


def load_external_plugin(path: Path) -> list[str]:
    """从任意目录加载第三方提供方插件（扩展点，供后续升级使用）。

    返回成功加载的模块名列表。
    """
    loaded: list[str] = []
    if not path.is_dir():
        return loaded
    for file in sorted(path.glob("*.py")):
        if file.name.startswith("_"):
            continue
        module_name = f"gwp_plugin_{file.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, file)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            loaded.append(file.stem)
        except Exception:  # noqa: BLE001
            log.exception("加载插件失败: %s", file)
    return loaded


def available_providers() -> dict[str, Type["BaseAIAdapter"]]:
    return discover()


def provider_ids() -> list[str]:
    return sorted(discover().keys())


def get_class(provider_id: str) -> Type["BaseAIAdapter"] | None:
    return discover().get(provider_id)


def provider_meta(provider_id: str) -> ProviderMeta | None:
    cls = get_class(provider_id)
    if cls is None:
        return None
    return cls.describe()


def create(provider_id: str, config: Config | None = None, **overrides: Any) -> "BaseAIAdapter":
    """按 provider_id 创建适配器实例。配置来自 config.json 与 secrets.json。"""
    cls = get_class(provider_id)
    if cls is None:
        raise AIError(
            f"未找到 AI 提供方“{provider_id}”。可用的有：{', '.join(provider_ids()) or '（空）'}"
        )
    return cls(config=config, **overrides)


def all_meta() -> list[ProviderMeta]:
    metas = []
    for provider_id in provider_ids():
        meta = provider_meta(provider_id)
        if meta is not None:
            metas.append(meta)
    return metas


# 让类型检查器认识 BaseAIAdapter，同时避免循环导入
from gwp.ai.base import BaseAIAdapter  # noqa: E402  (放在末尾：注册表需要它做类型标注)
