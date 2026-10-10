"""把安装器目录打成发布用的 zip，并做一次完整的安装/运行/卸载验收。"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

OUT = Path(r"D:\Great White Planet\DeepseekData\build\out")
STAGE = OUT / "installer_stage"
RELEASE = OUT / "Great White Planet 安装包.zip"
TEST = Path(r"D:\Great White Planet\DeepseekData\build\acceptance")

INSTALLER_EXE = "安装 Great White Planet.exe"
APP_EXE = "Great White Planet.exe"


def zip_stage() -> Path:
    if RELEASE.exists():
        RELEASE.unlink()
    count = 0
    with zipfile.ZipFile(RELEASE, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(STAGE.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(STAGE).as_posix())
                count += 1
    print(f"[打包] {count} 个文件 -> {RELEASE.name}  ({RELEASE.stat().st_size / 1024 / 1024:.1f} MB)")
    return RELEASE


def run_installer(exe: Path, target: Path, extra: list[str] | None = None) -> tuple[int, str]:
    args = [str(exe), "--silent", "--dir", str(target), "--no-shortcut"] + (extra or [])
    proc = subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=str(exe.parent)
    )
    out, err = proc.communicate(timeout=300)
    return proc.returncode, (out or b"").decode("utf-8", "replace") + (err or b"").decode("utf-8", "replace")


def main() -> int:
    archive = zip_stage()

    # ---------- 验收：解压 -> 安装 -> 运行 -> 卸载 ----------
    if TEST.exists():
        shutil.rmtree(TEST, ignore_errors=True)
    TEST.mkdir(parents=True, exist_ok=True)

    print("[验收 1/4] 解压发布包……")
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(TEST / "安装器")
    installer = TEST / "安装器" / INSTALLER_EXE
    print("   安装器:", installer.is_file())

    print("[验收 2/4] 静默安装……")
    target = TEST / "已安装" / "Great White Planet"
    start = time.time()
    code, output = run_installer(installer, target)
    print(f"   退出码 {code}，用时 {time.time() - start:.1f}s")
    if output.strip():
        print("   输出:", output.strip()[:300])

    files = list(target.rglob("*")) if target.exists() else []
    print("   文件数:", len([f for f in files if f.is_file()]))
    doc_dir = target / "_internal" / "Document"
    doc_names = sorted(p.name for p in doc_dir.glob("*")) if doc_dir.is_dir() else []
    checks = {
        "主程序": (target / APP_EXE).is_file(),
        "卸载器": (target / f"卸载 Great White Planet.exe").is_file(),
        "安装记录": (target / "uninstall.json").is_file(),
        "简要说明书PDF": (doc_dir / "Great White Planet 简要说明书.pdf").is_file(),
        "安装步骤说明PDF": (doc_dir / "Great White Planet 安装步骤说明.pdf").is_file(),
        "三份MD": len(list(doc_dir.glob("*.md"))) == 3,
        "无data目录": not (target / "data").exists(),
        # 需求：Document 里只带那几份说明文档，需求设计文档不随包分发
        "不含需求设计文档": not any("需求" in name for name in doc_names),
        "不含用户数据文件": not any(
            (target / name).exists()
            for name in ("data", "secrets.json", "boxes.json", "instance.lock")
        ),
    }
    for name, ok in checks.items():
        print(f"   {'OK ' if ok else 'FAIL'} {name}")
    print("   Document 内容:", doc_names)

    print("[验收 3/4] 启动安装好的程序……")
    # 刻意用**最小环境**启动：去掉所有 PYTHON* 变量、PATH 里剔除任何 python/venv 路径。
    # 目标电脑上可能根本没装 Python，所以软件必须自带运行时、不依赖外部环境。
    # （更严格的做法见 installer/verify_no_python.py：它会临时把本机 Python 目录改名。）
    env = {
        key: value for key, value in os.environ.items()
        if not key.upper().startswith("PYTHON")
        and key.upper() not in ("VIRTUAL_ENV", "GWP_ROOT")
    }
    env["PATH"] = os.pathsep.join(
        part for part in os.environ.get("PATH", "").split(os.pathsep)
        if part and "python" not in part.lower() and "venv" not in part.lower()
    )
    app = target / APP_EXE
    proc = subprocess.Popen(
        [str(app)], cwd=str(target), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(20)
    alive = proc.poll() is None
    log = target / "data" / "else data" / "logs" / "gwp.log"
    startup_error = target / "data" / "else data" / "logs" / "startup_error.log"
    print(f"   进程存活: {alive}")
    checks_env = {
        "自带运行时 python310.dll": (target / "_internal" / "python310.dll").is_file(),
        "无 PYTHONPATH 也能启动": alive,
        "无启动错误": not startup_error.is_file(),
        "自动创建 user data": (target / "data" / "user data").is_dir(),
        "自动创建 else data": (target / "data" / "else data").is_dir(),
    }
    for name, ok in checks_env.items():
        print(f"   {'OK ' if ok else 'FAIL'} {name}")
    if log.is_file():
        tail = log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-2:]
        for line in tail:
            print("   日志:", line[:150])
    if alive:
        proc.kill()

    print("[验收 4/4] 静默卸载……")
    uninstaller = target / f"卸载 Great White Planet.exe"
    if uninstaller.is_file():
        subprocess.Popen(
            [str(uninstaller), "--uninstall"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=str(target),
        )
        time.sleep(25)
        remaining_app = (target / APP_EXE).is_file()
        remaining_data = (target / "data").is_dir()
        print(f"   主程序已删除: {not remaining_app}")
        print(f"   用户数据保留: {remaining_data}（卸载不动 data 是刻意设计）")
    else:
        print("   没有卸载器，跳过")

    print("\n发布包:", archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
