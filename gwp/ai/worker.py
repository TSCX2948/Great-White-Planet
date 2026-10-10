"""把耗时的 AI 调用放到后台线程，避免界面卡死。

Qt 的信号/槽是线程安全的：工作线程只负责跑逻辑，通过信号把结果交回界面线程。

**给写测试的人一个重要提醒（踩过，很难查）**

``AIWorker`` 发出的是**跨线程排队信号**。在离屏（offscreen）平台上，
``QApplication.processEvents()`` **不会派发它们** ——
任务明明跑完了，槽函数永不执行，界面上一直停在"正在回答"，
而且**没有任何报错**，非常容易误判成被测代码有 bug。

实测三种写法：

* ``for _ in range(N): app.processEvents()`` → **收不到信号**；
* ``QEventLoop`` + ``QTimer.singleShot(timeout, loop.quit); loop.exec()`` → 收得到；
* 先 ``thread.wait(...)`` 再 ``processEvents()`` → 也收得到。

所以测试里等后台线程结果时要"泵"一下事件循环
（``tests/smoke_gui.py`` 里的 ``pump()`` 就是干这个的）。
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from gwp.ai.types import AIConfigError, AIError, AiQuestion, ChatCancelled

log = logging.getLogger(__name__)


class AIWorker(QThread):
    """在后台执行一个可调用对象。

    这个类只做三件事：启动线程、把回调转成信号、把异常转成信号。
    它不关心任务是聊天还是生成 summary。
    """

    chunk = pyqtSignal(str)                      # 流式文本片段
    progress = pyqtSignal(str, int, str)         # 消息, 百分比, 详情
    question = pyqtSignal(object, object)        # AiQuestion 对象, 回答容器
    finished_ok = pyqtSignal(object)             # 结果对象
    failed = pyqtSignal(str)                     # 错误消息
    cancelled = pyqtSignal()

    def __init__(
        self,
        task: Callable[..., Any],
        parent: QObject | None = None,
        label: str = "",
        pass_helpers: bool = True,
    ) -> None:
        super().__init__(parent)
        self._task = task
        self._label = label
        self._pass_helpers = pass_helpers
        self._cancel_event = threading.Event()
        self._question_event: threading.Event | None = None
        self._question_answer: str | None = None
        self._question_holder: dict[str, Any] = {}
        self._question_lock = threading.Lock()
        # 登记到全局线程表：退出时会被统一等待（见 core/threads.py）。
        # 不登记的话，线程还在跑就被销毁会让 Qt qFatal **直接中止进程**
        # （用户看到"闪退"，日志里什么都没有）。
        from gwp.core import threads as _threads

        _threads.register(self)

    # -- 协作式取消 -----------------------------------------------------

    def cancel(self) -> None:
        """请求取消。任务里的 should_cancel 回调会返回 True。"""
        self._cancel_event.set()
        # 若正在等待用户回答问题，唤醒它以免线程卡住
        with self._question_lock:
            if self._question_event is not None:
                self._question_event.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancel_event.is_set()

    # -- 供任务使用的回调 -----------------------------------------------

    def emit_chunk(self, text: str) -> None:
        if text:
            self.chunk.emit(text)

    def emit_progress(self, message: str, percent: int = -1, detail: str = "") -> None:
        self.progress.emit(message, int(percent), detail)

    def ask_question(self, question: AiQuestion) -> str | None:
        """在工作线程里阻塞等待界面回答。"""
        with self._question_lock:
            self._question_event = threading.Event()
            self._question_answer = None
        self.question.emit(question, self._question_holder)
        # 等待界面把答案写进 holder（或取消）
        self._question_event.wait(timeout=3600)
        with self._question_lock:
            self._question_event = None
        if self._cancel_event.is_set():
            return None
        return self._question_answer

    def answer_question(self, answer: str | None) -> None:
        """由界面线程调用：提交用户答案并唤醒工作线程。"""
        with self._question_lock:
            self._question_answer = answer
            if self._question_event is not None:
                self._question_event.set()

    # -- 线程体 ---------------------------------------------------------

    def run(self) -> None:  # noqa: D102 - QThread 接口
        try:
            if self._pass_helpers:
                result = self._task(
                    on_chunk=self.emit_chunk,
                    on_progress=self.emit_progress,
                    on_question=self.ask_question,
                    should_cancel=lambda: self._cancel_event.is_set(),
                )
            else:
                result = self._task()
        except ChatCancelled:
            self.cancelled.emit()
        except AIError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # noqa: BLE001 - 未预期异常也要让界面知道
            log.exception("后台任务失败: %s", self._label or self._task)
            self.failed.emit(f"发生未预期的错误：{exc}")
        else:
            if self._cancel_event.is_set():
                self.cancelled.emit()
            else:
                self.finished_ok.emit(result)
        finally:
            # 正常结束就从线程表里注销，别让退出流程白等它
            from gwp.core import threads as _threads

            _threads.unregister(self)


class SimpleWorker(QThread):
    """不涉及 AI 的后台任务（扫描目录、导入大量文件、导出 PDF）。"""

    progress = pyqtSignal(str, int, str)
    finished_ok = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, task: Callable[..., Any], parent: QObject | None = None, label: str = "") -> None:
        super().__init__(parent)
        self._task = task
        self._label = label
        self._cancel_event = threading.Event()
        from gwp.core import threads as _threads

        _threads.register(self)          # 退出时统一等待，见 core/threads.py

    def cancel(self) -> None:
        self._cancel_event.set()

    def emit_progress(self, message: str, percent: int = -1, detail: str = "") -> None:
        self.progress.emit(message, int(percent), detail)

    def run(self) -> None:
        try:
            result = self._task(
                on_progress=self.emit_progress,
                should_cancel=lambda: self._cancel_event.is_set(),
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("后台任务失败: %s", self._label)
            self.failed.emit(str(exc))
        else:
            self.finished_ok.emit(result)
        finally:
            from gwp.core import threads as _threads

            _threads.unregister(self)


def describe_error(exc: Exception) -> str:
    """把异常变成适合弹窗的中文说明。"""
    if isinstance(exc, AIConfigError):
        return str(exc)
    return str(exc) or exc.__class__.__name__


__all__ = ["AIWorker", "SimpleWorker", "describe_error"]
