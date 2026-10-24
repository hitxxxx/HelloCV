# 运行截图清单（全部为真机截图）

12 张图都在 **Ubuntu 22.04.5 + ROS 2 Humble** 的虚拟机里采集，不是合成图、不是示意图。
截图方式是 Xvfb 私有 X 屏幕 + `xterm`（`WenQuanYi Micro Hei Mono` 字体）+ `import -window root`，
脚本见 `ros2/scripts/guest_shot.sh`；RViz 那张用 `LIBGL_ALWAYS_SOFTWARE=1 rviz2`。

| 文件 | 命令 | 这张图证明了什么 |
| --- | --- | --- |
| `01-colcon-build.png` | `colcon build --symlink-install` | 两个包都能编过，`Summary: 2 packages finished [23.8s]` |
| `01-pkg-executables.png` | `ros2 pkg executables hello_cv_cpp` | **正好 7 行**（多一行 `libhello_cv_vision.so` 就是安装规则写错了） |
| `03-launch-full.png` | `ros2 launch hello_cv_cpp full_pipeline.launch.py` | 四个节点都起来，`frames=371 detections=371`、`updates=403 mode=ema`、`距原点 0.349 m` |
| `03-topic-info-v.png` | `ros2 topic info -v /vision/detection` | 两端 QoS 都是 `RELIABLE / VOLATILE`，Publisher 1 / Subscription 1 |
| `04-topic-echo.png` | `ros2 topic echo /vision/detection --once --no-arr` | 一条真实检测：`found: true`、`area: 1015`、`confidence: 0.995` |
| `04-topic-hz.png` | `ros2 topic hz /camera/image_raw` | `average rate: 30.007`，和相机参数的 30 fps 对得上 |
| `05-service-call.png` | `ros2 service call /set_mode ...` | 请求-响应的完整过程，含中文 `message` |
| `05-param.png` | `ros2 param list/get/set` | `get 180 → set 200 → get 200`，以及非法值被拒绝（`min_area 必须 >= 1`） |
| `06-tf2-echo.png` | `ros2 run tf2_ros tf2_echo map target` | Translation 在 0~0.35 m 内变化，Rotation 恒为单位四元数 |
| `06-view-frames.png` | `ros2 run tf2_tools view_frames` | TF 树：`camera_link` 静态（rate 10000）、`target` 动态（30.3 Hz） |
| `06-rviz.png` | `rviz2 -d .../hello_cv.rviz` | Fixed Frame=map、Grid、TF 轴、红色球 Marker 同时可见 |
| `07-lifecycle.png` | `ros2 lifecycle set/get /mission_node` | 状态机跑全流程，含 inactive 期间 `publisher is not activated` 的 WARN |

## 怎么复现

```bash
# 1) 装依赖（一次性）
sudo apt-get install -y xvfb openbox xterm imagemagick wmctrl fonts-wqy-microhei

# 2) 起一块虚拟屏幕
Xvfb :99 -screen 0 1360x880x24 & openbox --sm-disable &

# 3) 拍某一张图（脚本会 source 工作空间、打印命令、执行、保持窗口）
bash ros2/scripts/guest_shot.sh ~/shots/04-topic-echo.png "检测结果" \
     "ros2 topic echo /vision/detection --once --no-arr" 9

# 4) 裁掉底部空白（只裁上下，保持等宽）
python3 ros2/scripts/crop_shots.py ~/shots docs/screenshots
```

## 拍照的几个讲究

- 终端宽度至少 160 列，否则长日志（`[detector_node-2] ...`）会被截断；
- 一行里别放两条命令，一张图只证明一件事；
- 命令行本身要出现在图里（脚本会先打印一条青色的 `$ 命令`），否则看图的人不知道这是怎么跑出来的。
