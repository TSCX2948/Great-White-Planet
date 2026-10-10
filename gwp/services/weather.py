"""日期 / 时间 / 天气：首页日程栏上方的信息条。

天气**不需要用户配置、也不需要 API Key**，走两个免费公开接口：

1. **定位**：按出口 IP 大致定位（``ipapi.co``，失败时退到 ``ip-api.com``）；
2. **天气**：`Open-Meteo <https://open-meteo.com/>`_ 的免费预报接口
   （按经纬度取当前温度、体感、湿度、风速、天气代码）。

定位接口返回的往往是英文城市名，所以再用 Open-Meteo 的**反向地理编码**换成
中文地名（``language=zh``），这样"地区"一行显示的是本地叫法。

设计取舍
--------

* **只用标准库**（``urllib``）—— 不为了一个天气条引入第三方依赖，
  也避免打包时多带一个库；
* **任何一步失败都不抛异常**，返回一个带 ``error`` 的对象，界面显示
  「天气获取失败」而不是崩掉或弹一堆错误框（断网是常态）；
* 本模块**不依赖 Qt**，方便单测（网络请求可注入）。
"""

from __future__ import annotations

import json
import logging
import socket
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

log = logging.getLogger(__name__)

#: 网络超时（秒）。天气是锦上添花，不能拖住启动
TIMEOUT = 4.0

#: 一次查询的总预算（秒）。3 个定位接口 + 搜索 + 天气，慢网络下要 ~20 秒，
#: 但超过这个预算就没必要再等了 —— 用户看到的是"天气获取失败"，不是转圈。
TOTAL_BUDGET = 12.0

#: 接口地址
#: 注意：Open-Meteo **没有** ``/v1/reverse`` 端点（实测 404），
#: 所以中文地名是用已知城市名去 ``/v1/search`` 换（``language=zh``）。
IP_API_PRIMARY = "https://ipapi.co/json/"
IP_API_FALLBACK = "http://ip-api.com/json/?fields=status,city,regionName,country,lat,lon"
IP_API_THIRD = "http://ipwho.is/"
FORECAST_API = "https://api.open-meteo.com/v1/forecast"
GEOCODE_SEARCH_API = "https://geocoding-api.open-meteo.com/v1/search"

_USER_AGENT = "GreatWhitePlanet/1.0 (desktop study app)"

#: WMO 天气代码 → 中文描述（Open-Meteo 用的就是这套）
WMO_TEXT = {
    0: "晴",
    1: "晴间多云",
    2: "多云",
    3: "阴",
    45: "有雾",
    48: "雾凇",
    51: "毛毛雨",
    53: "小雨",
    55: "中雨",
    56: "冻毛毛雨",
    57: "冻雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "冻雨",
    67: "强冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "米雪",
    80: "阵雨",
    81: "强阵雨",
    82: "暴雨",
    85: "阵雪",
    86: "强阵雪",
    95: "雷阵雨",
    96: "雷阵雨伴冰雹",
    99: "强雷暴伴冰雹",
}


def wmo_text(code: int | None) -> str:
    """把 WMO 天气代码翻成中文；未知代码返回「未知天气」。"""
    if code is None:
        return "未知天气"
    return WMO_TEXT.get(int(code), "未知天气")


def wind_direction(degrees: float | None) -> str:
    """角度 → 方位（八向）。"""
    if degrees is None:
        return ""
    names = ("北", "东北", "东", "东南", "南", "西南", "西", "西北")
    index = int((float(degrees) % 360) / 45 + 0.5) % 8
    return names[index]


@dataclass
class Weather:
    """一次天气查询的结果。"""

    ok: bool = False
    #: 地区（省市 / 国家）
    location: str = ""
    temperature: float | None = None
    feels_like: float | None = None
    humidity: int | None = None
    wind_speed: float | None = None
    wind_deg: float | None = None
    code: int | None = None
    #: 观测时间（接口给的是当地时间）
    observed_at: str = ""
    #: 失败原因（``ok=False`` 时非空）
    error: str = ""

    @property
    def text(self) -> str:
        return wmo_text(self.code)

    @property
    def summary(self) -> str:
        """一行摘要，例如 ``18°C 多云``。"""
        if not self.ok:
            return self.error or "天气获取失败"
        if self.temperature is None:
            return self.text
        return f"{round(self.temperature)}°C {self.text}"

    @property
    def detail(self) -> str:
        """鼠标悬停时显示的详细信息。"""
        if not self.ok:
            return self.error or "天气获取失败"
        parts: list[str] = []
        if self.location:
            parts.append(self.location)
        if self.temperature is not None:
            parts.append(f"温度 {round(self.temperature)}°C")
        if self.feels_like is not None:
            parts.append(f"体感 {round(self.feels_like)}°C")
        if self.humidity is not None:
            parts.append(f"湿度 {self.humidity}%")
        if self.wind_speed is not None:
            wind = f"风 {round(self.wind_speed)} km/h"
            direction = wind_direction(self.wind_deg)
            if direction:
                wind += f"（{direction}风）"
            parts.append(wind)
        if self.observed_at:
            parts.append(f"观测 {self.observed_at}")
        return "\n".join(parts) if parts else "无数据"


