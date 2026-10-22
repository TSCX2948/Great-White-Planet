"""给打包出来的 exe 写入"属性 → 详细信息"里的版本信息。

为什么要单独生成
----------------
PyInstaller 在 spec 里用 ``version=`` 指定版本资源，但那需要一段
``VSVersionInfo(...)`` 表达式 —— **如果直接写在 spec 里，版本号就有了第二个来源**，
而"版本号只有一个来源"是这个项目一直在守的一条规则
（见 :mod:`gwp` 的 ``__version__``）。

所以这里**从 ``gwp/__init__.py`` 读出真实版本号**，再生成那一段文本。
改版本仍然只改一个地方，exe 属性会自动跟上。

怎么用（在 ``gwp.spec`` 里）::

    from build_version_info import write_version_file
    _ver = write_version_file(CODE, OUT)   # OUT 是临时目录
    exe = EXE(..., version=_ver, ...)
"""

from __future__ import annotations

import re
from pathlib import Path

#: 产品信息（这些不是"版本号"，写死没关系）
PRODUCT_NAME = "Great White Planet"
PRODUCT_NAME_CN = "大白星球"
COMPANY = "Great White Planet"
DESCRIPTION = "本地知识管理与 AI 辅助学习软件"
COPYRIGHT = "Great White Planet"

_TEMPLATE = """# 由 installer/build_version_info.py 自动生成 —— 不要手改
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={tuple4},
    prodvers={tuple4},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '080404B0',
        [StringStruct('CompanyName', {company!r}),
         StringStruct('FileDescription', {description!r}),
         StringStruct('FileVersion', {version!r}),
         StringStruct('InternalName', {internal!r}),
         StringStruct('LegalCopyright', {copyright!r}),
         StringStruct('OriginalFilename', {internal!r}),
         StringStruct('ProductName', {product!r}),
         StringStruct('ProductVersion', {version!r})])
    ]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
"""


def read_version(code_dir: Path) -> str:
    """从 ``gwp/__init__.py`` 读出 ``__version__``（**唯一来源**）。"""
    init = Path(code_dir) / "gwp" / "__init__.py"
    text = init.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.M)
    if match is None:
        raise RuntimeError(f"在 {init} 里找不到 __version__")
    return match.group(1)


def _tuple4(version: str) -> tuple[int, int, int, int]:
    """``"2.1.0"`` -> ``(2, 1, 0, 0)``；Windows 要四段数字。"""
    parts: list[int] = []
    for chunk in re.split(r"[.\-+]", version):
        try:
            parts.append(int(chunk))
        except ValueError:
            break
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])            # type: ignore[return-value]


def write_version_file(code_dir: Path, out_dir: Path) -> Path:
    """生成版本资源文件，返回它的路径（给 spec 的 ``version=`` 用）。"""
    version = read_version(code_dir)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / "version_info.txt"
    target.write_text(
        _TEMPLATE.format(
            tuple4=_tuple4(version),
            version=version,
            product=PRODUCT_NAME,
            internal="Great White Planet.exe",
            description=DESCRIPTION,
            company=COMPANY,
            copyright=COPYRIGHT,
        ),
        encoding="utf-8",
    )
    return target


if __name__ == "__main__":                 # 手动看一眼生成结果
    import sys

    here = Path(__file__).resolve()
    code = here.parent.parent
    print(write_version_file(code, code / "installer" / ".version_tmp"))
    print(read_version(code))
    sys.exit(0)
