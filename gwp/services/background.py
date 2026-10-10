"""主界面背景图管理。

规则（对应需求）：

* 图片统一放在 ``else data/background``，该目录就是"背景图库"；
* 更换背景时把**新图片复制进来**，旧图片**保留**，因此可以随时切回去；
* 文件名只改"后半部分的数字"：``桌面.png`` → ``桌面_1.png`` → ``桌面_2.png``，
  第二次导入同一个文件不会覆盖，也不会变成 ``桌面_1_1.png``；
* 当前生效的是哪一张记录在 ``config.json`` 的 ``ui.background_image``（相对路径）。

之所以把"当前用哪张"放在配置里而不是靠文件名排序，是为了保证
"换背景、重启、再换回来"的行为完全可预期。
"""

from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from gwp.core import constants as C
from gwp.core.config import Config
from gwp.core.paths import DataPaths, current as current_paths

log = logging.getLogger(__name__)

#: 目录名（位于 else data 下）
BACKGROUND_DIR_NAME = "background"

_IMAGE_EXTENSIONS = tuple(sorted(C.COVER_EXTENSIONS | {".webp", ".bmp", ".jpeg"}))

#: 末尾的 ``_数字``，用于实现"只改后半部分数字"
_TRAILING_NUMBER = re.compile(r"_(\d+)$")
#: 拆出"主名 + 序号"用于自然排序：``桌面_10`` 排在 ``桌面_9`` 之后
_SORT_KEY = re.compile(r"^(?P<name>.*?)_(?P<index>\d+)$")


@dataclass
class BackgroundEntry:
    """背景图库中的一个条目。"""

    path: Path
    name: str
    size: int
    mtime: float
    is_current: bool = False

    @property
    def size_label(self) -> str:
        size = float(self.size)
        for unit in ("B", "KB", "MB"):
            if size < 1024 or unit == "MB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} MB"


def sort_key(path: Path) -> tuple:
    """自然排序：同主名按序号排，序号按数值比较（``_10`` 在 ``_9`` 之后）。"""
    stem = path.stem
    match = _SORT_KEY.match(stem)
    if match:
        return (match.group("name").lower(), int(match.group("index")), stem.lower())
    return (stem.lower(), -1, stem.lower())


