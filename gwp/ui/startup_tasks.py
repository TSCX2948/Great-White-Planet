"""启动后台任务：预扫描目录、检查依赖、检查开机自启。

这些都在创建主窗口之后异步执行，避免拖慢启动（需求文档第十三节）。
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from gwp.bootstrap import AppContext
from gwp.services import dependencies

log = logging.getLogger(__name__)


class StartupWorker(QThread):
    """后台预扫描。只发结果，不改界面。"""

    finished_scan = pyqtSignal(int)          # 科目数量
    failed = pyqtSignal(str)

    def __init__(self, context: AppContext, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.context = context
        # 登记到全局线程表。这个线程最慢（要扫 7 个科目、20 多秒），
        # 也是"退出时还在跑"的头号嫌疑人 —— 见 core/threads.py 的说明。
        from gwp.core import threads as _threads

        _threads.register(self)

    def run(self) -> None:  # noqa: D102
        try:
            subjects = self.context.library.subjects(refresh=True)
            for subject in subjects:
                self.context.cache.record(
                    subject.path, subject.book_count, subject.file_count, subject.total_size
                )
            self.context.cache.save()
            self.finished_scan.emit(len(subjects))
        except Exception as exc:  # noqa: BLE001
            log.exception("预扫描失败")
            self.failed.emit(str(exc))
        finally:
            from gwp.core import threads as _threads

            _threads.unregister(self)


def check_startup_environment(context: AppContext) -> list[str]:
    """同步检查环境，返回需要提示用户的消息列表。"""
    messages: list[str] = []

    missing_required = dependencies.missing_required()
    if missing_required:
        names = "、".join(dependency.package for dependency in missing_required)
        messages.append(
            f"缺少必需的依赖：{names}\n请执行：{dependencies.install_command()}"
        )

    missing_optional = [
        dependency for dependency in dependencies.missing() if not dependency.required
    ]
    if missing_optional:
        names = "、".join(dependency.package for dependency in missing_optional)
        messages.append(
            f"以下可选依赖缺失，相关功能（如 PDF/Word/Excel 解析）不可用：{names}\n"
            f"需要时请执行：pip install {names}"
        )

    try:
        context.paths.ensure()
    except OSError as exc:
        messages.append(f"数据目录不可写：{context.paths.data_root}\n{exc}")

    return messages


__all__ = ["StartupWorker", "check_startup_environment"]
