cmake_minimum_required(VERSION 3.8)
project(hello_cv_interfaces)

# 这个包只做一件事：把 .msg / .srv 编译成 C++、Python 都能用的头文件与模块。
# 它不产生可执行文件，所以没有 add_executable。

find_package(ament_cmake REQUIRED)
# rosidl_default_generators 提供 rosidl_generate_interfaces() 这个 CMake 宏
find_package(rosidl_default_generators REQUIRED)
# 消息里用到了 std_msgs/Header，所以必须先找到 std_msgs
find_package(std_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Detection.msg"
  "srv/SetTrackingMode.srv"
  DEPENDENCIES std_msgs
)

# 让其他包在运行期能加载到编译出来的类型支持库（typesupport）
ament_export_dependencies(rosidl_default_runtime)

ament_package()
