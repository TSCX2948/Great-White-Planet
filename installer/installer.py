"""Great White Planet 安装程序（自带界面）。

软件本体（打包好的 `Great White Planet` 目录，压成一个 payload.zip）作为
**数据文件**被 PyInstaller 打进本程序，运行时从 ``sys._MEIPASS`` 取出来解压到
用户选择的目录。

为什么这么做：本机没有 Inno Setup / NSIS，而这个 Python 环境本身就能做出
带界面的安装程序，不需要任何第三方安装器制作工具。

行为：

* 双击 -> 图形界面安装（可选目录、可选桌面/开始菜单快捷方式）；
* ``--uninstall`` -> 按 uninstall.json 记录删除文件并清理快捷方式；
* ``--silent --dir <路径>`` -> 静默安装（供自动化测试使用）。
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import zipfile
from pathlib import Path

APP_NAME = "Great White Planet"
APP_EXE = "Great White Planet.exe"
PAYLOAD_NAME = "payload.zip"
UNINSTALL_FILE = "uninstall.json"
MANUAL_NAME = "Great White Planet 简要说明书.pdf"

#: 安装包默认目录：放在用户目录下，避免 Program Files 的写入限制
DEFAULT_DIR = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\Public")) / "Programs" / APP_NAME


# --------------------------------------------------------------------------
# 取出内置的软件数据
# --------------------------------------------------------------------------

def self_path() -> Path:
    return Path(sys.executable if getattr(sys, "frozen", False) else __file__).resolve()


def payload_path() -> Path:
    """定位内置的 payload.zip。

    依次尝试：

    1. ``sys._MEIPASS/payload.zip``（PyInstaller 打包的数据文件）；
    2. 可执行文件**同目录**的 ``payload.zip``
       —— 自解压包会先把安装器与 payload 解到同一个临时目录再运行，
       这种布局下就靠这一条找到；
    3. 本文件同目录（直接用源码调试时）。
    """
    meipass = getattr(sys, "_MEIPASS", None)
    candidates = []
    if meipass:
        candidates.append(Path(meipass) / PAYLOAD_NAME)
    candidates.append(self_path().parent / PAYLOAD_NAME)
    if not getattr(sys, "frozen", False):
        candidates.append(self_path().parent / PAYLOAD_NAME)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise RuntimeError(
        "安装包已损坏：找不到内置的软件数据（payload.zip）。\n"
        f"查找位置：{', '.join(str(c) for c in candidates)}\n"
        "请重新获取安装包。"
    )


def open_payload() -> zipfile.ZipFile:
    return zipfile.ZipFile(payload_path())


# --------------------------------------------------------------------------
# 安全输出
# --------------------------------------------------------------------------
#
# 安装器是**窗口化**（console=False）程序，此时 ``sys.stdout`` / ``sys.stderr``
# 可能是 ``None``，直接 ``print()`` 会抛 AttributeError；而异常又没地方写，
# 表现就是"点了一下什么也没发生"。所有输出都走这两个函数。

def say(message: str = "") -> None:
    stream = getattr(sys, "stdout", None)
    if stream is None:
        return
    try:
        stream.write(message + "\n")
        stream.flush()
    except (OSError, ValueError):
        pass


def warn(message: str) -> None:
    stream = getattr(sys, "stderr", None)
    if stream is None:
        return
    try:
        stream.write(message + "\n")
        stream.flush()
    except (OSError, ValueError):
        pass


# --------------------------------------------------------------------------
# 快捷方式
# --------------------------------------------------------------------------

def create_shortcut(link: Path, target: Path, workdir: Path, icon: Path | None = None) -> bool:
    """用 WScript.Shell 建 .lnk，避免依赖 pywin32。"""
    icon_part = f"$s.IconLocation = '{icon},0';" if icon and icon.is_file() else ""
    script = (
        "$ws = New-Object -ComObject WScript.Shell;"
        f"$s = $ws.CreateShortcut('{link}');"
        f"$s.TargetPath = '{target}';"
        f"$s.WorkingDirectory = '{workdir}';"
        f"$s.Description = '{APP_NAME}';"
        f"{icon_part}"
        "$s.Save();"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            check=True,
            capture_output=True,
            timeout=60,
        )
        return True
    except Exception:  # noqa: BLE001 - 建不了快捷方式不算致命
        return False


def start_menu_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(base) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


# --------------------------------------------------------------------------
# 安装 / 卸载
# --------------------------------------------------------------------------

def install_into(
    target_dir: Path,
    desktop: bool = True,
    start_menu: bool = True,
    progress=None,
) -> list[str]:
    """把内置数据解到 ``target_dir``。返回创建的快捷方式路径列表。"""
    notes: list[str] = []
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    with open_payload() as archive:
        members = archive.infolist()
        total = len(members) or 1
        for index, info in enumerate(members, start=1):
            archive.extract(info, str(target_dir))
            if progress is not None and (index % 20 == 0 or index == total):
                progress(index, total, info.filename)

    # 记录安装清单，供卸载使用
    installed: list[str] = []
    for path in target_dir.rglob("*"):
        if path.is_file():
            installed.append(str(path.relative_to(target_dir)))
    (target_dir / UNINSTALL_FILE).write_text(
        json.dumps(
            {"app": APP_NAME, "files": installed, "dirs": [str(target_dir)]},
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    exe = target_dir / APP_EXE
    icon = target_dir / "gwp" / "resources" / "icons" / "planet.ico"

    if desktop:
        desktop_dir = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
        link = desktop_dir / f"{APP_NAME}.lnk"
        if create_shortcut(link, exe, target_dir, icon):
            notes.append(str(link))

    if start_menu:
        menu = start_menu_dir() / APP_NAME
        menu.mkdir(parents=True, exist_ok=True)
        for name, target in (
            (APP_NAME, exe),
            ("卸载 " + APP_NAME, target_dir / f"卸载 {APP_NAME}.exe"),
        ):
            link = menu / f"{name}.lnk"
            if create_shortcut(link, target, target_dir, icon):
                notes.append(str(link))

    write_uninstaller(target_dir)
    return notes


def write_uninstaller(target_dir: Path) -> None:
    """生成卸载器：复制安装程序自身为「卸载 ….exe」，卸载时用 --uninstall。"""
    source = self_path()
    for name in (f"卸载 {APP_NAME}.exe",):
        try:
            shutil.copy2(source, target_dir / name)
        except OSError:
            pass


def uninstall_from(target_dir: Path | None = None) -> int:
    """按记录删除安装的文件与快捷方式。"""
    target_dir = Path(target_dir) if target_dir else self_path().parent
    record = target_dir / UNINSTALL_FILE
    files: list[str] = []
    if record.is_file():
        try:
            files = json.loads(record.read_text(encoding="utf-8")).get("files") or []
        except (OSError, ValueError):
            files = []

    # 清理快捷方式
    desktop_dir = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
    for link in (
        desktop_dir / f"{APP_NAME}.lnk",
        start_menu_dir() / APP_NAME / f"{APP_NAME}.lnk",
        start_menu_dir() / APP_NAME / f"卸载 {APP_NAME}.lnk",
    ):
        try:
            link.unlink(missing_ok=True)
        except OSError:
            pass
    try:
        menu = start_menu_dir() / APP_NAME
        if menu.is_dir() and not any(menu.iterdir()):
            menu.rmdir()
    except OSError:
        pass

    # 删除文件（保留用户数据目录 data/，避免误删用户内容）
    for relative in files:
        candidate = target_dir / relative
        if candidate.name == UNINSTALL_FILE:
            continue
        try:
            candidate.unlink(missing_ok=True)
        except OSError:
            pass

    # 自删：脚本延迟删除整个目录（含自身）
    script = (
        "Start-Sleep -Milliseconds 600;"
        f"Remove-Item -LiteralPath '{target_dir}' -Recurse -Force -ErrorAction SilentlyContinue"
    )
    subprocess.Popen(
        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", script],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return 0


# --------------------------------------------------------------------------
# 图形界面
# --------------------------------------------------------------------------

def run_gui() -> int:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    root = tk.Tk()
    root.title(f"安装 {APP_NAME}")
    root.geometry("620x420")
    root.resizable(False, False)

    state = {"dir": str(DEFAULT_DIR), "desktop": tk.BooleanVar(value=True),
             "menu": tk.BooleanVar(value=True), "busy": False}

    ttk.Label(root, text=APP_NAME, font=("Microsoft YaHei UI", 18, "bold")).pack(pady=(18, 2))
    ttk.Label(
        root,
        text="本地知识管理与 AI 辅助学习",
        font=("Microsoft YaHei UI", 10),
    ).pack()
    ttk.Label(
        root,
        text="安装包内不含任何用户数据，首次启动会自动创建数据目录。",
        font=("Microsoft YaHei UI", 9),
        foreground="#555555",
    ).pack(pady=(6, 0))

    frame = ttk.LabelFrame(root, text="安装位置", padding=10)
    frame.pack(fill="x", padx=18, pady=14)
    entry = ttk.Entry(frame, width=62)
    entry.insert(0, state["dir"])
    entry.pack(side="left", fill="x", expand=True)

    def choose() -> None:
        chosen = filedialog.askdirectory(title="选择安装位置", initialdir=state["dir"])
        if chosen:
            state["dir"] = str(Path(chosen) / APP_NAME) if Path(chosen).name != APP_NAME else chosen
            entry.delete(0, "end")
            entry.insert(0, state["dir"])

    ttk.Button(frame, text="浏览…", command=choose).pack(side="left", padx=(8, 0))

    options = ttk.LabelFrame(root, text="快捷方式", padding=10)
    options.pack(fill="x", padx=18)
    ttk.Checkbutton(options, text="创建桌面快捷方式", variable=state["desktop"]).pack(anchor="w")
    ttk.Checkbutton(options, text="创建开始菜单项", variable=state["menu"]).pack(anchor="w")

    bar = ttk.Progressbar(root, length=560, mode="determinate")
    bar.pack(pady=(16, 4), padx=18, fill="x")
    status = ttk.Label(root, text="准备就绪", font=("Microsoft YaHei UI", 9))
    status.pack()

    buttons = ttk.Frame(root)
    buttons.pack(pady=14)

    def do_install() -> None:
        if state["busy"]:
            return
        target = Path(entry.get().strip() or state["dir"])
        if target.exists() and any(target.iterdir()):
            if not messagebox.askyesno(
                "目录非空",
                f"{target}\n\n这个目录不是空的。继续安装会覆盖同名文件（用户数据 data 不会被覆盖）。\n\n继续吗？",
            ):
                return
        state["busy"] = True
        install_button.config(state="disabled", text="正在安装…")

        def progress(done: int, total: int, name: str) -> None:
            bar["value"] = done / total * 100
            status.config(text=f"正在安装 {done}/{total}：{name[:46]}")
            root.update_idletasks()

        def worker() -> None:
            try:
                notes = install_into(target, state["desktop"].get(), state["menu"].get(), progress)
            except Exception as exc:  # noqa: BLE001
                root.after(0, lambda: fail(exc))
                return
            root.after(0, lambda: done(target, notes))

        def fail(exc: Exception) -> None:
            state["busy"] = False
            install_button.config(state="normal", text="开始安装")
            messagebox.showerror("安装失败", f"安装过程中出错：\n\n{exc}")

        def done(target: Path, notes: list[str]) -> None:
            bar["value"] = 100
            status.config(text="安装完成")
            state["busy"] = False
            install_button.config(state="normal", text="开始安装")
            extra = "\n".join(f"  · {n}" for n in notes) or "  （未创建快捷方式）"
            messagebox.showinfo(
                "安装完成",
                f"{APP_NAME} 已安装到：\n{target}\n\n快捷方式：\n{extra}\n\n"
                f"随程序附带的《{MANUAL_NAME}》也在安装目录里。",
            )
            if messagebox.askyesno("启动", "现在启动 " + APP_NAME + " 吗？"):
                try:
                    subprocess.Popen([str(target / APP_EXE)], cwd=str(target))
                except OSError as exc:
                    messagebox.showwarning("启动失败", str(exc))
            root.destroy()

        threading.Thread(target=worker, daemon=True).start()

    install_button = ttk.Button(buttons, text="开始安装", command=do_install)
    install_button.pack(side="left", padx=6)
    ttk.Button(buttons, text="退出", command=root.destroy).pack(side="left", padx=6)

    root.mainloop()
    return 0


# --------------------------------------------------------------------------
# 入口
# --------------------------------------------------------------------------

def parse_args(argv: list[str]) -> dict:
    options = {"uninstall": False, "silent": False, "dir": "", "no_shortcut": False}
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--uninstall":
            options["uninstall"] = True
        elif item == "--silent":
            options["silent"] = True
        elif item == "--no-shortcut":
            options["no_shortcut"] = True
        elif item == "--dir" and index + 1 < len(argv):
            index += 1
            options["dir"] = argv[index]
        index += 1
    return options


def main(argv: list[str]) -> int:
    options = parse_args(argv)

    if options["uninstall"]:
        return uninstall_from()

    if options["silent"]:
        target = Path(options["dir"] or DEFAULT_DIR)
        try:
            notes = install_into(
                target,
                desktop=not options["no_shortcut"],
                start_menu=not options["no_shortcut"],
            )
        except Exception as exc:  # noqa: BLE001 - 静默模式也要给可诊断的痕迹
            warn(f"安装失败：{type(exc).__name__}: {exc}")
            return 1
        say(f"已安装到 {target}")
        for note in notes:
            say(f"  快捷方式: {note}")
        return 0

    return run_gui()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
