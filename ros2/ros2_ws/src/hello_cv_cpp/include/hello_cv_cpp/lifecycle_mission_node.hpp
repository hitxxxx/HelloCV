#ifndef HELLO_CV_CPP__LIFECYCLE_MISSION_NODE_HPP_
#define HELLO_CV_CPP__LIFECYCLE_MISSION_NODE_HPP_

#include <memory>
#include <string>

#include "rclcpp_lifecycle/lifecycle_node.hpp"
#include "rclcpp_lifecycle/lifecycle_publisher.hpp"
#include "std_msgs/msg/string.hpp"

namespace hello_cv
{

/// 受管节点（LifecycleNode）示例：一个"任务播报器"。
/// 它只在自己被 activate 之后才真正干活，configure / activate / deactivate /
/// cleanup 四个状态切换都用 ros2 lifecycle set 触发，可以清楚看到资源何时分配、何时释放。
class LifecycleMissionNode : public rclcpp_lifecycle::LifecycleNode
{
public:
  explicit LifecycleMissionNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  using CallbackReturn =
    rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;

  CallbackReturn on_configure(const rclcpp_lifecycle::State & state) override;
  CallbackReturn on_activate(const rclcpp_lifecycle::State & state) override;
  CallbackReturn on_deactivate(const rclcpp_lifecycle::State & state) override;
  CallbackReturn on_cleanup(const rclcpp_lifecycle::State & state) override;
  CallbackReturn on_shutdown(const rclcpp_lifecycle::State & state) override;

  void on_timer();

  rclcpp_lifecycle::LifecyclePublisher<std_msgs::msg::String>::SharedPtr status_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
  int ticks_{0};
  std::string mission_name_{"hello_cv_vision"};
};

}  // namespace hello_cv

#endif  // HELLO_CV_CPP__LIFECYCLE_MISSION_NODE_HPP_
