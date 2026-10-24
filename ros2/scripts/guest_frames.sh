#!/usr/bin/env bash
# 在虚拟机里生成 TF 树（tf2_tools view_frames 会写 frames.pdf），供截图/插图使用。
set -o pipefail
source /opt/ros/humble/setup.bash
source "$HOME/ros2_ws/install/setup.bash"

pkill -x xterm 2>/dev/null
pkill -x rviz2 2>/dev/null
# 先确保流水线在跑（TF 需要 target 帧有发布者）
if ! ros2 node list 2>/dev/null | grep -q tracker_node; then
  setsid nohup ros2 launch hello_cv_cpp full_pipeline.launch.py use_rviz:=false \
    > /tmp/pl.log 2>&1 < /dev/null &
  sleep 14
fi

cd /tmp
rm -f frames.pdf
ros2 run tf2_tools view_frames 2>&1 | tail -2
ls -l /tmp/frames.pdf
