#include "hello_cv_cpp/lifecycle_mission_node.hpp"

#include <chrono>
#include <functional>
#include <memory>
#include <string>
#include <utility>

namespace hello_cv
{

LifecycleMissionNode::LifecycleMissionNode(const rclcpp::NodeOptions & options)
: rclcpp_lifecycle::LifecycleNode("mission_node", options)
{
  mission_name_ = this->declare_parameter<std::string>("mission_name", "hello_cv_vision");
  RCLCPP_INFO(
    this->get_logger(),
    "mission_node 已创建，当前状态 = %s（还没有申请任何资源）",
    this->get_current_state().label().c_str());
}

LifecycleMissionNode::CallbackReturn LifecycleMissionNode::on_configure(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  // configure 阶段：只申请"占了不干活"的资源（话题、定时器、内存），
  // 不对外发布数据。好处是可以在启动时统一准备好，等外部给指令再 activate。
  status_pub_ = this->create_publisher<std_msgs::msg::String>("mission_status", 10);
  timer_ = this->create_wall_timer(
    std::chrono::seconds(1), std::bind(&LifecycleMissionNode::on_timer, this));

  RCLCPP_INFO(this->get_logger(), "on_configure(): 已创建 publisher 与 1Hz 定时器");
  return CallbackReturn::SUCCESS;
}

LifecycleMissionNode::CallbackReturn LifecycleMissionNode::on_activate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  // 受管节点里的 publisher 默认是"关闭"的，必须显式 on_activate 才会真的发数据。
  status_pub_->on_activate();
  ticks_ = 0;
  RCLCPP_INFO(this->get_logger(), "on_activate(): 开始发布任务状态");
  return CallbackReturn::SUCCESS;
}

LifecycleMissionNode::CallbackReturn LifecycleMissionNode::on_deactivate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  status_pub_->on_deactivate();
  RCLCPP_INFO(this->get_logger(), "on_deactivate(): 停止发布（资源仍保留）");
  return CallbackReturn::SUCCESS;
}

LifecycleMissionNode::CallbackReturn LifecycleMissionNode::on_cleanup(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  // cleanup 阶段：释放 configure 时申请的资源，回到 unconfigured。
  timer_->cancel();
  timer_.reset();
  status_pub_.reset();
  ticks_ = 0;
  RCLCPP_INFO(this->get_logger(), "on_cleanup(): 已释放 publisher 与定时器");
  return CallbackReturn::SUCCESS;
}

LifecycleMissionNode::CallbackReturn LifecycleMissionNode::on_shutdown(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  RCLCPP_WARN(this->get_logger(), "on_shutdown(): 收到 shutdown 请求");
  if (timer_) {
    timer_->cancel();
    timer_.reset();
  }
  status_pub_.reset();
  return CallbackReturn::SUCCESS;
}

void LifecycleMissionNode::on_timer()
{
  ++ticks_;
  std_msgs::msg::String msg;
  msg.data = mission_name_ + " ticking #" + std::to_string(ticks_);
  status_pub_->publish(msg);

  RCLCPP_INFO(this->get_logger(), "发布：%s", msg.data.c_str());
}

}  // namespace hello_cv

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  // 默认构造用 rclcpp::NodeOptions()，所以 launch 里的参数全部从命令行/参数文件注入，
  // 节点内部不需要再写一遍参数——这也是为什么这里这么短。
  rclcpp::spin(std::make_shared<hello_cv::LifecycleMissionNode>());
  rclcpp::shutdown();
  return 0;
}

