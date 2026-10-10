@echo off
chcp 65001 >nul
title Great White Planet (调试)
set CODE_DIR=%~dp0
if exist "%CODE_DIR%venv\Scripts\python.exe" (
    "%CODE_DIR%venv\Scripts\python.exe" "%CODE_DIR%run.py" %*
) else (
    python "%CODE_DIR%run.py" %*
)
echo.
echo 程序已退出，按任意键关闭窗口。
pause >nul
