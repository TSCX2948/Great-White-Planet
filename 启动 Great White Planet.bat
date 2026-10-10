@echo off
chcp 65001 >nul
title Great White Planet
set CODE_DIR=%~dp0
if exist "%CODE_DIR%venv\Scripts\pythonw.exe" (
    start "" "%CODE_DIR%venv\Scripts\pythonw.exe" "%CODE_DIR%run.pyw" %*
) else (
    echo [!] 没有找到 venv，尝试使用系统 python...
    start "" pythonw "%CODE_DIR%run.pyw" %*
)
