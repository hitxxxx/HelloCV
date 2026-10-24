# HelloCV · ROS2 视觉流水线

第三次任务（ROS2）的完整实现：两个包、7 个可执行文件，把"合成相机 → 亮斑检测 → EMA 跟踪 →
TF 广播 → RViz 可视化 → tf2 查询"串成一条链路，覆盖 Topic / Service / Parameter / TF / RViz /
launch / LifecycleNode 七个知识点。

> **不使用 OpenCV**：检测部分是一段 20 行的像素循环（阈值 + 一阶矩质心），
> 依赖只有 `rclcpp` 家族。少一个依赖，就少一次"我到底装没装对"的怀疑。

## 目录结构

```text
ros2/
├── ros2_ws/                                  # 工作空间
│   └── src/
│       ├── hello_cv_interfaces/              # 接口包：只有消息/服务定义
│       │   ├── msg/Detection.msg             # 检测结果（header + found + cx/cy/area/confidence）
│       │   ├── srv/SetTrackingMode.srv        # 切换跟踪模式（raw / ema）
│       │   ├── CMakeLists.txt
│       │   └── package.xml
│       └── hello_cv_cpp/                     # 实现包
│           ├── include/hello_cv_cpp/          # 7 个头文件
│           ├── src/                           # 7 个源文件 + vision_utils.cpp
│           ├── launch/                        # 5 个 launch 文件
│           ├── config/params.yaml             # 参数文件
│           ├── rviz/hello_cv.rviz             # RViz 配置
│           ├── test/test_vision.cpp           # 8 个 gtest 用例
│           ├── CMakeLists.txt
│           └── package.xml
├── scripts/
│   ├── build.sh                               # colcon build 的封装（--clean / --pkg）
│   ├── check_env.sh                           # 环境自检（缺什么装什么）
│   ├── verify_stack.sh                        # 一键跑完所有 ros2 命令并落盘报告
│   ├── verify_algorithm.py                    # 离线复算 8 个 gtest 用例的期望值（不需要 ROS2）
│   ├── simulate_camera.py                     # 离线复现 camera_node 的合成图 + 检测（不需要 ROS2）
│   ├── check_braces.py                        # C++ 源码括号配平的粗糙静态检查（没有编译器时的兜底）
│   └── make_figures.py                         # 生成笔记里的三张示意图（需要 Pillow）
└── docs/
    ├── yuque/                                 # 七篇笔记（Markdown，可直接导入语雀）
    ├── figures/                               # 三张示意图 PNG
    └── screenshots/                           # 12 张真机运行截图（清单见 README）
```

## 环境配置

目标发行版 **ROS2 Humble**（Ubuntu 22.04）。Jazzy（Ubuntu 24.04）也能编，见文末"兼容性"。

```bash
# 1) 装 ROS2 Humble（已装可跳过）
sudo apt install software-properties-common curl
sudo add-apt-repository universe
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install ros-humble-desktop ros-humble-tf2-tools python3-colcon-common-extensions

# 2) 装本项目依赖（两个包声明的都在 rosdep 里）
cd ros2/ros2_ws
sudo rosdep init && rosdep update       # 只需一次
rosdep install --from-paths src --ignore-src -r -y
```

每个新终端都要 source 两层（顺序不能反）：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash          # 工作空间的，必须后 source
```

> Windows / macOS 上想跑，用 WSL2 + Ubuntu 22.04，或 Docker：
> `docker run -it --rm -v "$PWD:/ws" ros:humble bash`。

## 编译

```bash
cd ros2/ros2_ws
colcon build --symlink-install
source install/setup.bash

# 或者用脚本（多了环境检查与 --clean / --pkg）
bash ../scripts/build.sh
bash ../scripts/build.sh --clean                # 删 build/ install/ log/ 重来
bash ../scripts/build.sh --pkg hello_cv_cpp     # 只编一个包
```

先自检环境：

```bash
bash ../scripts/check_env.sh
```

它会逐项检查 `ROS_DISTRO`、`ros2`/`colcon`/`rviz2`、`tf2_tools`、以及 9 个 C++ 依赖包，
缺什么就直接告诉你装哪个包。

## 使用方法

### 1. 最小示例（2 个节点）

```bash
ros2 launch hello_cv_cpp camera_detector.launch.py
# 换阈值、改话题名、顺手开 rviz
ros2 launch hello_cv_cpp camera_detector.launch.py threshold:=170 use_rviz:=true
```

### 2. 完整流水线（4 个节点 + 可选 rviz）

```bash
ros2 launch hello_cv_cpp full_pipeline.launch.py
ros2 launch hello_cv_cpp full_pipeline.launch.py use_rviz:=true fps:=15 log_level:=debug
```

起来之后：

| 命令 | 看什么 |
| --- | --- |
| `ros2 topic hz /camera/image_raw` | 相机频率（默认 30Hz） |
| `ros2 topic hz /vision/detection` | 检测频率（应与相机相同） |
| `ros2 topic echo /vision/detection --once --no-arr` | 一次检测结果 |
| `ros2 topic hz /tf` | TF 广播频率 |

### 3. TF + 静态变换

```bash
ros2 launch hello_cv_cpp tf_bringup.launch.py
ros2 run tf2_tools view_frames              # 生成 frames.pdf
ros2 run tf2_ros tf2_echo map target
```

`full_pipeline.launch.py` **不含**静态变换（`map → camera_link` 在 `tf_bringup.launch.py` 里），
因为"环境配置"和"算法流水线"应该分开。所以想在 RViz 里看到 `camera_link`，用 `tf_bringup`。

### 4. 切换跟踪模式（服务）

```bash
ros2 service list | grep set_mode
ros2 service call /set_mode hello_cv_interfaces/srv/SetTrackingMode "{mode: raw, alpha: 0.2}"
ros2 service call /set_mode hello_cv_interfaces/srv/SetTrackingMode "{mode: ema, alpha: 0.5}"

