#include "hello_cv_cpp/detector_node.hpp"

#include <algorithm>
#include <functional>
#include <string>
#include <utility>
#include <vector>

#include "hello_cv_cpp/vision_utils.hpp"

namespace hello_cv
{

DetectorNode::DetectorNode(const rclcpp::NodeOptions & options)
: rclcpp::Node("detector_node", options)
{
  intensity_threshold_ = this->declare_parameter<int>("intensity_threshold", 180);
  min_area_ = this->declare_parameter<int>("min_area", 200);
  max_area_ = this->declare_parameter<int>("max_area", 50000);
  expected_area_ = std::max(1.0, this->declare_parameter<double>("expected_area", 1020.0));
  qos_reliability_ = this->declare_parameter<std::string>("qos_reliability", "reliable");

  // ---------- 订阅 ----------
  // 用 sensor_data 这类 profile 也行；这里显式写出来，方便和相机端对比。
  rclcpp::QoS qos(rclcpp::KeepLast(10));
  if (qos_reliability_ == "best_effort") {
    qos.best_effort();
  } else {
    qos.reliable();
  }
  qos.durability_volatile();

  image_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
    "image_raw", qos,
    std::bind(&DetectorNode::on_image, this, std::placeholders::_1));

  detection_pub_ =
    this->create_publisher<hello_cv_interfaces::msg::Detection>("detection", rclcpp::QoS(10));

  // ---------- 参数回调 ----------
  // add_on_set_parameters_callback 注册的是「即将生效前」的钩子：
  // 返回 successful=false 就相当于否决这次修改，命令行会看到失败原因。
  param_cb_ = this->add_on_set_parameters_callback(
    std::bind(&DetectorNode::on_parameter_set, this, std::placeholders::_1));

  RCLCPP_INFO(
    this->get_logger(),
    "detector_node 启动：threshold=%d，min_area=%d，QoS=%s",
    intensity_threshold_, min_area_, qos_reliability_.c_str());
}

rcl_interfaces::msg::SetParametersResult DetectorNode::on_parameter_set(
  const std::vector<rclcpp::Parameter> & params)
{
  rcl_interfaces::msg::SetParametersResult result;
  result.successful = true;
  result.reason = "ok";

  for (const auto & p : params) {
    if (p.get_name() == "intensity_threshold") {
      const int v = static_cast<int>(p.as_int());
      if (v < 0 || v > 255) {
        result.successful = false;
        result.reason = "intensity_threshold 必须在 [0, 255]，收到 " + std::to_string(v);
        return result;  // 提前返回：不修改任何成员，保证"失败就是全不变"
      }
      intensity_threshold_ = v;
    } else if (p.get_name() == "min_area") {
      const int v = static_cast<int>(p.as_int());
      if (v < 1) {
        result.successful = false;
        result.reason = "min_area 必须 >= 1，收到 " + std::to_string(v);
        return result;
      }
      min_area_ = v;
    } else if (p.get_name() == "max_area") {
      max_area_ = static_cast<int>(p.as_int());
    } else if (p.get_name() == "expected_area") {
      expected_area_ = std::max(1.0, p.as_double());
    }
    // 其他参数（比如 qos_reliability）改了也不生效——QoS 在 create_publisher 时就固定了，
    // 这里刻意不处理，正好用来在笔记里说明「哪些参数能热改、哪些不能」。
  }

  RCLCPP_INFO(this->get_logger(), "参数已更新：threshold=%d min_area=%d", intensity_threshold_, min_area_);
  return result;
}

void DetectorNode::on_image(const sensor_msgs::msg::Image::ConstSharedPtr & msg)
{
  ++frames_;

  // 防御：假设别人可能发别的编码/坏数据过来，节点不能因为一条怪消息就崩
  if (msg->encoding != "mono8") {
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 2000,
      "只支持 mono8，收到 %s，已忽略", msg->encoding.c_str());
    return;
  }
  const std::size_t need =
    static_cast<std::size_t>(msg->step) * static_cast<std::size_t>(msg->height);
  if (msg->data.size() < need) {
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 2000,
      "data 长度 %zu 小于 step*height=%zu，已忽略", msg->data.size(), need);
    return;
  }

  const BlobResult blob = find_bright_blob(
    msg->data.data(),
    static_cast<int>(msg->width), static_cast<int>(msg->height),
    static_cast<int>(msg->step),
    intensity_threshold_, min_area_);

  hello_cv_interfaces::msg::Detection det;
  // 直接沿用图像的 header：时间戳和 frame_id 完全对齐，下游做 TF 查表时才不会"时间对不上"
  det.header = msg->header;
  det.found = blob.found && blob.area <= static_cast<double>(max_area_);
  if (det.found) {
    det.cx = static_cast<float>(blob.cx);
    det.cy = static_cast<float>(blob.cy);
    det.area = static_cast<float>(blob.area);
    det.confidence = static_cast<float>(
      std::clamp(blob.area / expected_area_, 0.0, 1.0));
    ++detections_;
  } else {
    det.cx = 0.0F;
    det.cy = 0.0F;
    det.area = 0.0F;
    det.confidence = 0.0F;
  }

  detection_pub_->publish(det);

  RCLCPP_INFO_THROTTLE(
    this->get_logger(), *this->get_clock(), 1000,
    "frames=%lu detections=%lu 最近一帧: found=%d (%.1f, %.1f) area=%.0f",
    static_cast<unsigned long>(frames_), static_cast<unsigned long>(detections_),
    static_cast<int>(det.found), det.cx, det.cy, det.area);
}

}  // namespace hello_cv

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  // 默认构造用 rclcpp::NodeOptions()，所以 launch 里的参数全部从命令行/参数文件注入，
  // 节点内部不需要再写一遍参数——这也是为什么这里这么短。
  rclcpp::spin(std::make_shared<hello_cv::DetectorNode>());
  rclcpp::shutdown();
  return 0;
}

