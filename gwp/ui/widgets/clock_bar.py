"""日程栏上方的信息条：日期 · 星期 · 时间 · 天气（含地区）。

* **日期与时间**：本地计算，**立刻显示**，每秒走一次（不联网）；
* **天气**：后台线程拉一次（需求：只在启动时拉一次），拿到再填上。
  没拿到就显示「天气获取失败」，鼠标悬停看原因。

为什么天气必须放线程里：这些免费接口在慢网络下要 ~20 秒才回来。
放主线程会把整个界面卡住 —— 而它只是锦上添花的信息。
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QEvent, QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from gwp.services import weather as W

log = logging.getLogger(__name__)

#: 等待超时后"挂起"的天气线程。
#:
#: 为什么需要它：这些免费接口在慢网络下要 ~20 秒才返回，而 ``QThread.wait()``
#: 只能等有限的几秒。如果超时后就把 QThread 对象丢掉，Qt 会在它**还在跑**的时候
#: 析构它并打印 ``QThread: Destroyed while thread is still running``。
#: 所以把引用留在模块级集合里，等线程自己结束后再移除 —— 进程退出时它自然收尾。
_DETACHED: set["WeatherWorker"] = set()


class WeatherWorker(QThread):
    """后台拉一次天气。

    支持**取消**：正在抓取时 ``cancel()`` 会让下一次分片检查时就中止请求，
    而不是干等到超时。这一点很关键 —— ``QThread.quit()`` 对阻塞在 socket 上的
    ``urlopen`` 是无效的，线程会一直挂着；如果在它还在跑的时候析构 QThread，
    Qt 会打印警告，进程退出时甚至直接段错误（实测崩过）。
    """

    fetched = pyqtSignal(object)          # W.Weather

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cancelled = False
        # 同时登记到全局线程表（core/threads.py）：
        # 本类自己的 _DETACHED 保活表只管"别被回收"，
        # 而退出时"所有线程都要等完"这件事由全局表统一负责 ——
        # 否则漏掉一个就又是一次随机闪退。
        from gwp.core import threads as _threads

        _threads.register(self)

    def cancel(self) -> None:
        self._cancelled = True

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:                # noqa: D102 - QThread 约定
        try:
            result = W.query_weather(cancelled=lambda: self._cancelled)
        except Exception as exc:  # noqa: BLE001 - 后台线程不能把异常抛出去
            log.warning("天气线程异常：%s", exc)
            result = W.Weather(ok=False, error="天气获取失败")
        finally:
            from gwp.core import threads as _threads

            _threads.unregister(self)
        if self._cancelled:
            return                        # 已取消：不往界面发结果
        self.fetched.emit(result)


class ClockWeatherBar(QFrame):
    """日期 / 时间 / 天气 信息条。"""

    def __init__(self, parent: QWidget | None = None, *, auto_fetch: bool = True) -> None:
        super().__init__(parent)
        self.setObjectName("ClockBar")
        self._weather_enabled = bool(auto_fetch)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        # ---- 第一行：日期 + 星期，右侧时间 ----
        top = QHBoxLayout()
        top.setSpacing(8)
        self.lbl_date = QLabel("")
        self.lbl_date.setObjectName("ClockDate")
        top.addWidget(self.lbl_date)
        top.addStretch(1)
        self.lbl_time = QLabel("")
        self.lbl_time.setObjectName("ClockTime")
        top.addWidget(self.lbl_time)
        layout.addLayout(top)

        # ---- 第二行：地区 + 天气 ----
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self.lbl_place = QLabel("定位中…")
        self.lbl_place.setObjectName("Muted")
        bottom.addWidget(self.lbl_place)
        bottom.addStretch(1)
        self.lbl_weather = QLabel("天气获取中…")
        self.lbl_weather.setObjectName("ClockWeather")
        bottom.addWidget(self.lbl_weather)
        layout.addLayout(bottom)

        self._worker: WeatherWorker | None = None
        self._weather: W.Weather | None = None

        # 时间每秒走一次
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        self._tick()

        if auto_fetch:
            self.start_fetch()

    # ------------------------------------------------------------------

    def _tick(self) -> None:
        self.lbl_date.setText(W.date_text())
        self.lbl_time.setText(W.time_text())

    def start_fetch(self) -> None:
        """拉一次天气（后台）。重复调用会忽略正在跑的那次。"""
        if not self._weather_enabled:
            self.lbl_weather.setText("天气已关闭")
            self.lbl_weather.setToolTip("在「设置 → 界面」里打开「显示天气」即可恢复")
            self.lbl_place.setVisible(False)
            return
        if self._worker is not None:
            if self._worker.isRunning():
                return
            # 已经结束但 finished 还没派发到主线程：等它走完清理再起新的，
            # 否则新旧两个 worker 会互相覆盖引用。
            self._worker.cancel()
            self._worker.wait(500)
            self._worker = None
        self.lbl_weather.setText("天气获取中…")
        self.lbl_place.setText("定位中…")
        self.lbl_place.setVisible(True)
        worker = WeatherWorker(self)
        worker.fetched.connect(self._on_fetched)
        worker.finished.connect(self._on_finished)
        self._worker = worker
        worker.start()

    def set_weather_enabled(self, enabled: bool) -> None:
        """开关天气（不显示日期时间条本身，只控制联网取天气）。"""
        enabled = bool(enabled)
        if enabled == self._weather_enabled:
            return
        self._weather_enabled = enabled
        if not enabled:
            self.stop()
            self.lbl_weather.setText("天气已关闭")
            self.lbl_weather.setToolTip("在设置里打开「显示天气」即可恢复")
            self.lbl_place.setVisible(False)
        else:
            self.lbl_place.setVisible(True)
            self.start_fetch()

    def _on_fetched(self, result: object) -> None:
        if not isinstance(result, W.Weather):
            return
        self._weather = result
        self.lbl_place.setText(result.location or ("地区未知" if not result.ok else ""))
        self.lbl_place.setVisible(bool(result.location))
        self.lbl_weather.setText(result.summary)
        self.lbl_weather.setToolTip(result.detail)
        self.lbl_place.setToolTip(result.detail)
        self.lbl_weather.setProperty("weatherFailed", not result.ok)
        # 失败态用灰色，别把"没联网"渲染成刺眼的错误
        self.lbl_weather.setStyleSheet(
            "" if result.ok else "color: #8A8F98;"
        )

    def _on_finished(self) -> None:
        """线程结束。

        只清理**自己那个** worker：旧线程结束时不能把新线程的引用抹掉，
        否则 ``start_fetch`` 会以为没有线程在跑，从而重复起线程；
        更糟的是 ``stop`` 会找不到真正在跑的那个。
        """
        sender = self.sender()
        if sender is self._worker:
            self._worker = None
        if sender is not None:
            sender.deleteLater()

    def stop(self, *, force: bool = False) -> None:
        """停掉定时器与天气线程。

        除了 ``MainWindow.closeEvent``，**控件被销毁时也必须调用** ——
        否则 QThread 会在还在跑的时候被析构，Qt 会打印
        ``QThread: Destroyed while thread is still running``。

        ``force=True``（测试用）会一直等到线程真的结束；正常退出时只等 1.5 秒，
        不为了一个天气条让软件关不上。
        """
        self._timer.stop()
        worker = self._worker
        self._worker = None
        if worker is None:
            return
        # 先取消：让请求在下一个分片检查时自己退出（通常 0.4 秒内）
        worker.cancel()
        worker.quit()
        # 注意：PyQt6 的 QThread.wait(-1) 会 OverflowError（无符号整数），
        # 所以"无限等"用一个足够大的毫秒数。
        timeout = 30_000 if force else 3000
        if worker.wait(timeout):
            return
        # 极慢网络下还没回来：别丢引用，交给保活表，等它自己结束。
        # 请求总预算只有 TOTAL_BUDGET 秒，所以它一定会结束。
        log.debug("天气线程仍未结束，转入保活等待")
        worker.setParent(None)
        _DETACHED.add(worker)
        worker.finished.connect(lambda w=worker: _DETACHED.discard(w))

    def event(self, event) -> bool:  # noqa: N802 - Qt 接口
        """销毁前停掉线程，避免 QThread 带线程析构。

        注意：Qt6 里**没有** ``QEvent.Type.Destroy``（PyQt6 会抛 AttributeError），
        所以这里只挂 ``Close`` / ``DeferredDelete``；正常退出由
        ``MainWindow.closeEvent`` 调 :meth:`stop` 兜住。
        """
        if event.type() in (QEvent.Type.Close, QEvent.Type.DeferredDelete):
            self.stop()
        return super().event(event)

    # -- 便于测试 ------------------------------------------------------

    @property
    def weather(self) -> W.Weather | None:
        return self._weather

    def apply_weather(self, result: W.Weather) -> None:
        """直接设置天气结果（测试用，跳过网络）。"""
        self._on_fetched(result)


__all__ = ["ClockWeatherBar", "WeatherWorker"]
