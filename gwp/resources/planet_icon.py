"""内置"太白金星"图标的绘制（纯 Pillow + numpy，不依赖 Qt）。

为什么用程序画而不是直接放一张图：
* ico 需要 16～256 像素共 10 档分辨率，程序画可以逐档单独优化微缩细节；
* 不引入版权不明的图片；
* 以后想换成真实照片，只要把图片放进 ``resources/icons`` 或指定 ``ui.app_icon``，
  代码会自动优先使用文件（见 :mod:`gwp.resources.app_icon`）。

设计取向：太白金星即金星，中国古称"启明/长庚"，是天上最亮的星。
因此图标用**暖白金色的行星本体**，带柔和的云带与光晕，在深色背景上像一颗亮星。
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

# --------------------------------------------------------------------------
# 配色
#
# 太白金星即金星：中国古称"启明/长庚"，《史记》说它"色白"，所以主色取**暖白**，
# 只在暗部与临边带一点金铜色。深空底色用偏蓝的黑，让白金色更亮。
# --------------------------------------------------------------------------

CORE_LIGHT = (255, 254, 250)
CORE_MID = (247, 240, 219)
TERMINATOR = (196, 168, 118)
DEEP = (104, 80, 44)
GLOW = (255, 232, 178)
SPACE_TOP = (24, 32, 52)
SPACE_BOTTOM = (9, 12, 22)
STAR = (255, 255, 255)

#: 可选的图标风格
STYLES = ("badge", "sphere_clouds", "bright_star", "crescent", "ringed", "radiant")

#: 默认风格：圆角底板 + 太白金星 + 轨道 + 启明星亮点，微缩到 16px 仍清晰
DEFAULT_STYLE = "badge"


# --------------------------------------------------------------------------
# 小工具
# --------------------------------------------------------------------------

def _grid(size: float) -> tuple[np.ndarray, np.ndarray]:
    """返回中心坐标系下的 (x, y)，范围约 [-1, 1]。"""
    axis = (np.arange(int(size)) + 0.5) / size * 2.0 - 1.0
    x, y = np.meshgrid(axis, axis)
    return x, y


def _alpha_composite(base: Image.Image, layer: Image.Image) -> Image.Image:
    return Image.alpha_composite(base.convert("RGBA"), layer.convert("RGBA"))


def _to_image(rgb: np.ndarray, alpha: np.ndarray) -> Image.Image:
    data = np.dstack([np.clip(rgb, 0, 255), np.clip(alpha * 255.0, 0, 255)]).astype(np.uint8)
    return Image.fromarray(data, mode="RGBA")


def _starfield(rgb: np.ndarray, alpha: np.ndarray, size: float, seed: int = 7) -> None:
    """在背景上撒一层小星点（按比例定位，缩小时自动减量）。"""
    rng = np.random.default_rng(seed)
    count = int(np.clip(size / 6, 8, 46))
    for _ in range(count):
        cx = rng.uniform(0.06, 0.94) * size
        cy = rng.uniform(0.06, 0.94) * size
        radius = max(0.5, rng.uniform(0.6, 1.5) * size / 128.0)
        brightness = rng.uniform(0.35, 0.95)
        y0, y1 = int(max(0, cy - radius - 1)), int(min(size, cy + radius + 2))
        x0, x1 = int(max(0, cx - radius - 1)), int(min(size, cx + radius + 2))
        if y1 <= y0 or x1 <= x0:
            continue
        ys, xs = np.mgrid[y0:y1, x0:x1]
        dist = np.sqrt((xs + 0.5 - cx) ** 2 + (ys + 0.5 - cy) ** 2)
        falloff = np.clip(1.0 - dist / (radius * 2.4), 0.0, 1.0) ** 2
        mask = falloff * brightness
        for channel in range(3):
            region = rgb[y0:y1, x0:x1, channel]
            rgb[y0:y1, x0:x1, channel] = region * (1 - mask) + STAR[channel] * mask
        alpha[y0:y1, x0:x1] = np.clip(alpha[y0:y1, x0:x1] + mask * 0.9, 0, 1)


def _glow_layer(size: float, radius: float, intensity: float = 1.0) -> Image.Image:
    """给行星加一圈柔光（用高斯模糊做，比手写衰减更好看）。"""
    canvas = Image.new("RGBA", (int(size), int(size)), (0, 0, 0, 0))
    x, y = _grid(size)
    distance = np.sqrt(x * x + y * y)
    core = np.clip(1.0 - distance / radius, 0.0, 1.0) ** 2.2
    rgba = np.zeros((int(size), int(size), 4), dtype=np.float32)
    rgba[..., 0] = GLOW[0]
    rgba[..., 1] = GLOW[1]
    rgba[..., 2] = GLOW[2]
    rgba[..., 3] = core * 255.0 * intensity
    canvas = Image.fromarray(rgba.astype(np.uint8), mode="RGBA")
    return canvas.filter(ImageFilter.GaussianBlur(radius=size * 0.05))


def _rounded_square(size: float, radius_ratio: float = 0.24) -> Image.Image:
    """圆角方形遮罩（让图标像应用图标而不是裸圆）。"""
    x, y = _grid(size)
    half = 1.0 - radius_ratio
    dx = np.clip(np.abs(x) - half, 0, None)
    dy = np.clip(np.abs(y) - half, 0, None)
    distance = np.sqrt(dx * dx + dy * dy)
    mask = np.clip(1.0 - distance / radius_ratio, 0.0, 1.0)
    alpha = (mask * 255).astype(np.uint8)
    rgba = np.zeros((int(size), int(size), 4), dtype=np.uint8)
    rgba[..., 3] = alpha
    return Image.fromarray(rgba, mode="RGBA")


# --------------------------------------------------------------------------
# 各种风格
# --------------------------------------------------------------------------

def _render_sphere(
    size: float,
    *,
    bands: bool = True,
    ring: bool = False,
    crescent: bool = False,
    planet_scale: float = 1.0,
) -> Image.Image:
    x, y = _grid(size)
    distance = np.sqrt(x * x + y * y)
    # 小尺寸时把行星画大一点，否则 16px 下只剩一个灰点
    planet_radius = 0.66 * planet_scale
    # 3D 球面法线（z 为朝向观察者的分量）
    rho = np.clip(distance / planet_radius, 0, 1)
    z = np.sqrt(np.clip(1.0 - rho * rho, 0, 1))

    rgb = np.zeros((int(size), int(size), 3), dtype=np.float32)
    alpha = np.zeros((int(size), int(size)), dtype=np.float32)

    # 背景：深空渐变 + 星点
    gradient = np.clip((y + 1.0) / 2.0, 0, 1)
    for channel in range(3):
        rgb[..., channel] = (
            SPACE_TOP[channel] * (1 - gradient) + SPACE_BOTTOM[channel] * gradient
        )
    alpha[:] = 1.0
    _starfield(rgb, alpha, size)

    # 行星本体：明暗由光照方向决定（光来自右上方）
    light = np.array([0.55, -0.6, 0.58])
    light = light / np.linalg.norm(light)
    normal_x = np.clip(x / planet_radius, -1, 1)
    normal_y = np.clip(y / planet_radius, -1, 1)
    lambert = np.clip(normal_x * light[0] + normal_y * light[1] + z * light[2], 0.0, 1.0)

    if crescent:
        lambert = np.clip(lambert - 0.42, 0.0, 1.0) / 0.58

    shade = np.clip(0.18 + 0.92 * lambert, 0.0, 1.2)
    for channel in range(3):
        base = CORE_MID[channel] * shade + CORE_LIGHT[channel] * np.clip(lambert - 0.55, 0, 1) * 0.7
        rgb[..., channel] = np.where(
            distance <= planet_radius,
            base,
            rgb[..., channel],
        )

    # 云带（金星标志性特征）：把球面纬度映射成正弦带，小尺寸也要看得见
    if bands:
        latitude = np.arcsin(np.clip(normal_y, -1, 1)) / (math.pi / 2)
        band = np.sin(latitude * 5.1 + 0.6) * 0.5 + np.sin(latitude * 11.3 - 1.2) * 0.22
        strength = 0.20 if size < 32 else 0.16
        band_strength = np.clip(band, -1, 1) * strength * np.clip(z, 0, 1) ** 0.6
        # 带纹随经度有轻微起伏，看起来更像云
        band_strength *= 0.65 + 0.35 * np.cos(np.clip(normal_x, -1, 1) * 4.0)
        # 极区稍亮（金星有明亮的极区云盖）
        polar = np.clip(np.abs(latitude) - 0.62, 0, 1) / 0.38 * 0.14
        for channel in range(3):
            tone = 255 if channel == 0 else (240 if channel == 1 else 212)
            target = tone
            blended = rgb[..., channel] + band_strength * (target - rgb[..., channel]) * 0.6
            blended = blended + polar * (255 - blended) * 0.5
            rgb[..., channel] = np.where(distance <= planet_radius, blended, rgb[..., channel])

    # 边缘压暗 + 大气亮边
    limb = np.clip((distance - planet_radius * 0.82) / (planet_radius * 0.18), 0, 1)
    for channel in range(3):
        dark = DEEP[channel] * limb * 0.45
        rgb[..., channel] = np.where(distance <= planet_radius, rgb[..., channel] - dark, rgb[..., channel])
    rim = np.clip(1.0 - np.abs(distance - planet_radius * 1.02) / (planet_radius * 0.1), 0, 1)
    rim = rim * np.clip(lambert * 1.3, 0, 1)
    for channel in range(3):
        tone = (255, 236, 190)[channel]
        rgb[..., channel] = np.where(
            distance <= planet_radius * 1.12,
            np.clip(rgb[..., channel] + rim * (tone - rgb[..., channel]) * 0.8, 0, 255),
            rgb[..., channel],
        )

    # 球体之外的柔光
    halo = np.clip(1.0 - np.abs(distance - planet_radius) / (planet_radius * 0.9), 0, 1) ** 2
    halo = np.where(distance > planet_radius, halo * 0.5, 0)
    for channel in range(3):
        rgb[..., channel] = np.clip(rgb[..., channel] + halo * GLOW[channel] * 0.35, 0, 255)

    image = _to_image(rgb, alpha)

    # 光环（可选）：后半圈藏在球后，只有前半圈压在球上。
    # 注意这里的椭圆必须真绕球心做投影，否则会像"斜着切开行星"。
    if ring:
        radius = planet_radius * 1.62
        thickness = 0.045                      # 环的宽度（相对行星半径）
        tilt = 0.30                            # 扁率：越小越接近侧视
        angle = math.radians(-18)
        sx = x * math.cos(angle) - y * math.sin(angle)
        sy = x * math.sin(angle) + y * math.cos(angle)
        # 沿长轴的位置（-1..1）与到环中心的归一化距离
        axial = sx / radius
        ring_distance = np.sqrt(axial ** 2 + (sy / (radius * tilt)) ** 2)
        band = np.clip(1.0 - np.abs(ring_distance - 1.0) / (thickness * 3.0), 0, 1) ** 1.2
        # 沿环的亮度变化，模拟公转方向上的明暗
        sheen = 0.6 + 0.4 * np.clip(np.cos(np.arctan2(sy / tilt, sx) * 1.5), 0, 1)
        # 环的前半部分：屏幕坐标下 y 越大越靠前（配合 -18° 倾斜近似）
        front = np.clip((sy + 0.06) / 0.2, 0, 1)
        behind_sphere = distance <= planet_radius * 0.995
        visibility = np.where(behind_sphere, front, 1.0)
        alpha_ring = band * sheen * visibility * 230

        rgba = np.zeros((int(size), int(size), 4), dtype=np.float32)
        tone = np.array([255, 242, 210], dtype=np.float32)
        rgba[..., 0:3] = tone
        rgba[..., 3] = alpha_ring
        ring_layer = Image.fromarray(rgba.astype(np.uint8), mode="RGBA")
        ring_layer = ring_layer.filter(ImageFilter.GaussianBlur(radius=max(0.35, size * 0.004)))
        if size < 40:
            # 微缩时环太细会变成脏点，小尺寸干脆淡化
            ring_layer.putalpha(ring_layer.getchannel("A").point(lambda v: int(v * 0.55)))
        image = _alpha_composite(image, ring_layer)

    return image


def _render_bright_star(size: float, planet_scale: float = 1.0) -> Image.Image:
    """"启明星"风格：一颗四芒亮星 + 轨道弧。小尺寸会放大星芒。"""
    x, y = _grid(size)
    distance = np.sqrt(x * x + y * y)
    spread = max(1.0, planet_scale)          # 小尺寸时星芒更粗更长
    rgb = np.zeros((int(size), int(size), 3), dtype=np.float32)
    alpha = np.zeros((int(size), int(size)), dtype=np.float32)
    gradient = np.clip((y + 1.0) / 2.0, 0, 1)
    for channel in range(3):
        rgb[..., channel] = SPACE_TOP[channel] * (1 - gradient) + SPACE_BOTTOM[channel] * gradient
    alpha[:] = 1.0
    _starfield(rgb, alpha, size)

    # 四芒星：两个正交的细长菱形叠加
    spike = np.clip(1.0 - distance / 0.95, 0, 1) ** 1.6
    half_width = 0.055 * spread
    horizontal = (
        np.clip(1.0 - np.abs(y) / half_width, 0, 1)
        * np.clip(1.0 - np.abs(x) / 0.95, 0, 1) ** 0.7
    )
    vertical = (
        np.clip(1.0 - np.abs(x) / half_width, 0, 1)
        * np.clip(1.0 - np.abs(y) / 0.95, 0, 1) ** 0.7
    )
    diagonal = (
        np.clip(1.0 - np.abs(x - y) / (0.05 * spread), 0, 1)
        * np.clip(1.0 - np.abs(x + y) / (0.05 * spread), 0, 1)
    )
    star = np.clip(spike * 1.0 + horizontal * 0.85 + vertical * 0.85 + diagonal * 0.35, 0, 1.4)
    core = np.clip(1.0 - distance / (0.34 * spread), 0, 1) ** 1.2
    for channel in range(3):
        tone = (255, 249, 226)[channel]
        rgb[..., channel] = np.clip(rgb[..., channel] + star * (tone - rgb[..., channel]) * 0.95, 0, 255)
        rgb[..., channel] = np.clip(
            rgb[..., channel] + core * (255 - rgb[..., channel]) * 0.9, 0, 255
        )

    # 轨道弧（象征行星）
    angle = math.radians(-22)
    sx = x * math.cos(angle) - y * math.sin(angle)
    sy = x * math.sin(angle) + y * math.cos(angle)
    ellipse = np.sqrt((sx / 0.92) ** 2 + (sy / 0.3) ** 2)
    orbit = np.clip(1.0 - np.abs(ellipse - 1.0) / 0.03, 0, 1)
    glow = Image.fromarray(
        np.dstack(
            [
                np.full((int(size), int(size)), 255, dtype=np.float32),
                np.full((int(size), int(size)), 226, dtype=np.float32),
                np.full((int(size), int(size)), 170, dtype=np.float32),
                orbit * 120,
            ]
        ).astype(np.uint8),
        mode="RGBA",
    )
    image = _alpha_composite(_to_image(rgb, alpha), glow.filter(ImageFilter.GaussianBlur(size * 0.008)))
    return image


def _render_badge(size: float, planet_scale: float = 1.0) -> Image.Image:
    """徽章风格：圆角底板 + 太白金星 + 一道轨道。

    "太白"即《史记》里说的"色白"，所以行星取暖白；右上角加一颗小亮星（启明星）。
    小尺寸时行星会放大，微缩后仍能一眼看出是颗星球。
    """
    x, y = _grid(size)
    distance = np.sqrt(x * x + y * y)

    rgb = np.zeros((int(size), int(size), 3), dtype=np.float32)
    alpha = np.zeros((int(size), int(size)), dtype=np.float32)
    # 底板渐变（深空蓝 -> 靛）
    gradient = np.clip((x + y + 2.0) / 4.0, 0, 1)
    top = np.array([40, 58, 112], dtype=np.float32)
    bottom = np.array([14, 20, 40], dtype=np.float32)
    for channel in range(3):
        rgb[..., channel] = top[channel] * (1 - gradient) + bottom[channel] * gradient
    alpha[:] = 1.0

    planet_radius = min(0.60, 0.50 * planet_scale)
    offset_x, offset_y = -0.04, 0.03
    px, py = x - offset_x, y - offset_y
    pd = np.sqrt(px * px + py * py)
    rho = np.clip(pd / planet_radius, 0, 1)
    z = np.sqrt(np.clip(1 - rho * rho, 0, 1))
    # 光照来自左上，边缘留一点暖金
    light = np.array([-0.34, -0.42, 0.84])
    light = light / np.linalg.norm(light)
    lambert = np.clip(
        np.clip(px / planet_radius, -1, 1) * light[0]
        + np.clip(py / planet_radius, -1, 1) * light[1]
        + z * light[2],
        0,
        1,
    )
    if size < 40:
        # 微缩时提亮，避免糊成一个暗球
        shade = 0.42 + 0.72 * lambert
    else:
        shade = 0.30 + 0.85 * lambert
    highlight = np.clip(lambert - 0.58, 0.0, None) * 0.75
    rim = np.clip(1.0 - np.abs(pd - planet_radius * 1.02) / (planet_radius * 0.16), 0, 1)
    for channel in range(3):
        tone = CORE_MID[channel] * shade + CORE_LIGHT[channel] * highlight
        tone = tone + rim * ((255, 244, 214)[channel] - tone) * 0.35
        rgb[..., channel] = np.where(pd <= planet_radius, tone, rgb[..., channel])

    # 一道轨道（后半圈被行星遮住）
    radius = planet_radius * 1.5
    tilt = 0.30
    angle = math.radians(-16)
    sx = x * math.cos(angle) - y * math.sin(angle)
    sy = x * math.sin(angle) + y * math.cos(angle)
    axial = sx / radius
    ring_distance = np.sqrt(axial ** 2 + (sy / (radius * tilt)) ** 2)
    band = np.clip(1.0 - np.abs(ring_distance - 1.0) / 0.13, 0, 1) ** 1.2
    front = np.clip((sy + 0.05) / 0.18, 0, 1)
    visibility = np.where(pd <= planet_radius * 0.99, front, 1.0)
    orbit = band * visibility
    for channel in range(3):
        tone = (255, 238, 196)[channel]
        rgb[..., channel] = np.clip(rgb[..., channel] + orbit * (tone - rgb[..., channel]) * 0.9, 0, 255)

    # 右上角的"启明星"亮点（小十字光芒）
    sparkle_x, sparkle_y = 0.46, -0.50
    sd = np.sqrt((x - sparkle_x) ** 2 + (y - sparkle_y) ** 2)
    spread = 0.11 if size >= 40 else 0.16
    sparkle = np.clip(1.0 - sd / spread, 0, 1) ** 1.6
    cross = (
        np.clip(1.0 - np.abs(y - sparkle_y) / (spread * 0.16), 0, 1)
        * np.clip(1.0 - np.abs(x - sparkle_x) / (spread * 1.5), 0, 1)
        + np.clip(1.0 - np.abs(x - sparkle_x) / (spread * 0.16), 0, 1)
        * np.clip(1.0 - np.abs(y - sparkle_y) / (spread * 1.5), 0, 1)
    )
    sparkle = np.clip(sparkle + cross * 0.7, 0, 1.3)
    for channel in range(3):
        rgb[..., channel] = np.clip(rgb[..., channel] + sparkle * (255 - rgb[..., channel]) * 0.9, 0, 255)

    image = _to_image(rgb, alpha)
    # 圆角裁切
    from PIL import ImageDraw

    mask = Image.new("L", (int(size), int(size)), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=size * 0.23, fill=255)
    image.putalpha(mask)
    return image


def _render_radiant(size: float, planet_scale: float = 1.0) -> Image.Image:
    """光芒风格：行星 + 放射光线，像古星图里的"太白"。"""
    image = _render_sphere(size, bands=True, planet_scale=planet_scale)
    ray_layer = Image.new("RGBA", (int(size), int(size)), (0, 0, 0, 0))
    x, y = _grid(size)
    distance = np.sqrt(x * x + y * y)
    angle = np.arctan2(y, x)
    rays = np.clip(np.cos(angle * 8.0) * 0.5 + 0.5, 0, 1) ** 3
    ring_center = 0.82 * planet_scale
    falloff = np.clip(1.0 - np.abs(distance - ring_center) / 0.34, 0, 1) ** 1.2
    ring = rays * falloff
    rgba = np.zeros((int(size), int(size), 4), dtype=np.float32)
    rgba[..., 0] = 255
    rgba[..., 1] = 233
    rgba[..., 2] = 182
    rgba[..., 3] = ring * 150
    ray_layer = Image.fromarray(rgba.astype(np.uint8), mode="RGBA")
    ray_layer = ray_layer.filter(ImageFilter.GaussianBlur(max(0.5, size * 0.01)))
    combined = _alpha_composite(image, ray_layer)
    # 外圈圆角裁切，避免光线被切得太生硬
    mask = Image.new("L", (int(size), int(size)), 0)
    from PIL import ImageDraw

    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=size * 0.24, fill=255)
    combined.putalpha(Image.composite(combined.getchannel("A"), Image.new("L", mask.size, 0), mask))
    return combined


# --------------------------------------------------------------------------
# 对外接口
# --------------------------------------------------------------------------

def frame_scale(size: int) -> float:
    """小尺寸时把主体画大一些，保证 16px 下也能看清是什么。

    这是"逐档优化"的意义：同一个图标不同分辨率用不同的构图比例。
    """
    if size <= 16:
        return 1.42
    if size <= 24:
        return 1.34
    if size <= 32:
        return 1.24
    if size <= 48:
        return 1.14
    if size <= 64:
        return 1.06
    return 1.0


def render(style: str = DEFAULT_STYLE, size: int = 256, supersample: int = 4) -> Image.Image:
    """渲染指定风格与尺寸的图标（返回 RGBA）。"""
    if style not in STYLES:
        raise ValueError(f"未知的图标风格：{style}（可选：{', '.join(STYLES)}）")

    big = float(size * max(1, supersample))
    scale = frame_scale(size)
    if style == "sphere_clouds":
        image = _render_sphere(big, bands=True, planet_scale=scale)
    elif style == "crescent":
        image = _render_sphere(big, bands=True, crescent=True, planet_scale=scale)
    elif style == "ringed":
        image = _render_sphere(big, bands=True, ring=True, planet_scale=scale)
    elif style == "bright_star":
        image = _render_bright_star(big, planet_scale=scale)
    elif style == "badge":
        image = _render_badge(big, planet_scale=scale)
    else:
        image = _render_radiant(big, planet_scale=scale)

    if supersample > 1:
        image = image.resize((size, size), Image.LANCZOS)

    # 小尺寸下额外锐化一点，避免糊成一团
    if size <= 32:
        image = image.filter(ImageFilter.UnsharpMask(radius=1.0, percent=70, threshold=2))
    return image


def render_sizes(
    style: str = DEFAULT_STYLE,
    sizes: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256),
) -> dict[int, Image.Image]:
    return {size: render(style, size) for size in sizes}


def save_ico(style: str, target: Path, sizes: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)) -> Path:
    """把某个风格写成一个多分辨率 .ico。"""
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    images = render_sizes(style, sizes)
    largest = max(sizes)
    images[largest].save(
        target,
        format="ICO",
        sizes=[(size, size) for size in sorted(sizes)],
        append_images=[images[size] for size in sorted(sizes) if size != largest],
    )
    return target


def save_png(style: str, target: Path, size: int = 512) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    render(style, size).save(target, format="PNG")
    return target


def preview_sheet(
    styles: tuple[str, ...] = STYLES,
    sizes: tuple[int, ...] = (16, 24, 32, 48, 64, 128),
    target: Path | None = None,
) -> Image.Image:
    """生成一张对比图，便于挑选风格。"""
    padding = 16
    label_height = 26
    columns = len(sizes)
    cell_width = max(sizes) + padding
    sheet_width = padding + columns * cell_width
    sheet_height = padding + len(styles) * (max(sizes) + label_height + padding)
    sheet = Image.new("RGBA", (sheet_width, sheet_height), (245, 246, 250, 255))

    from PIL import ImageDraw

    draw = ImageDraw.Draw(sheet)
    for row, style in enumerate(styles):
        top = padding + row * (max(sizes) + label_height + padding)
        draw.text((padding, top), style, fill=(40, 48, 64, 255))
        for column, size in enumerate(sizes):
            image = render(style, size)
            left = padding + column * cell_width + (max(sizes) - size) // 2
            sheet.alpha_composite(image, (left, top + label_height))
    if target is not None:
        sheet.convert("RGB").save(target, format="PNG")
    return sheet


def qt_pixmap(size: int = 256, style: str = DEFAULT_STYLE):
    """给 Qt 用的 QPixmap（延迟导入，避免核心逻辑依赖 Qt）。"""
    from PyQt6.QtGui import QImage, QPixmap

    image = render(style, size, supersample=2)
    data = image.tobytes("raw", "RGBA")
    qimage = QImage(data, image.width, image.height, QImage.Format.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimage)


__all__ = [
    "DEFAULT_STYLE",
    "STYLES",
    "preview_sheet",
    "qt_pixmap",
    "render",
    "render_sizes",
    "save_ico",
    "save_png",
]
