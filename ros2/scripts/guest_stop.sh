#!/usr/bin/env bash
# 清掉所有本项目相关的节点/launch 进程。
#
# 两个坑（都真的踩过）：
#   1. 不要把这些模式直接写进 ssh 的命令行里——pkill -f 会匹配到那条 ssh 命令本身，
#      把自己的 shell 一起杀掉，ssh 直接返回 255。
#   2. Linux 的进程名（comm）被内核截断到 15 个字符，所以 lifecycle_mission_node、
#      static_transform_publisher、mode_service_client 这类长名字用 pkill -x 是匹不上的，
#      只会"看起来执行了"，进程其实还在。
source /opt/ros/humble/setup.bash 2>/dev/null
source "$HOME/ros2_ws/install/setup.bash" 2>/dev/null

# 短名字：按进程名精确匹配
for p in camera_node detector_node tracker_node tf_lookup_node param_demo_node; do
  pkill -x "$p" 2>/dev/null
done

# 长名字（>15 字符）：只能按命令行匹配
pkill -f 'lifecycle_mission_node' 2>/dev/null
pkill -f 'static_transform_publisher' 2>/dev/null
pkill -f 'mode_service_client' 2>/dev/null

# launch 拉起的进程组
pkill -f 'bin/ros2 launch hello_cv_cpp' 2>/dev/null
pkill -f 'ros2_ws/install/hello_cv_cpp/lib' 2>/dev/null

sleep 2
ros2 node list 2>/dev/null || true
