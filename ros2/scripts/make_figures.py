#!/usr/bin/env python3
"""HelloCV · 笔记配图生成器

为什么不截 rviz 的图，而是“画”图：
  1. 架构图、状态机、QoS 对照表这类东西，画出来比截图更清楚；
  2. 截图依赖分辨率/主题/字体，换台机器就花了；
  3. 图是可复现的：改一行代码重新生成，比翻相册找截图靠谱。

依赖：Pillow（pip install pillow）
用法： python3 scripts/make_figures.py
输出： docs/figures/*.png
"""
from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(HERE, os.pardir, "docs", "figures")

# ---------------------------------------------------------------- 配色
INK = (31, 36, 48)
MUTED = (107, 114, 128)
LINE = (203, 213, 225)
BG = (255, 255, 255)
PANEL = (247, 249, 252)
BLUE = (47, 111, 235)
BLUE_BG = (235, 242, 255)
GREEN = (22, 163, 74)
GREEN_BG = (235, 250, 240)
AMBER = (217, 119, 6)
AMBER_BG = (255, 247, 235)
PURPLE = (124, 58, 237)
PURPLE_BG = (243, 238, 255)
RED = (220, 38, 38)

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhl.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]


def _font_path() -> str:
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("找不到中文字体，请把 FONT_CANDIDATES 改成你机器上的字体路径")


FONT_PATH = _font_path()
_cache: dict = {}


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key not in _cache:
        try:
            _cache[key] = ImageFont.truetype(FONT_PATH, size, index=1 if bold else 0)
        except Exception:
            _cache[key] = ImageFont.truetype(FONT_PATH, size)
    return _cache[key]


def text_w(d, s, f):
    return d.textlength(s, font=f)


def fit_font(d, s, box_w, start, bold=False, floor=11):
    size = start
    while size > floor and text_w(d, s, font(size, bold)) > box_w:
        size -= 1
    return font(size, bold)


def box(d, xy, fill, outline, radius=16, width=2):
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def centered(d, cx, y, s, f, fill):
    d.text((cx - text_w(d, s, f) / 2, y), s, font=f, fill=fill)


def right_aligned(d, x_right, y, s, f, fill):
    d.text((x_right - text_w(d, s, f), y), s, font=f, fill=fill)


def card(d, xy, title, subtitle=None, extra=None, fill=BLUE_BG, outline=BLUE,
         tsize=25, ssize=17, esize=15):
    """一个“节点卡片”：标题 + 一行副标题 + 若干行细节，整体垂直居中。"""
    box(d, xy, fill, outline)
    x0, y0, x1, y1 = xy
    cx = (x0 + x1) / 2
    lines = []
    if subtitle:
        lines.append((subtitle, ssize, MUTED))
    if extra:
        lines.extend([(e, esize, INK) for e in extra])

    gap = 7
    total = tsize + gap + sum(sz + gap for _, sz, _ in lines)
    y = y0 + (y1 - y0 - total) / 2
    tf = fit_font(d, title, x1 - x0 - 28, tsize, bold=True)
    centered(d, cx, y, title, tf, INK)
    y += tsize + gap
    for s, sz, col in lines:
        f = fit_font(d, s, x1 - x0 - 28, sz)
        centered(d, cx, y, s, f, col)
        y += sz + gap


def tag(d, cx, cy, title, sub=None, width=None, color=INK, sub_color=MUTED):
    """话题/服务标签：两行（名字 + 类型），整体上下居中于 cy。"""
    ft = font(17)
    fs = font(13)
    w = width or max(text_w(d, title, ft), text_w(d, sub, fs) if sub else 0) + 30
    h = 54 if sub else 34
    box(d, (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), (255, 255, 255), LINE, radius=12, width=2)
    if sub:
        centered(d, cx, cy - 20, title, ft, color)
        centered(d, cx, cy + 5, sub, fs, sub_color)
    else:
        centered(d, cx, cy - 9, title, ft, color)


