#!/usr/bin/env python3
"""把截图底部的大片空白裁掉，只保留有内容的区域。

用法：
    python crop_shots.py <输入目录> <输出目录>

原理：截图里的文字/图形都比背景亮（背景 #0f1319，文字 #e6e8eb），
所以逐行统计"最亮通道 > 90"的像素数，最后一行有内容的位置就是裁切点。
只裁上下（宽度保持整屏），这样一组图的宽度一致，贴到笔记里更整齐。
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

BRIGHT = 90        # 灰度阈值：超过就算"有内容"
MIN_COUNT = 3      # 一行里至少几个亮像素才算有内容（排除噪点）
PAD_TOP = 0
PAD_BOTTOM = 26    # 底边留一点呼吸感


def content_bottom(im: Image.Image) -> int:
    """返回最后一个"有内容"的行号（含）。"""
    gray = im.convert("L")
    width, height = gray.size
    pixels = gray.load()
    for y in range(height - 1, -1, -1):
        count = 0
        for x in range(0, width, 2):
            if pixels[x, y] > BRIGHT:
                count += 1
                if count >= MIN_COUNT:
                    return y
    return height - 1


def crop_one(src: Path, dst: Path) -> tuple[int, int]:
    im = Image.open(src).convert("RGB")
    bottom = min(im.height, content_bottom(im) + PAD_BOTTOM)
    out = im.crop((0, PAD_TOP, im.width, bottom))
    dst.parent.mkdir(parents=True, exist_ok=True)
    out.save(dst, optimize=True)
    return im.height, out.height


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    src_dir, dst_dir = Path(argv[1]), Path(argv[2])
    files = sorted(p for p in src_dir.glob("*.png") if p.name.startswith(("0", "1")))
    if not files:
        print(f"没有在 {src_dir} 找到截图")
        return 1
    for src in files:
        before, after = crop_one(src, dst_dir / src.name)
        print(f"{src.name}: {before}px -> {after}px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
