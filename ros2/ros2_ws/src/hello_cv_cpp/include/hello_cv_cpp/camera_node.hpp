#ifndef HELLO_CV_CPP__CAMERA_NODE_HPP_
#define HELLO_CV_CPP__CAMERA_NODE_HPP_

#include <chrono>
#include <cstdint>
#include <memory>
#include <random>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/image.hpp"

namespace hello_cv
{

/// 相机模拟节点：生成一张 mono8 图像，里面有一个绕圈运动的高斯亮斑。
/// 没有真实相机也能把整条「图像 → 检测 → 跟踪 → TF」链路跑起来。
class CameraNode : public rclcpp::Node
{
public:
  explicit CameraNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  void on_timer();
  /// 把（可配置的）QoS 参数翻译成实际的 QoS 对象
  rclcpp::QoS make_qos() const;

  // ---- 参数 ----
  int width_{320};
  int height_{240};
  double fps_{30.0};
  double radius_{26.0};      ///< 亮斑半径（像素）
  double omega_{0.8};        ///< 圆周运动角速度（rad/s）
  double center_x_{160.0};   ///< 圆周圆心 x
  double center_y_{120.0};   ///< 圆周圆心 y
  double orbit_r_{70.0};     ///< 圆周半径
  double noise_sigma_{6.0};  ///< 背景噪声标准差
  int background_{28};       ///< 背景基准灰度
  std::string frame_id_{"camera_link"};
  std::string qos_reliability_{"reliable"};

  // ---- 运行时状态 ----
  std::chrono::steady_clock::time_point last_stamp_;
  double elapsed_{0.0};
  std::mt19937 rng_;
  std::normal_distribution<double> noise_dist_{0.0, 1.0};

  rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr image_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

}  // namespace hello_cv

#endif  // HELLO_CV_CPP__CAMERA_NODE_HPP_
