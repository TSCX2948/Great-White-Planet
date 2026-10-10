"""Great White Planet 静默启动脚本（不显示控制台窗口）。

由桌面快捷方式或开机自启调用。出错时会写日志到
``data/else data/logs/startup_error.log``，下次用 run.py 启动即可看到原因。
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))


def _report(detail: str) -> None:
    try:
        log_dir = CODE_DIR.parent / "data" / "else data" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "startup_error.log").write_text(
            f"argv={sys.argv}\npython={sys.executable}\ncwd={os.getcwd()}\n\n{detail}",
            encoding="utf-8",
        )
    except OSError:
        pass


def main() -> int:
    try:
        from gwp.app import run

        return run(sys.argv[1:])
    except Exception:  # noqa: BLE001
        _report(traceback.format_exc())
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