# 或者用自带的客户端（带退出码，适合写脚本）
ros2 run hello_cv_cpp mode_service_client ema 0.2
```

非法值会被拒绝（`success: false` + 具体原因），不会静默生效：

```bash
ros2 service call /set_mode hello_cv_interfaces/srv/SetTrackingMode "{mode: ema, alpha: 5.0}"
# success=False, message='alpha 必须落在 (0, 1] 区间内'
```

### 5. 参数（运行中热更新）

```bash
ros2 param list /detector_node
ros2 param get /detector_node intensity_threshold
ros2 param set /detector_node intensity_threshold 200      # 合法
ros2 param set /detector_node intensity_threshold 999      # 被拒，且有原因
ros2 param dump /detector_node                             # 导出成 YAML
```

### 6. 受管节点（LifecycleNode）

```bash
ros2 launch hello_cv_cpp lifecycle_bringup.launch.py          # 自动 configure + activate
ros2 launch hello_cv_cpp lifecycle_bringup.launch.py autostart:=false   # 只 configure

ros2 lifecycle get /mission_node
ros2 lifecycle set /mission_node deactivate
ros2 lifecycle set /mission_node activate
ros2 lifecycle set /mission_node cleanup
ros2 topic echo /mission_status          # 只有 active 状态才有数据
```

### 7. 参数演示（两个命名空间）

```bash
ros2 launch hello_cv_cpp param_demo.launch.py
ros2 param list /robot1/param_demo
ros2 param list /robot2/param_demo        # counter 与 mode 不同
ros2 param set /robot2/param_demo counter -1     # 被拒
```

### 8. 一键验证

```bash
bash ../scripts/verify_stack.sh
# 报告写到 docs/verify_report_<时间戳>.txt（命令 + 真实输出）
```

## 节点一览

| 可执行文件 | 订阅 | 发布 | 服务 |
| --- | --- | --- | --- |
| `camera_node` | — | `/camera/image_raw` | — |
| `detector_node` | `/camera/image_raw` | `/vision/detection` | — |
| `tracker_node` | `/vision/detection` | `/vision/track`、`/tf`、`/vision/target_marker` | `/set_mode` |
| `tf_lookup_node` | `/tf` | — | — |
| `param_demo_node` | — | — | — |
| `lifecycle_mission_node` | — | `/mission_status` | — |
| `mode_service_client` | — | — | 调用 `/set_mode` |

## 消息与服务

```text
# hello_cv_interfaces/msg/Detection
std_msgs/Header header
bool    found
float32 cx          # detector 输出像素；tracker 输出米（看 header.frame_id）
float32 cy
float32 area
float32 confidence

# hello_cv_interfaces/srv/SetTrackingMode
string  mode        # raw | ema
float64 alpha       # (0, 1]
---
bool    success
string  message
```

## 测试

```bash
cd ros2/ros2_ws
colcon test --packages-select hello_cv_cpp
colcon test-result --verbose
```

`test/test_vision.cpp` 有 8 个用例，覆盖：质心计算、面积下限、`step > width` 的行对齐、
空指针/非法尺寸、EMA 首帧吸附、EMA 收敛、`alpha` 卫生化、像素转米。

```bash
# 只跑这一个可执行文件（不用 colcon）
./build/hello_cv_cpp/test_vision
```

### 没有 ROS2 也能做的三项离线验证

这台开发机没有 ROS2 / 编译器，所以我把"能离线验证的部分"单独拆出来跑了一遍：

```bash
# 1) 算法逻辑：把 find_bright_blob / EmaFilter 用 Python 重写，按 gtest 的同一组期望值断言
python3 scripts/verify_algorithm.py      # 26 条断言全 PASS

