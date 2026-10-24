#ifndef HELLO_CV_CPP__TRACKER_NODE_HPP_
#define HELLO_CV_CPP__TRACKER_NODE_HPP_

#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/transform_stamped.hpp"
#include "visualization_msgs/msg/marker.hpp"
#include "tf2_ros/transform_broadcaster.h"

#include "hello_cv_cpp/vision_utils.hpp"
#include "hello_cv_interfaces/msg/detection.hpp"
#include "hello_cv_interfaces/srv/set_tracking_mode.hpp"

namespace hello_cv
{

/// 跟踪节点：把像素坐标的检测结果平滑成「米」为单位的轨迹点，
/// 并以 TF（map -> target）和 RViz Marker 的形式发布出去。
/// 同时它还是 SetTrackingMode 服务的服务端，可以在运行中切换平滑策略。
class TrackerNode : public rclcpp::Node
{
public:
  explicit TrackerNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  void on_detection(const hello_cv_interfaces::msg::Detection & msg);
  void on_set_mode(
    const std::shared_ptr<hello_cv_interfaces::srv::SetTrackingMode::Request> request,
    std::shared_ptr<hello_cv_interfaces::srv::SetTrackingMode::Response> response);
  void publish_marker(double x, double y, const rclcpp::Time & stamp);

  // ---- 参数 ----
  double alpha_{0.35};
  double meters_per_pixel_{0.005};
  std::string frame_id_{"map"};
  std::string target_frame_{"target"};
  bool vertical_flip_{true};
  bool publish_marker_{true};
  double marker_diameter_{0.12};

  // ---- 状态 ----
  std::string mode_{"ema"};
  EmaFilter ema_;
  int image_width_{320};
  int image_height_{240};
  bool has_target_{false};
  uint64_t updates_{0};

  rclcpp::Subscription<hello_cv_interfaces::msg::Detection>::SharedPtr detection_sub_;
  rclcpp::Publisher<hello_cv_interfaces::msg::Detection>::SharedPtr track_pub_;
  rclcpp::Publisher<visualization_msgs::msg::Marker>::SharedPtr marker_pub_;
  rclcpp::Service<hello_cv_interfaces::srv::SetTrackingMode>::SharedPtr mode_srv_;
  std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
};

}  // namespace hello_cv

#endif  // HELLO_CV_CPP__TRACKER_NODE_HPP_
