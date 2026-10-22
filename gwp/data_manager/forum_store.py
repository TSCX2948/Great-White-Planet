"""论坛列表：用户在「论坛」菜单里自己维护的网址。

需求
----
> 论坛添加新增/删除论坛功能，需要用户提供论坛名称 网址

原来这里只有**一条硬编码**的东西（菜单里写死「牢大CS」，
网址从 ``forum.laoda_cs_url`` 读）。现在改成**列表**：
用户自己加、自己删、自己改。

存在哪
------
写在 ``config.json`` 的 ``forum.list`` 里（一个数组）。为什么不单独开一个文件：

* 这是**设置**，不是用户资料 —— 跟着配置走、跟着配置备份，最省心；
* 论坛网址是"这台机器上我想用哪几个"，不是"我的学习数据"。

老配置怎么办
------------
老版本只有 ``forum.laoda_cs_url``（单条）。第一次读的时候把那条**搬进列表**，
作为第一条 —— 见 :func:`load`。这样升级后用户原来那个论坛不会凭空消失。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import urlparse

log = logging.getLogger(__name__)

#: 配置里的点号路径
CONFIG_KEY = "forum.list"

#: 老版本的单条配置键（升级时搬进列表）
LEGACY_URL_KEY = "forum.laoda_cs_url"
LEGACY_NAME = "牢大CS"
LEGACY_URL = "https://cs9.x-way.work/"

#: 名称最长多少字（菜单项太长会把菜单撑得很宽）
MAX_NAME_LEN = 24

#: 列表最多几条（菜单放得下、也免得用户误以为能当书签管理器）
MAX_FORUMS = 20


@dataclass(frozen=True)
class Forum:
    """一个论坛：名称 + 网址。"""

    name: str
    url: str

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "url": self.url}


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------

def normalize_url(raw: str) -> str:
    """把用户填的网址补全成可用的形式。

    用户经常只填 ``cs9.x-way.work`` 或 ``www.example.com/forum`` ——
    漏了协议。直接拿去 ``open_url`` 会失败，所以这里自动补 ``https://``。

    只允许 http / https：``mailto:`` 之类不是"论坛网址"，
    放行它们会让菜单变成一个奇怪的东西。
    """
    text = (raw or "").strip()
    if not text:
        return ""
    text = "".join(text.split())          # 去掉中间的空格/换行
    if "://" not in text:
        text = "https://" + text
    return text


def validate_name(raw: str, *, taken: list[str] | None = None) -> str:
    """检查名称。返回空串表示没问题，否则返回**给用户看的原因**。"""
    name = (raw or "").strip()
    if not name:
        return "名称不能为空"
    if len(name) > MAX_NAME_LEN:
        return f"名称太长了（最多 {MAX_NAME_LEN} 个字）"
    if any(ch in name for ch in "\t\n\r"):
        return "名称不能包含换行或制表符"
    if taken and name in taken:
        return f"已经有一个叫「{name}」的论坛了，换个名字"
    return ""


def validate_url(raw: str) -> str:
    """检查网址。返回空串表示没问题，否则返回给用户看的原因。"""
    url = normalize_url(raw)
    if not url:
        return "网址不能为空"
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return "只支持 http / https 网址"
    if not parsed.netloc:
        return "网址看起来不完整（缺少域名）"
    # 域名里至少得有一个点，或者是个 IP —— 挡掉 "https://abc" 这种手滑
    host = parsed.netloc.split(":")[0]
    if "." not in host and host.lower() != "localhost":
        return "网址看起来不完整（域名里缺少点）"
    return ""


# ---------------------------------------------------------------------------
# 读写
# ---------------------------------------------------------------------------

def _to_forum(raw) -> Forum | None:
    """把配置里的一项转成 :class:`Forum`；坏数据返回 ``None``。"""
    if isinstance(raw, dict):
        name = str(raw.get("name", "")).strip()
        url = normalize_url(str(raw.get("url", "")))
    elif isinstance(raw, str):
        # 容忍"只写了网址"的老写法：用域名当名称
        url = normalize_url(raw)
        name = urlparse(url).netloc or url
    else:
        return None
    if not name or not url:
        return None
    return Forum(name=name, url=url)


def load(config) -> list[Forum]:
    """读出论坛列表（顺带完成老配置的搬家）。

    **搬家只在 ``forum.list`` 这个键根本不存在时做。**

    这条判据很关键。我第一版写成"列表为空就搬家"，于是出了个很烦的 bug：
    用户把论坛**全删光**之后，下次打开菜单会看到「牢大CS」**自己回来了**
    —— 因为"空列表"被当成了"还没搬过家"。实测确认过这个复活现象。

    所以要把两件事分开：

    * 键不存在（``None``）-> 老配置搬家；
    * 键存在但是 ``[]`` -> 用户主动删光了 -> **就该是空的**，不许复活。
    """
    raw_items = config.get(CONFIG_KEY)
    if isinstance(raw_items, list):
        forums: list[Forum] = []
        for raw in raw_items:
            forum = _to_forum(raw)
            if forum is not None:
                forums.append(forum)
        # 键存在（哪怕解析后为空）就以此为准，**不再碰老配置**
        return forums
    if raw_items is not None:
        # 坏数据（不是列表）：同样不搬家，避免出现"删不掉的幽灵条目"
        log.warning("forum.list 不是列表（%s），已忽略", type(raw_items).__name__)
        return []

    # ---- 老配置搬家：只有 laoda_cs_url 的时代，把它当第一条 ----
    #
    # 为什么放在"读"里而不是写一个迁移脚本：迁移脚本要有人去调，
    # 而"读"是每次打开菜单都会走的路径 —— 放在这里**一定会被执行到**。
    legacy = config.get(LEGACY_URL_KEY, LEGACY_URL)
    legacy_forum = _to_forum({"name": LEGACY_NAME, "url": legacy or LEGACY_URL})
    if legacy_forum is not None:
        log.info("论坛列表尚不存在，已把老的 %s 搬进列表作为第一条", LEGACY_URL_KEY)
        return [legacy_forum]
    return []


def save(config, forums: list[Forum]) -> None:
    """写回配置（同时把老的单条键清掉，避免两处数据打架）。

    ``forum.list`` 一定会被写出来（哪怕是空数组）——
    这是 :func:`load` 判断"用户是不是主动删光了"的依据。
    """
    payload = [f.to_dict() for f in forums[:MAX_FORUMS]]
    config.set(CONFIG_KEY, payload)
    # 老键留着会让"我删了它怎么又回来了"发生
    config.set(LEGACY_URL_KEY, "")
    try:
        config.save()
    except Exception:  # noqa: BLE001 - 保存失败要让调用方知道，但别炸掉整个界面
        log.exception("保存论坛列表失败")
        raise


def add(config, name: str, url: str) -> list[Forum]:
    """加一个论坛。返回新的列表（**不做校验**，校验在界面层做，好给提示）。"""
    forums = load(config)
    forums.append(Forum(name=name.strip(), url=normalize_url(url)))
    save(config, forums)
    return forums


def remove(config, name: str) -> list[Forum]:
    """按名称删一个论坛。返回新的列表。"""
    forums = [f for f in load(config) if f.name != name]
    save(config, forums)
    return forums


def rename(config, old_name: str, new_name: str, url: str) -> list[Forum]:
    """改某个论坛的名称/网址（就地替换，保持顺序）。"""
    forums = load(config)
    updated = [
        Forum(name=new_name.strip(), url=normalize_url(url))
        if f.name == old_name else f
        for f in forums
    ]
    save(config, updated)
    return updated


def move(config, name: str, delta: int) -> list[Forum]:
    """把某个论坛在列表里上移/下移（菜单顺序 = 列表顺序）。"""
    forums = load(config)
    index = next((i for i, f in enumerate(forums) if f.name == name), None)
    if index is None:
        return forums
    target = max(0, min(len(forums) - 1, index + delta))
    if target == index:
        return forums
    forums.insert(target, forums.pop(index))
    save(config, forums)
    return forums


__all__ = [
    "CONFIG_KEY",
    "Forum",
    "LEGACY_NAME",
    "LEGACY_URL",
    "MAX_FORUMS",
    "MAX_NAME_LEN",
    "add",
    "load",
    "move",
    "normalize_url",
    "remove",
    "rename",
    "save",
    "validate_name",
    "validate_url",
]
