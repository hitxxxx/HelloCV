// 纯算法层的单元测试：不需要启动任何 ROS 节点，`colcon test` 直接跑。
// 这正是「把算法从节点里抽出来」的好处——测试成本从"起 5 个节点 + 开 rviz"降到毫秒级。
#include <gtest/gtest.h>

#include <cstdint>
#include <vector>

#include "hello_cv_cpp/vision_utils.hpp"

namespace
{

/// 造一张 w*h 的 mono8 灰度图，背景为 background，在 (cx, cy) 处画一个边长 side 的亮方块
std::vector<uint8_t> make_image_with_square(
  int w, int h, int cx, int cy, int side, uint8_t background = 10, uint8_t bright = 255)
{
  std::vector<uint8_t> data(static_cast<std::size_t>(w) * static_cast<std::size_t>(h), background);
  const int half = side / 2;
  for (int y = cy - half; y <= cy + half; ++y) {
    for (int x = cx - half; x <= cx + half; ++x) {
      if (x >= 0 && x < w && y >= 0 && y < h) {
        data[static_cast<std::size_t>(y) * static_cast<std::size_t>(w) + static_cast<std::size_t>(x)] = bright;
      }
    }
  }
  return data;
}

}  // namespace

TEST(VisionUtils, FindsBlobCentroid)
{
  const int w = 64;
  const int h = 48;
  const auto img = make_image_with_square(w, h, 20, 10, 5);  // 5x5 -> 25 个像素

  const auto r = hello_cv::find_bright_blob(img.data(), w, h, w, 128, 10);

  EXPECT_TRUE(r.found);
  EXPECT_DOUBLE_EQ(r.cx, 20.0);
  EXPECT_DOUBLE_EQ(r.cy, 10.0);
  EXPECT_DOUBLE_EQ(r.area, 25.0);
  EXPECT_GT(r.mean_intensity, 250.0);
}

TEST(VisionUtils, RejectsTooSmallBlob)
{
  const int w = 64;
  const int h = 48;
  const auto img = make_image_with_square(w, h, 32, 24, 3);  // 3x3 -> 9 个像素

  const auto r = hello_cv::find_bright_blob(img.data(), w, h, w, 128, 100);

  EXPECT_FALSE(r.found);  // 面积不够，按约定当作"没找到"
  EXPECT_DOUBLE_EQ(r.area, 0.0);
}

TEST(VisionUtils, HandlesRowPadding)
{
  // 真实图像经常 step != width（有行对齐填充），算法必须按 step 跨行
  const int w = 10;
  const int h = 6;
  const int step = 16;
  std::vector<uint8_t> data(static_cast<std::size_t>(step) * static_cast<std::size_t>(h), 0);
  // 在 (2, 4) 和 (3, 4) 各放一个亮点
  data[static_cast<std::size_t>(4) * step + 2] = 200;
  data[static_cast<std::size_t>(4) * step + 3] = 200;

  const auto r = hello_cv::find_bright_blob(data.data(), w, h, step, 128, 1);

  EXPECT_TRUE(r.found);
  EXPECT_DOUBLE_EQ(r.cx, 2.5);
  EXPECT_DOUBLE_EQ(r.cy, 4.0);
  EXPECT_DOUBLE_EQ(r.area, 2.0);
}

TEST(VisionUtils, RejectsNullAndBadGeometry)
{
  const auto r = hello_cv::find_bright_blob(nullptr, 10, 10, 10, 128, 1);
  EXPECT_FALSE(r.found);

  const uint8_t dummy[100] = {0};
  const auto r2 = hello_cv::find_bright_blob(dummy, 10, 10, 4, 128, 1);  // step < width
  EXPECT_FALSE(r2.found);
}

TEST(EmaFilter, FirstSampleSnaps)
{
  hello_cv::EmaFilter f;
  f.alpha = 0.1;  // 故意用很小的 alpha：如果第一次不平滑，结果会从 0 慢慢爬
  f.update(100.0, 50.0);

  EXPECT_TRUE(f.initialized);
  EXPECT_DOUBLE_EQ(f.x, 100.0);
  EXPECT_DOUBLE_EQ(f.y, 50.0);
}

TEST(EmaFilter, ConvergesWithAlpha)
{
  hello_cv::EmaFilter f;
  f.alpha = 0.5;
  f.update(0.0, 0.0);
  f.update(10.0, 20.0);

  EXPECT_DOUBLE_EQ(f.x, 5.0);
  EXPECT_DOUBLE_EQ(f.y, 10.0);

  f.reset();
  EXPECT_FALSE(f.initialized);
}

TEST(EmaFilter, SanitizeAlpha)
{
  EXPECT_DOUBLE_EQ(hello_cv::sanitize_alpha(0.0), 0.3);
  EXPECT_DOUBLE_EQ(hello_cv::sanitize_alpha(-1.0), 0.3);
  EXPECT_DOUBLE_EQ(hello_cv::sanitize_alpha(1.5), 0.3);
  EXPECT_DOUBLE_EQ(hello_cv::sanitize_alpha(1.0), 1.0);
  EXPECT_DOUBLE_EQ(hello_cv::sanitize_alpha(0.25), 0.25);
}

TEST(VisionUtils, PixelToMeter)
{
  // 320 宽、每像素 5mm：中心 160 对应 0 米，0 对应 -0.8 米
  EXPECT_DOUBLE_EQ(hello_cv::pixel_to_meter(160.0, 320, 0.005), 0.0);
  EXPECT_DOUBLE_EQ(hello_cv::pixel_to_meter(0.0, 320, 0.005), -0.8);
  EXPECT_DOUBLE_EQ(hello_cv::pixel_to_meter(320.0, 320, 0.005), 0.8);
}
