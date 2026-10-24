#!/usr/bin/env bash
# 在虚拟 X 屏幕（Xvfb + openbox）里开一个真实终端窗口，把命令的真实输出截成 PNG。
# 用法： hv_shot.sh <输出文件> "<窗口标题>" "<要执行的命令>" [等待秒数]
#
# 为什么是 xterm + 文泉驿等宽微米黑：
#   - lxterminal / gnome-terminal 在 Xvfb 里都需要 dbus 会话，实测窗口根本不 map；
#   - Noto Sans Mono CJK 这类字体的 ASCII 是双宽的，截图里英文会散架；
#   - 文泉驿等宽微米黑 ASCII 半宽、中文全宽，单字体就能覆盖中英文。
set -u

OUT="$1"; TITLE="$2"; CMD="$3"; WAIT="${4:-8}"
DISP=":99"
SHOT_W=1360
SHOT_H=880

if ! pgrep -x Xvfb > /dev/null; then
  Xvfb "$DISP" -screen 0 ${SHOT_W}x${SHOT_H}x24 > /dev/null 2>&1 &
  sleep 2
fi
export DISPLAY="$DISP"
export SHOT_CMD="$CMD"
pgrep -x openbox > /dev/null || { openbox --sm-disable > /dev/null 2>&1 & sleep 1; }

xterm -title "$TITLE" -geometry 164x46+0+0 -fs 10 \
      -fa "WenQuanYi Micro Hei Mono" \
      -bg "#0f1319" -fg "#e6e8eb" -bw 0 -b 8 \
      -e bash -lc '
        source /opt/ros/humble/setup.bash 2>/dev/null
        [ -f ~/ros2_ws/install/setup.bash ] && source ~/ros2_ws/install/setup.bash
        cd ~/ros2_ws
        printf "\033[38;5;114m\$ %s\033[0m\n" "$SHOT_CMD"
        eval "$SHOT_CMD"
        sleep 600' > /dev/null 2>&1 &
XT=$!
sleep "$WAIT"
import -window root "$OUT" 2>/dev/null || { xwd -root -silent | convert xwd:- "$OUT"; }
kill "$XT" 2>/dev/null
echo "saved $OUT"
