# HelloCV

本仓库用于记录 **Linux 学习与实践**、**ROS2 环境配置**，以及创新平台培训的实践任务
（第二次任务 · LLM 见 [`llm/`](llm/)，第三次任务 · ROS2 见 [`ros2/`](ros2/)）。

## 目录结构

```text
HelloCV/
├── README.md              # 本文件：项目说明 + 语雀笔记汇总
├── llm/                   # 第二次任务 · LLM 实践任务：石头剪刀布决策网关
│   ├── gateway/           #   网关核心：JSON 容错 / 规则 / 上游转发 / 编排
│   ├── tests/             #   93 个测试
│   ├── docs/              #   任务书、设计说明、语雀笔记草稿
│   ├── run_gateway.py     #   一行 JSON 进、一行 JSON 出
│   ├── play_game.py       #   和本地对手打 N 轮
│   └── mock_llm_server.py #   本地假上游（故意返回坏数据）
└── ros2/                  # 第三次任务 · ROS2：视觉流水线（Topic/Service/Param/TF/RViz/launch）
    ├── ros2_ws/src/
    │   ├── hello_cv_interfaces/   # 接口包：msg/Detection、srv/SetTrackingMode
    │   └── hello_cv_cpp/          # 实现包：7 个可执行文件 + launch + config + rviz + test
    ├── scripts/           # build.sh / check_env.sh / verify_stack.sh / make_figures.py
    └── docs/
        ├── yuque/         # 七篇语雀笔记（Markdown，可直接导入）
        ├── figures/       # 三张示意图
        └── screenshots/   # 12 张真机运行截图 + 清单
```

## 第二次任务 · LLM：石头剪刀布决策网关

把一行 JSON 请求转发给 **DeepSeek 官方 API**，再把模型返回的任意文本整理成一行严格合法的
JSON 决策（`{"time": …, "option": "rock|scissor|paper"}`）。重点是**不可信输出的容错**与
**永不崩溃的兜底**。

```bash
cd llm
pip install -r requirements.txt
export DEEPSEEK_API_KEY=sk-...          # PowerShell: $env:DEEPSEEK_API_KEY="sk-..."
python selfcheck.py                     # 93 passed
python play_game.py --rounds 10         # 和 DeepSeek 玩 10 轮
```

- 详细说明：[`llm/README.md`](llm/README.md)
- 设计说明（三级容错 / 重试分类 / time 归属）：[`llm/docs/design.md`](llm/docs/design.md)
- 语雀笔记草稿：[`llm/docs/yuque-note.md`](llm/docs/yuque-note.md)

## 第三次任务 · ROS2：HelloCV 视觉流水线

两个包、7 个可执行文件，把「合成相机 → 亮斑检测 → EMA 跟踪 → TF 广播 → RViz 可视化 → tf2 查询」
串成一条链路，覆盖 **Topic / Service / Parameter / TF / RViz / launch / LifecycleNode** 七个知识点。
检测部分**不用 OpenCV**（阈值 + 一阶矩质心，20 行像素循环），依赖只有 `rclcpp` 家族。

```bash
cd ros2/ros2_ws
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash

ros2 launch hello_cv_cpp full_pipeline.launch.py                     # 4 个节点
ros2 launch hello_cv_cpp full_pipeline.launch.py use_rviz:=true      # 带 RViz
bash ../scripts/verify_stack.sh                                      # 一键验证并落盘报告
```

| 想验证什么 | 命令 |
| --- | --- |
| 话题通不通 | `ros2 topic hz /camera/image_raw` / `ros2 topic echo /vision/detection --once --no-arr` |
| 服务 | `ros2 service call /set_mode hello_cv_interfaces/srv/SetTrackingMode "{mode: raw, alpha: 0.2}"` |
| 参数 | `ros2 param set /detector_node intensity_threshold 200` |
| TF 树 | `ros2 run tf2_tools view_frames` / `ros2 run tf2_ros tf2_echo map target` |
| 受管节点 | `ros2 lifecycle set /mission_node activate` |

- 详细说明：[`ros2/README.md`](ros2/README.md)
- 语雀笔记（七篇，Markdown 源文件）：[`ros2/docs/yuque/`](ros2/docs/yuque/)，入口是
  [`00-索引与阅读顺序.md`](ros2/docs/yuque/00-索引与阅读顺序.md)

