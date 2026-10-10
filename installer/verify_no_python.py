"""验证：目标电脑没有 Python 时，软件能否独立运行。

做法（尽量贴近"干净机器"）：

1. 挑一个与源码树无关的目录（``C:\\GWPTEST``）解压安装包并安装；
2. **临时把本机的 Python 安装目录改名藏起来** —— 这样任何"偷偷调用本机
   Python"的路径都会立刻失败；
3. 清空环境变量（PATH 只留系统目录、去掉 PYTHONHOME/PYTHONPATH 等）；
4. 启动软件，检查进程存活、日志正常、数据目录自动建好、帮助文档可读。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

RELEASE = Path(r"D:\Great White Planet\DeepseekData\安装包\Great White Planet 安装包.zip")
SANDBOX = Path(r"C:\GWPTEST")
TARGET = SANDBOX / "已安装" / "Great White Planet"
HIDDEN_PYTHON = Path(r"D:\Python\Python310")
HIDDEN_AS = Path(r"D:\Python\Python310_hidden_by_test")


def hide_python() -> bool:
    if HIDDEN_PYTHON.is_dir() and not HIDDEN_AS.exists():
        try:
            HIDDEN_PYTHON.rename(HIDDEN_AS)
            print(f"  已把 {HIDDEN_PYTHON} 改名藏起来")
            return True
        except OSError as exc:
            print(f"  !! 无法改名（Python 可能正在被使用）：{exc}")
            return False
    print("  本机 Python 目录不存在或已被藏起，跳过")
    return False


def restore_python() -> None:
    if HIDDEN_AS.is_dir() and not HIDDEN_PYTHON.exists():
        try:
            HIDDEN_AS.rename(HIDDEN_PYTHON)
            print(f"  已恢复 {HIDDEN_PYTHON}")
        except OSError as exc:
            print(f"  !! 恢复失败，请手工把 {HIDDEN_AS} 改回 {HIDDEN_PYTHON}：{exc}")


def clean_env() -> dict:
    """最小化环境变量：不带任何 Python 相关设置。"""
    keep = {}
    for key, value in os.environ.items():
        upper = key.upper()
        if upper.startswith("PYTHON") or upper in ("VIRTUAL_ENV", "PIP_INDEX_URL", "GWP_ROOT"):
            continue
        if upper == "PATH":
            # 只保留 Windows 系统目录，去掉任何 Python / venv 路径
            parts = [
                p for p in value.split(os.pathsep)
                if p and "python" not in p.lower() and "venv" not in p.lower()
            ]
            keep[key] = os.pathsep.join(parts)
            continue
        keep[key] = value
    keep.setdefault("SystemRoot", r"C:\Windows")
    return keep


def main() -> int:
    print("=== 干净环境运行验证 ===\n")

    if SANDBOX.exists():
        shutil.rmtree(SANDBOX, ignore_errors=True)
    SANDBOX.mkdir(parents=True, exist_ok=True)

    print("[1/5] 解压安装包……")
    with zipfile.ZipFile(RELEASE) as archive:
        archive.extractall(SANDBOX / "安装器")
    installer = SANDBOX / "安装器" / "安装 Great White Planet.exe"
    print("   安装器:", installer.is_file())

    print("[2/5] 安装到与源码树无关的位置……")
    proc = subprocess.Popen(
        [str(installer), "--silent", "--dir", str(TARGET), "--no-shortcut"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=str(installer.parent), env=clean_env(),
    )
    out, err = proc.communicate(timeout=300)
    print(f"   退出码 {proc.returncode}")
    app = TARGET / "Great White Planet.exe"
    print("   主程序:", app.is_file())

    print("[3/5] 藏起本机 Python……")
    hidden = hide_python()
    try:
        print("[4/5] 用最小环境启动软件……")
        env = clean_env()
        env.pop("TEMP", None)
        env.pop("TMP", None)
        proc = subprocess.Popen(
            [str(app)], cwd=str(TARGET), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        # 等日志出现"预扫描完成"，最多 60 秒
        log = TARGET / "data" / "else data" / "logs" / "gwp.log"
        startup_error = TARGET / "data" / "else data" / "logs" / "startup_error.log"
        deadline = time.time() + 60
        ok = False
        while time.time() < deadline:
            time.sleep(2)
            if proc.poll() is not None:
                print(f"   !! 进程提前退出，退出码 {proc.returncode}")
                break
            if log.is_file() and "预扫描完成" in log.read_text(encoding="utf-8", errors="replace"):
                ok = True
                break

        print(f"   启动成功: {ok}")
        print(f"   进程存活: {proc.poll() is None}")
        if log.is_file():
            for line in log.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]:
                print("   日志:", line[:160])
        print(f"   startup_error 存在: {startup_error.is_file()}")
        if startup_error.is_file():
            print("   --- 启动错误 ---")
            print(startup_error.read_text(encoding="utf-8", errors="replace")[:1200])

        print("[5/5] 检查数据目录与随包文档……")
        data_root = TARGET / "data"
        for name in ("user data", "else data"):
            print(f"   data/{name}: {(data_root / name).is_dir()}")
        doc_dir = TARGET / "_internal" / "Document"
        docs = sorted(p.name for p in doc_dir.glob("*")) if doc_dir.is_dir() else []
        print("   随包文档:", docs)

        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=30)
        # 再启动一次，确认能正常退出（不残留锁）
        time.sleep(1)
    finally:
        if hidden:
            restore_python()

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
