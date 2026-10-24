#include "hello_cv_cpp/tracker_node.hpp"

#include <algorithm>
#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <utility>

#include "hello_cv_cpp/vision_utils.hpp"

namespace hello_cv
{

TrackerNode::TrackerNode(const rclcpp::NodeOptions & options)
: rclcpp::Node("tracker_node", options)
{
  alpha_ = sanitize_alpha(this->declare_parameter<double>("alpha", 0.35));
  meters_per_pixel_ = this->declare_parameter<double>("meters_per_pixel", 0.005);
  frame_id_ = this->declare_parameter<std::string>("frame_id", "map");
  target_frame_ = this->declare_parameter<std::string>("target_frame", "target");
  vertical_flip_ = this->declare_parameter<bool>("vertical_flip", true);
  publish_marker_ = this->declare_parameter<bool>("publish_marker", true);
  marker_diameter_ = this->declare_parameter<double>("marker_diameter", 0.12);
  image_width_ = this->declare_parameter<int>("image_width", 320);
  image_height_ = this->declare_parameter<int>("image_height", 240);
  mode_ = this->declare_parameter<std::string>("mode", "ema");

  ema_.alpha = alpha_;

  detection_sub_ = this->create_subscription<hello_cv_interfaces::msg::Detection>(
    "detection", rclcpp::QoS(10),
    std::bind(&TrackerNode::on_detection, this, std::placeholders::_1));

  track_pub_ =
    this->create_publisher<hello_cv_interfaces::msg::Detection>("track", rclcpp::QoS(10));
  marker_pub_ = this->create_publisher<visualization_msgs::msg::Marker>(
    "target_marker", rclcpp::QoS(10));

  mode_srv_ = this->create_service<hello_cv_interfaces::srv::SetTrackingMode>(
    "set_mode",
    std::bind(
      &TrackerNode::on_set_mode, this,
      std::placeholders::_1, std::placeholders::_2));

  // TransformBroadcaster 内部会自己建 publisher 和 timer，不需要我们管
  tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);

  RCLCPP_INFO(
    this->get_logger(),
    "tracker_node 启动：mode=%s alpha=%.2f m/px=%.4f %s->%s",
    mode_.c_str(), alpha_, meters_per_pixel_,
    frame_id_.c_str(), target_frame_.c_str());
}

void TrackerNode::on_detection(const hello_cv_interfaces::msg::Detection & msg)
{
  if (!msg.found) {
    has_target_ = false;
    return;
  }

  // 像素 -> 米：先平移到图像中心，再乘标定比例；y 轴按需翻转（图像向下、地图向上）
  double x = pixel_to_meter(msg.cx, image_width_, meters_per_pixel_);
  double y = pixel_to_meter(msg.cy, image_height_, meters_per_pixel_);
  if (vertical_flip_) {
    y = -y;
  }

  // 平滑策略由服务在运行中控制
  if (mode_ == "ema") {
    ema_.alpha = alpha_;
    ema_.update(x, y);
    x = ema_.x;
    y = ema_.y;
  } else {
    ema_.reset();  // raw 模式下清掉滤波器状态，避免切回 ema 时从旧值慢慢爬
  }

  has_target_ = true;
  ++updates_;

  // ---- 1. 发布 TF：map -> target ----
  geometry_msgs::msg::TransformStamped t;
  t.header.stamp = msg.header.stamp;   // 关键：用检测的时间戳，而不是 now()
  t.header.frame_id = frame_id_;
  t.child_frame_id = target_frame_;
  t.transform.translation.x = x;
  t.transform.translation.y = y;
  t.transform.translation.z = 0.0;
  t.transform.rotation.x = 0.0;
  t.transform.rotation.y = 0.0;
  t.transform.rotation.z = 0.0;
  t.transform.rotation.w = 1.0;        // 无旋转的四元数必须显式写 1，否则会被当成非法姿态
  tf_broadcaster_->sendTransform(t);

  // ---- 2. 转发一份跟踪结果，方便 ros2 topic echo 直接看 ----
  hello_cv_interfaces::msg::Detection out;
  out.header = msg.header;
  out.header.frame_id = frame_id_;     // 注意：这里已经换成米制坐标，frame 不再等于相机
  out.found = true;
  out.cx = static_cast<float>(x);
  out.cy = static_cast<float>(y);
  out.area = msg.area;
  out.confidence = msg.confidence;
  track_pub_->publish(out);

  // ---- 3. RViz Marker ----
  if (publish_marker_) {
    publish_marker(x, y, msg.header.stamp);
  }

  RCLCPP_INFO_THROTTLE(
    this->get_logger(), *this->get_clock(), 1000,
    "updates=%lu mode=%s 目标位置 (%.3f, %.3f) m",
    static_cast<unsigned long>(updates_), mode_.c_str(), x, y);
}

void TrackerNode::publish_marker(double x, double y, const rclcpp::Time & stamp)
{
  visualization_msgs::msg::Marker m;
  m.header.stamp = stamp;
  m.header.frame_id = frame_id_;
  m.ns = "target";
  m.id = 0;
  m.type = visualization_msgs::msg::Marker::SPHERE;
  m.action = visualization_msgs::msg::Marker::ADD;
  m.pose.position.x = x;
  m.pose.position.y = y;
  m.pose.position.z = 0.0;
  m.pose.orientation.w = 1.0;
  m.scale.x = marker_diameter_;
  m.scale.y = marker_diameter_;
  m.scale.z = marker_diameter_;
  m.color.r = 1.0F;
  m.color.g = 0.25F;
  m.color.b = 0.15F;
  m.color.a = 0.9F;
  marker_pub_->publish(m);
}

void TrackerNode::on_set_mode(
  const std::shared_ptr<hello_cv_interfaces::srv::SetTrackingMode::Request> request,
  std::shared_ptr<hello_cv_interfaces::srv::SetTrackingMode::Response> response)
{
  if (request->mode == "raw") {
    mode_ = "raw";
    response->success = true;
    response->message = "已切换为 raw（不平滑）";
  } else if (request->mode == "ema") {
    if (request->alpha <= 0.0 || request->alpha > 1.0) {
      response->success = false;
      response->message = "alpha 必须在 (0, 1]，收到 " + std::to_string(request->alpha);
      return;
    }
    mode_ = "ema";
    alpha_ = request->alpha;
    response->success = true;
    response->message = "已切换为 ema，alpha=" + std::to_string(alpha_);
  } else {
    response->success = false;
    response->message = "未知模式 '" + request->mode + "'，只支持 raw / ema";
  }

  RCLCPP_INFO(
    this->get_logger(), "服务调用：mode=%s -> %s（%s）",
    request->mode.c_str(), response->success ? "成功" : "失败", response->message.c_str());
}

}  // namespace hello_cv

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  // 默认构造用 rclcpp::NodeOptions()，所以 launch 里的参数全部从命令行/参数文件注入，
  // 节点内部不需要再写一遍参数——这也是为什么这里这么短。
  rclcpp::spin(std::make_shared<hello_cv::TrackerNode>());
  rclcpp::shutdown();
  return 0;
}

