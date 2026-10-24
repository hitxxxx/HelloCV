// 纯算法层：不依赖任何 ROS 头文件，可以单独用 g++ 编译、单独写单元测试。
// 把算法从节点里抽出来的好处是：节点只负责「收发消息」，算法只负责「算」。
#ifndef HELLO_CV_CPP__VISION_UTILS_HPP_
#define HELLO_CV_CPP__VISION_UTILS_HPP_

#include <cstddef>
#include <cstdint>

namespace hello_cv
{

/// 一帧图像的检测结果
struct BlobResult
{
  bool found{false};          ///< 是否找到满足条件的目标
  double cx{0.0};             ///< 质心 x（像素）
  double cy{0.0};             ///< 质心 y（像素）
  double area{0.0};           ///< 参与计算的像素个数
  double mean_intensity{0.0}; ///< 目标区域的平均灰度
};

/**
 * 在 mono8 图像里找「最亮的连通块」的质心。
 *
 * 注意：这里用的是「阈值 + 一阶矩」的近似做法——不真正做连通域标记，
 * 而是把所有亮度超过阈值的像素一起算质心。当画面里只有一个亮斑时，
 * 这和真正的连通域分析结果等价；有多个亮斑时会得到它们的合成质心。
 * 这样做的原因是实现简单、不需要 OpenCV，而本项目的目的只是演示
 * ROS2 的消息流，不是做一个真正的视觉算法。
 *
 * @param data   图像首字节指针
 * @param width  宽
 * @param height 高
 * @param step   每一行的字节数（mono8 时等于 width，但接口上不能假设）
 * @param threshold 灰度阈值，>= threshold 的像素算作目标
 * @param min_area  面积小于该值时认为「没找到目标」
 */
BlobResult find_bright_blob(
  const uint8_t * data,
  int width,
  int height,
  int step,
  int threshold,
  int min_area);

/**
 * 指数滑动平均（EMA）滤波器：新值权重 alpha，越大越"跟手"、越小越"稳"。
 *   y_k = alpha * x_k + (1 - alpha) * y_{k-1}
 */
struct EmaFilter
{
  double alpha{0.3};
  double x{0.0};
  double y{0.0};
  bool initialized{false};

  void reset();
  void update(double nx, double ny);
};

/// 把 alpha 夹到 (0, 1] 区间；非法值返回默认的 0.3
double sanitize_alpha(double alpha);

/// 像素坐标 → 米（把原点从图像左上角平移到图像中心，再乘以标定比例）
/// 注意：这里只做平移+缩放，y 轴翻不翻转由调用方决定（见 tracker_node 的 vertical_flip 参数）
double pixel_to_meter(double pixel, int size, double meters_per_pixel);

}  // namespace hello_cv

#endif  // HELLO_CV_CPP__VISION_UTILS_HPP_