def arrow(d, p0, p1, color=INK, width=3, dashed=False, head=11):
    if dashed:
        _dashed_line(d, p0, p1, color, width)
    else:
        d.line([p0, p1], fill=color, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    x, y = p1
    d.polygon([
        (x, y),
        (x - head * math.cos(ang - 0.42), y - head * math.sin(ang - 0.42)),
        (x - head * math.cos(ang + 0.42), y - head * math.sin(ang + 0.42)),
    ], fill=color)


def path_arrow(d, points, color=INK, width=3):
    """折线箭头：前面的线段不带箭头，最后一段带箭头。"""
    for i in range(len(points) - 2):
        d.line([points[i], points[i + 1]], fill=color, width=width)
    arrow(d, points[-2], points[-1], color, width)


def _dashed_line(d, p0, p1, color, width, dash=9, gap=7):
    x0, y0 = p0
    x1, y1 = p1
    length = math.hypot(x1 - x0, y1 - y0)
    if length == 0:
        return
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    t = 0.0
    while t < length:
        t2 = min(t + dash, length)
        d.line([(x0 + ux * t, y0 + uy * t), (x0 + ux * t2, y0 + uy * t2)],
               fill=color, width=width)
        t = t2 + gap


def section_label(d, x, y, s, color=BLUE):
    d.text((x, y), s, font=font(23, bold=True), fill=color)


def canvas(w, h, title, subtitle):
    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.text((56, 34), title, font=font(37, bold=True), fill=INK)
    d.text((56, 86), subtitle, font=font(18), fill=MUTED)
    d.line([(56, 122), (w - 56, 122)], fill=LINE, width=2)
    return img, d


# =============================================================================
# 图 1：总体架构
# =============================================================================
def fig_architecture(path: str):
    W, H = 1480, 1120
    img, d = canvas(W, H, "HelloCV 视觉流水线 · 节点与接口总览",
                    "两个包：hello_cv_interfaces（只定义 msg/srv）　+　hello_cv_cpp（节点实现）")

    section_label(d, 56, 142, "① 主链路：话题（Topic）· 发布-订阅，异步、单向")

    bw = 720
    x0 = (W - bw) / 2
    cx = W / 2
    cam = (x0, 186, x0 + bw, 312)
    det = (x0, 412, x0 + bw, 538)
    trk = (x0, 638, x0 + bw, 784)

    card(d, cam, "camera_node", "合成相机：mono8 灰度图，亮斑绕圈飞",
         ["参数 width / height / fps / orbit_radius / omega / seed"], BLUE_BG, BLUE)
    card(d, det, "detector_node", "亮斑检测：阈值筛选 + 一阶矩求质心",
         ["不做连通域标记 —— 一个亮斑一个质心，够用就好"], GREEN_BG, GREEN)
    card(d, trk, "tracker_node", "EMA 平滑 + 像素→米 + 广播 TF",
         ["mode=ema / raw 可运行时切换（服务）",
          "输出 /tf · /vision/track · /vision/target_marker"], PURPLE_BG, PURPLE)

    g1 = (cam[3] + det[1]) / 2      # 第一条话题标签的 y 中心
    g2 = (det[3] + trk[1]) / 2
    tag(d, cx, g1, "/camera/image_raw", "sensor_msgs/msg/Image　reliable")
    tag(d, cx, g2, "/vision/detection", "hello_cv_interfaces/msg/Detection　reliable")

    arrow(d, (cx, cam[3]), (cx, g1 - 27), INK, 4)
    arrow(d, (cx, g1 + 27), (cx, det[1]), INK, 4)
    arrow(d, (cx, det[3]), (cx, g2 - 27), INK, 4)
    arrow(d, (cx, g2 + 27), (cx, trk[1]), INK, 4)

    # ---------- ② 服务：控制链路 ----------
    section_label(d, 56, 596, "② 控制链路：服务（Service）· 同步请求/应答", AMBER)
    client = (56, 646, 300, 740)
    card(d, client, "mode_service_client", "/set_mode（srv）", None, AMBER_BG, AMBER, tsize=19, ssize=15)
    arrow(d, (300, 693), (x0, 693), AMBER, 3, dashed=True)

    # ---------- ③ 输出去向 ----------
    section_label(d, 56, 766, "③ 输出去向：可视化 / 查询 / 工具")
    oy0, oy1 = 870, 998
    b1 = (56, oy0, 400, oy1)
    b2 = (460, oy0, 820, oy1)
    b3 = (880, oy0, 1424, oy1)
    card(d, b1, "/tf（tf2）", "map → target 动态广播", ["父 map　子 target"], BLUE_BG, BLUE, tsize=23)
    card(d, b2, "RViz2", "TF 树 + Marker 球 + 图像", ["Fixed Frame = map"], PURPLE_BG, PURPLE, tsize=23)
    card(d, b3, "tf_lookup_node / tf2_tools", "每秒查一次 map→target；view_frames 画树",
         ["验证 TF 真的在发，而不是我以为它在发"], GREEN_BG, GREEN, tsize=23)

    for tgt in (b1, b2, b3):
        tx = (tgt[0] + tgt[2]) / 2
        arrow(d, (cx, trk[3]), (tx, oy0), INK, 3)

    # ---------- ④ 参数带 ----------
    d.rounded_rectangle((56, 1032, 1424, 1096), radius=14, fill=PANEL, outline=LINE, width=2)
    d.text((80, 1046), "④ 参数（Parameter）· 与话题/服务正交的第三条通道",
           font=font(18, bold=True), fill=INK)
    d.text((80, 1070),
           "ros2 param list / get / set　·　declare_parameter + add_on_set_parameters_callback　·　config/params.yaml",
           font=font(14), fill=MUTED)

    img.save(path)
    print("wrote", path)


# =============================================================================
# 图 2：生命周期状态机
# =============================================================================
def fig_lifecycle(path: str):
    W, H = 1520, 800
    img, d = canvas(W, H, "ROS2 受管节点（LifecycleNode）状态机",
                    "四个状态、五个迁移：configure / activate / deactivate / cleanup / shutdown")

    sx0, sx1 = 520, 940
    st = {
        "unconfigured": (sx0, 180, sx1, 300),
        "inactive": (sx0, 380, sx1, 500),
        "active": (sx0, 580, sx1, 700),
    }
    fin = (1060, 560, 1440, 680)
    cmid = (sx0 + sx1) / 2

    card(d, st["unconfigured"], "unconfigured", "未配置", ["对象已存在", "没有定时器 / 发布器"], PANEL, MUTED)
    card(d, st["inactive"], "inactive", "已配置、未激活", ["资源都建好了", "但 publish 被压住"], AMBER_BG, AMBER)
    card(d, st["active"], "active", "运行中", ["定时器在跑、消息真的发出去"], GREEN_BG, GREEN)
    card(d, fin, "finalized", "已终结", ["只能销毁，不能复活"], (242, 242, 244), MUTED)

    # configure / activate
    arrow(d, (cmid, 300), (cmid, 380), INK, 4)
    d.text((cmid + 16, 310), "configure", font=font(17, bold=True), fill=INK)
    d.text((cmid + 16, 336), "on_configure()", font=font(14), fill=MUTED)

    arrow(d, (cmid, 500), (cmid, 580), INK, 4)
    d.text((cmid + 16, 510), "activate", font=font(17, bold=True), fill=INK)
    d.text((cmid + 16, 536), "on_activate()", font=font(14), fill=MUTED)

    # deactivate：active 左 → 左侧走廊 → 回 inactive 左
    path_arrow(d, [(sx0, 640), (410, 640), (410, 440), (sx0, 440)], AMBER, 3)
    right_aligned(d, 400, 510, "deactivate", font(16, bold=True), AMBER)
    right_aligned(d, 400, 534, "on_deactivate()", font(14), MUTED)

    # cleanup：inactive 左 → 更外侧走廊 → 回 unconfigured 左
    path_arrow(d, [(sx0, 420), (320, 420), (320, 240), (sx0, 240)], MUTED, 3)
    right_aligned(d, 310, 326, "cleanup", font(16, bold=True), MUTED)
    right_aligned(d, 310, 350, "on_cleanup()", font(14), MUTED)

    # shutdown：任意状态（这里画 active → finalized 作代表）
    arrow(d, (sx1, 620), (fin[0], 620), RED, 3, dashed=True)
    d.text((sx1 + 8, 588), "shutdown", font=font(15, bold=True), fill=RED)
    d.text((sx1 + 8, 636), "任意状态", font=font(13), fill=RED)

    # ---------- 说明面板 ----------
    px0, py0, px1, py1 = 1000, 150, 1440, 520
    d.rounded_rectangle((px0, py0, px1, py1), radius=14, fill=PANEL, outline=LINE, width=2)
    d.text((px0 + 20, py0 + 14), "为什么要这套状态机？", font=font(19, bold=True), fill=INK)
    notes = [
        ("① 配置与运行分离", ["加载参数、建 pub/sub 放在 configure；",
                              "数据流在 activate —— 起停不重建资源。"]),
        ("② 可被外部控制", ["launch 用 ChangeState 事件驱动；",
                            "ros2 lifecycle set 也能手动切。"]),
        ("③ 错误可回退", ["on_configure 返回 FAILURE 时，节点",
                          "停在 unconfigured，而不是直接崩。"]),
        ("④ 空转陷阱", ["configure 完不会自动 activate；",
                        "连发两个事件会因状态未到而失败。"]),
    ]
    y = py0 + 54
    for head, bodies in notes:
        d.text((px0 + 20, y), head, font=font(15, bold=True), fill=INK)
        y += 21
        for b in bodies:
            d.text((px0 + 30, y), b, font=font(14), fill=MUTED)
            y += 21
        y += 10

    img.save(path)
    print("wrote", path)


# =============================================================================
# 图 3：QoS 对照表
# =============================================================================
def fig_qos(path: str):
    W, H = 1560, 830
    img, d = canvas(W, H, "QoS：把可靠性变成可调参数",
                    "同一条话题，两边的 QoS 必须兼容，否则订阅者静默收不到数据")

    cols = [56, 300, 620, 900, 1100, 1504]
    y = 166
    header = ["策略", "可选值", "默认值", "HelloCV 用", "说人话"]
    d.rectangle((cols[0], y, cols[-1], y + 52), fill=(31, 36, 48))
    for i, h in enumerate(header):
        d.text((cols[i] + 16, y + 14), h, font=font(18, bold=True), fill=(255, 255, 255))
    y += 52

    rows = [
        ("Reliability", "reliable / best_effort", "reliable", "reliable",
         "丢了要不要重传；best_effort 适合高频传感器"),
        ("Durability", "volatile / transient_local", "volatile", "volatile",
         "后来的订阅者补不补历史消息（latched topic）"),
        ("History", "keep_last / keep_all", "keep_last", "keep_last",
         "只留最近 N 条，还是全留（内存杀手）"),
        ("Depth", ">= 1", "10", "10",
         "队列长度；发得比收得快时，多出来的会被丢"),
        ("Deadline", "Duration", "无", "无",
         "承诺多久内必到一条，超时触发回调"),
        ("Lifespan", "Duration", "无", "无",
         "消息的保质期，过期就丢、不再投递"),
    ]
    rh = 74
    for idx, row in enumerate(rows):
        fill = (255, 255, 255) if idx % 2 == 0 else (247, 249, 252)
        d.rectangle((cols[0], y, cols[-1], y + rh), fill=fill, outline=LINE, width=1)
        for i, cell in enumerate(row):
            size = 18 if i == 0 else (15 if i == 4 else 16)
            f = fit_font(d, cell, cols[i + 1] - cols[i] - 30, size, bold=(i == 0))
            d.text((cols[i] + 16, y + (rh - size) / 2 - 2), cell, font=f, fill=INK)
        y += rh

    # 关键结论
    cy0 = y + 24
    d.rounded_rectangle((56, cy0, 1504, cy0 + 132), radius=14, fill=(255, 244, 240), outline=RED, width=2)
    d.text((80, cy0 + 16), "最容易踩的坑：QoS 不兼容时不报错，只是对方收不到",
           font=font(21, bold=True), fill=RED)
    d.text((80, cy0 + 56),
           "例：发端 best_effort、收端 reliable → 根本建立不了连接。用 ros2 topic info <topic> -v 看两端 QoS。",
           font=font(15), fill=INK)
    d.text((80, cy0 + 84),
           "现象是话题明明有数据、订阅者就是不触发，比崩溃难查十倍 —— 所以本项目统一 reliable + volatile + keep_last(10)。",
           font=font(15), fill=INK)

    img.save(path)
    print("wrote", path)


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    fig_architecture(os.path.join(OUT_DIR, "fig-architecture.png"))
    fig_lifecycle(os.path.join(OUT_DIR, "fig-lifecycle.png"))
    fig_qos(os.path.join(OUT_DIR, "fig-qos.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
