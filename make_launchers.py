"""创建一个不需要依赖 python 环境的启动器（可选）。

多数情况下直接用 ``run.pyw`` 就够了；本脚本额外生成两个 Windows 批处理文件：

* ``启动 Great White Planet.bat``  —— 双击即可启动（带控制台，方便看报错）
* ``安装依赖.bat``                 —— 双击安装/修复依赖

放在 code 目录下，方便分发给别人或在没有配置 PATH 的机器上使用。
"""

from __future__ import annotations

import sys
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
VENV_PYTHON = CODE_DIR / "venv" / "Scripts" / "python.exe"
VENV_PYTHONW = CODE_DIR / "venv" / "Scripts" / "pythonw.exe"

BAT_START = """@echo off
chcp 65001 >nul
title Great White Planet
set CODE_DIR=%~dp0
if exist "%CODE_DIR%venv\\Scripts\\pythonw.exe" (
    start "" "%CODE_DIR%venv\\Scripts\\pythonw.exe" "%CODE_DIR%run.pyw" %*
) else (
    echo [!] 没有找到 venv，尝试使用系统 python...
    start "" pythonw "%CODE_DIR%run.pyw" %*
)
"""

BAT_DEBUG = """@echo off
chcp 65001 >nul
title Great White Planet (调试)
set CODE_DIR=%~dp0
if exist "%CODE_DIR%venv\\Scripts\\python.exe" (
    "%CODE_DIR%venv\\Scripts\\python.exe" "%CODE_DIR%run.py" %*
) else (
    python "%CODE_DIR%run.py" %*
)
echo.
echo 程序已退出，按任意键关闭窗口。
pause >nul
"""

BAT_INSTALL = """@echo off
chcp 65001 >nul
title 安装 Great White Planet 依赖
set CODE_DIR=%~dp0
cd /d "%CODE_DIR%"
if not exist "venv\\Scripts\\python.exe" (
    echo 正在创建虚拟环境 venv ...
    python -m venv venv
)
echo 正在安装依赖 ...
"venv\\Scripts\\python.exe" -m pip install --upgrade pip
"venv\\Scripts\\python.exe" -m pip install PyQt6 markdown pygments pymupdf python-docx python-pptx openpyxl pillow
echo.
echo 安装完成。现在可以双击「启动 Great White Planet.bat」。
pause >nul
"""


def main() -> int:
    files = {
        "启动 Great White Planet.bat": BAT_START,
        "启动 Great White Planet（调试）.bat": BAT_DEBUG,
        "安装依赖.bat": BAT_INSTALL,
    }
    for name, content in files.items():
        target = CODE_DIR / name
        target.write_text(content, encoding="utf-8-sig", newline="\r\n")
        print(f"已生成：{target}")

    print()
    print(f"虚拟环境解释器：{VENV_PYTHON if VENV_PYTHON.exists() else '（未找到，请先创建 venv）'}")
    if not VENV_PYTHONW.exists():
        print("提示：venv 中没有 pythonw.exe，静默启动会回退到 python.exe。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