class BackgroundManager:
    """背景图库的读写。"""

    def __init__(self, config: Config | None = None, paths: DataPaths | None = None) -> None:
        self.config = config or Config.load()
        self.paths = paths or current_paths()

    # ------------------------------------------------------------------
    # 位置
    # ------------------------------------------------------------------

    @property
    def directory(self) -> Path:
        return self.paths.else_data / BACKGROUND_DIR_NAME

    def ensure_directory(self) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        return self.directory

    def _resolve(self, stored: str) -> Path | None:
        """把配置里记录的路径解析成真实文件。"""
        value = (stored or "").strip()
        if not value:
            return None
        candidate = Path(value)
        # 先按"相对 background 目录"理解（默认存法）
        if not candidate.is_absolute():
            relative = self.directory / candidate
            if relative.is_file():
                return relative
        if candidate.is_file():
            return candidate
        return None

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------

    @property
    def current_stored(self) -> str:
        return str(self.config.get("ui.background_image", "") or "").strip()

    def current_path(self) -> Path | None:
        """当前背景图的绝对路径；没有设置或文件已丢失时返回 None。"""
        resolved = self._resolve(self.current_stored)
        if resolved is None and self.current_stored:
            log.warning("配置的背景图不存在，已忽略：%s", self.current_stored)
        return resolved

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("ui.background_enabled", True)) and self.current_path() is not None

    def entries(self) -> list[BackgroundEntry]:
        """列出图库里的所有图片（当前使用的那张会标记出来）。"""
        if not self.directory.is_dir():
            return []
        current = self.current_path()
        result: list[BackgroundEntry] = []
        for path in self.directory.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in _IMAGE_EXTENSIONS:
                continue
            try:
                stat = path.stat()
            except OSError:
                continue
            result.append(
                BackgroundEntry(
                    path=path,
                    name=path.name,
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                    is_current=bool(current is not None and path == current),
                )
            )
        result.sort(key=lambda item: sort_key(item.path))
        return result

    # ------------------------------------------------------------------
    # 写入
    # ------------------------------------------------------------------

    def unique_target(self, source: Path) -> Path:
        """为新背景图算出「只改后半部分数字」的目标文件名。

        规则（``桌面.png`` 为例）：

        * 图库里没有同名文件 -> ``桌面.png``；
        * 已存在 -> ``桌面_1.png``、``桌面_2.png`` …依此类推；
        * 已经带序号（``桌面_1.png``）时，以**去掉序号的主名**为基准继续递增，
          因此第二次导入 ``桌面.png`` 得到 ``桌面_2.png``，而不是 ``桌面_1_1.png``。
        """
        self.ensure_directory()
        stem = source.stem or "background"
        suffix = source.suffix.lower() or ".png"

        match = _TRAILING_NUMBER.search(stem)
        base = stem[: match.start()] if match else stem
        base = base or "background"

        target = self.directory / f"{base}{suffix}"
        if not target.exists():
            return target
        for index in range(1, 10000):
            candidate = self.directory / f"{base}_{index}{suffix}"
            if not candidate.exists():
                return candidate
        raise OSError(f"无法为 {source.name} 生成唯一的背景文件名")

    def add(self, source: Path, make_current: bool = True) -> Path:
        """把一张图片加入图库（复制，不删除原图，也不删除旧背景）。

        返回图库中的新文件路径。
        """
        source = Path(source)
        if not source.is_file():
            raise FileNotFoundError(f"图片不存在：{source}")
        if source.suffix.lower() not in _IMAGE_EXTENSIONS:
            raise ValueError(
                "仅支持以下图片格式：" + "、".join(ext.lstrip(".") for ext in _IMAGE_EXTENSIONS)
            )

        # 已经在图库里就直接用，避免重复复制
        try:
            if source.parent.resolve() == self.directory.resolve():
                target = source
            else:
                target = self.unique_target(source)
        except OSError:
            target = self.unique_target(source)

        if target != source:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            log.info("已导入背景图：%s", target)

        if make_current:
            self.set_current(target)
        return target

    def set_current(self, target: Path) -> None:
        """把某张图设为当前背景（写进配置）。"""
        target = Path(target)
        try:
            stored = target.relative_to(self.directory).as_posix()
        except ValueError:
            stored = str(target)
        self.config.set("ui.background_image", stored)
        self.config.set("ui.background_enabled", True)
        self.config.save()

    def clear(self) -> None:
        """不再使用背景图（图片文件保留在图库里）。"""
        self.config.set("ui.background_image", "")
        self.config.save()

    def remove(self, target: Path, delete_file: bool = True) -> None:
        """从图库移除一张图；若它正是当前背景，则同时取消背景。"""
        target = Path(target)
        current = self.current_path()
        if current is not None and target == current:
            self.clear()
        if delete_file:
            try:
                target.unlink()
            except OSError:
                log.exception("删除背景图失败：%s", target)


def _qss_url(value: str) -> str:
    """把路径转成 QSS 里可用的 ``url(...)`` 写法。"""
    text = str(value).replace("\\", "/")
    return f'"{text}"'


def resolve_background(
    config: Config | None = None, paths: DataPaths | None = None
) -> tuple[Path | None, str, float, tuple[int, int, int]]:
    """一次性取出绘制背景需要的全部参数。

    返回 ``(图片路径, 填充方式, 蒙层不透明度, 蒙层颜色)``；
    没有可用背景时图片路径为 ``None``。

    背景由 :class:`~gwp.ui.widgets.background_area.BackgroundImageWidget` 自绘，
    不走 QSS —— 因为实测 QSS 的 ``background-image`` 在存在
    ``QMainWindow`` 背景规则时**完全不绘制**（详见该控件的说明）。
    """
    manager = BackgroundManager(config, paths)
    if not manager.enabled:
        return None, "cover", 0.0, (0, 0, 0)
    image = manager.current_path()
    if image is None:
        return None, "cover", 0.0, (0, 0, 0)

    fit = str(manager.config.get("ui.background_fit", "cover") or "cover").lower()
    if fit not in ("cover", "contain", "stretch", "center"):
        fit = "cover"
    try:
        overlay = float(manager.config.get("ui.background_overlay", 0.0) or 0.0)
    except (TypeError, ValueError):
        overlay = 0.0
    overlay = max(0.0, min(0.9, overlay))

    theme = str(manager.config.get("ui.theme", "light") or "light").lower()
    # 蒙层用黑色压暗；深色主题下也用黑（更沉），保持简单可预期
    return image, fit, overlay, (0, 0, 0) if theme != "dark" else (0, 0, 0)