# --------------------------------------------------------------------------
# 网络
# --------------------------------------------------------------------------

def _get_json(
    url: str,
    timeout: float = TIMEOUT,
    cancelled=None,
    deadline: float | None = None,
) -> dict:
    """GET 一个 JSON 接口。

    * ``cancelled``：一个返回 True 就中止的回调。**这是让按钮/关窗能立刻生效的关键** ——
      ``QThread.quit()`` 对阻塞在 socket 上的 ``urlopen`` 无效，线程会一直挂到超时
      为止，进程退出时带线程析构 QThread 会直接段错误（实测崩过）。
      所以这里用短超时分片轮询，每片之间检查一次取消标志。
    * ``deadline``：``time.monotonic()`` 时间戳，到点抛 :class:`TimeoutError`。
    """
    import time

    def expired() -> bool:
        return deadline is not None and time.monotonic() >= deadline

    if expired():
        raise TimeoutError("已超过本次查询的时间预算")
    if cancelled is not None and cancelled():
        raise TimeoutError("已取消")

    request = Request(url, headers={"User-Agent": _USER_AGENT})
    slice_seconds = min(timeout, 0.4)
    started = time.monotonic()
    while True:
        if cancelled is not None and cancelled():
            raise TimeoutError("已取消")
        if expired():
            raise TimeoutError("已超过本次查询的时间预算")
        try:
            with urlopen(request, timeout=slice_seconds) as response:  # noqa: S310
                raw = response.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError(f"接口返回的不是对象：{url}")
            return data
        except (TimeoutError, socket.timeout):
            # 分片超时：可能是整体太慢，也可能只是这一片没读到 —— 看总预算
            if time.monotonic() - started >= timeout or expired():
                raise TimeoutError(f"请求超时：{url}") from None
            continue
        except URLError as exc:
            if isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)):
                if time.monotonic() - started >= timeout or expired():
                    raise TimeoutError(f"请求超时：{url}") from None
                continue
            raise


