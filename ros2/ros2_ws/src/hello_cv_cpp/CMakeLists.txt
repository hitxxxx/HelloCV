cmake_minimum_required(VERSION 3.8)
project(hello_cv_cpp)

# -Wall -Wextra 只是警告，不开 -Werror：ROS2 头文件本身偶尔也会告警，
# 一开 -Werror 就会因为"别人的头文件"编译失败。
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ---------- 1. 找依赖 ----------
find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(rcl_interfaces REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(hello_cv_interfaces REQUIRED)

# ---------- 2. 纯算法静态库 ----------
# 抽成库的目的：detector 和 test 都能链接它，而它本身完全不依赖 ROS。
add_library(hello_cv_vision SHARED src/vision_utils.cpp)
target_include_directories(hello_cv_vision PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)

# ---------- 3. 各个可执行节点 ----------
# 每个 add_executable 对应一个 src/*.cpp，里面自带 main()
add_executable(camera_node src/camera_node.cpp)
ament_target_dependencies(camera_node rclcpp std_msgs sensor_msgs)

add_executable(detector_node src/detector_node.cpp)
target_link_libraries(detector_node hello_cv_vision)
ament_target_dependencies(detector_node rclcpp rcl_interfaces std_msgs sensor_msgs hello_cv_interfaces)

add_executable(tracker_node src/tracker_node.cpp)
target_link_libraries(tracker_node hello_cv_vision)
ament_target_dependencies(tracker_node
  rclcpp std_msgs geometry_msgs visualization_msgs tf2 tf2_ros hello_cv_interfaces)

add_executable(tf_lookup_node src/tf_lookup_node.cpp)
ament_target_dependencies(tf_lookup_node rclcpp geometry_msgs tf2 tf2_ros)

add_executable(param_demo_node src/param_demo_node.cpp)
ament_target_dependencies(param_demo_node rclcpp rcl_interfaces)

add_executable(lifecycle_mission_node src/lifecycle_mission_node.cpp)
ament_target_dependencies(lifecycle_mission_node rclcpp rclcpp_lifecycle std_msgs)

add_executable(mode_service_client src/mode_service_client.cpp)
ament_target_dependencies(mode_service_client rclcpp hello_cv_interfaces)

# ---------- 4. 安装 ----------
install(TARGETS
  hello_cv_vision
  camera_node
  detector_node
  tracker_node
  tf_lookup_node
  param_demo_node
  lifecycle_mission_node
  mode_service_client
  DESTINATION lib/${PROJECT_NAME}
)

# launch / config / rviz 必须 install，否则 `ros2 launch` 在别的目录下找不到它们。
# 配合 `colcon build --symlink-install` 时，这里会变成软链接，改完不用重新编译。
install(DIRECTORY launch config rviz
  DESTINATION share/${PROJECT_NAME}
)

# ---------- 5. 测试 ----------
if(BUILD_TESTING)
  find_package(ament_cmake_gtest REQUIRED)

  ament_add_gtest(test_vision test/test_vision.cpp)
  target_link_libraries(test_vision hello_cv_vision)
endif()

ament_package()
