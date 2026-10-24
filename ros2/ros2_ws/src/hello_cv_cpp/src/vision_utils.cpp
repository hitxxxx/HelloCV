// 纯算法实现：不含 ROS，方便单独测试。
#include "hello_cv_cpp/vision_utils.hpp"

#include <algorithm>
#include <cmath>

namespace hello_cv
{

BlobResult find_bright_blob(
  const uint8_t * data,
  int width,
  int height,
  int step,
  int threshold,
  int min_area)
{
  BlobResult result;

  if (data == nullptr || width <= 0 || height <= 0 || step < width) {
    return result;
  }

  // 用 double 累加，防止大面积图像时 int 溢出（1600x1200 的亮斑就可能超 int 范围外的像素数）
  double sum_x = 0.0;
  double sum_y = 0.0;
  double sum_v = 0.0;
  double count = 0.0;

  for (int v = 0; v < height; ++v) {
    const uint8_t * row = data + static_cast<std::size_t>(v) * static_cast<std::size_t>(step);
    for (int u = 0; u < width; ++u) {
      const int value = static_cast<int>(row[u]);
      if (value >= threshold) {
        sum_x += u;
        sum_y += v;
        sum_v += value;
        count += 1.0;
      }
    }
  }

  if (count < static_cast<double>(std::max(min_area, 1))) {
    return result;  // found 保持 false
  }

  result.found = true;
  result.cx = sum_x / count;
  result.cy = sum_y / count;
  result.area = count;
  result.mean_intensity = sum_v / count;
  return result;
}

void EmaFilter::reset()
{
  initialized = false;
  x = 0.0;
  y = 0.0;
}

void EmaFilter::update(double nx, double ny)
{
  if (!initialized) {
    // 第一次必须直接接住测量值，否则会从 (0,0) 慢慢爬过来，看起来像"漂移"
    x = nx;
    y = ny;
    initialized = true;
    return;
  }
  const double a = sanitize_alpha(alpha);
  x = a * nx + (1.0 - a) * x;
  y = a * ny + (1.0 - a) * y;
}

double sanitize_alpha(double alpha)
{
  if (!std::isfinite(alpha) || alpha <= 0.0 || alpha > 1.0) {
    return 0.3;
  }
  return alpha;
}

double pixel_to_meter(double pixel, int size, double meters_per_pixel)
{
  // 把原点从左上角平移到图像中心，再按标定比例换算成米
  const double center = static_cast<double>(size) * 0.5;
  return (pixel - center) * meters_per_pixel;
}

}  // namespace hello_cv