def locate(cancelled=None, deadline: float | None = None) -> tuple[float, float, str, str]:
    """按出口 IP 定位，返回 ``(纬度, 经度, 城市, 国家)``。

    三个免费接口依次尝试，任一成功即可；都失败就抛异常。
    用多个是因为实测 ``ipapi.co`` 会返回 403（数据中心 IP / 限流），
    不能只依赖一个。
    """
    errors: list[str] = []

    try:
        data = _get_json(IP_API_PRIMARY, cancelled=cancelled, deadline=deadline)
        if data.get("latitude") is not None:
            return (
                float(data["latitude"]),
                float(data["longitude"]),
                str(data.get("city") or ""),
                str(data.get("country_name") or data.get("country") or ""),
            )
        errors.append(f"ipapi.co: {data.get('reason') or '无坐标'}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"ipapi.co: {exc}")

    try:
        data = _get_json(IP_API_FALLBACK, cancelled=cancelled, deadline=deadline)
        if data.get("status") == "success" and data.get("lat") is not None:
            return (
                float(data["lat"]),
                float(data["lon"]),
                str(data.get("city") or ""),
                str(data.get("country") or ""),
            )
        errors.append(f"ip-api.com: {data.get('message') or '无坐标'}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"ip-api.com: {exc}")

    try:
        data = _get_json(IP_API_THIRD, cancelled=cancelled, deadline=deadline)
        if data.get("success") and data.get("latitude") is not None:
            return (
                float(data["latitude"]),
                float(data["longitude"]),
                str(data.get("city") or ""),
                str(data.get("country") or ""),
            )
        errors.append(f"ipwho.is: {data.get('message') or '无坐标'}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"ipwho.is: {exc}")

    raise RuntimeError("定位失败；" + "；".join(errors))


def localize_place(
    city: str,
    country: str = "",
    latitude: float | None = None,
    cancelled=None,
    deadline: float | None = None,
) -> str:
    """把英文城市名换成中文地名（``Beijing`` → ``中国 · 北京市``）。

    Open-Meteo 没有反向地理编码接口，所以这里是**用城市名去搜**，
    并在结果里挑离给定经纬度最近的那个。任何失败都返回空串（不致命）。
    """
    clean = (city or "").strip()
    if not clean:
        return ""
    try:
        query = urlencode({"name": clean, "language": "zh", "count": 5})
        data = _get_json(
            f"{GEOCODE_SEARCH_API}?{query}",
            cancelled=cancelled,
            deadline=deadline,
        )
        results = data.get("results")
        if not isinstance(results, list) or not results:
            return ""
        candidates = [r for r in results if isinstance(r, dict)]
        if not candidates:
            return ""
        if latitude is not None:
            def distance(item: dict) -> float:
                try:
                    return abs(float(item.get("latitude", 0)) - latitude)
                except (TypeError, ValueError):
                    return 1e9
            candidates.sort(key=distance)
        first = candidates[0]
        name = str(first.get("name") or "")
        admin = str(first.get("admin1") or "")
        origin = str(first.get("country") or country or "")
        # 中文结果里 admin1 常常是"北京市"、name 是"北京"（缩写），
        # 直接拼会得到「中国 · 北京市 · 北京」这种重复。短的那个被长的包含时丢掉。
        pieces: list[str] = []
        for piece in (origin, admin, name):
            if not piece:
                continue
            if any(piece in kept or kept in piece for kept in pieces):
                continue
            pieces.append(piece)
        return " · ".join(pieces)
    except Exception:  # noqa: BLE001 - 地名只是锦上添花
        log.debug("地名本地化失败", exc_info=True)
        return ""


def fetch_weather(
    latitude: float,
    longitude: float,
    location: str = "",
    cancelled=None,
    deadline: float | None = None,
) -> Weather:
    """按经纬度取当前天气。"""
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,"
                       "weather_code,wind_speed_10m,wind_direction_10m",
            "timezone": "auto",
        }
    )
    data = _get_json(
        f"{FORECAST_API}?{query}", cancelled=cancelled, deadline=deadline
    )
    current = data.get("current")
    if not isinstance(current, dict):
        raise RuntimeError("天气接口没有返回 current 字段")

    def number(key: str):
        value = current.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    humidity = number("relative_humidity_2m")
    return Weather(
        ok=True,
        location=location,
        temperature=number("temperature_2m"),
        feels_like=number("apparent_temperature"),
        humidity=int(humidity) if humidity is not None else None,
        wind_speed=number("wind_speed_10m"),
        wind_deg=number("wind_direction_10m"),
        code=int(current["weather_code"]) if current.get("weather_code") is not None else None,
        observed_at=str(current.get("time") or "").replace("T", " "),
    )


def query_weather(cancelled=None) -> Weather:
    """完整流程：定位 → 中文地名 → 天气。**任何失败都返回 ok=False 的对象。**"""
    deadline = time.monotonic() + TOTAL_BUDGET
    try:
        latitude, longitude, city, country = locate(cancelled, deadline)
    except Exception as exc:  # noqa: BLE001
        if cancelled is not None and cancelled():
            # 用户关窗/取消，不是"没联网"，别误导
            return Weather(ok=False, error="已取消")
        log.info("天气定位失败：%s", exc)
        return Weather(ok=False, error="无法定位（可能没联网）")

    place = localize_place(city, country, latitude, cancelled, deadline)
    if not place:
        place = " · ".join(p for p in (country, city) if p)

    try:
        weather = fetch_weather(latitude, longitude, place, cancelled, deadline)
    except (URLError, socket.timeout, TimeoutError):
        return Weather(ok=False, location=place, error="天气获取失败（网络不可用）")
    except Exception as exc:  # noqa: BLE001
        log.info("天气获取失败：%s", exc)
        return Weather(ok=False, location=place, error="天气获取失败")
    return weather


# --------------------------------------------------------------------------
# 日期与时间（本地，不联网）
# --------------------------------------------------------------------------

_WEEKDAYS = ("星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日")


def date_text(moment: datetime | None = None) -> str:
    """``2026年10月9日 星期五``。"""
    now = moment or datetime.now()
    return f"{now.year}年{now.month}月{now.day}日 {_WEEKDAYS[now.weekday()]}"


def time_text(moment: datetime | None = None, with_seconds: bool = True) -> str:
    """``16:39:36``（``with_seconds=False`` 时是 ``16:39``）。"""
    now = moment or datetime.now()
    return now.strftime("%H:%M:%S" if with_seconds else "%H:%M")


__all__ = [
    "TIMEOUT",
    "WMO_TEXT",
    "Weather",
    "date_text",
    "fetch_weather",
    "localize_place",
    "locate",
    "query_weather",
    "time_text",
    "wind_direction",
    "wmo_text",
]
