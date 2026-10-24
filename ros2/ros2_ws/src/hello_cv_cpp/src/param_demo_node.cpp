#include "hello_cv_cpp/param_demo_node.hpp"

#include <chrono>
#include <functional>
#include <string>
#include <vector>

namespace hello_cv
{

ParamDemoNode::ParamDemoNode(const rclcpp::NodeOptions & options)
: rclcpp::Node("param_demo_node", options)
{
  // declare_parameter 的第二个参数既是"默认值"，也决定了参数的类型。
  // 类型一旦确定，命令行 set 成别的类型会直接失败——这是 ROS2 参数的类型安全。
  counter_ = this->declare_parameter<int64_t>("counter", 0);
  threshold_ = this->declare_parameter<double>("threshold", 0.5);
  verbose_ = this->declare_parameter<bool>("verbose", true);
  mode_ = this->declare_parameter<std::string>("mode", "demo");
  frame_id_ = this->declare_parameter<std::string>("frame_id", "map");

  param_cb_ = this->add_on_set_parameters_callback(
    std::bind(&ParamDemoNode::on_parameter_set, this, std::placeholders::_1));

  timer_ = this->create_wall_timer(
    std::chrono::seconds(2), std::bind(&ParamDemoNode::on_timer, this));

  RCLCPP_INFO(
    this->get_logger(), "param_demo_node 启动，用 ros2 param list /param_demo_node 查看参数");
}

rcl_interfaces::msg::SetParametersResult ParamDemoNode::on_parameter_set(
  const std::vector<rclcpp::Parameter> & params)
{
  rcl_interfaces::msg::SetParametersResult result;
  result.successful = true;
  result.reason = "ok";

  // 第一步：只校验，不改任何成员。全部合法才进入第二步。
  // 这样批量设置时不会出现「改了一半」的中间状态。
  for (const auto & p : params) {
    if (p.get_name() == "threshold") {
      const double v = p.as_double();
      if (v < 0.0 || v > 1.0) {
        result.successful = false;
        result.reason = "threshold 必须落在 [0.0, 1.0]，收到 " + std::to_string(v);
        return result;
      }
    } else if (p.get_name() == "mode") {
      const std::string v = p.as_string();
      if (v != "demo" && v != "production" && v != "debug") {
        result.successful = false;
        result.reason = "mode 只允许 demo / production / debug，收到 " + v;
        return result;
      }
    } else if (p.get_name() == "counter") {
      if (p.as_int() < 0) {
        result.successful = false;
        result.reason = "counter 不能为负数";
        return result;
      }
    }
  }

  // 第二步：校验通过，同步到成员变量
  for (const auto & p : params) {
    if (p.get_name() == "threshold") {
      threshold_ = p.as_double();
    } else if (p.get_name() == "mode") {
      mode_ = p.as_string();
    } else if (p.get_name() == "verbose") {
      verbose_ = p.as_bool();
    } else if (p.get_name() == "counter") {
      counter_ = p.as_int();
    } else if (p.get_name() == "frame_id") {
      frame_id_ = p.as_string();
    }
    ++param_changes_;
  }

  // ⚠️ 这里刻意**不**调用 this->set_parameter()。
  // 参数回调本身就在"设置参数"的临界区里，回调里再 set 会重入同一把锁，
  // 轻则多触发一次回调，重则直接死锁。要联动别的参数，应该用定时器/线程延后做。
  RCLCPP_INFO(
    this->get_logger(), "参数更新：threshold=%.2f mode=%s verbose=%d（累计 %ld 次）",
    threshold_, mode_.c_str(), static_cast<int>(verbose_),
    static_cast<long>(param_changes_));
  return result;
}

void ParamDemoNode::on_timer()
{
  if (!verbose_) {
    return;
  }
  RCLCPP_INFO(
    this->get_logger(), "[%ld] mode=%s threshold=%.2f frame_id=%s",
    static_cast<long>(counter_), mode_.c_str(), threshold_, frame_id_.c_str());
}

}  // namespace hello_cv

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  // 默认构造用 rclcpp::NodeOptions()，所以 launch 里的参数全部从命令行/参数文件注入，
  // 节点内部不需要再写一遍参数——这也是为什么这里这么短。
  rclcpp::spin(std::make_shared<hello_cv::ParamDemoNode>());
  rclcpp::shutdown();
  return 0;
}

