"""文件剪贴板：复制 / 剪切 / 粘贴。

* 应用内部的剪贴板状态放在这里（一组路径 + 是复制还是剪切）；
* 同时把路径写进**系统剪贴板**，因此可以和资源管理器互相粘贴
  （在资源管理器里 Ctrl+C，回到软件里就能粘贴，反之亦然）；
* 剪切采用"粘贴成功后才删除源文件"的策略，中途失败不会丢文件。

这个模块不依赖 Qt，因此可以单独测试。
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from gwp.services import file_ops

log = logging.getLogger(__name__)

COPY = "copy"
CUT = "cut"


@dataclass
class FileClipboard:
    """一组待粘贴的文件/文件夹。"""

    paths: list[Path] = field(default_factory=list)
    mode: str = COPY

    # ------------------------------------------------------------------

    @property
    def is_empty(self) -> bool:
        return not self.paths

    @property
    def is_cut(self) -> bool:
        return self.mode == CUT

    @property
    def count(self) -> int:
        return len(self.paths)

    def set(self, paths: list[Path], mode: str = COPY) -> None:
        """记录一批文件，并同步到系统剪贴板。"""
        self.paths = [Path(item) for item in paths]
        self.mode = CUT if mode == CUT else COPY
        self._sync_system_clipboard()

    def clear(self) -> None:
        self.paths = []
        self.mode = COPY

    def describe(self) -> str:
        if self.is_empty:
            return "剪贴板为空"
        action = "剪切" if self.is_cut else "复制"
        if self.count == 1:
            return f"已{action}：{self.paths[0].name}"
        return f"已{action} {self.count} 个项目"

    def contains(self, path: Path) -> bool:
        try:
            target = Path(path).resolve()
        except OSError:
            target = Path(path)
        for item in self.paths:
            try:
                if item.resolve() == target:
                    return True
            except OSError:
                if item == target:
                    return True
        return False

    def would_paste_into_itself(self, folder: Path) -> bool:
        """判断把内容粘到 ``folder`` 会不会"粘进自己"。

        ``folder`` 等于剪贴板里的某个文件夹、或位于它内部，都算（这类操作必须阻止，
        否则剪切一个文件夹到它所在目录会把它自己删掉）。

        注意："把文件夹**里面**的文件**粘贴回同一个文件夹**"是合法操作：
        此时会自动改名、并且不删除源文件，因此这里只针对文件夹本身及其子目录。
        """
        try:
            folder = Path(folder).resolve()
        except OSError:
            folder = Path(folder)
        for item in self.paths:
            if not item.is_dir():
                continue
            try:
                resolved = item.resolve()
            except OSError:
                resolved = item
            if resolved == folder:
                return True
            try:
                folder.relative_to(resolved)
                return True
            except (ValueError, OSError):
                continue
        return False

    # ------------------------------------------------------------------

    def _sync_system_clipboard(self) -> None:
        """把路径放进系统剪贴板，便于和资源管理器互通。"""
        if not self.paths:
            return
        try:
            _set_windows_clipboard(self.paths, self.is_cut)
        except Exception:  # noqa: BLE001 - 失败不影响应用内粘贴
            log.debug("写入系统剪贴板失败（不影响应用内粘贴）", exc_info=True)

    # ------------------------------------------------------------------

    def paste(self, target_dir: Path) -> list[file_ops.ImportResult]:
        """把剪贴板内容粘贴到目标目录。

        * 已存在同名文件时自动改名（``名称_1``…），不覆盖你的资料；
        * 剪切模式下只有复制成功的项目才会删除源文件。
        """
        target_dir = Path(target_dir)
        if self.is_empty:
            return []
        target_dir.mkdir(parents=True, exist_ok=True)

        suffix_style = "_1"
        results = file_ops.import_files(
            self.paths,
            target_dir,
            overwrite=False,
            copy=True,
            suffix_style=suffix_style,
        )

        if self.is_cut:
            removed: list[Path] = []
            for result, source in zip(results, self.paths):
                if not result.ok:
                    continue
                # 源和目标相同（粘贴回原目录）时不要删除，否则等于自己删自己
                if result.target is not None:
                    try:
                        same = result.target.resolve() == source.resolve()
                    except OSError:
                        same = result.target == source
                    if same:
                        continue
                try:
                    if source.is_dir():
                        import shutil

                        shutil.rmtree(source, ignore_errors=False)
                    else:
                        source.unlink()
                    removed.append(source)
                except OSError:
                    log.exception("剪切后删除源文件失败：%s", source)
            for source in removed:
                self.paths = [item for item in self.paths if item != source]
            if not self.paths:
                self.clear()
        return results


# --------------------------------------------------------------------------
# 系统剪贴板（Windows：CF_HDROP，让资源管理器可以粘贴）
# --------------------------------------------------------------------------

def _set_windows_clipboard(paths: list[Path], cut: bool) -> None:
    if not sys.platform.startswith("win"):
        raise OSError("仅 Windows 支持写文件剪贴板")
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        # 无头环境（自动化测试）里没有真实剪贴板，直接跳过
        raise OSError("当前为无界面环境")

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    user32 = ctypes.WinDLL("user32", use_last_error=True)

    # 64 位下必须声明参数/返回类型，否则句柄会被截断成 32 位（GlobalLock 会失败）
    kernel32.GlobalAlloc.restype = ctypes.c_void_p
    kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalUnlock.restype = wintypes.BOOL
    kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    kernel32.GlobalFree.restype = ctypes.c_void_p
    kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
    user32.OpenClipboard.restype = wintypes.BOOL
    user32.OpenClipboard.argtypes = [ctypes.c_void_p]
    user32.EmptyClipboard.restype = wintypes.BOOL
    user32.SetClipboardData.restype = ctypes.c_void_p
    user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]
    user32.CloseClipboard.restype = wintypes.BOOL
    # 注意：RegisterClipboardFormatW 属于 user32（不是 shell32）
    user32.RegisterClipboardFormatW.restype = wintypes.UINT
    user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]

    GMEM_MOVEABLE = 0x0002
    CF_HDROP = 15

    class DROPFILES(ctypes.Structure):
        _fields_ = [
            ("pFiles", wintypes.DWORD),
            ("pt", wintypes.POINT),
            ("fNC", wintypes.BOOL),
            ("fWide", wintypes.BOOL),
        ]

    file_list = "\0".join(str(Path(path).resolve()) for path in paths) + "\0\0"
    encoded = file_list.encode("utf-16-le")
    header_size = ctypes.sizeof(DROPFILES)
    total = header_size + len(encoded)

    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, total)
    if not handle:
        raise OSError(f"GlobalAlloc 失败（错误码 {ctypes.get_last_error()}）")
    pointer = kernel32.GlobalLock(handle)
    if not pointer:
        error = ctypes.get_last_error()
        kernel32.GlobalFree(handle)
        raise OSError(f"GlobalLock 失败（错误码 {error}）")
    try:
        drop = DROPFILES()
        drop.pFiles = header_size
        drop.fWide = True
        ctypes.memmove(pointer, ctypes.byref(drop), header_size)
        ctypes.memmove(pointer + header_size, encoded, len(encoded))
    finally:
        kernel32.GlobalUnlock(handle)

    # 附加"剪切/复制"标记（2=移动，5=复制），资源管理器据此决定粘贴后是否删除源文件。
    # 这一步是可选的：失败了也不能影响主数据（文件列表）的写入。
    preferred_format = 0
    preferred_handle = None
    try:
        preferred_format = user32.RegisterClipboardFormatW("Preferred DropEffect")
        if preferred_format:
            preferred_handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, 4)
            if preferred_handle:
                effect_pointer = kernel32.GlobalLock(preferred_handle)
                if effect_pointer:
                    effect = wintypes.DWORD(2 if cut else 5)
                    ctypes.memmove(effect_pointer, ctypes.byref(effect), 4)
                    kernel32.GlobalUnlock(preferred_handle)
    except Exception:  # noqa: BLE001
        log.debug("准备 Preferred DropEffect 失败（不影响复制粘贴）", exc_info=True)
        preferred_format = 0
        if preferred_handle:
            kernel32.GlobalFree(preferred_handle)
            preferred_handle = None

    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        if preferred_handle:
            kernel32.GlobalFree(preferred_handle)
        raise OSError(f"OpenClipboard 失败（错误码 {ctypes.get_last_error()}）")
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(CF_HDROP, handle):
            raise OSError(f"SetClipboardData(CF_HDROP) 失败（错误码 {ctypes.get_last_error()}）")
        handle = None       # 所有权已交给系统，不能再 GlobalFree
        if preferred_format and preferred_handle:
            if user32.SetClipboardData(preferred_format, preferred_handle):
                preferred_handle = None
    finally:
        user32.CloseClipboard()
        if handle:
            kernel32.GlobalFree(handle)
        if preferred_handle:
            kernel32.GlobalFree(preferred_handle)


def read_system_clipboard_files() -> list[Path]:
    """从系统剪贴板读出文件列表（用于接收资源管理器里复制的文件）。"""
    if not sys.platform.startswith("win"):
        return []
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return []
    import ctypes
    from ctypes import wintypes

    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        shell32 = ctypes.WinDLL("shell32", use_last_error=True)
        user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
        user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.OpenClipboard.argtypes = [ctypes.c_void_p]
        user32.GetClipboardData.restype = ctypes.c_void_p
        user32.GetClipboardData.argtypes = [wintypes.UINT]
        user32.CloseClipboard.restype = wintypes.BOOL
        shell32.DragQueryFileW.restype = wintypes.UINT
        shell32.DragQueryFileW.argtypes = [
            ctypes.c_void_p,
            wintypes.UINT,
            wintypes.LPWSTR,
            wintypes.UINT,
        ]

        CF_HDROP = 15
        if not user32.IsClipboardFormatAvailable(CF_HDROP):
            return []
        if not user32.OpenClipboard(None):
            return []
        try:
            handle = user32.GetClipboardData(CF_HDROP)
            if not handle:
                return []
            count = shell32.DragQueryFileW(handle, 0xFFFFFFFF, None, 0)
            paths: list[Path] = []
            for index in range(count):
                length = shell32.DragQueryFileW(handle, index, None, 0)
                buffer = ctypes.create_unicode_buffer(length + 1)
                shell32.DragQueryFileW(handle, index, buffer, length + 1)
                if buffer.value:
                    paths.append(Path(buffer.value))
            return paths
        finally:
            user32.CloseClipboard()
    except Exception:  # noqa: BLE001
        log.debug("读取系统剪贴板失败", exc_info=True)
        return []


__all__ = [
    "COPY",
    "CUT",
    "FileClipboard",
    "read_system_clipboard_files",
]