def background_qss(config: Config | None = None, paths: DataPaths | None = None) -> str:
    """生成主界面背景相关的样式表片段；没有可用背景图时返回空串。

    **这里不画背景图**（图由控件自绘）。这里只负责：
    把中间的容器设成透明，让自绘的背景透出来；以及给标题栏加一层半透明织带，
    保证标题/搜索框压在任何壁纸上都看得清。
    """
    manager = BackgroundManager(config, paths)
    if not manager.enabled or manager.current_path() is None:
        return ""

    return f"""
/* 背景图由 BackgroundImageWidget 自绘；这里只清掉"页面容器"的底色，让背景透出来。

   三个踩过的坑，都写在这里避免以后再犯：
   1. 必须显式列出 QStackedWidget —— 基础样式表给它带了不透明底色，
      漏掉就会出现"只有最外一条缝能看到背景，中间一片纯色"；
   2. **只能按名字锁定顶层页面栈**（MainPageStack），不能用笼统的
      ``QStackedWidget > QWidget``：QTabWidget 内部也有一个 QStackedWidget
      （qt_tabwidget_stackedwidget），文件表格正是它的直接子控件，
      笼统选择器会把表格也清成透明 -> 文字压在壁纸上直接看不清；
   3. 不能用后代选择器（``... QWidget``）：它带 ID 前缀，优先级高于基础样式表的
      ``QTableWidget {{...}}``，同样会把表格清成透明。
   因此下面只点名 MainPageStack，并且不碰表格/列表的任何 background。 */
QWidget#MainBackgroundArea,
QWidget#MainBackgroundArea QWidget#MainContentArea,
QWidget#MainBackgroundArea QStackedWidget#MainPageStack,
QWidget#MainBackgroundArea QStackedWidget#MainPageStack > QWidget,
QWidget#MainBackgroundArea QSplitter,
QWidget#MainBackgroundArea QSplitter > QWidget {{
  background: transparent;
}}
/* 滚动区域的 viewport 是独立一层：QSS 里选 QScrollArea 管不到它，
   首页科目网格那片浅灰就是这么来的。必须点名 viewport 及其内容容器。 */
QWidget#MainBackgroundArea QScrollArea,
QWidget#MainBackgroundArea QScrollArea > QWidget,
QWidget#MainBackgroundArea QScrollArea > QWidget > QWidget {{
  background: transparent;
}}
/* 标签栏是"文字直接贴着的一层"，必须保留底色（默认的 tab 是透明的） */
QWidget#MainBackgroundArea QTabBar {{
  background: {_surface_color(manager.config)};
  border-radius: 10px;
}}
QWidget#MainBackgroundArea QTabBar::tab:!selected {{
  background: {_surface_alt_color(manager.config)};
}}
/* 标题栏加一层半透明织带，保证"我的科目/搜索框"压在壁纸上也看得清 */
QWidget#MainBackgroundArea QWidget#HeaderBar {{
  background: {_header_color(manager.config)};
  border-radius: 10px;
}}
"""


def _palette(config: Config) -> dict:
    """取当前主题的配色（避免为几个颜色把 themes 整个导进来）。"""
    from gwp.services.themes import palette

    try:
        return palette(str(config.get("ui.theme", "light") or "light"))
    except Exception:  # noqa: BLE001 - 配色异常时退回浅色
        return palette("light")


def _surface_color(config: Config) -> str:
    return str(_palette(config).get("surface", "#FFFFFF"))


def _surface_alt_color(config: Config) -> str:
    return str(_palette(config).get("surface_alt", "#F4F6FB"))


def _header_color(config: Config) -> str:
    """标题栏织带的颜色：浅色主题用半透明白，深色主题用半透明黑。"""
    theme = str(config.get("ui.theme", "light") or "light").lower()
    return "rgba(255, 255, 255, 0.86)" if theme != "dark" else "rgba(24, 28, 36, 0.86)"


def content_margins(config: Config | None = None, paths: DataPaths | None = None) -> int:
    """内容区四周留边。

    默认 0（背景直接铺满工作区）。保留这个开关是为了以后想做"背景当外框"的
    样式时不用改布局代码。
    """
    manager = BackgroundManager(config, paths)
    if not manager.enabled:
        return 0
    try:
        return max(0, min(60, int(manager.config.get("ui.background_margin", 0) or 0)))
    except (TypeError, ValueError):
        return 0


__all__ = [
    "BACKGROUND_DIR_NAME",
    "BackgroundEntry",
    "BackgroundManager",
    "background_qss",
    "content_margins",
    "sort_key",
]
