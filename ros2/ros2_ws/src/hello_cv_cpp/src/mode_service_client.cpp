// 简单的 C++ 服务客户端：命令行切跟踪模式。
//   ros2 run hello_cv_cpp mode_service_client ema 0.6
//   ros2 run hello_cv_cpp mode_service_client raw
#include <chrono>
#include <cstdlib>
#include <memory>
#include <string>

#include "rclcpp/rclcpp.hpp"

#include "hello_cv_interfaces/srv/set_tracking_mode.hpp"

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);

  auto node = rclcpp::Node::make_shared("mode_service_client");
  auto client = node->create_client<hello_cv_interfaces::srv::SetTrackingMode>("set_mode");

  const std::string mode = (argc > 1) ? argv[1] : "ema";
  const double alpha = (argc > 2) ? std::atof(argv[2]) : 0.35;

  // 服务可能还没起来（tracker_node 启动比较晚），等最多 5 秒再放弃
  if (!client->wait_for_service(std::chrono::seconds(5))) {
    RCLCPP_ERROR(node->get_logger(), "等待服务 /set_mode 超时：tracker_node 启动了吗？");
    rclcpp::shutdown();
    return 1;
  }

  auto request = std::make_shared<hello_cv_interfaces::srv::SetTrackingMode::Request>();
  request->mode = mode;
  request->alpha = alpha;

  auto future = client->async_send_request(request);

  // 这里必须 spin 一下：async_send_request 只把请求塞进队列，
  // 真正的收发要靠 executor 跑起来才会完成 future。
  const auto ret = rclcpp::spin_until_future_complete(node, future);
  int exit_code = 0;
  if (ret == rclcpp::FutureReturnCode::SUCCESS) {
    const auto response = future.get();
    if (response->success) {
      RCLCPP_INFO(node->get_logger(), "切换成功：%s", response->message.c_str());
    } else {
      RCLCPP_WARN(node->get_logger(), "服务端拒绝了请求：%s", response->message.c_str());
      exit_code = 2;
    }
  } else {
    RCLCPP_ERROR(node->get_logger(), "服务调用失败（超时或被中断）");
    exit_code = 3;
  }

  rclcpp::shutdown();
  return exit_code;
}
