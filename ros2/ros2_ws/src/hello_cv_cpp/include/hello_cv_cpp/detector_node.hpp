#ifndef HELLO_CV_CPP__DETECTOR_NODE_HPP_
#define HELLO_CV_CPP__DETECTOR_NODE_HPP_

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"
#include "sensor_msgs/msg/image.hpp"

#include "hello_cv_interfaces/msg/detection.hpp"

namespace hello_cv
{

/// 检测节点：订阅图像，找出亮斑质心，发布 Detection。
/// 关键点是「阈值可以在运行中改」——用参数回调做校验，非法值直接拒掉。
class DetectorNode : public rclcpp::Node
{
public:
  explicit DetectorNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  void on_image(const sensor_msgs::msg::Image::ConstSharedPtr & msg);
  rcl_interfaces::msg::SetParametersResult on_parameter_set(
    const std::vector<rclcpp::Parameter> & params);

  int intensity_threshold_{180};
  int min_area_{200};
  int max_area_{50000};
  double expected_area_{1020.0};  ///< 把"面积"换算成 0~1 的置信度：半径 26 的亮斑在阈值 180 下实测约 1018
  std::string qos_reliability_{"reliable"};

  uint64_t frames_{0};
  uint64_t detections_{0};

  rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_sub_;
  rclcpp::Publisher<hello_cv_interfaces::msg::Detection>::SharedPtr detection_pub_;
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr param_cb_;
};

}  // namespace hello_cv

#endif  // HELLO_CV_CPP__DETECTOR_NODE_HPP_
