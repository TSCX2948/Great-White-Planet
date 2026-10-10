"""一键构建安装包。

流程：

1. 用 PyInstaller 构建软件本体（``gwp.spec``，onedir）；
2. 校验产物**不含任何用户数据**（data / secrets.json / config.json 等）；
3. 把软件本体压成 zip，**追加到安装器 exe 尾部**；
4. 用 PyInstaller 构建安装器（onefile，windowed）。

用法::

    python installer/build_installer.py

产物::

    DeepseekData/build/out/安装 Great White Planet.exe
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent        # code
PROJECT = CODE.parent                                # <软件根>
BUILD = PROJECT / "DeepseekData" / "build"
DIST = BUILD / "dist"
WORK = BUILD / "work"
OUT = BUILD / "out"
INSTALLER_SRC = CODE / "installer"
SHIM = INSTALLER_SRC / "build_shim"
MANUAL = PROJECT / "Document" / "Great White Planet 简要说明书.pdf"

PACKAGE_NAME = "Great White Planet"
INSTALLER_EXE = "安装 Great White Planet.exe"

#: 产物里绝不允许出现的东西（用户数据 / 密钥 / 运行时痕迹）
FORBIDDEN = (
    "user data",
    "else data",
    "secrets.json",
    "config.json",
    "boxes.json",
    "instance.lock",
    "chats",
    "summary_backup",
)


def run(cmd: list[str], env: dict | None = None) -> int:
    print("  $", " ".join(cmd))
    return subprocess.call(cmd, env=env)


def build_package() -> Path:
    print("[1/4] 构建软件本体……")
    env = dict(os.environ)
    # Python 3.10.0 的 dis 有越界 bug，PyInstaller 扫描字节码会崩；
    # 通过 PYTHONPATH 注入只在构建期生效的补丁（不进产物）
    env["PYTHONPATH"] = str(SHIM)
    env["PYTHONIOENCODING"] = "utf-8"
    code = run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", str(DIST), "--workpath", str(WORK),
        str(CODE / "gwp.spec"),
    ], env=env)
    bundle = DIST / PACKAGE_NAME
    if code != 0 or not bundle.is_dir():
        raise SystemExit(f"构建失败（退出码 {code}）")
    return bundle


def verify_package(bundle: Path) -> None:
    """确认产物干净：不含任何用户数据。"""
    print("[2/4] 校验产物不含用户数据……")
    problems: list[str] = []
    for path in bundle.rglob("*"):
        if path.name in FORBIDDEN:
            problems.append(str(path.relative_to(bundle)))
    if problems:
        for item in problems:
            print("   !! 不该出现的文件:", item)
        raise SystemExit("产物包含用户数据，已中止打包。")

    size = sum(p.stat().st_size for p in bundle.rglob("*") if p.is_file())
    print(f"   OK：{size / 1024 / 1024:.1f} MB，未发现用户数据")

    for name in (
        "Great_White_Planet_功能说明.md",
        "Great_White_Planet_设计思想.md",
        "Great_White_Planet_使用说明.md",
        "Great White Planet 简要说明书.pdf",
        "Great White Planet 安装步骤说明.pdf",
        # 书稿 PDF 是**可选**的：用户明确要求"不要 PDF，留 md 就行"，
        # 而 md 走的是另一份清单。所以这里只报告、不算失败。
        "开发实践——Great White Planet.pdf",
    ):
        found = list(bundle.rglob(name))
        optional = name.startswith("开发实践")
        mark = "OK " if found else ("跳过" if optional else "缺少")
        print(f"   {mark} 随包文档：{name}")


def make_zip(bundle: Path) -> Path:
    print("[3/4] 压缩软件本体……")
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / "payload.zip"
    if target.exists():
        target.unlink()
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(bundle).as_posix())
                count += 1
    print(f"   {count} 个文件 -> {target.stat().st_size / 1024 / 1024:.1f} MB")
    return target


def build_installer(payload: Path) -> Path:
    print("[4/4] 构建安装器……")
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SHIM)
    env["PYTHONIOENCODING"] = "utf-8"

    # 为什么不用 --onefile：本机（以及不少装了安全软件的机器）会直接拦掉
    # onefile 自解压引导，进程根本不启动，且不给任何提示。
    # 改为 --onedir：安装器 exe + 同目录的 payload.zip，
    # 再由 Windows 自带的 IExpress 打成单文件自解压包（见 make_sfx）。
    inner_dist = OUT / "installer_dist"
    inner_work = OUT / "installer_work"
    code = run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onedir", "--windowed",
        "--name", "_installer_base",
        "--distpath", str(inner_dist), "--workpath", str(inner_work),
        "--specpath", str(inner_work),
        "--hidden-import", "tkinter",
        "--hidden-import", "tkinter.ttk",
        "--hidden-import", "tkinter.filedialog",
        "--hidden-import", "tkinter.messagebox",
        "--exclude-module", "PyQt6",
        "--exclude-module", "numpy",
        "--exclude-module", "pandas",
        "--exclude-module", "matplotlib",
        "--exclude-module", "pymupdf",
        str(INSTALLER_SRC / "installer.py"),
    ], env=env)

    base_dir = inner_dist / "_installer_base"
    base = base_dir / "_installer_base.exe"
    if code != 0 or not base.is_file():
        raise SystemExit(f"安装器构建失败（退出码 {code}）")

    # 组装发布用的安装器目录：exe（改名）+ payload.zip + 说明文件
    stage = OUT / "installer_stage"
    if stage.exists():
        shutil.rmtree(stage, ignore_errors=True)
    shutil.copytree(base_dir, stage)
    (stage / "_installer_base.exe").rename(stage / INSTALLER_EXE)
    shutil.copy2(payload, stage / "payload.zip")
    readme = INSTALLER_SRC / "release_readme.txt"
    if readme.is_file():
        shutil.copy2(readme, stage / "使用说明（先读我）.txt")

    size = sum(p.stat().st_size for p in stage.rglob("*") if p.is_file())
    print(f"   安装器目录：{stage}  ({size / 1024 / 1024:.1f} MB)")
    return stage


def make_sfx(stage: Path) -> Path:
    """用 Windows 自带的 IExpress 把安装器目录打成**单文件自解压包**。

    IExpress 的 SED 里只能逐个列出文件（不支持目录），所以把安装器目录里的
    文件全部平铺列出；自解压后会执行 ``安装 Great White Planet.exe``，
    而安装器会在**同目录**找到 payload.zip（见 ``installer.payload_path``）。
    """
    print("[5/5] 用 IExpress 打成单文件自解压包……")
    iexpress = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "iexpress.exe"
    target = OUT / INSTALLER_EXE
    if not iexpress.is_file():
        print("   本机没有 IExpress，改为直接发布安装器目录")
        return stage

    files = sorted(p for p in stage.rglob("*") if p.is_file())
    body = [
        "[Version]",
        "Class=IEXPRESS",
        "SEDVersion=3",
        "[Options]",
        "PackagePurpose=InstallApp",
        "ShowInstallProgramWindow=1",
        "HideExtractAnimation=0",
        "UseLongFileName=1",
        "InsideCompressed=0",
        "CAB_FixedSize=0",
        "CAB_ResvCodeSigning=0",
        "RebootMode=N",
        f"TargetName={target}",
        f"FriendlyName={PACKAGE_NAME} 安装程序",
        f"AppLaunched={INSTALLER_EXE}",
        "PostInstallCmd=<None>",
        "AdminQuietInstCmd=",
        "UserQuietInstCmd=",
        "SourceFiles=SourceFiles",
        "[SourceFiles]",
        f"SourceFiles0={stage}",
        "[SourceFiles0]",
    ]
    for index, item in enumerate(files):
        body.append(f"%FILE{index:02d}%={item.relative_to(stage).as_posix()}")
    body.append("[Strings]")
    body.append("")
    sed = OUT / "installer.sed"
    sed.write_text("\r\n".join(body), encoding="utf-8", errors="replace")

    target.unlink(missing_ok=True)
    code = subprocess.call([str(iexpress), "/N", "/Q", str(sed)])
    if code == 0 and target.is_file():
        print(f"   -> {target}  ({target.stat().st_size / 1024 / 1024:.1f} MB)")
        return target
    print(f"   IExpress 退出码 {code}，改为发布安装器目录")
    return stage


def main() -> int:
    print("Great White Planet 安装包构建\n")
    if not MANUAL.is_file():
        print(f"[提示] 未找到说明书 PDF：{MANUAL}")
        print("       请先运行：python installer/make_manual_pdf.py")

    bundle = build_package()
    verify_package(bundle)
    payload = make_zip(bundle)
    stage = build_installer(payload)
    result = make_sfx(stage)

    print("\n完成：", result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
