"""
从 cosmic.png 抠出行星盘面，输出 planet-disk.png（PNG alpha）。

策略：
- 行星近似位于图像中心偏左，半径约图宽 22%。用户需要根据实际图像微调下面三个参数
- 先用硬边圆裁剪，再在边缘加 1-2 px 羽化（高斯模糊 alpha），溶入背景
- 输出与原图等大的透明 PNG，仅保留圆内像素

这样前端只需把 planet-disk.png 叠在 SVG 粒子层之上，圆盘内像素会遮挡住经过行星背后的粒子，
粒子出了圆盘就显示在前景，制造正确的"前后遮挡"错觉。
"""

from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]  # web/
SRC = ROOT / "public" / "login" / "cosmic.png"
DST = ROOT / "public" / "login" / "planet-disk.png"

# 微调参数（归一化到图片尺寸）
CENTER_X = 0.462
CENTER_Y = 0.515
RADIUS = 0.215
FEATHER_PX = 3


def main() -> None:
    src = Image.open(SRC).convert("RGBA")
    w, h = src.size
    cx, cy = int(w * CENTER_X), int(h * CENTER_Y)
    r = int(min(w, h) * RADIUS)

    # 建一个单通道蒙板：圆内 255，圆外 0
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    if FEATHER_PX > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=FEATHER_PX))

    # 用蒙板当 alpha
    disk = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    disk.paste(src, (0, 0), mask)
    disk.save(DST, optimize=True)

    print(f"wrote {DST.relative_to(ROOT)}  size={w}x{h}  center=({cx},{cy}) r={r}")


if __name__ == "__main__":
    main()