## 环境与工具链记录

- ROS2：Ubuntu 22.04.5 + **Humble**（安装与验证步骤见 [`ros2/README.md`](ros2/README.md)，
  Jazzy 兼容性说明见 [该文"兼容性"一节](ros2/README.md#兼容性jazzy--ubuntu-2404)）；
  编译与运行都在虚拟机里真机完成，截图见 [`ros2/docs/screenshots/`](ros2/docs/screenshots/)
- 基础工具：`sudo apt install nmap ssh git ...`
- Node.js 与 PM2：`sudo apt install nodejs npm` ...

## 语雀笔记汇总

| 笔记 | 语雀链接（公开可访问） | 仓库内 Markdown（一定可访问） |
| --- | --- | --- |
| Linux 学习与实践记录 | <https://www.yuque.com/g/yuqueyonghu-8qsy6m/vkceqs/collaborator/join?token=agDjvvPviBf3dKcU> | — |
| 《git traning》 | <https://www.yuque.com/yuqueyonghu-8qsy6m/dgvebc/> | — |
| LLM 实践任务：决策网关实现笔记 | 待发布 | [`llm/docs/yuque-note.md`](llm/docs/yuque-note.md) |
| ROS2 · 00 总索引与阅读顺序 | 待发布 | [`00-索引与阅读顺序.md`](ros2/docs/yuque/00-索引与阅读顺序.md) |
| ROS2 · 01 工作空间与包结构 | 待发布 | [`01-工作空间与包结构.md`](ros2/docs/yuque/01-工作空间与包结构.md) |
| ROS2 · 02 C++ 节点与生命周期 | 待发布 | [`02-C++节点与生命周期.md`](ros2/docs/yuque/02-C++节点与生命周期.md) |
| ROS2 · 03 命令行工具实操 | 待发布 | [`03-命令行工具实操.md`](ros2/docs/yuque/03-命令行工具实操.md) |
| ROS2 · 04 Topic 与 QoS | 待发布 | [`04-Topic与QoS.md`](ros2/docs/yuque/04-Topic与QoS.md) |
| ROS2 · 05 Service 与参数 | 待发布 | [`05-Service与参数.md`](ros2/docs/yuque/05-Service与参数.md) |
| ROS2 · 06 TF 与 RViz | 待发布 | [`06-TF与RViz.md`](ros2/docs/yuque/06-TF与RViz.md) |
| ROS2 · 07 launch 文件 | 待发布 | [`07-launch文件.md`](ros2/docs/yuque/07-launch文件.md) |

> **笔记已经整理成"打开就能整篇粘贴"的形态**：文中的图片、跨篇链接全部是
> `raw.githubusercontent.com` / `github.com` 的**绝对地址**，粘进语雀后图片会由语雀自己抓取，
> 不需要再一张张上传。
>
> 发布步骤（每篇都一样）：新建语雀文档 → 把 `ros2/docs/yuque/` 下对应的 `.md` **全文**粘贴 →
> 右上角「分享」设为**互联网可见** → 复制链接，把上表「待发布」替换掉。
> **务必用无痕窗口打开一次确认不用登录也能看**，否则按 0 分算。

## 已知限制

第三次任务（ROS2）的代码在 **Ubuntu 22.04.5 + ROS 2 Humble** 的虚拟机里真机编译、真机运行过：
`colcon build` 两个包通过、`colcon test` 9 个用例全绿、`ros2 pkg executables` 正好 7 行、
端到端 30 Hz、TF 与 RViz 都正常出图。12 张截图在 [`ros2/docs/screenshots/`](ros2/docs/screenshots/)，
原始终端记录在 [`ros2/docs/verify-transcript.txt`](ros2/docs/verify-transcript.txt)。

编译和运行一共暴露了 8 个真问题（都写进了对应笔记的"真机踩坑"小节），其中两个值得一提：
亮斑第一版用高斯，阈值 180 只圈住 7.7 px、面积 185 < `min_area` 200，**默认参数下检测不到目标还不报错**；
`tracker_node` 第一版只 `declare_parameter` 不接回调，`ros2 param set` 显示成功但节点内部仍是旧值。
只在一套环境（Humble + 默认 RMW）上验证过，换环境请重跑 `ros2/scripts/verify_stack.sh`。