# 2) 合成图像 + 检测的端到端复算：默认参数下到底能不能检测到目标
python3 scripts/simulate_camera.py
#   默认参数：12/12 帧检测到，面积 1011~1023（mean 1017.9），质心误差 max 0.079 px
#   阈值敏感性：100 -> 1411，180 -> 1016，240 -> 706（单调下降，质心不动）

# 3) C++ 源码括号配平（没有编译器时的兜底检查）
python3 scripts/check_braces.py          # 16 个文件全部配平
```

第 2 项不是"跑着玩"的：**它抓到了一个真 bug**。第一版用高斯亮斑（sigma = radius/3），
阈值 180 时只能圈住半径 ~7.7 像素、面积 185，比 `min_area: 200` 还小——
默认参数下 `detector_node` 会一直输出 `found: false`，整条流水线"能启动、什么都不发生"。
改成"平台 + 平滑过渡带"后面积约 1018，`expected_area` 也从 2100 改成 1020。
完整复盘写在 [`docs/yuque/04-Topic与QoS.md`](docs/yuque/04-Topic与QoS.md) 第 5 节。

## 设计说明（几个刻意的取舍）

| 取舍 | 理由 |
| --- | --- |
| 不用 OpenCV | 阈值 + 一阶矩只需 20 行；依赖是要还的（编译时间、镜像大小、版本冲突） |
| 不做连通域标记 | 场景只有一个亮斑，全图一阶矩 = 该亮斑质心；代价是"两个亮斑会算出中点"，已写进注释 |
| 亮斑用"平台 + smoothstep 过渡带"而不是高斯 | 第一版高斯（sigma=radius/3）太尖：阈值 180 只圈住 7.7px、面积 185 < `min_area` 200 → 默认参数下检测不到目标。改成平台后面积 ~1018，且阈值仍能明显改变面积 |
| 无目标时发 `found: false` | 让"没有"成为一种显式状态，而不是"不发消息"（下游无法区分"没目标"和"发布者挂了"） |
| 统一 `reliable + volatile + KeepLast(10)` | 宁可稳；`reliability` 做成参数，方便真机上对比实验 |
| TF 时间戳用检测时间戳 | 与图像严格对齐；代价是查询方必须用 `TimePointZero` |
| 接口单独一个包 | 将来写 Python 调试工具时，不必被迫依赖 C++ 实现 |

## 已知限制

1. **只在一套环境上验证过**：Ubuntu 22.04.5 + ROS 2 Humble（虚拟机，`~/ros2_ws`）。
   实测结果：`colcon build` 两个包通过、`colcon test` 9 个用例全绿、`ros2 pkg executables`
   正好 7 行、端到端 30 Hz、TF 与 RViz 正常；截图在 `docs/screenshots/`，原始终端记录在
   `docs/verify-transcript.txt`。换发行版（如 Jazzy）或换 RMW 仍需重跑 `scripts/verify_stack.sh`。
2. `find_bright_blob` 只适用于**单目标**场景（多目标会算合成质心）。
3. `TimerAction(2.0)` 是"错峰启动"的缓解措施，不是"等就绪"的严格方案。
4. `camera_node` 与 `tracker_node` 都有一个叫 `frame_id` 的参数，含义不同（图像帧名 vs TF 父坐标系）——
   保留是为了不和已有代码/文档不一致，`config/params.yaml` 里有注释说明。

## 兼容性（Jazzy / Ubuntu 24.04）

代码用的是 `rclcpp` 的稳定 API，理论上只需把 `source /opt/ros/humble/setup.bash` 换成
`/opt/ros/jazzy/setup.bash`。两个已知差异：

- `static_transform_publisher` 的**位置参数**写法在 Jazzy 里已废弃，本项目用的是命名参数
  （`--x --y --z --frame-id --child-frame-id`），两边都能跑；
- Jazzy 默认 C++17 已满足本项目要求（`CMakeLists.txt` 里显式 `set(CMAKE_CXX_STANDARD 17)`）。

## 语雀笔记

**已发布（公开可访问，一篇覆盖全部七个知识点）**：<https://www.yuque.com/yuqueyonghu-8qsy6m/vr3cga/ahtegobxnmsz2q2h>

源文件是 [`docs/ROS2学习笔记.md`](docs/ROS2学习笔记.md)（718 行 · 14 张真机截图 · 34 段代码）。

想深读的话，七篇分篇正文在 [`docs/yuque/`](docs/yuque/)，入口是
[`00-索引与阅读顺序.md`](docs/yuque/00-索引与阅读顺序.md)；也有七篇合并全量版
[`docs/ROS2学习笔记-全一篇.md`](docs/ROS2学习笔记-全一篇.md)。
