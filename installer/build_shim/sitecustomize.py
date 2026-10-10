"""打包期间使用的补丁（仅通过 PYTHONPATH 生效，不进入发布产物）。

问题：本机 Python 3.10.0 的 ``dis._get_const_info`` 在常量索引越界时会抛
``IndexError``，PyInstaller 扫描字节码时必然踩到（PyInstaller 6.22 的
``modulegraph.util.iterate_instructions`` 直接调用 ``dis.get_instructions``）。

修法：把 ``_get_const_info`` 换成"越界就退回索引本身"的安全版本。
这是 CPython 后续版本修掉的同类问题，语义与新版一致。
"""

from __future__ import annotations

import dis

_original = dis._get_const_info  # type: ignore[attr-defined]


def _safe_get_const_info(const_index, const_list):
    try:
        return _original(const_index, const_list)
    except (IndexError, TypeError):
        argval = const_index
        return argval, repr(argval)


dis._get_const_info = _safe_get_const_info  # type: ignore[attr-defined]
