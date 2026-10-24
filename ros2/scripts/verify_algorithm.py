"""离线复算 vision_utils 的 8 个 gtest 期望值。

本机没有 C++ 编译器，跑不了 gtest；但算法是纯数学，可以用 Python 把
find_bright_blob / EmaFilter / sanitize_alpha / pixel_to_meter 逐行重写一遍，
再用 test_vision.cpp 里的同一组期望值做断言。这样至少能证明「期望值没写错」，
剩下的风险是 C++ 语法/编译错误，那部分只能靠真机 colcon build。
"""
import math

FAILED = []


def check(name, got, want, tol=1e-12):
    ok = abs(got - want) <= tol
    print(f"{'PASS' if ok else 'FAIL'}  {name}: got={got!r} want={want!r}")
    if not ok:
        FAILED.append(name)


def find_bright_blob(data, width, height, step, threshold, min_area):
    if data is None or width <= 0 or height <= 0 or step < width:
        return {"found": False, "cx": 0.0, "cy": 0.0, "area": 0.0, "mean": 0.0}
    sx = sy = sv = cnt = 0.0
    for v in range(height):
        row = data[v * step: v * step + width]
        for u, value in enumerate(row):
            if value >= threshold:
                sx += u
                sy += v
                sv += value
                cnt += 1.0
    if cnt < max(min_area, 1):
        return {"found": False, "cx": 0.0, "cy": 0.0, "area": 0.0, "mean": 0.0}
    return {"found": True, "cx": sx / cnt, "cy": sy / cnt,
            "area": cnt, "mean": sv / cnt}


def sanitize_alpha(a):
    if not math.isfinite(a) or a <= 0.0 or a > 1.0:
        return 0.3
    return a


def pixel_to_meter(px, size, mpp):
    return (px - size / 2.0) * mpp


def square_image(w, h, cx, cy, side, bg=10, bright=255):
    data = bytearray([bg]) * (w * h)
    half = side // 2
    for y in range(cy - half, cy + half + 1):
        for x in range(cx - half, cx + half + 1):
            if 0 <= x < w and 0 <= y < h:
                data[y * w + x] = bright
    return bytes(data)


# 1. FindsBlobCentroid
r = find_bright_blob(square_image(64, 48, 20, 10, 5), 64, 48, 64, 128, 10)
check("FindsBlobCentroid.found", float(r["found"]), 1.0)
check("FindsBlobCentroid.cx", r["cx"], 20.0)
check("FindsBlobCentroid.cy", r["cy"], 10.0)
check("FindsBlobCentroid.area", r["area"], 25.0)
print(f"{'PASS' if r['mean'] > 250.0 else 'FAIL'}  FindsBlobCentroid.mean>250: {r['mean']}")

# 2. RejectsTooSmallBlob
r = find_bright_blob(square_image(64, 48, 32, 24, 3), 64, 48, 64, 128, 100)
check("RejectsTooSmallBlob.found", float(r["found"]), 0.0)
check("RejectsTooSmallBlob.area", r["area"], 0.0)

# 3. HandlesRowPadding
w, h, step = 10, 6, 16
data = bytearray(step * h)
data[4 * step + 2] = 200
data[4 * step + 3] = 200
r = find_bright_blob(bytes(data), w, h, step, 128, 1)
check("HandlesRowPadding.found", float(r["found"]), 1.0)
check("HandlesRowPadding.cx", r["cx"], 2.5)
check("HandlesRowPadding.cy", r["cy"], 4.0)
check("HandlesRowPadding.area", r["area"], 2.0)

# 4. RejectsNullAndBadGeometry
check("RejectsNull.found", float(find_bright_blob(None, 10, 10, 10, 128, 1)["found"]), 0.0)
check("BadStep.found", float(find_bright_blob(bytes(100), 10, 10, 4, 128, 1)["found"]), 0.0)

# 5. EmaFilter
class Ema:
    def __init__(self, alpha):
        self.alpha = alpha
        self.x = self.y = 0.0
        self.initialized = False

    def update(self, nx, ny):
        if not self.initialized:
            self.x, self.y, self.initialized = nx, ny, True
            return
        a = sanitize_alpha(self.alpha)
        self.x = a * nx + (1.0 - a) * self.x
        self.y = a * ny + (1.0 - a) * self.y

    def reset(self):
        self.initialized = False
        self.x = self.y = 0.0


f = Ema(0.1)
f.update(100.0, 50.0)
check("FirstSampleSnaps.x", f.x, 100.0)
check("FirstSampleSnaps.y", f.y, 50.0)

f = Ema(0.5)
f.update(0.0, 0.0)
f.update(10.0, 20.0)
check("Converges.x", f.x, 5.0)
check("Converges.y", f.y, 10.0)
f.reset()
check("Reset.initialized", float(f.initialized), 0.0)

# 6. SanitizeAlpha
check("sanitize(0.0)", sanitize_alpha(0.0), 0.3)
check("sanitize(-1.0)", sanitize_alpha(-1.0), 0.3)
check("sanitize(1.5)", sanitize_alpha(1.5), 0.3)
check("sanitize(1.0)", sanitize_alpha(1.0), 1.0)
check("sanitize(0.25)", sanitize_alpha(0.25), 0.25)

# 7. PixelToMeter
check("px2m(160)", pixel_to_meter(160.0, 320, 0.005), 0.0)
check("px2m(0)", pixel_to_meter(0.0, 320, 0.005), -0.8)
check("px2m(320)", pixel_to_meter(320.0, 320, 0.005), 0.8)

print()
print("ALL PASS" if not FAILED else f"FAILED: {FAILED}")
raise SystemExit(1 if FAILED else 0)
