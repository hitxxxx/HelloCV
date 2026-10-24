#include "hello_cv_cpp/tf_lookup_node.hpp"

#include <chrono>
#include <cmath>
#include <functional>
#include <memory>
#include <string>

#include "tf2/exceptions.h"
#include "tf2/time.h"

namespace hello_cv
{

TfLookupNode::TfLookupNode(const rclcpp::NodeOptions & options)
: rclcpp::Node("tf_lookup_node", options)
{
  target_frame_ = this->declare_parameter<std::string>("target_frame", "map");
  source_frame_ = this->declare_parameter<std::string>("source_frame", "target");
  rate_hz_ = this->declare_parameter<double>("rate_hz", 1.0);
  rate_hz_ = std::max(0.1, rate_hz_);

  // Buffer 是"缓存 + 插值"的核心：它需要 clock 才能处理时间戳
  tf_buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
  // 多传一个 spin_thread=true，Listener 会自己开线程收 /tf；
  // 不传的话要求主线程在 spin，否则订阅回调永远不会被触发（这是新手最常踩的坑之一）。
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_, this, true);

  const auto period = std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::duration<double>(1.0 / rate_hz_));
  timer_ = this->create_wall_timer(period, std::bind(&TfLookupNode::on_timer, this));

  RCLCPP_INFO(
    this->get_logger(), "tf_lookup_node 启动：查询 %s -> %s，%.1f Hz",
    target_frame_.c_str(), source_frame_.c_str(), rate_hz_);
}

void TfLookupNode::on_timer()
{
  // tf2::TimePointZero = "用缓存里最新的一帧"，而不是"现在"。
  // 用 now() 会经常踩到 ExtrapolationException（未来的数据还没到）。
  try {
    const geometry_msgs::msg::TransformStamped ts =
      tf_buffer_->lookupTransform(target_frame_, source_frame_, tf2::TimePointZero);

    const auto & p = ts.transform.translation;
    const double dist = std::hypot(p.x, p.y);
    RCLCPP_INFO(
      this->get_logger(),
      "%s -> %s: (%.3f, %.3f, %.3f) m，距原点 %.3f m",
      target_frame_.c_str(), source_frame_.c_str(), p.x, p.y, p.z, dist);
  } catch (const tf2::LookupException & ex) {
    // 帧名根本不存在（拼错、或者发布者没起来）
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 2000, "LookupException: %s", ex.what());
  } catch (const tf2::ConnectivityException & ex) {
    // 两帧之间没有连通的变换链
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 2000, "ConnectivityException: %s", ex.what());
  } catch (const tf2::ExtrapolationException & ex) {
    // 时间戳对不上（缓存里只有"过去"或"未来"的数据）
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 2000, "ExtrapolationException: %s", ex.what());
  } catch (const tf2::TransformException & ex) {
    // 兜底：tf2 的所有异常都继承自它
    RCLCPP_WARN_THROTTLE(
      this->get_logger(), *this->get_clock(), 2000, "TransformException: %s", ex.what());
  }
}

}  // namespace hello_cv

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  // 默认构造用 rclcpp::NodeOptions()，所以 launch 里的参数全部从命令行/参数文件注入，
  // 节点内部不需要再写一遍参数——这也是为什么这里这么短。
  rclcpp::spin(std::make_shared<hello_cv::TfLookupNode>());
  rclcpp::shutdown();
  return 0;
}

