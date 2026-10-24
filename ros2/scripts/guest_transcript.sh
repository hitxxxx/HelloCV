#!/usr/bin/env bash
# 在虚拟机里把笔记 03「命令行工具实操」涉及的命令真跑一遍，输出成一份可粘贴的实录。
# 用法：bash guest_transcript.sh > /tmp/transcript.txt
set -o pipefail
source /opt/ros/humble/setup.bash
source "$HOME/ros2_ws/install/setup.bash"
cd "$HOME/ros2_ws"

run() {                 # run <命令...>：先回显 $ 命令，再跑，输出原样
  printf '\n$ %s\n' "$*"
  "$@" 2>&1
}

echo "############ 0. 环境"
printf '\n$ ros2 --version-ish\n'
ros2 pkg prefix hello_cv_cpp
printf '\n$ printenv ROS_DISTRO\n'; printenv ROS_DISTRO

echo
echo "############ 1. 编译产物"
run ros2 pkg executables hello_cv_cpp
run ros2 interface show hello_cv_interfaces/msg/Detection

echo
echo "############ 2. 起流水线（后台），等 12 秒"
setsid nohup ros2 launch hello_cv_cpp full_pipeline.launch.py > /tmp/pl.log 2>&1 < /dev/null &
sleep 12

run ros2 node list
printf '\n$ ros2 node info /camera_node\n'
ros2 node info /camera_node 2>&1

echo
echo "############ 3. 话题"
run ros2 topic list -t
printf '\n$ ros2 topic info -v /vision/detection\n'
ros2 topic info -v /vision/detection 2>&1
printf '\n$ ros2 topic echo /vision/detection --once --no-arr\n'
timeout 6 ros2 topic echo /vision/detection --once --no-arr 2>&1
printf '\n$ timeout 5 ros2 topic hz /camera/image_raw\n'
timeout 5 ros2 topic hz /camera/image_raw 2>&1 | tail -3
printf '\n$ timeout 6 ros2 topic bw /camera/image_raw\n'
timeout 6 ros2 topic bw /camera/image_raw 2>&1 | tail -3

echo
echo "############ 4. 服务"
run ros2 service list -t
printf '\n$ ros2 service type /set_mode\n'
ros2 service type /set_mode 2>&1
printf '\n$ ros2 service call /set_mode hello_cv_interfaces/srv/SetTrackingMode "{mode: raw}"\n'
ros2 service call /set_mode hello_cv_interfaces/srv/SetTrackingMode "{mode: raw}" 2>&1

echo
echo "############ 5. 参数"
printf '\n$ ros2 param list /tracker_node\n'
ros2 param list /tracker_node 2>&1
printf '\n$ ros2 param get /tracker_node alpha\n'
ros2 param get /tracker_node alpha 2>&1
printf '\n$ ros2 param set /tracker_node alpha 0.5\n'
ros2 param set /tracker_node alpha 0.5 2>&1
printf '\n$ ros2 param get /tracker_node alpha\n'
ros2 param get /tracker_node alpha 2>&1
printf '\n$ ros2 param set /tracker_node alpha 1.5   # 非法值\n'
ros2 param set /tracker_node alpha 1.5 2>&1

echo
echo "############ 6. TF"
printf '\n$ timeout 6 ros2 run tf2_ros tf2_echo map target\n'
timeout 6 ros2 run tf2_ros tf2_echo map target 2>&1 | tail -8

echo
echo "############ 7. 受管节点（另起一个，避免和流水线抢）"
ros2 daemon stop > /dev/null 2>&1   # 清掉 CLI 的节点缓存，否则刚起的节点可能查不到
setsid nohup ros2 run hello_cv_cpp lifecycle_mission_node > /tmp/lc.log 2>&1 < /dev/null &
sleep 6
printf '\n$ ros2 lifecycle get /mission_node\n'
ros2 lifecycle get /mission_node 2>&1
printf '\n$ ros2 lifecycle set /mission_node configure\n'
ros2 lifecycle set /mission_node configure 2>&1
sleep 2   # 状态切换是异步的：不等这一步，下一条命令会报 Unknown transition requested
printf '\n$ ros2 lifecycle get /mission_node\n'
ros2 lifecycle get /mission_node 2>&1
printf '\n$ ros2 lifecycle set /mission_node activate\n'
ros2 lifecycle set /mission_node activate 2>&1
sleep 3
printf '\n$ ros2 lifecycle get /mission_node\n'
ros2 lifecycle get /mission_node 2>&1
printf '\n$ ros2 lifecycle set /mission_node deactivate\n'
ros2 lifecycle set /mission_node deactivate 2>&1
sleep 2
printf '\n$ ros2 lifecycle set /mission_node cleanup\n'
ros2 lifecycle set /mission_node cleanup 2>&1
sleep 1
printf '\n$ ros2 lifecycle get /mission_node\n'
ros2 lifecycle get /mission_node 2>&1

echo
echo "############ 8. 收尾"
pkill -x lifecycle_mission_node 2>/dev/null
pkill -f "bin/ros2 launch hello_cv_cpp" 2>/dev/null
pkill -x camera_node 2>/dev/null
pkill -x detector_node 2>/dev/null
pkill -x tracker_node 2>/dev/null
pkill -x tf_lookup_node 2>/dev/null
sleep 1
echo done
