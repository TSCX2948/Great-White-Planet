"""程序内图标：统一从"资源文件优先、内置绘制兜底"的规则取图。

优先级（想换成自己的图片时按这个顺序生效）：

1. ``config.json`` 的 ``ui.app_icon`` 指定的图片/ico；
2. ``gwp/resources/icons/planet.ico``；
3. ``gwp/resources/icons/planet.png``；
4. 都没有时，用代码画的内置"太白金星"图标（见 :mod:`gwp.resources.planet_icon`）。

换成真实图片的两种方式：

* 把图片另存为 ``gwp/resources/icons/planet.png``（或 .ico），重启软件；
* 或执行 ``python -m gwp.cli icon --image "你的图片.png"`` 自动转成 ico 并替换。
"""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap

from gwp.core.paths import resources_dir

log = logging.getLogger(__name__)

ICON_DIR_NAME = "icons"
ICO_NAME = "planet.ico"
PNG_NAME = "planet.png"

#: 快捷方式与窗口图标需要的分辨率档位
ICON_SIZES: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def icon_dir() -> Path:
    """图标目录。"""
    return resources_dir() / ICON_DIR_NAME


def candidate_files() -> list[Path]:
    """按优先级列出候选图标文件。"""
    directory = icon_dir()
    return [
        directory / ICO_NAME,
        directory / "app.ico",
        directory / PNG_NAME,
        directory / "app.png",
        resources_dir() / ICO_NAME,
        resources_dir() / PNG_NAME,
    ]


def resolve_icon_file(config=None) -> Path | None:
    """找出实际要用的图标文件；找不到返回 None。"""
    if config is not None:
        configured = str(config.get("ui.app_icon", "") or "").strip()
        if configured:
            candidate = Path(configured)
            if candidate.is_file():
                return candidate
            log.warning("配置的图标文件不存在，将使用内置图标：%s", configured)
    for candidate in candidate_files():
        if candidate.is_file():
            return candidate
    return None


def app_icon(config=None, color: str = "#4F7CFF", size: int = 256) -> QIcon:
    """取程序图标（窗口、任务栏、对话框都用它）。"""
    file = resolve_icon_file(config)
    if file is not None:
        icon = QIcon(str(file))
        if not icon.isNull():
            return icon
        log.warning("图标文件无法加载，改用内置图标：%s", file)
    return fallback_icon(color=color, size=size)


def fallback_icon(color: str = "#4F7CFF", size: int = 256) -> QIcon:
    """内置绘制的"太白金星"图标。"""
    try:
        from gwp.resources import planet_icon

        return QIcon(planet_icon.qt_pixmap(size=size))
    except Exception:  # noqa: BLE001 - 兜底失败时也不能让界面缺图
        log.exception("内置图标绘制失败，退回纯色方块")
        return _simple_icon(color, size)


def pixmap(config=None, size: int = 64) -> QPixmap:
    """取一张固定尺寸的 QPixmap（用于"关于"对话框等场合）。"""
    file = resolve_icon_file(config)
    if file is not None:
        loaded = QPixmap(str(file))
        if not loaded.isNull():
            return loaded.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
    try:
        from gwp.resources import planet_icon

        return planet_icon.qt_pixmap(size=size)
    except Exception:  # noqa: BLE001
        return app_icon(config, size=size).pixmap(size, size)


def ensure_builtin_icon(style: str | None = None, force: bool = False) -> Path:
    """生成内置图标文件（ico + png）。已存在且 force=False 时跳过。"""
    from gwp.resources import planet_icon

    style = style or planet_icon.DEFAULT_STYLE
    directory = icon_dir()
    directory.mkdir(parents=True, exist_ok=True)
    ico_path = directory / ICO_NAME
    png_path = directory / PNG_NAME
    if force or not ico_path.exists():
        planet_icon.save_ico(style, ico_path, ICON_SIZES)
        log.info("已生成图标：%s（风格 %s）", ico_path, style)
    if force or not png_path.exists():
        planet_icon.save_png(style, png_path, size=512)
        log.info("已生成图标：%s", png_path)
    return ico_path


def install_image(source: Path, style: str | None = None, size: int = 512) -> Path:
    """把一张外部图片安装成程序图标（转成多分辨率 ico + png）。

    图片会先被裁成正方形（居中裁切），再缩放到 512 并生成 ico。
    """
    from PIL import Image

    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(f"图片不存在：{source}")

    with Image.open(source) as original:
        image = original.convert("RGBA")
    # 居中裁成正方形，避免拉伸变形
    side = min(image.width, image.height)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    if image.width != size:
        image = image.resize((size, size), Image.LANCZOS)

    directory = icon_dir()
    directory.mkdir(parents=True, exist_ok=True)
    png_path = directory / PNG_NAME
    image.save(png_path, format="PNG")

    ico_path = directory / ICO_NAME
    ordered = sorted(ICON_SIZES)
    largest = ordered[-1]
    frames = {
        item: image.resize((item, item), Image.LANCZOS) for item in ordered if item != largest
    }
    image.save(
        ico_path,
        format="ICO",
        sizes=[(item, item) for item in ordered],
        append_images=[frames[item] for item in ordered if item != largest],
    )

    # 清掉可能存在的旧 app.ico/app.png，避免优先级混乱
    for stale in (directory / "app.ico", directory / "app.png"):
        if stale.exists():
            try:
                stale.unlink()
            except OSError:
                pass
    log.info("已安装自定义图标：%s", ico_path)
    return ico_path


def _simple_icon(color: str, size: int) -> QIcon:
    from PyQt6.QtGui import QColor, QPainter

    pixmap_ = QPixmap(size, size)
    pixmap_.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap_)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size * 0.22, size * 0.22)
    painter.end()
    return QIcon(pixmap_)


__all__ = [
    "ICON_DIR_NAME",
    "ICON_SIZES",
    "ICO_NAME",
    "PNG_NAME",
    "app_icon",
    "candidate_files",
    "ensure_builtin_icon",
    "fallback_icon",
    "icon_dir",
    "install_image",
    "pixmap",
    "resolve_icon_file",
]
