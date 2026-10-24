"""离线复算 camera_node 的合成图像 + detector 的质心算法。

用途有两个：
1. 证明「默认参数下真的能检测到目标」——第一版用高斯亮斑时，阈值 180 只圈住半径
   ~7.7 像素（面积 ~181），比 min_area=200 还小，默认参数根本出不了结果。
2. 给出 `expected_area` 这个参数该填多少（它只用于把面积换算成 0~1 的 confidence）。

与 C++ 的对应关系：
  src/camera_node.cpp  on_timer()       -> render_frame()
  src/vision_utils.cpp find_bright_blob()-> find_bright_blob()
"""
import math
import random

W, H = 320, 240
RADIUS = 26.0          # blob_radius
ORBIT = 70.0           # orbit_radius
BG = 28                # background
NOISE = 6.0            # noise_sigma
PEAK = 227.0
SEED = 42


def render_frame(cx: float, cy: float, rng: random.Random, noise: float = NOISE) -> bytes:
    edge = max(1.0, RADIUS * 0.5)
    reach = int(math.ceil(RADIUS)) + 1
    x0, x1 = max(0, int(cx) - reach), min(W - 1, int(cx) + reach)
    y0, y1 = max(0, int(cy) - reach), min(H - 1, int(cy) + reach)
    buf = bytearray(W * H)
    for y in range(H):
        base = y * W
        for x in range(W):
            value = BG + (rng.gauss(0.0, noise) if noise > 0 else 0.0)
            if x0 <= x <= x1 and y0 <= y <= y1:
                d = math.hypot(x - cx, y - cy)
                u = min(1.0, max(0.0, (RADIUS - d) / edge))
                value += PEAK * (u * u * (3.0 - 2.0 * u))
            buf[base + x] = min(255, max(0, int(value)))
    return bytes(buf)


def find_bright_blob(data: bytes, width: int, height: int, step: int,
                     threshold: int, min_area: int):
    sx = sy = cnt = 0.0
    for v in range(height):
        row = data[v * step: v * step + width]
        for u, value in enumerate(row):
            if value >= threshold:
                sx += u
                sy += v
                cnt += 1.0
    if cnt < max(min_area, 1):
        return None
    return sx / cnt, sy / cnt, cnt


def main() -> int:
    rng = random.Random(SEED)
    frames = 12
    positions = [
        (W / 2 + ORBIT * math.cos(2 * math.pi * i / frames),
         H / 2 + ORBIT * math.sin(2 * math.pi * i / frames))
        for i in range(frames)
    ]

    print("== 默认参数：threshold=180 min_area=200 expected_area=? ==")
    areas, errs = [], []
    for (cx, cy) in positions:
        img = render_frame(cx, cy, rng)
        got = find_bright_blob(img, W, H, W, 180, 200)
        if got is None:
            print(f"  !! ({cx:6.1f},{cy:6.1f}) 没检测到（面积不足 min_area）")
            continue
        mx, my, area = got
        areas.append(area)
        errs.append(math.hypot(mx - cx, my - cy))
    mean_area = sum(areas) / len(areas)
    print(f"  检测到 {len(areas)}/{len(positions)} 帧")
    print(f"  面积: min={min(areas):.0f} max={max(areas):.0f} mean={mean_area:.1f}")
    print(f"  质心误差: max={max(errs):.3f} px  mean={sum(errs)/len(errs):.3f} px")
    print(f"  => expected_area 建议值 = {round(mean_area)}")

    print("\n== 阈值敏感性（同一位置，距离中心 70px 处）==")
    rng2 = random.Random(SEED)
    cx, cy = W / 2 + ORBIT, H / 2.0
    img = render_frame(cx, cy, rng2)
    for t in (100, 120, 150, 180, 200, 220, 240):
        got = find_bright_blob(img, W, H, W, t, 1)
        if got is None:
            print(f"  threshold={t:3d}  ->  无")
        else:
            mx, my, area = got
            print(f"  threshold={t:3d}  ->  area={area:7.0f}  cx={mx:7.2f} cy={my:7.2f}")

    print("\n== 对照：第一版的高斯亮斑（sigma=radius/3）在 threshold=180 时 ==")
    def render_gauss(cx, cy):
        inv = 1.0 / (2.0 * RADIUS * RADIUS / 9.0)
        buf = bytearray(W * H)
        for y in range(H):
            for x in range(W):
                d2 = (x - cx) ** 2 + (y - cy) ** 2
                v = BG + PEAK * math.exp(-d2 * inv)
                buf[y * W + x] = min(255, max(0, int(v)))
        return bytes(buf)

    got = find_bright_blob(render_gauss(W / 2.0, H / 2.0), W, H, W, 180, 1)
    print(f"  area={got[2]:.0f}  （< min_area=200，默认参数会判定为 found=false）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
