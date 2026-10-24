#include "hello_cv_cpp/camera_node.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <memory>
#include <utility>

namespace hello_cv
{

CameraNode::CameraNode(const rclcpp::NodeOptions & options)
: rclcpp::Node("camera_node", options)
{
  // ---------- 1. 声明参数 ----------
  // ROS2 里「用之前必须声明」，否则 get_parameter 会抛 ParameterNotDeclaredException。
  // 这里同时给出默认值，参数文件里没写的就用默认值。
  width_ = this->declare_parameter<int>("width", 320);
  height_ = this->declare_parameter<int>("height", 240);
  fps_ = std::max(1.0, this->declare_parameter<double>("fps", 30.0));
  radius_ = this->declare_parameter<double>("blob_radius", 26.0);
  omega_ = this->declare_parameter<double>("omega", 0.8);
  center_x_ = this->declare_parameter<double>("center_x", width_ / 2.0);
  center_y_ = this->declare_parameter<double>("center_y", height_ / 2.0);
  orbit_r_ = this->declare_parameter<double>("orbit_radius", 70.0);
  noise_sigma_ = this->declare_parameter<double>("noise_sigma", 6.0);
  background_ = this->declare_parameter<int>("background", 28);
  frame_id_ = this->declare_parameter<std::string>("frame_id", "camera_link");
  qos_reliability_ = this->declare_parameter<std::string>("qos_reliability", "reliable");

  // 参数文件里的值可能超出合理范围，这里做一次"防御性收口"，
  // 免得面积算错、或者 width 为负数导致 data 长度爆炸。
  width_ = std::clamp(width_, 16, 4096);
  height_ = std::clamp(height_, 16, 4096);
  noise_dist_ = std::normal_distribution<double>(0.0, noise_sigma_);
  rng_.seed(static_cast<std::mt19937::result_type>(
    this->declare_parameter<int>("seed", 42)));

  // ---------- 2. 建发布者 ----------
  // QoS 必须在 create_publisher 时一次性给定，运行中改不了——这是它和参数最大的区别。
  image_pub_ = this->create_publisher<sensor_msgs::msg::Image>("image_raw", make_qos());

  // ---------- 3. 定时器 ----------
  const auto period = std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::duration<double>(1.0 / fps_));
  last_stamp_ = std::chrono::steady_clock::now();
  timer_ = this->create_wall_timer(period, std::bind(&CameraNode::on_timer, this));

  RCLCPP_INFO(
    this->get_logger(),
    "camera_node 启动：%dx%d @ %.1f Hz，frame_id=%s，QoS=%s",
    width_, height_, fps_, frame_id_.c_str(), qos_reliability_.c_str());
}

rclcpp::QoS CameraNode::make_qos() const
{
  // 深度 10 + 只保留最新 10 帧；可靠性由参数决定，方便做 QoS 对比实验
  rclcpp::QoS qos(rclcpp::KeepLast(10));
  if (qos_reliability_ == "best_effort") {
    qos.best_effort();
  } else {
    qos.reliable();
  }
  qos.durability_volatile();  // 不缓存给"后来才连上的订阅者"，符合传感器数据的语义
  return qos;
}

void CameraNode::on_timer()
{
  const auto now = std::chrono::steady_clock::now();
  const double dt = std::chrono::duration<double>(now - last_stamp_).count();
  last_stamp_ = now;
  elapsed_ += dt;

  auto msg = std::make_unique<sensor_msgs::msg::Image>();
  msg->header.stamp = this->now();
  msg->header.frame_id = frame_id_;
  msg->height = static_cast<uint32_t>(height_);
  msg->width = static_cast<uint32_t>(width_);
  msg->encoding = "mono8";      // 单通道 8 位灰度：一个像素一个字节，最省事也最够用
  msg->is_bigendian = 0;
  msg->step = static_cast<uint32_t>(width_);  // 每行字节数，mono8 时等于宽度
  msg->data.assign(
    static_cast<std::size_t>(width_) * static_cast<std::size_t>(height_), 0);

  // 亮斑中心：绕 (center_x_, center_y_) 做圆周运动
  const double cx = center_x_ + orbit_r_ * std::cos(elapsed_ * omega_);
  const double cy = center_y_ + orbit_r_ * std::sin(elapsed_ * omega_);

  // 只在这块矩形里算亮斑，其余像素纯背景
  const int reach = static_cast<int>(std::ceil(radius_)) + 1;
  const int x0 = std::max(0, static_cast<int>(cx) - reach);
  const int x1 = std::min(width_ - 1, static_cast<int>(cx) + reach);
  const int y0 = std::max(0, static_cast<int>(cy) - reach);
  const int y1 = std::min(height_ - 1, static_cast<int>(cy) + reach);

  // 亮斑形状：中心一块饱和的平台 + 半个半径宽的平滑过渡带（smoothstep）。
  //
  // 为什么不用高斯？第一版就是高斯（sigma = radius/3），算了一下：
  // 峰值 227、背景 28、阈值 180 时，能过阈值的半径只有 ~7.7 像素，面积约 181；
  // 而 min_area 默认 200 —— 也就是说「默认参数下这个节点根本检测不到目标」。
  // 高斯太尖，阈值稍高就只剩中心几个像素。改成「平台 + 过渡带」之后：
  //   阈值 180 圈住的半径 ≈ radius - 0.62 * edge ≈ 18 px，面积约 1.0e3 像素，
  //   既在 min_area 之上，调阈值也能看到面积单调变化（见 docs/yuque/04）。
  const double edge = std::max(1.0, radius_ * 0.5);

  for (int y = 0; y < height_; ++y) {
    uint8_t * row = msg->data.data() + static_cast<std::size_t>(y) * static_cast<std::size_t>(msg->step);
    for (int x = 0; x < width_; ++x) {
      // 背景：一个固定灰度 + 高斯噪声，模拟真实相机的底噪
      double value = static_cast<double>(background_) + noise_dist_(rng_);
      if (x >= x0 && x <= x1 && y >= y0 && y <= y1) {
        const double d = std::hypot(x - cx, y - cy);
        const double u = std::clamp((radius_ - d) / edge, 0.0, 1.0);
        const double s = u * u * (3.0 - 2.0 * u);   // smoothstep：0 -> 1 平滑过渡
        value += 227.0 * s;
      }
      row[x] = static_cast<uint8_t>(std::clamp(value, 0.0, 255.0));
    }
  }

  image_pub_->publish(std::move(msg));
}

}  // namespace hello_cv

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  // 默认构造用 rclcpp::NodeOptions()，所以 launch 里的参数全部从命令行/参数文件注入，
  // 节点内部不需要再写一遍参数——这也是为什么这里这么短。
  rclcpp::spin(std::make_shared<hello_cv::CameraNode>());
  rclcpp::shutdown();
  return 0;
}

