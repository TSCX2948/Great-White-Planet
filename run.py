"""Great White Planet 启动脚本（带控制台，便于排查问题）。

安静启动请使用 run.pyw（不弹控制台窗口）。
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))


def main() -> int:
    try:
        from gwp.app import run

        return run(sys.argv[1:])
    except Exception:  # noqa: BLE001 - 启动期任何异常都要让用户看见
        detail = traceback.format_exc()
        print("Great White Planet 启动失败：\n", file=sys.stderr)
        print(detail, file=sys.stderr)
        try:
            log_dir = CODE_DIR.parent / "data" / "else data" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / "startup_error.log").write_text(
                f"argv={sys.argv}\npython={sys.executable}\ncwd={os.getcwd()}\n\n{detail}",
                encoding="utf-8",
            )
            print(f"详细信息已写入：{log_dir / 'startup_error.log'}", file=sys.stderr)
        except OSError:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
