#!/usr/bin/env bash
# =============================================================================
# HelloCV · 环境自检
# =============================================================================
# 装好 ROS2 之后、编译之前先跑这个，把"版本/路径/工具/依赖"逐条打出来。
# 出问题时最容易漏的三件事它都覆盖了：
#   1. source 了没（ROS_DISTRO / AMENT_PREFIX_PATH）
#   2. 发行版对不对（Humble vs Jazzy，接口有差异）
#   3. 依赖包齐不齐（rosidl / tf2 / lifecycle）
#
# 用法： ./scripts/check_env.sh
# =============================================================================
set -uo pipefail   # 故意不加 -e：自检脚本要"尽量都跑一遍"，而不是遇错就停

ok()   { printf '  \033[32m[ OK ]\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m[WARN]\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31m[FAIL]\033[0m %s\n' "$*"; }

echo "=============================================="
echo " HelloCV · ROS2 环境自检"
echo "=============================================="

# ---------- 1. 发行版 ----------
echo; echo "[1] ROS2 发行版"
if [[ -n "${ROS_DISTRO:-}" ]]; then
  ok "ROS_DISTRO=${ROS_DISTRO}"
  case "${ROS_DISTRO}" in
    humble|jazzy) ok "发行版受支持（Humble / Jazzy 都验证过）" ;;
    *) warn "本笔记基于 Humble 编写，${ROS_DISTRO} 上接口可能略有差异" ;;
  esac
  [[ -n "${AMENT_PREFIX_PATH:-}" ]] && ok "AMENT_PREFIX_PATH 已设置" \
    || warn "AMENT_PREFIX_PATH 为空，source 可能没生效"
else
  bad "没检测到 ROS_DISTRO —— 先执行 source /opt/ros/<distro>/setup.bash"
fi

echo; echo "[2] 关键命令"
for cmd in ros2 colcon rviz2; do
  if command -v "${cmd}" >/dev/null 2>&1; then
    ok "${cmd} -> $(command -v "${cmd}")"
  else
    bad "找不到 ${cmd}"
  fi
done
# tf2_tools 是"可选但强烈建议"的：view_frames 生成 PDF 要用
command -v ros2 >/dev/null 2>&1 && ros2 pkg prefix tf2_tools >/dev/null 2>&1 \
  && ok "tf2_tools 已安装（ros2 run tf2_tools view_frames 可用）" \
  || warn "tf2_tools 未安装：sudo apt install ros-\${ROS_DISTRO}-tf2-tools"

# ---------- 3. 依赖包 ----------
echo; echo "[3] 依赖包"
for pkg in rclcpp rclcpp_lifecycle std_msgs sensor_msgs geometry_msgs visualization_msgs tf2 tf2_ros rosidl_default_generators; do
  if ros2 pkg prefix "${pkg}" >/dev/null 2>&1; then
    ok "${pkg}"
  else
    bad "${pkg} 缺失 —— sudo apt install ros-\${ROS_DISTRO}-${pkg//_/-}"
  fi
done

# ---------- 4. 工作空间 ----------
echo; echo "[4] 工作空间"
WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
for d in "${WS_DIR}/ros2_ws/src/hello_cv_interfaces" "${WS_DIR}/ros2_ws/src/hello_cv_cpp"; do
  [[ -d "${d}" ]] && ok "找到 $(basename "${d}")" || bad "缺少 $(basename "${d}")"
done
if [[ -f "${WS_DIR}/ros2_ws/install/setup.bash" ]]; then
  ok "已编译过（install/setup.bash 存在）"
else
  warn "还没编译：先跑 ./scripts/build.sh"
fi

# ---------- 5. 正在跑的东西 ----------
echo; echo "[5] 运行时状态（可选，仅提示）"
if [[ -n "${ROS_DISTRO:-}" ]]; then
  nodes=$(ros2 node list 2>/dev/null | wc -l)
  ok "当前在线节点数：${nodes}"
  [[ ${nodes} -eq 0 ]] && warn "没有节点在跑；如果想测 launch，先起一个终端跑 full_pipeline"
fi

echo; echo "自检结束。"
