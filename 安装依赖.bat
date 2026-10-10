@echo off
chcp 65001 >nul
title 安装 Great White Planet 依赖
set CODE_DIR=%~dp0
cd /d "%CODE_DIR%"
if not exist "venv\Scripts\python.exe" (
    echo 正在创建虚拟环境 venv ...
    python -m venv venv
)
echo 正在安装依赖 ...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install PyQt6 markdown pygments pymupdf python-docx python-pptx openpyxl pillow
echo.
echo 安装完成。现在可以双击「启动 Great White Planet.bat」。
pause >nul
