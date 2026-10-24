#ifndef HELLO_CV_CPP__PARAM_DEMO_NODE_HPP_
#define HELLO_CV_CPP__PARAM_DEMO_NODE_HPP_

#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rclcpp/rclcpp.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"

namespace hello_cv
{

/// 参数演示节点：把 ROS2 支持的常见参数类型都声明一遍，
/// 并用参数回调做「范围校验 + 失败即整体不改」，专门用来演示
/// ros2 param list/get/set/dump/load 这一套命令。
class ParamDemoNode : public rclcpp::Node
{
public:
  explicit ParamDemoNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

private:
  void on_timer();
  rcl_interfaces::msg::SetParametersResult on_parameter_set(
    const std::vector<rclcpp::Parameter> & params);

  int64_t counter_{0};
  double threshold_{0.5};
  bool verbose_{true};
  std::string mode_{"demo"};
  std::string frame_id_{"map"};

  int64_t param_changes_{0};  ///< 统计被成功修改过多少次（仅内部状态，不对外暴露成参数）
  rclcpp::TimerBase::SharedPtr timer_;
  rclcpp::node_interfaces::OnSetParametersCallbackHandle::SharedPtr param_cb_;
};

}  // namespace hello_cv

#endif  // HELLO_CV_CPP__PARAM_DEMO_NODE_HPP_
