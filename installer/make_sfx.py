"""用 IExpress 把安装器目录打成单文件自解压包（最小化 SED 试错）。"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

OUT = Path(r"D:\Great White Planet\DeepseekData\build\out")
STAGE = OUT / "installer_stage"
TARGET = OUT / "安装 Great White Planet.exe"
WORK = OUT / "sfx_work"


def try_sed(name: str, files: list[Path], extra_options: dict[str, str]) -> Path | None:
    """按给定 SED 配置试做一次，返回产物路径（失败返回 None）。"""
    work = WORK / name
    if work.exists():
        import shutil

        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    # 把所有文件复制到工作目录（IExpress 不支持子目录，全部平铺）
    flat: list[str] = []
    for index, source in enumerate(files):
        flat_name = f"f{index:04d}_{source.name}"
        (work / flat_name).write_bytes(source.read_bytes())
        flat.append(flat_name)

    product = work / "sfx.exe"
    options = {
        "PackagePurpose": "InstallApp",
        "ShowInstallProgramWindow": "1",
        "HideExtractAnimation": "0",
        "UseLongFileName": "1",
        "InsideCompressed": "0",
        "CAB_FixedSize": "0",
        "CAB_ResvCodeSigning": "0",
        "RebootMode": "N",
        "TargetName": str(product),
        "FriendlyName": "Great White Planet",
        "AppLaunched": "安装 Great White Planet.exe",
        "PostInstallCmd": "<None>",
        "AdminQuietInstCmd": "",
        "UserQuietInstCmd": "",
    }
    options.update(extra_options)

    lines = ["[Version]", "Class=IEXPRESS", "SEDVersion=3", "[Options]"]
    lines += [f"{key}={value}" for key, value in options.items()]
    lines += [
        "SourceFiles=SourceFiles",
        "[SourceFiles]",
        f"SourceFiles0={work}",
        "[SourceFiles0]",
    ]
    for index in range(len(flat)):
        lines.append(f"%FILE{index:02d}%={flat[index]}")
    lines.append("[Strings]")
    lines.append("")
    sed = work / "installer.sed"
    # IExpress 需要 ANSI/本地编码，用 mbcs 写
    sed.write_text("\r\n".join(lines), encoding="mbcs", errors="replace")

    iexpress = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "iexpress.exe"
    proc = subprocess.run(
        [str(iexpress), "/N", "/Q", str(sed)],
        capture_output=True, timeout=900,
    )
    print(f"  [{name}] 退出码={proc.returncode} stderr={proc.stderr.decode('mbcs', 'replace')[:200]}")
    if product.is_file() and product.stat().st_size > 0:
        return product
    # IExpress 有时把产物放到当前目录
    fallback = Path.cwd() / product.name
    if fallback.is_file():
        return fallback
    return None


def main() -> int:
    stage = STAGE
    files = [p for p in sorted(stage.rglob("*")) if p.is_file()]
    print(f"安装器目录 {len(files)} 个文件，"
          f"{sum(f.stat().st_size for f in files) / 1024 / 1024:.1f} MB")

    # 先只拿两个小文件试试 IExpress 本身是否可用，避免每次都在 80MB 上试错
    small = sorted(files, key=lambda p: p.stat().st_size)[:3]
    print("先用最小样例验证 IExpress 可用性：")
    probe = try_sed("probe", small, {})
    print("  小样例产物:", probe)
    if probe is None:
        print("IExpress 在本机不可用，放弃单文件方案。")
        return 1

    print("用完整目录制作：")
    result = try_sed("full", files, {})
    if result is not None:
        print(f"  单文件自解压包: {result} ({result.stat().st_size / 1024 / 1024:.1f} MB)")
        return 0
    print("完整目录制作失败（可能是 CAB 体积上限）。")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
