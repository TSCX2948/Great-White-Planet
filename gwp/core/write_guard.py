"""测试期间**禁止写真实数据**的硬保护。

为什么需要它（两次真实事故）
----------------------------
我在做端到端验证时，两次都改到了用户**真实的**书目数据：

1. 第一次：测试脚本把真实书目的目录复制进沙箱后，**误用了真实的 Book 对象**，
   于是「生成总结」就地重写了用户真实书目的 summary；
2. 第二次：脚本用 ``Config.load(..., force=True)`` 载入真实配置，
   配置里的 ``paths.data_root`` 指向真实数据目录 —— 我设的那一行被覆盖，
   整个脚本其实一直**在操作真实数据**。

两次都靠"生成前自动备份"救回来了，但两次都说明同一件事：

> **"每写一处都记得检查"是靠不住的。** 我检查过，还是漏了。

所以这里的保护不放在任何一条业务路径上，而是放在
**Python 解释器自己身上** —— :func:`sys.addaudithook`。

它为什么靠得住
--------------
审计钩子会在**每一次** ``open`` / ``os.replace`` / ``os.remove`` / ``os.rename``
发生时被调用，不管是哪个模块、哪条路径、谁写的代码。
于是"忘记检查"这件事在结构上不可能发生 ——
跟第 45 章"把记得清理换成结构必然"是同一个思路。

什么时候生效（对正常使用**零影响**）
------------------------------------
只在**看起来像测试**的时候启用：

* 设了环境变量 ``GWP_ROOT``（测试/迁移约定），或
* 存在环境变量 ``GWP_TEST_SENTINEL`` 指向的哨兵文件；

并且**允许**写在 ``GWP_ROOT`` 之下，或写在系统临时目录之下
（测试大量使用 ``tempfile``，而且 Windows 的 temp 可能不在 GWP_ROOT 里）。

需要故意写真实数据时（开发调试），设 ``GWP_ALLOW_REAL_WRITE=1``。
"""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

#: 审计钩子关心的写操作
_WRITE_EVENTS = frozenset({
    "open",             # mode 含 w/a/x/+ 时
    "os.replace",
    "os.rename",
    "os.remove",
    "os.unlink",
    "os.rmdir",
    "os.mkdir",
    "os.chmod",
    "os.truncate",
    "shutil.copyfile",
    "shutil.copymode",
    "shutil.copystat",
    "shutil.move",
    "shutil.rmtree",
})

#: 装过的钩子只装一次
_installed = False

#: 记录已经拦下来的次数（便于测试断言）
blocked_count = 0


def _allowed_roots() -> list[Path]:
    """允许写入的根目录。"""
    roots: list[Path] = []
    sandbox = os.environ.get("GWP_ROOT")
    if sandbox:
        roots.append(Path(sandbox))
    # 测试大量用 tempfile；Windows 上 temp 常常不在 GWP_ROOT 之下
    for value in (tempfile.gettempdir(), os.environ.get("TEMP"),
                  os.environ.get("TMP")):
        if value:
            roots.append(Path(value))
    resolved: list[Path] = []
    for root in roots:
        try:
            resolved.append(root.resolve())
        except OSError:
            continue
    return resolved


def _is_allowed(path_text: str, roots: list[Path]) -> bool:
    try:
        target = Path(path_text).resolve()
    except (OSError, ValueError):
        return True          # 判断不了的放过（宁可漏也不要误伤）
    for root in roots:
        if target == root or root in target.parents:
            return True
    return False


def _should_guard() -> bool:
    if os.environ.get("GWP_ALLOW_REAL_WRITE"):
        return False
    if os.environ.get("GWP_ROOT"):
        return True
    sentinel = os.environ.get("GWP_TEST_SENTINEL")
    if sentinel:
        try:
            return Path(sentinel).is_file()
        except OSError:
            return False
    return False


def install_test_write_guard() -> bool:
    """装上硬保护；返回是否真的装上了。

    这个函数**只做一件事**，不依赖任何业务模块，所以可以被任何入口调用。
    """
    global _installed
    if _installed:
        return True
    if not _should_guard():
        return False

    roots = _allowed_roots()

    def _hook(event: str, args: tuple) -> None:
        global blocked_count
        if event not in _WRITE_EVENTS:
            return
        # ---- 只关心"写" ----
        if event == "open":
            if len(args) < 2:
                return
            path_text, mode = args[0], args[1]
            if not isinstance(mode, str):
                return
            if not any(ch in mode for ch in "wax+"):
                return          # 只读不算
        else:
            if not args:
                return
            path_text = args[0]
        if not isinstance(path_text, (str, bytes, os.PathLike)):
            return
        try:
            text = os.fsdecode(path_text)
        except (TypeError, ValueError):
            return
        if _is_allowed(text, roots):
            return
        blocked_count += 1
        message = (
            f"[GWP 测试写保护] 已拦截对沙箱外的写入：{event} {text}\n"
            f"  允许写入的位置：{[str(r) for r in roots]}\n"
            f"  这通常是测试脚本误用了真实数据目录。\n"
            f"  确实需要写真实数据时，请设环境变量 GWP_ALLOW_REAL_WRITE=1。"
        )
        log.error(message)
        raise PermissionError(message)

    sys.addaudithook(_hook)
    _installed = True
    log.info("已启用测试写保护：沙箱 %s 之外一律拒绝写入",
             os.environ.get("GWP_ROOT"))
    return True


__all__ = ["blocked_count", "install_test_write_guard"]
