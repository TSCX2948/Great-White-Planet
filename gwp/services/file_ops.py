"""文件导入/复制/移动/删除等磁盘操作。

需求文档第十节：用户上传的内容进 ``data``；非用户直接上传的内容（例如从 PDF
渲染出来的图片）进 ``else data``。本模块负责在两者之间做正确的摆放。
"""

from __future__ import annotations

import logging
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from gwp.core import constants as C

log = logging.getLogger(__name__)


@dataclass
class ImportResult:
    source: Path
    target: Path | None
    status: str        # copied | skipped | overwritten | renamed | error
    message: str = ""

    @property
    def ok(self) -> bool:
        return self.status in ("copied", "overwritten", "renamed")

    @property
    def label(self) -> str:
        return {
            "copied": "已复制",
            "overwritten": "已覆盖",
            "renamed": "已重命名导入",
            "skipped": "已跳过",
            "error": "失败",
        }.get(self.status, self.status)


def is_importable(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in C.IMPORTABLE_EXTENSIONS


def unique_path(target: Path, suffix_style: str = "_1") -> Path:
    """目标已存在时生成不冲突的名字。

    ``suffix_style`` 支持两种写法：

    * ``"_1"``（默认）：末尾数字作为序号位，得到 ``name_1.md``、``name_2.md``；
    * ``"({n})"``：用 ``{n}`` 占位，得到 ``name(1).md``。

    之所以"替换末尾数字"而不是"直接拼接"，是为了让重复粘贴的结果可预期：
    ``a.md`` -> ``a_1.md``，而不是 ``a_1.md`` -> ``a_11.md``。
    """
    if not target.exists():
        return target

    stem = target.stem
    # 去掉末尾已有的序号，避免多次粘贴后变成 a_111
    base = re.sub(r"_\d+$", "", stem) or stem

    if "{n}" in suffix_style:
        make = lambda index: suffix_style.format(n=index)  # noqa: E731
    elif len(suffix_style) > 1 and suffix_style[-1].isdigit():
        head = suffix_style[:-1]
        make = lambda index: f"{head}{index}"  # noqa: E731
    else:
        make = lambda index: f"{suffix_style}{index}"  # noqa: E731

    for index in range(1, 1000):
        candidate = target.with_name(f"{base}{make(index)}{target.suffix}")
        if not candidate.exists():
            return candidate
    raise OSError(f"无法为 {target.name} 生成唯一文件名")


def import_files(
    sources: list[Path],
    target_dir: Path,
    overwrite: bool = False,
    copy: bool = True,
    suffix_style: str = "_1",
) -> list[ImportResult]:
    """把文件复制（或移动）到目标目录。目录会被递归复制。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    results: list[ImportResult] = []
    for source in sources:
        source = Path(source)
        try:
            if not source.exists():
                results.append(ImportResult(source, None, "error", "源文件不存在"))
                continue
            if source.resolve() == target_dir.resolve():
                results.append(ImportResult(source, None, "skipped", "源和目标相同"))
                continue

            destination = target_dir / source.name
            if source.is_dir() and destination.exists() and overwrite:
                shutil.rmtree(destination, ignore_errors=True)

            if destination.exists() and not overwrite:
                new_destination = unique_path(destination, suffix_style)
                _transfer(source, new_destination, copy)
                results.append(ImportResult(source, new_destination, "renamed",
                                            f"目标已存在，改名为 {new_destination.name}"))
                continue

            if destination.exists() and overwrite:
                _replace(source, destination, copy)
                results.append(ImportResult(source, destination, "overwritten"))
                continue

            _transfer(source, destination, copy)
            results.append(ImportResult(source, destination, "copied"))
        except OSError as exc:
            log.exception("导入失败: %s", source)
            results.append(ImportResult(source, None, "error", str(exc)))
    return results


def _transfer(source: Path, destination: Path, copy: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if copy:
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)
    else:
        shutil.move(str(source), str(destination))


def _replace(source: Path, destination: Path, copy: bool) -> None:
    if destination.is_dir():
        shutil.rmtree(destination, ignore_errors=True)
    elif destination.exists():
        destination.unlink()
    _transfer(source, destination, copy)


def delete_path(path: Path, to_recycle: bool = True) -> bool:
    """删除文件或文件夹。优先放进回收站，失败则永久删除。"""
    path = Path(path)
    if not path.exists():
        return False
    if to_recycle:
        try:
            from gwp.services import shell_ops

            if shell_ops.send_to_recycle_bin(path):
                return True
        except Exception:  # noqa: BLE001
            log.warning("移入回收站失败，改为永久删除: %s", path)
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
    else:
        path.unlink()
    return True


def rename_path(path: Path, new_name: str) -> Path:
    """重命名文件或文件夹（保持所在目录不变）。"""
    path = Path(path)
    target = path.with_name(new_name)
    if target.exists():
        raise OSError(f"“{new_name}”已经存在")
    path.rename(target)
    return target


def copy_into_assets(source: Path, assets_dir: Path, sub_dir: str = "") -> Path:
    """把资源文件复制进 ``else data/assets``（图片等不直接存入用户数据）。"""
    target_dir = assets_dir / sub_dir if sub_dir else assets_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    target = unique_path(target_dir / source.name)
    shutil.copy2(source, target)
    return target


def dir_stats(path: Path, max_files: int = 20000) -> tuple[int, int]:
    """返回 (文件数, 总字节数)。"""
    count = 0
    size = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    size += item.stat().st_size
                except OSError:
                    continue
                count += 1
                if count >= max_files:
                    break
    except OSError:
        pass
    return count, size


def find_vscode() -> str:
    """找 VSCode（``code`` 命令或常见安装路径）。找不到返回空串。

    优先用 ``code`` 命令：用户可能装在非默认位置，而安装时一般会加进 PATH。

    **必须在 ``code.cmd`` 之前优先 ``code.exe``**：实测 Windows 的
    ``shutil.which('code')`` 会返回 ``...\\bin\\code.CMD``（批处理包装），
    它需要经过一层 shell 才能跑；而同一个目录下的 ``Code.exe``
    可以被直接启动，少一层就少一类引号/编码问题（见
    :func:`open_in_vscode` 里那个 ``cmd /c`` 的真实 bug）。
    """
    import sys

    if not sys.platform.startswith("win"):
        return ""
    # PATH 上优先找真正的可执行文件
    for name in ("code.exe", "code", "code.cmd", "code.bat"):
        found = shutil.which(name)
        if found:
            return found
    # 常见安装位置。注意"从 code.cmd 反推 Code.exe"也在这里做 ——
    # 装到非默认目录时，这是唯一能找到真正 exe 的办法。
    candidates = [
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft VS Code\Code.exe"),
        r"D:\VS Code\Code.exe",
        r"D:\VS Code\bin\code.exe",
        r"D:\VS Code\bin\code.cmd",
        r"C:\VS Code\Code.exe",
        r"C:\VS Code\bin\code.exe",
        r"C:\VS Code\bin\code.cmd",
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    # 最后再全盘搜一下 PATH 里的 code.*，避免上面都落空
    for name in ("code", "code.cmd", "code.bat", "code.exe"):
        found = shutil.which(name)
        if found:
            return found
    return ""


def vscode_command(editor: str, target: Path | str) -> list[str]:
    """拼出"用 VSCode 打开文件"的命令行。抽成函数是为了**能被测试断言**。

    这里**刻意不判断扩展名、也不套任何 shell**（见 :func:`open_in_vscode`
    里那个真实的 ``cmd /c`` bug）：直接给出 ``[编辑器, 文件]`` 两个参数，
    交给 Windows 自己去处理引号。
    """
    return [str(editor), str(target)]


def open_in_vscode(path: Path | str) -> bool:
    """用 VSCode 打开文件。**没有 VSCode 时返回 False**，由调用方兜底。

    ``code <文件>`` 会在已有的 VSCode 窗口里加一个标签页，不会每次弹新窗口 ——
    对"就看一个 JSON"来说正合适。

    **不要用 ``cmd /c`` 去调 ``code.cmd``**（这是个真实的 bug）。
    曾经写成::

        ["cmd", "/c", editor, str(target)]        # ← 错误

    看起来"批处理要通过 cmd 调更稳"，实际上 ``cmd /c`` 需要**自己**处理引号：
    路径里有空格时它会把命令拆断，于是报::

        'D:\VS' is not recognized as an internal or external command

    用户装的正是 ``D:\VS Code\``，所以这条路径 100% 失败，
    而软件还会因为没抛异常而报"成功"（返回 True）——
    表现为"点了没反应"。**这个 bug 只在含空格的安装路径下出现**，
    所以我在纯 ASCII 的临时目录里测试时一直是好的。

    正确做法：**让 Python 直接启动它**。``subprocess`` 在 Windows 上走
    ``CreateProcessW``，会按 Windows 自己的规则给每个参数加引号，
    ``.cmd`` / ``.bat`` 交给系统处理（等价于 ``ShellExecute`` 的语义），
    **不需要也不应该我们再套一层 cmd**。实测这样调用返回码是 0，
    含中文的路径也正常；VSCode 关掉时能起新窗口、文件真的被打开
    （窗口标题就是文件名）。
    """
    import subprocess

    editor = find_vscode()
    target = Path(path)
    if not editor or not target.is_file():
        log.info("没有找到 VSCode，无法用它打开：%s", target)
        return False
    try:
        subprocess.Popen(  # noqa: S603
            vscode_command(editor, target),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(target.parent),
        )
        log.info("已用 VSCode 打开：%s（编辑器=%s）", target, editor)
        return True
    except OSError:
        log.exception("用 VSCode 打开失败：%s", target)
        return False


def reveal_in_explorer(path: Path) -> bool:
    """在资源管理器中定位文件/文件夹。"""
    import subprocess
    import sys

    path = Path(path)
    try:
        if sys.platform.startswith("win"):
            if path.is_dir():
                subprocess.Popen(["explorer", str(path)])  # noqa: S603,S607
            else:
                subprocess.Popen(["explorer", "/select,", str(path)])  # noqa: S603,S607
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])  # noqa: S603,S607
        else:
            subprocess.Popen(["xdg-open", str(path.parent)])  # noqa: S603,S607
        return True
    except OSError:
        log.exception("打开资源管理器失败: %s", path)
        return False


def open_with_system(path: Path) -> bool:
    """用系统默认程序打开文件。"""
    import os
    import sys

    path = Path(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]  # noqa: S606
        elif sys.platform == "darwin":
            import subprocess

            subprocess.Popen(["open", str(path)])  # noqa: S603,S607
        else:
            import subprocess

            subprocess.Popen(["xdg-open", str(path)])  # noqa: S603,S607
        return True
    except OSError:
        log.exception("打开文件失败: %s", path)
        return False
