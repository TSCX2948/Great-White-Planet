"""Great White Planet 打包入口。

与 ``run.py`` 的区别：本文件**只负责启动**，不依赖 ``__file__`` 的目录层级，
因此打包成 exe 后也能正确工作（打包后 ``__file__`` 指向解包目录）。

启动失败时会弹出一个消息框 —— 打包后的程序通常没有控制台，
只往 stderr 写用户是看不到的。
"""

from __future__ import annotations

import os
import sys
import traceback


def _report_failure(detail: str) -> None:
    """把启动失败写到日志文件，并尽量弹窗告知用户。"""
    written = ""
    try:
        from gwp.core.paths import project_root

        log_dir = project_root() / "data" / "else data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        target = log_dir / "startup_error.log"
        target.write_text(
            f"argv={sys.argv}\n"
            f"exe={sys.executable}\n"
            f"frozen={getattr(sys, 'frozen', False)}\n"
            f"cwd={os.getcwd()}\n\n{detail}",
            encoding="utf-8",
        )
        written = str(target)
    except Exception:  # noqa: BLE001 - 记录失败也不能影响报错
        pass

    message = "Great White Planet 启动失败。\n\n" + detail.strip().splitlines()[-1]
    if written:
        message += f"\n\n详细信息已写入：\n{written}"
    try:
        from PyQt6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, "启动失败", message)
    except Exception:  # noqa: BLE001 - 连 GUI 都起不来就退回控制台
        print(message, file=sys.stderr)


def main() -> int:
    try:
        from gwp.app import run

        return run(sys.argv[1:])
    except SystemExit:
        raise
    except BaseException:  # noqa: BLE001 - 启动期任何异常都要让用户看见
        _report_failure(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
