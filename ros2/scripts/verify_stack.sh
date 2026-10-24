#!/usr/bin/env bash
# =============================================================================
# HelloCV · 流水线验收脚本
# =============================================================================
# 这个脚本是"实操记录"的来源：它把课上要用的 ros2 命令按顺序跑一遍，
# 每条命令前面打印一行 `$ 命令`，输出原样保留，最后汇总成一份文本报告。
# 笔记里的"运行结果"截图/代码块，就是从这份报告里摘的。
#
# 用法：
#   # 终端 A：起流水线
#   ros2 launch hello_cv_cpp full_pipeline.launch.py
#   # 终端 B：验收
#   ./scripts/verify_stack.sh
#
# 生成的报告默认写到 docs/verify_report_<时间>.txt（不进 git，见 .gitignore）
# =============================================================================
set -uo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${WS_DIR}/docs"
mkdir -p "${OUT_DIR}"
REPORT="${OUT_DIR}/verify_report_$(date +%Y%m%d_%H%M%S).txt"

# 有的命令要"等一会儿"，统一给个上限，避免脚本卡死
run() {
  local desc="$1"; shift
  {
    echo
    echo "--------------------------------------------------------------------"
    echo "# ${desc}"
    echo "\$ $*"
  } | tee -a "${REPORT}"
  # 先把输出收进变量、再 tee，才能拿到命令本身的退出码
  # （直接 `cmd | tee` 拿到的是 tee 的退出码，永远是 0，等于没测）
  local out rc
  out="$(timeout 12 "$@" 2>&1)"; rc=$?
  printf '%s\n' "${out}" | tee -a "${REPORT}"
  echo "    (exit=${rc})" | tee -a "${REPORT}"
}

section() {
  {
    echo
    echo "===================================================================="
    echo "== $*"
    echo "===================================================================="
  } | tee -a "${REPORT}"
}

{
  echo "HelloCV 流水线验收报告"
  echo "时间: $(date '+%Y-%m-%d %H:%M:%S %z')"
  echo "主机: $(uname -srm)"
  echo "ROS_DISTRO: ${ROS_DISTRO:-<未设置>}"
} | tee -a "${REPORT}"

# ---------------- 1. 节点与话题 ----------------
section "节点 / 话题：谁在发、谁在收"
run "节点列表"            ros2 node list
run "节点详情(camera_node)" ros2 node info /camera_node
run "话题列表(带类型)"     ros2 topic list -t
run "话题详情"            ros2 topic info /camera/image_raw -v
run "话题带宽"            ros2 topic bw --window 10 /camera/image_raw
run "话题频率(3 秒)"       ros2 topic hz /camera/image_raw
run "看一帧图像头"         ros2 topic echo --once --no-arr /camera/image_raw
run "看一条检测结果"       ros2 topic echo --once /vision/detection

# ---------------- 2. 手动发话题 ----------------
section "手动 pub：不写节点也能喂数据"
# -1 = 只发 1 条就退出；这里发一条"找不到目标"的检测，观察 tracker 的反应
run "手动发布一条检测"     ros2 topic pub --once /vision/detection \
  hello_cv_interfaces/msg/Detection \
  "{header: {frame_id: camera_link}, found: true, cx: 100.0, cy: 120.0, area: 1020.0, confidence: 1.0}"

# ---------------- 3. 服务 ----------------
section "服务：同步请求/应答"
run "服务列表"            ros2 service list -t
run "服务类型"            ros2 service type /set_mode
run "切到 raw（不平滑）"   ros2 service call /set_mode \
  hello_cv_interfaces/srv/SetTrackingMode "{mode: raw, alpha: 0.0}"
run "切回 ema"            ros2 service call /set_mode \
  hello_cv_interfaces/srv/SetTrackingMode "{mode: ema, alpha: 0.5}"
run "非法参数应被拒绝"     ros2 service call /set_mode \
  hello_cv_interfaces/srv/SetTrackingMode "{mode: ema, alpha: 5.0}"

# ---------------- 4. 参数 ----------------
section "参数：查看 / 修改 / 落盘"
run "参数列表"            ros2 param list /tracker_node
run "读参数"              ros2 param get /tracker_node alpha
run "改参数"              ros2 param set /tracker_node alpha 0.8
run "存成 yaml"           ros2 param dump /tracker_node
run "非法参数(应失败)"     ros2 param set /detector_node intensity_threshold 999

# ---------------- 5. TF ----------------
section "TF：树形结构与查询"
run "TF 话题频率"          ros2 topic hz /tf --window 20
run "tf2_echo(map->target)" ros2 run tf2_ros tf2_echo map target
run "静态变换"            ros2 run tf2_ros tf2_echo map camera_link
# view_frames 会生成 frames_<时间>.pdf，需要 graphviz
( cd "${OUT_DIR}" && timeout 8 ros2 run tf2_tools view_frames 2>&1 | tee -a "${REPORT}" )

# ---------------- 6. rqt / 图形化（可选）----------------
section "提示"
cat <<'EOF' | tee -a "${REPORT}"
想看图形化界面（需要 GUI）：rqt_graph / rqt_plot / rqt_console / rviz2
  rqt_graph   —— 节点与话题的连接图（最直观地看懂 launch 干了什么）
  rqt_plot    —— /vision/track 里的 cx/cy 画曲线，看平滑前后差别
  rqt_console —— 按级别过滤日志

注意：本脚本里凡是有 timeout 的命令，超时属于正常（比如 tf2_echo 会一直刷）。
EOF

echo
echo "报告已写入：${REPORT}"
