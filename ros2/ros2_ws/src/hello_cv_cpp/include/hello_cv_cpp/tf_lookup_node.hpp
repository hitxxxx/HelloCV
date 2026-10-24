#ifndef HELLO_CV_CPP__TF_LOOKUP_NODE_HPP_
#define HELLO_CV_CPP__TF_LOOKUP_NODE_HPP_

#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"
#include "tf2_ros/buffer.h"
#include "tf2_ros/transform_listener.h"

namespace hello_cv
{

/// TF 监听节点：以固定频率查询 map -> target 的变换，并打印成"人话"。
/// 用来演示 tf2_ros::Buffer + TransformListener，以及查询失败的三种常见异常。
class TfLookupNode : public rclcpp::Node
{
public:
  explicit TfLookupNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  void on_timer();

  std::string target_frame_{"map"};
  std::string source_frame_{"target"};
  double rate_hz_{1.0};

  std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
  std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
  rclcpp::TimerBase::SharedPtr timer_;
};

}  // namespace hello_cv

#endif  // HELLO_CV_CPP__TF_LOOKUP_NODE_HPP_
