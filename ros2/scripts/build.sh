#!/usr/bin/env bash
# =============================================================================
# HelloCV · 一键编译
# =============================================================================
# 干了三件事：检查环境 → colcon build → 提示怎么 source。
# 用 --symlink-install 的原因：改 launch/yaml/rviz 不用重新 build，
# install 目录里是指向 src 的软链接，调参时省掉一大半时间。
#
# 用法：
#   ./scripts/build.sh              # 全量编译
#   ./scripts/build.sh --clean      # 先清掉 build/install/log 再编译
#   ./scripts/build.sh --pkg hello_cv_cpp   # 只编某一个包
# =============================================================================
set -euo pipefail

WS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${WS_DIR}/ros2_ws"

CLEAN=0
PKG_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --clean) CLEAN=1; shift ;;
    --pkg)   PKG_ARGS=(--packages-select "$2"); shift 2 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

# ---------- 1. 环境自检 ----------
if [[ -z "${ROS_DISTRO:-}" ]]; then
  echo "[build] 没检测到 ROS_DISTRO，先 source 环境：" >&2
  echo "        source /opt/ros/humble/setup.bash" >&2
  exit 1
fi
echo "[build] ROS_DISTRO=${ROS_DISTRO}"

if ! command -v colcon >/dev/null 2>&1; then
  echo "[build] 找不到 colcon，请先： sudo apt install python3-colcon-common-extensions" >&2
  exit 1
fi

# ---------- 2. 清理（可选） ----------
if [[ ${CLEAN} -eq 1 ]]; then
  echo "[build] 清理 build/ install/ log/"
  rm -rf build install log
fi

# ---------- 3. 编译 ----------
# --event-handlers console_direct+ ：把编译输出直接打到终端，
# 出错时第一现场就在眼前，不用去翻 log/latest_build。
echo "[build] colcon build ..."
colcon build \
  --symlink-install \
  --event-handlers console_direct+ \
  --cmake-args -DCMAKE_BUILD_TYPE=Release \
  "${PKG_ARGS[@]}"

cat <<EOF

[build] 编译完成。新开一个终端时记得：
        source ${WS_DIR}/ros2_ws/install/setup.bash

[build] 快速验证：
        ros2 pkg executables hello_cv_cpp
        ros2 launch hello_cv_cpp camera_detector.launch.py
EOF
