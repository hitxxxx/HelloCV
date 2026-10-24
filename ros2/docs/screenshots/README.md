# 截图清单（待补）

这次任务在没有 ROS2 环境的机器上完成，所以终端截图**没有实拍**。这一份是"照着敲就能补齐"的清单：
一条命令、一张图、一段"这张图证明了什么"。

补图之后：

1. 把图片放进本目录（`docs/screenshots/`），文件名照下面写；
2. 回到 `docs/yuque/*.md` 把 `📷 截图占位` 那一段换成 `![说明](screenshots/xxx.png)`；
3. 同时删掉笔记开头"环境说明"里"没有实跑"那句话——补上了就该改口。

前置条件（Ubuntu 22.04 + ROS2 Humble）：

```bash
sudo apt install ros-humble-desktop ros-humble-tf2-tools python3-colcon-common-extensions
cd HelloCV/ros2/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

| # | 文件名 | 命令 | 这张图证明什么 |
| --- | --- | --- | --- |
| 1 | `01-colcon-build.png` | `colcon build --symlink-install` | 两个包编过，`Summary: 2 packages finished` |
| 2 | `01-pkg-executables.png` | `ros2 pkg executables hello_cv_cpp` | 7 个可执行文件都装在 `lib/hello_cv_cpp/` 下 |
| 3 | `03-launch-full.png` | `ros2 launch hello_cv_cpp full_pipeline.launch.py` | 4 个节点都起来，日志前缀带 launch 的进程编号 |
| 4 | `03-topic-info-v.png` | `ros2 topic info -v /camera/image_raw` | 两侧 QoS 都是 RELIABLE / VOLATILE / KEEP_LAST(10) |
| 5 | `04-topic-echo.png` | `ros2 topic echo /vision/detection --once --no-arr` | 一条真实检测结果（cx/cy/area/confidence 有值） |
| 6 | `06-view-frames.png` | `ros2 run tf2_tools view_frames` 后打开 `frames.pdf` | TF 树 `map → camera_link` 与 `map → target`，频率标注 |
| 7 | `06-rviz.png` | `ros2 launch hello_cv_cpp full_pipeline.launch.py use_rviz:=true` | Grid + TF 轴 + 球体；Fixed Frame = map |
| 8 | `07-lifecycle.png` | `ros2 lifecycle get /mission_node` + `ros2 lifecycle set /mission_node activate` | 状态从 unconfigured 走到 active，`/mission_status` 开始有数据 |

拍照小技巧：

- 终端窗口宽度拉大到 100 列以上，否则 `ros2 topic info -v` 会折行；
- 明暗主题都行，但**别用透明背景**，贴到语雀上会看不清；
- 一张图只证明一件事。`colcon build` 的图里不要混进 `ros2 run` 的输出。
