"""截取图形安装器的真实界面，供安装说明 PDF 使用。"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import subprocess
import time
from pathlib import Path

STAGE = Path(r"D:\Great White Planet\DeepseekData\build\out\installer_stage")
EXE = STAGE / "安装 Great White Planet.exe"

# 直接写进 Document\installer_shots —— 安装说明 Markdown 就是从这里引用图片的，
# 放在这里才是唯一来源，不再另存一份到 build 下产生重复文件。
OUT = Path(r"D:\Great White Planet\Document\installer_shots")

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def find_window(pid: int, min_width: int = 300) -> int:
    """找该进程里最大的可见顶层窗口。"""
    best = [0, 0]

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def callback(hwnd, _lparam):
        owner = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value != pid or not user32.IsWindowVisible(hwnd):
            return True
        rect = RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        if width >= min_width and width * (rect.bottom - rect.top) > best[0]:
            best[0] = width * (rect.bottom - rect.top)
            best[1] = hwnd
        return True

    user32.EnumWindows(callback, 0)
    return best[1]


def grab(hwnd: int, target: Path) -> tuple[int, int]:
    """抓取窗口的**客户区**（不含标题栏与边框），避免带入桌面的黑边。"""
    rect = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rect))
    width = rect.right - rect.left
    height = rect.bottom - rect.top

    hdc = user32.GetDC(hwnd)
    memdc = gdi32.CreateCompatibleDC(hdc)
    bitmap = gdi32.CreateCompatibleBitmap(hdc, width, height)
    gdi32.SelectObject(memdc, bitmap)
    gdi32.BitBlt(memdc, 0, 0, width, height, hdc, 0, 0, 0x00CC0020 | 0x40000000)

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
            ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
            ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
            ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
            ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
            ("biClrImportant", wintypes.DWORD),
        ]

    header = BITMAPINFOHEADER()
    header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    header.biWidth = width
    header.biHeight = -height          # 负数 = 自上而下
    header.biPlanes = 1
    header.biBitCount = 32
    header.biCompression = 0

    buffer_size = width * height * 4
    buffer = ctypes.create_string_buffer(buffer_size)
    gdi32.GetDIBits(memdc, bitmap, 0, height, buffer, ctypes.byref(header), 0)

    from PIL import Image

    image = Image.frombuffer("RGBA", (width, height), buffer, "raw", "BGRA", 0, 1)
    image.convert("RGB").save(target)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(memdc)
    user32.ReleaseDC(hwnd, hdc)
    return width, height


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "01_welcome.png").unlink(missing_ok=True)

    print("启动安装器……")
    proc = subprocess.Popen([str(EXE)], cwd=str(STAGE))
    hwnd = 0
    for _ in range(20):
        time.sleep(1)
        hwnd = find_window(proc.pid)
        if hwnd:
            break
    if not hwnd:
        print("!! 没找到安装器窗口")
        proc.kill()
        return 1
    print("窗口句柄:", hwnd)

    # 置顶并激活，保证截图内容正确
    user32.SetForegroundWindow(hwnd)
    user32.ShowWindow(hwnd, 9)      # SW_RESTORE
    time.sleep(1.5)

    target = OUT / "01_welcome.png"
    width, height = grab(hwnd, target)
    print(f"已截图: {target}  {width}x{height}  {target.stat().st_size} 字节")

    proc.kill()
    proc.wait(timeout=30)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
