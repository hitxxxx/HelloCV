# HelloCV · ROS 2 学习笔记

> 这是 HelloCV 仓库第三次任务（ROS 2）的完整笔记：把七个学习点（工作空间与包、节点与生命周期、命令行工具、Topic 与 QoS、Service 与参数、TF 与 RViz、launch）串成一条**能跑通的视觉流水线**。
> 环境是 Ubuntu 22.04.5 + ROS 2 Humble，文中所有截图、终端输出都是真机跑出来的（2026-10-24）。

## 目录

1. 第一篇 · 从零理解 ros2_ws：工作空间、两个包、以及 CMakeLists 到底在写什么
2. 第二篇 · C++ 节点怎么写、以及"受管节点"到底管住了什么
3. 第三篇 · 命令行工具实操：把 ROS 2 当成一个可以"查"的系统
4. 第四篇 · Topic 与 QoS：为什么"话题有数据，订阅者却没反应"
5. 第五篇 · Service 与参数服务器：把"操作"和"配置"分开
6. 第六篇 · TF 与 RViz：让"米"和"像素"在同一张地图上对上
7. 第七篇 · launch 文件：把"一串命令"写成"一份声明"

附录 A · 实操记录与验证

附录 B · 仓库结构与入口

---

## 这次做了什么

用两个 ROS2 包（`hello_cv_interfaces` 定义消息/服务，`hello_cv_cpp` 实现 7 个可执行文件）
搭了一条**不依赖 OpenCV 的视觉流水线**：合成相机发 `mono8` 图像 → 阈值 + 一阶矩算亮斑质心 →
EMA 平滑 + 像素转米 → 广播 `map→target` 的 TF + RViz 球体 → 用 tf2 查询验证。
整条链路覆盖了 Topic / Service / Parameter / TF / RViz / launch / LifecycleNode 七个知识点。

![节点与接口总览](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/figures/fig-architecture.png)

---

## 第一篇 · 从零理解 ros2_ws：工作空间、两个包、以及 CMakeLists 到底在写什么

### 0. 一句话总结

ROS2 的一个**包（package）**= 一份 `package.xml`（我是谁、依赖谁）+ 一份 `CMakeLists.txt`（怎么编、编出什么、
装到哪）；一堆包放在 `src/` 下，`colcon build` 把它们编到 `build/`、装到 `install/`，然后
`source install/setup.bash` 让 `ros2 run` 能按名字找到它们。

一句话记住三件事：**包名在 package.xml 里**、**可执行文件装到 `lib/<包名>/`**、**`ros2 run <包名> <可执行名>` 靠这两样对上号**。

### 1. 概念对照表（我自己的理解）

| 概念 | 我的理解 | 在本项目里的具体样子 |
| --- | --- | --- |
| 工作空间 workspace | 一个"工程根目录"，里面固定有 `src/`，编译后长出 `build/ install/ log/` | `ros2_ws/` |
| 包 package | 能被 `colcon` 识别、能被 `ros2 run` 找到的最小发布单元 | `hello_cv_interfaces`、`hello_cv_cpp` |
| 构建类型 | 决定"用什么工具编"：`ament_cmake`（C/C++）还是 `ament_python`（Python） | 两个包都是 `ament_cmake` |
| colcon | 构建工具，本身不认识 ROS，只按"包"并行调用各自的构建系统 | `colcon build --symlink-install` |
| install 空间 | 编译产物的"假根目录"，`source install/setup.bash` 后它才进 `AMENT_PREFIX_PATH` | `install/hello_cv_cpp/lib/hello_cv_cpp/camera_node` |
| 接口包 | 只放 `.msg/.srv`，不写逻辑；它的价值是**让依赖方不必重编实现** | `hello_cv_interfaces` |

### 2. 目录长什么样

```text
ros2/ros2_ws/
├── src/                                   # 只有这里是我的代码，其余都是生成物
│   ├── hello_cv_interfaces/               # 接口包：只有消息/服务定义
│   │   ├── msg/Detection.msg
│   │   ├── srv/SetTrackingMode.srv
│   │   ├── CMakeLists.txt
│   │   └── package.xml
│   └── hello_cv_cpp/                      # 实现包：节点、launch、参数、rviz
│       ├── include/hello_cv_cpp/*.hpp
│       ├── src/*.cpp
│       ├── launch/*.launch.py
│       ├── config/params.yaml
│       ├── rviz/hello_cv.rviz
│       ├── test/test_vision.cpp
│       ├── CMakeLists.txt
│       └── package.xml
├── build/                                 # colcon 生成：中间文件
├── install/                               # colcon 生成：最终产物（被 source 的那个）
└── log/                                   # colcon 生成：每次构建的日志
```

`build/ install/ log/` **不该进 git**（本仓库 `.gitignore` 已忽略）。判断一个目录是不是"生成物"，
有个很土但可靠的办法：删掉它能不能靠一条命令重建？能，就是生成物。

### 3. 两个包，两种 package.xml

#### 3.1 接口包 `hello_cv_interfaces/package.xml`

```xml
<package format="3">
  <name>hello_cv_interfaces</name>
  <version>0.1.0</version>
  <description>HelloCV 视觉流水线的消息与服务定义（只有接口，没有实现）</description>
  <maintainer email="hitxxxx@example.com">HelloCV</maintainer>
  <license>MIT</license>

  <buildtool_depend>ament_cmake</buildtool_depend>
  <buildtool_depend>rosidl_default_generators</buildtool_depend>  <!-- 生成 C++ 头文件 -->
  <exec_depend>rosidl_default_runtime</exec_depend>                <!-- 运行时反序列化 -->
  <depend>std_msgs</depend>

  <!-- 关键一行：告诉 colcon/rosidl "我是接口包"，否则生成的代码不会被别的包看到 -->
  <member_of_group>rosidl_interface_packages</member_of_group>

  <export><build_type>ament_cmake</build_type></export>
</package>
```

三个容易漏的点：

1. `rosidl_default_generators` 是 **buildtool**（只在编译期用），`rosidl_default_runtime` 是 **exec**（运行时用），
   写混了 `rosdep` 检查就会报错。
2. `<member_of_group>rosidl_interface_packages</member_of_group>` 不加，接口包照样能编，
   但**别的包 `#include` 不到生成的头文件**——这个坑报错信息很不直观。
3. 接口包里**不要**写 `<depend>rclcpp</depend>`。接口不依赖任何客户端库，这是它存在的意义。

#### 3.2 实现包 `hello_cv_cpp/package.xml` 的依赖段

```xml
<depend>rclcpp</depend>
<depend>rclcpp_lifecycle</depend>          <!-- 只给 lifecycle_mission_node 用 -->
<depend>rcl_interfaces</depend>
<depend>std_msgs</depend>
<depend>sensor_msgs</depend>
<depend>geometry_msgs</depend>
<depend>visualization_msgs</depend>        <!-- RViz Marker -->
<depend>tf2</depend>
<depend>tf2_ros</depend>
<depend>hello_cv_interfaces</depend>       <!-- 依赖自己写的接口包 -->

<exec_depend>ros2launch</exec_depend>      <!-- ros2 launch 命令 -->
<exec_depend>rviz2</exec_depend>
<exec_depend>tf2_tools</exec_depend>       <!-- view_frames -->
```

`<depend>` 是 `<build_depend>`+`<build_export_depend>`+`<exec_depend>` 的简写。**只在编译期需要**的头文件
（比如 `hello_cv_interfaces` 的生成头）用 `depend` 也不会错，但把 `rviz2` 写成 `depend` 就不合适了——
它跟编译毫无关系，只是运行时要启动。

### 4. CMakeLists 到底在写什么

`hello_cv_cpp/CMakeLists.txt` 的骨架（删掉注释后的主干）：

```cmake
cmake_minimum_required(VERSION 3.8)
project(hello_cv_cpp)

if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()
add_compile_options(-Wall -Wextra -Wpedantic)   # 注意：故意不加 -Werror

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)
find_package(std_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(hello_cv_interfaces REQUIRED)

# 1) 纯算法编成库，好让 test_vision 直接链它
add_library(hello_cv_vision SHARED src/vision_utils.cpp)
target_include_directories(hello_cv_vision PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>)

# 2) 每个节点一个可执行文件
add_executable(camera_node src/camera_node.cpp)
ament_target_dependencies(camera_node rclcpp sensor_msgs hello_cv_interfaces)
# ... 其余 6 个同理 ...

# 3) 装到 lib/<包名>/ —— 这是 ros2 run 能找到它的唯一位置
install(TARGETS
  camera_node detector_node tracker_node tf_lookup_node
  param_demo_node lifecycle_mission_node mode_service_client
  DESTINATION lib/${PROJECT_NAME})

# 4) launch / 参数 / rviz 属于"运行时资源"，装到 share/<包名>/
install(DIRECTORY launch config rviz DESTINATION share/${PROJECT_NAME})

ament_package()
```

四条必须记住的规则：

| 规则 | 写错了会怎样 |
| --- | --- |
| 可执行文件必须装到 `lib/${PROJECT_NAME}` | `ros2 run` 报 `No executable found`，但文件明明在 `install/` 里另一个目录躺着 |
| 资源目录装到 `share/${PROJECT_NAME}` | `FindPackageShare('hello_cv_cpp')` 拿到空路径，launch 里读 YAML/launch 嵌套全崩 |
| **`ament_package()` 必须是最后一行** | 报 `ament_package() cannot be called more than once`，或者 `install` 目录里没有 `package.xml` |
| 接口包用 `rosidl_generate_interfaces()` 而不是 `add_library` | 头文件不生成，`#include "hello_cv_interfaces/msg/detection.hpp"` 找不到 |

接口包的 CMakeLists 核心就三行：

```cmake
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Detection.msg"
  "srv/SetTrackingMode.srv"
  DEPENDENCIES std_msgs)
ament_export_dependencies(rosidl_default_runtime)
```

### 5. 编译与运行

```bash
# 一次性：装依赖（Ubuntu 22.04 + Humble）
sudo rosdep init && rosdep update
cd ros2_ws
rosdep install --from-paths src --ignore-src -r -y

# 每次都做：编译
colcon build --symlink-install --event-handlers console_direct+

# 每次开新终端都要做：让当前 shell 认识这个工作空间
source install/setup.bash
```

`--symlink-install` 的意义：`install/` 里的 launch/python 文件是**符号链接**，改完不用重编，直接生效。
C++ 源码不行，仍然要重编。

一次干净的构建应该看到（Humble + colcon 的典型输出）：

```text
Starting >>> hello_cv_interfaces
Finished <<< hello_cv_interfaces [12.3s]
Starting >>> hello_cv_cpp
Finished <<< hello_cv_cpp [24.1s]

Summary: 2 packages finished [36.8s]
```

![colcon build 的真实输出](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/01-colcon-build.png)
> 复现命令：`cd ros2/ros2_ws && colcon build --symlink-install`。

自检四连（少了任何一条都是"没装好"）：

```bash
ros2 pkg list | grep hello_cv            # 两个包都在
ros2 pkg prefix hello_cv_cpp             # 打印 install/hello_cv_cpp
ros2 interface show hello_cv_interfaces/msg/Detection
ros2 pkg executables hello_cv_cpp        # 7 个可执行文件
```

`ros2 pkg executables hello_cv_cpp` 的输出应该正好 7 行：

```text
hello_cv_cpp camera_node
hello_cv_cpp detector_node
hello_cv_cpp lifecycle_mission_node
hello_cv_cpp mode_service_client
hello_cv_cpp param_demo_node
hello_cv_cpp tf_lookup_node
hello_cv_cpp tracker_node
```

![ros2 pkg executables：正好 7 个可执行文件](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/01-pkg-executables.png)

### 6. 我踩到的 / 差点踩到的坑

#### 6.1 `source` 的层级写错

`source install/setup.bash` 和 `source /opt/ros/humble/setup.bash` 是**两层**，都要 source，且**顺序不能反**：

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash          # 必须后 source，否则工作空间被系统 ROS 覆盖
```

反过来写，`ros2 pkg list` 里就找不到自己的包。这个错误的报错是 `Package 'hello_cv_cpp' not found`，
看起来像"没编成功"，其实是"没 source 对"。

#### 6.2 改了 `.msg` 只编了实现包

`colcon build --packages-select hello_cv_cpp` 不会重编接口包，结果是**旧的头文件 + 新的实现**，
运行时字段对不上、反序列化直接崩。改消息后必须：

```bash
colcon build --packages-select hello_cv_interfaces hello_cv_cpp
```

#### 6.3 在 `src/` 外面执行 `colcon build`

`colcon build` 必须在**工作空间根**（有 `src/` 的那层）执行。在 `src/hello_cv_cpp/` 里执行，
它会把这个单包当成一个工作空间编，产物散落在包目录里，`ros2 run` 依然找不到。

#### 6.4 为什么我把接口单独拆一个包

一开始我图省事，想把 `.msg` 直接塞进 `hello_cv_cpp`。想了一下没这么干，理由是**依赖方向**：
将来如果写一个 Python 的调试工具，它只需要 `hello_cv_interfaces`，不该被迫依赖 C++ 实现包（更不该被
`rclcpp` 拖进来）。拆开之后，改实现不会触发接口包重编，改接口才触发——这个边界在工程上省时间。

这算是我对这个任务"项目结构"这一项的个人理解：**包不是按"文件多少"拆的，是按"谁会独立依赖它"拆的。**

### 7.5 真机踩坑：两个"只有真编译才会暴露"的问题

#### 7.5.1 `CMakeLists.txt` 少了 `include_directories(include)`

第一次 `colcon build` 直接红：

```
fatal error: hello_cv_cpp/camera_node.hpp: 没有那个文件或目录
```

一开始我以为是把 `include/` 写错了，后来才想明白：我只有 `hello_cv_vision` 这个库用
`target_include_directories(... PUBLIC $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>)`
把路径"传播"出去了，而 `camera_node`、`tf_lookup_node`、`param_demo_node`、
`lifecycle_mission_node`、`mode_service_client` 这五个可执行文件**根本不链接那个库**，
自然也就继承不到它的 PUBLIC include 路径。

修法是在 `find_package(hello_cv_interfaces REQUIRED)` 之后加一行：

```cmake
include_directories(include)   # 让所有目标都能 #include "hello_cv_cpp/xxx.hpp"
```

> 教训：`target_include_directories` 的 PUBLIC 只对**链接了这个 target 的人**生效；
> 一个工程里只要有一个目标没链接它，"局部生效"就会变成"局部编译失败"。
> 这类问题在只读代码时几乎不可能发现，因为头文件名字看起来是对的。

#### 7.5.2 SHARED 库被装进了可执行文件目录

`ros2 pkg executables hello_cv_cpp` 一开始输出 **8 行**，最后一行是：

```
hello_cv_cpp libhello_cv_vision.so
```

原因是我图省事，把所有 target 一起写进了 `install(TARGETS ... DESTINATION lib/${PROJECT_NAME})`，
于是 SHARED 库也被扔进了 `lib/hello_cv_cpp/`，而 `ros2 pkg executables` 会把那个目录下的
**所有文件**都当可执行文件列出来。

修法是分开装：

```cmake
install(TARGETS camera_node detector_node tracker_node tf_lookup_node
                param_demo_node lifecycle_mission_node mode_service_client
        DESTINATION lib/${PROJECT_NAME})
install(TARGETS hello_cv_vision
        ARCHIVE DESTINATION lib
        LIBRARY DESTINATION lib
        RUNTIME DESTINATION bin)
```

改完正好 7 行——`ros2 pkg executables` 的行数本身就是一条可验证的断言。

### 7. 验收清单

- [x] `src/` 下两个包，各自有 `package.xml`（format 3）与 `CMakeLists.txt`
- [x] 接口包带 `rosidl_interface_packages` 组声明
- [x] 7 个可执行文件都 `install(TARGETS ... DESTINATION lib/${PROJECT_NAME})`
- [x] `launch/ config/ rviz/` 都装到 `share/${PROJECT_NAME}`
- [x] `.gitignore` 忽略 `build/ install/ log/`
- [x] 在真机 Humble 上 `colcon build` 通过（真机已验证）

---

## 第二篇 · C++ 节点怎么写、以及"受管节点"到底管住了什么

### 0. 一句话总结

一个 ROS2 C++ 节点就是"**一个对象 + 四行 main**"：`rclcpp::init` → `make_shared<MyNode>()` →
`rclcpp::spin(...)` → `rclcpp::shutdown()`；节点内部的"活"全部挂在**定时器、订阅、服务**这几类回调上，
`spin` 就是那个不断把回调喂给它们的循环。

而 `LifecycleNode` 在普通节点外面又套了一层**状态机**：建资源（configure）、开阀门（activate）、关阀门
（deactivate）、拆资源（cleanup），让"启动"变成**可控、可回退、可外部编排**的动作。

### 1. 普通节点的骨架

`camera_node` 的构造函数是典型写法，逐段看：

```cpp
CameraNode::CameraNode(const rclcpp::NodeOptions & options)
: Node("camera_node", options), rng_(0)
{
  // ---------- 1. 参数：声明即默认值，类型在声明时就定了 ----------
  width_  = this->declare_parameter<int>("width", 320);
  height_ = this->declare_parameter<int>("height", 240);
  fps_    = std::max(1.0, this->declare_parameter<double>("fps", 30.0));
  // 参数文件里的值可能超出合理范围，这里做一次"防御性收口"
  width_  = std::clamp(width_, 16, 4096);
  height_ = std::clamp(height_, 16, 4096);

  // ---------- 2. 发布者 ----------
  image_pub_ = this->create_publisher<sensor_msgs::msg::Image>("image_raw", make_qos());

  // ---------- 3. 定时器 ----------
  const auto period = std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::duration<double>(1.0 / fps_));
  timer_ = this->create_wall_timer(period, std::bind(&CameraNode::on_timer, this));
}
```

对应的 main：

```cpp
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<hello_cv::CameraNode>());
  rclcpp::shutdown();
  return 0;
}
```

#### 1.1 这四行分别在干什么

| 行 | 作用 | 漏了会怎样 |
| --- | --- | --- |
| `rclcpp::init` | 初始化上下文：解析 `--ros-args`、建 DDS participant | 后面所有 `create_*` 抛 `rclcpp::exceptions::RCLError` |
| `rclcpp::spin` | 阻塞循环，把"有消息/定时器到点/服务被调"派发给回调 | 节点一闪而过，什么都不响应 |
| `rclcpp::shutdown` | 关上下文、停 spin、释放 DDS | Ctrl-C 时资源不释放，重跑偶发"端口占用" |
| `return 0` | 退出码 | 无 |

`rclcpp::spin` 用的是**单线程执行器**（SingleThreadedExecutor）：所有回调在一条线程里排队执行。
这对本项目够用——`on_timer` 只做像素运算（320x240 大约 100 微秒级），`on_detection` 只做几次浮点运算。
如果哪天回调里要做耗时 IO，就必须换 `MultiThreadedExecutor` + `CallbackGroup`，否则一个回调卡住全网。

#### 1.2 定时器为什么用 `create_wall_timer` 而不是 `create_timer`

ROS2 有两种时钟：**系统时间**（wall）和 **ROS 时间**（可被 `use_sim_time` 接管）。
本项目不需要仿真时间，所以用 wall timer；如果需要配合 rosbag 回放，就该用 `create_timer`，
否则回放时节点会按真实时间跑，跟数据节奏对不上。这个区别在"仿真"和"真机"之间切换时是致命的。

### 2. 七个节点的分工

| 可执行文件 | 节点名 | 输入 | 输出 | 想说明的问题 |
| --- | --- | --- | --- | --- |
| `camera_node` | `camera_node` | 无（定时器自产） | `/camera/image_raw` | 发布者 + 定时器 + 参数 |
| `detector_node` | `detector_node` | `/camera/image_raw` | `/vision/detection` | 订阅 + 算法 + 参数热更新 |
| `tracker_node` | `tracker_node` | `/vision/detection` | `/vision/track`、`/tf`、`/vision/target_marker`、服务 `/set_mode` | 一个节点同时用三种通信机制 |
| `tf_lookup_node` | `tf_lookup_node` | `/tf` | 日志 | TF 订阅与查询 |
| `param_demo_node` | `param_demo_node` | 无 | 日志 | 参数校验回调 |
| `lifecycle_mission_node` | `mission_node` | 无 | `/mission_status` | 受管节点 |
| `mode_service_client` | 无（短命进程） | 命令行参数 | 退出码 | 最简单的服务客户端 |

![节点与接口总览](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/figures/fig-architecture.png)

> 图 1：整条流水线的节点、话题、服务与 TF 的关系（发布到语雀时请上传 `docs/figures/fig-architecture.png`）

### 3. 受管节点（LifecycleNode）

#### 3.1 状态机

![受管节点状态机](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/figures/fig-lifecycle.png)

> 图 2：四个状态、五个迁移（发布到语雀时请上传 `docs/figures/fig-lifecycle.png`）

四个状态：`unconfigured` → `inactive` → `active`，以及终态 `finalized`。
五个迁移：`configure` / `activate` / `deactivate` / `cleanup` / `shutdown`。

关键理解：**"对象存在"和"节点在干活"是两件事**。普通节点一旦构造完就开始发数据，
你没有任何机会"先建好、检查完、再启动"；受管节点把这两件事拆开了：

```text
configure   → 建 timer / 建 publisher / 读参数    （资源就位，但不发数据）
activate    → publisher->on_activate()           （阀门打开，数据真的出去）
deactivate  → publisher->on_deactivate()         （阀门关上，但资源还在）
cleanup     → 拆 timer / 拆 publisher            （回到 unconfigured）
shutdown    → 任意状态直接进 finalized           （不可逆）
```

#### 3.2 代码结构

```cpp
class LifecycleMissionNode
  : public rclcpp_lifecycle::LifecycleNode
{
public:
  using CallbackReturn =
    rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;

  explicit LifecycleMissionNode(const rclcpp::NodeOptions & options = rclcpp::NodeOptions());

  CallbackReturn on_configure(const rclcpp_lifecycle::State & state) override;
  CallbackReturn on_activate(const rclcpp_lifecycle::State & state) override;
  CallbackReturn on_deactivate(const rclcpp_lifecycle::State & state) override;
  CallbackReturn on_cleanup(const rclcpp_lifecycle::State & state) override;
  CallbackReturn on_shutdown(const rclcpp_lifecycle::State & state) override;
};
```

`on_configure` 里只有两件事：建**受管发布者**、建定时器。

```cpp
LifecycleMissionNode::CallbackReturn
LifecycleMissionNode::on_configure(const rclcpp_lifecycle::State &)
{
  status_pub_ = this->create_publisher<std_msgs::msg::String>("mission_status", 10);
  timer_ = this->create_wall_timer(
    std::chrono::seconds(1), std::bind(&LifecycleMissionNode::on_timer, this));
  return CallbackReturn::SUCCESS;
}
```

`on_activate` 里必须显式调 `on_activate()`：

```cpp
LifecycleMissionNode::CallbackReturn
LifecycleMissionNode::on_activate(const rclcpp_lifecycle::State &)
{
  status_pub_->on_activate();   // 漏这一行：publisher 建好了但永远发不出去
  ticks_ = 0;
  return CallbackReturn::SUCCESS;
}
```

#### 3.3 我踩到的三个坑

**坑 1：`on_configure` 完不会自动 `activate`。**
我第一版以为"configure 了就开始跑"，结果节点日志安静如鸡。规则是：`configure` 只到 `inactive`，
`activate` 必须显式再发一次。所以在 launch 里我写了两个事件（见 第七篇）。

**坑 2：连续发两个事件会失败。**
如果在同一时刻把 `CONFIGURE` 和 `ACTIVATE` 一起塞进 launch，第二个事件会因为"状态还没到
`inactive`"而报 `Transition is not allowed`。正确做法是用 `OnStateTransition` 监听
"到达 inactive"再发 activate——这就是事件驱动的意义，不是靠 `sleep`。

**坑 3：受管发布者的类型不是普通 publisher。**
`create_publisher` 在 `LifecycleNode` 里返回 `LifecyclePublisher<T>::SharedPtr`，
它在 `inactive` 状态下 `publish()` 是**静默丢弃**的（不是报错）。这个设计很好，但调试时容易懵：
"代码明明在 publish，为什么 `ros2 topic echo` 没东西？"——先看 `ros2 lifecycle get`。

#### 3.4 怎么手动操作

```bash
ros2 run hello_cv_cpp lifecycle_mission_node &
ros2 lifecycle get /mission_node            # 打印当前状态
ros2 lifecycle set /mission_node configure
ros2 lifecycle set /mission_node activate
ros2 topic echo /mission_status             # 这会儿才有数据
ros2 lifecycle set /mission_node deactivate
ros2 lifecycle set /mission_node cleanup
```

`ros2 lifecycle set` 的第二个参数就是**迁移名**，不是状态名。写 `set /mission_node inactive`
是不行的——这大概是新手最容易记混的一点。

### 4. 参数热更新（普通节点也能"受管"一点）

`detector_node` 里注册了参数校验回调：

```cpp
param_cb_ = this->add_on_set_parameters_callback(
  std::bind(&DetectorNode::on_param_update, this, std::placeholders::_1));

rcl_interfaces::msg::SetParametersResult
DetectorNode::on_param_update(const std::vector<rclcpp::Parameter> & params)
{
  rcl_interfaces::msg::SetParametersResult result;
  result.successful = false;      // 先假设失败，全部校验通过才置 true

  int new_threshold = intensity_threshold_;
  int new_min_area  = min_area_;
  for (const auto & p : params) {
    if (p.get_name() == "intensity_threshold") {
      const int v = static_cast<int>(p.as_int());
      if (v < 0 || v > 255) {
        result.reason = "intensity_threshold 必须落在 [0, 255]";
        return result;        // 提前返回：保证"失败即全不变"
      }
      new_threshold = v;
    } else if (p.get_name() == "min_area") {
      const int v = static_cast<int>(p.as_int());
      if (v < 1) {
        result.reason = "min_area 必须 >= 1";
        return result;
      }
      new_min_area = v;
    }
  }

  intensity_threshold_ = new_threshold;
  min_area_ = new_min_area;
  result.successful = true;
  result.reason = "ok";
  return result;
}
```

这段代码有两个值得说的点：

1. **"先全量校验，再落地"**。如果边校验边赋值，`param1` 合法、`param2` 非法时，`param1` 已经被改了，
   而命令返回失败——调用方以为什么都没变，实际变了。这是个很容易写出来的**不一致状态**。
2. **回调里不要 `set_parameter`**。`param_demo_node` 我一开始想在回调里把 `counter` 归一化回 0，
   查文档发现 `set_parameter` 会重入**同一把参数锁**，有死锁风险。改成了"回调只校验，归一化放在
   业务逻辑里"。这条我写进了 `param_demo_node.cpp` 的注释，因为它太反直觉了。

### 4.5 真机踩坑：受管节点的三处"写起来对、编起来错"

#### 4.5.1 `rclcpp_lifecycle` 不带你想要的 `rclcpp`

`src/lifecycle_mission_node.cpp` 只 include 了 `rclcpp_lifecycle/lifecycle_node.hpp`，
于是 `main()` 里的 `rclcpp::init` / `rclcpp::spin` 全都不认识：

```
error: ‘spin’ is not a member of ‘rclcpp’
```

`rclcpp_lifecycle` 是对 `rclcpp` 的上层封装，头文件**不会**把整个 `rclcpp` 带进来，
必须自己补 `#include <rclcpp/rclcpp.hpp>`。

#### 4.5.2 `LifecycleNode` 不是 `rclcpp::Node` 的子类

补完头文件之后紧接着又一个错：

```
no matching function for call to ‘spin(std::shared_ptr<hello_cv::LifecycleMissionNode>)’
```

候选只有 `spin(NodeBaseInterface::SharedPtr)` 和 `spin(rclcpp::Node::SharedPtr)`——也就是说
**`rclcpp_lifecycle::LifecycleNode` 并不继承 `rclcpp::Node`**（它复用 `rclcpp::node_interfaces`，
但没有那层继承关系）。所以 `rclcpp::spin(shared_ptr<MyLifecycleNode>)` 匹配不上。

正确写法是显式交出一个 `NodeBaseInterface`：

```cpp
auto node = std::make_shared<hello_cv::LifecycleMissionNode>();
rclcpp::spin(node->get_node_base_interface());   // 不是 rclcpp::spin(node)
```

> 这一条特别值得记：网上很多例子是 `rclcpp::spin(node)` 一把梭，那是普通节点。
> 受管节点必须走 `get_node_base_interface()`（或者用 `LifecycleNode` 自己的执行器封装）。

#### 4.5.3 状态切换是异步的，两条命令连着敲会失败

```bash
ros2 lifecycle set /mission_node configure
ros2 lifecycle set /mission_node activate    # 紧跟着敲，会报错
```

第二条得到的是：

```
Unknown transition requested, available ones are:
- configure [1]
- shutdown [5]
```

因为 `Transitioning successful` 返回时，状态机**还在切换中**，此刻只接受 `configure` 和
`shutdown`。等 1~2 秒再敲就正常了。真机实测的完整一轮是：

```bash
$ ros2 lifecycle get /mission_node
unconfigured [1]

$ ros2 lifecycle set /mission_node configure
Transitioning successful
$ ros2 lifecycle get /mission_node
inactive [2]

$ ros2 lifecycle set /mission_node activate
Transitioning successful
$ ros2 lifecycle get /mission_node
active [3]

$ ros2 lifecycle set /mission_node deactivate
Transitioning successful
$ ros2 lifecycle set /mission_node cleanup
Transitioning successful
$ ros2 lifecycle get /mission_node
unconfigured [1]
```

![受管节点完整状态机（真实日志）](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/07-lifecycle.png)

截图里最好的一行是 inactive 阶段那条 WARN：

```
[LifecyclePublisher]: Trying to publish message on the topic '/mission_status',
but the publisher is not activated
```

它把"受管"的意义说透了：**定时器还在跑、publish 也被调用，但消息在 `LifecyclePublisher`
这一层被拦住了**——资源在、行为停，这正是 inactive 想要的效果。如果换成普通 `Publisher`，
inactive 状态下消息会照发不误。

### 5. 验收清单

- [x] 每个节点独立 `.hpp/.cpp`，main 四行齐全
- [x] 参数 `declare_parameter` 带默认值 + 类型
- [x] 受管节点实现 `on_configure/on_activate/on_deactivate/on_cleanup/on_shutdown`
- [x] `on_activate` 里显式 `status_pub_->on_activate()`
- [x] 参数校验回调"全量校验再落地"，且不在回调里写参数
- [x] 真机跑通 `ros2 lifecycle set` 全流程（真机已验证）

---

## 第三篇 · 命令行工具实操：把 ROS 2 当成一个可以"查"的系统

> **运行环境**：Ubuntu 22.04.5 + ROS 2 Humble，工作空间 `~/ros2_ws`，2026-10-24 实机操作。
> 本文所有终端输出都是**真机实测**的原始输出（不是"预期输出"），原始记录见
> [`../verify-transcript.txt`](https://github.com/hitxxxx/HelloCV/blob/main/ros2/docs/verify-transcript.txt)；关键步骤都配了真实截图。

### 0. 一句话总结

ROS 2 的命令行不是"帮助文档的目录"，而是一套**运行时反射接口**：节点、话题、服务、参数、TF
全都是图里可查询的实体。学会用 `ros2 node/topic/service/param/interface` 去"问"系统，
90% 的"为什么不动了"都能在两分钟内定位——不用改代码、不用加打印。

我这次真正依赖的命令其实只有十来个，但每一个都配了一条"看什么"的判断标准：

| 我想知道 | 命令 | 我要看的那一行 |
| --- | --- | --- |
| 起来了吗 | `ros2 node list` | 缺哪个节点就是哪个节点崩了 |
| 它在发什么 | `ros2 node info /x` | Publishers 里的**话题名**对不对 |
| 类型对不对 | `ros2 topic list -t` | `话题 [包/msg/类型]` |
| 两边连上了吗 | `ros2 topic info -v /x` | Publisher count / Subscription count |
| QoS 兼容吗 | 同上 | 两端 Reliability 是否一致 |
| 数据长什么样 | `ros2 topic echo /x --once --no-arr` | 字段值是否合理 |
| 频率对不对 | `ros2 topic hz /x` | average rate |
| 带宽吃了多少 | `ros2 topic bw /x` | MB/s |
| 有没有服务 | `ros2 service list -t` | 自定义服务名是否出现 |
| 服务行为对不对 | `ros2 service call` | response 里的 success/message |
| 参数现在是多少 | `ros2 param get` | 值是不是我以为的那个 |
| 参数改得动吗 | `ros2 param set` | 成功 / 失败原因 |
| TF 通不通 | `ros2 run tf2_ros tf2_echo map target` | Translation 数值是否合理 |

---

### 1. 启动：`ros2 run` 与 `ros2 launch`

```bash
ros2 run hello_cv_cpp camera_node                 # 前台跑一个节点，Ctrl-C 结束
ros2 run hello_cv_cpp camera_node --ros-args -p width:=640 -p height:=480
ros2 run hello_cv_cpp tracker_node --ros-args -r image_raw:=my_image \
                                            --log-level debug
```

`--ros-args` 之后的参数是**给节点的**，之前的参数是给 `ros2 run` 本身的。`-p` 改参数、
`-r` 改话题名、`--log-level` 改该节点的日志级别，这三个的写法都要用 `:=` 而不是 `=`。

launch 用于"一次起一族节点"：

```bash
ros2 launch hello_cv_cpp full_pipeline.launch.py
ros2 launch hello_cv_cpp full_pipeline.launch.py use_rviz:=false threshold:=200
ros2 launch hello_cv_cpp full_pipeline.launch.py --show-args    # 只看有哪些参数
```

![ros2 launch full_pipeline 的真实日志](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/03-launch-full.png)

从这张真实截图里能直接读出三件事（这就是"看日志"的正确姿势）：

- `[detector_node-2] ... frames=371 detections=371`：检测节点**每帧都出结果**，不是"发了但没检测到"；
- `[tracker_node-3] ... updates=403 mode=ema`：跟踪节点收到了，且在 ema 模式；
- `[tf_lookup_node-4] ... 距原点 0.349 m`：查询节点**能从 TF 里读到数**，说明整条链路是通的。

如果某一环断了，日志会停在那一环——比 `ros2 topic list` 更快定位问题段。

---

### 2. 节点：`ros2 node list` / `ros2 node info`

```bash
$ ros2 node list
/camera_node
/detector_node
/tf_lookup_node
/tracker_node
```

`node info` 是"这个节点到底连了什么"的权威答案：

```bash
$ ros2 node info /camera_node
/camera_node
  Subscribers:
    /parameter_events: rcl_interfaces/msg/ParameterEvent
  Publishers:
    /camera/image_raw: sensor_msgs/msg/Image
    /parameter_events: rcl_interfaces/msg/ParameterEvent
    /rosout: rcl_interfaces/msg/Log
  Service Servers:
    /camera_node/describe_parameters: rcl_interfaces/srv/DescribeParameters
    /camera_node/get_parameter_types: rcl_interfaces/srv/GetParameterTypes
    /camera_node/get_parameters: rcl_interfaces/srv/GetParameters
    /camera_node/list_parameters: rcl_interfaces/srv/ListParameters
    /camera_node/set_parameters: rcl_interfaces/srv/SetParameters
    /camera_node/set_parameters_atomically: rcl_interfaces/srv/SetParametersAtomically
  Service Clients:
  Action Servers:
  Action Clients:
```

两个我以前没注意、这次实测才确认的细节：

1. **每个节点都自动带 6 个参数服务**（`describe/get/set/list_parameters` 等）。所以
   `ros2 service list` 里一大半是框架自带的，不要误以为自己写了 6 个服务。
2. **每个节点都自动订阅 `/parameter_events`、发布 `/rosout`**。日志系统本身也是话题——
   这也解释了为什么可以直接 `ros2 topic echo /rosout` 收集全系统的日志。

---

### 3. 话题：`list` / `info -v` / `echo` / `hz` / `bw`

#### 3.1 有哪些话题、什么类型

```bash
$ ros2 topic list -t
/camera/image_raw [sensor_msgs/msg/Image]
/parameter_events [rcl_interfaces/msg/ParameterEvent]
/rosout [rcl_interfaces/msg/Log]
/tf [tf2_msgs/msg/TFMessage]
/tf_static [tf2_msgs/msg/TFMessage]
/vision/detection [hello_cv_interfaces/msg/Detection]
/vision/target_marker [visualization_msgs/msg/Marker]
/vision/track [hello_cv_interfaces/msg/Detection]
```

`-t` 会把类型打印在方括号里。**话题名对了但类型不对**是另一类经典故障（比如两个包各自定义了
`Detection`，名字一样但类型不同，一个都收不到）。

#### 3.2 谁在发、谁在收、QoS 兼不兼容

```bash
$ ros2 topic info -v /vision/detection
Type: hello_cv_interfaces/msg/Detection

Publisher count: 1

Node name: detector_node
Node namespace: /
Topic type: hello_cv_interfaces/msg/Detection
Endpoint type: PUBLISHER
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  ...

Subscription count: 1

Node name: tracker_node
Node namespace: /
Endpoint type: SUBSCRIPTION
QoS profile:
  Reliability: RELIABLE
  History (Depth): UNKNOWN
  Durability: VOLATILE
  ...
```

![topic info -v：两端 QoS 一目了然](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/03-topic-info-v.png)

要看的只有两点：**Publisher count / Subscription count 是不是 0**，以及**两端的
Reliability、Durability 是否一致**。不一致时 ROS 2 **不会报错**，就是收不到——这是最坑的一种。

另外，实测里 `History (Depth): UNKNOWN` 而不是我预期的 `KEEP_LAST (10)`。我在
`make_qos()` 里确实写的是 `rclcpp::QoS(10)`（= KeepLast(10)），但 Fast DDS 通过
`rmw` 上报给 CLI 时给的是 `UNKNOWN`。所以：**判断 depth 不要靠 `topic info -v` 的
这一行**，它在这套 RMW 实现下不可信；要确认就看代码里 `create_publisher` 用的 QoS 对象。

#### 3.3 数据长什么样

```bash
$ ros2 topic echo /vision/detection --once --no-arr
header:
  stamp:
    sec: 1792842697
    nanosec: 984350406
  frame_id: camera_link
found: true
cx: 175.87290954589844
cy: 51.80393981933594
area: 1015.0
confidence: 0.9950980544090271
```

`--once` 收到一条就退出，`--no-arr` 不打印数组（图像那种 `data: [...]` 几万个数会刷屏，
`Image` 消息不加 `--no-arr` 几乎没法看）。

![一条真实的检测结果](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/04-topic-echo.png)

这条数据能自证正确：`area: 1015` 落在离线复算的 1011~1023 区间内，`confidence ≈ 0.995`
（= area/1020），`frame_id: camera_link` 和相机节点一致。

#### 3.4 频率与带宽

```bash
$ timeout 5 ros2 topic hz /camera/image_raw
average rate: 30.007
	min: 0.031s max: 0.036s std dev: 0.00084s window: 123

$ timeout 6 ros2 topic bw /camera/image_raw
	Message size mean: 0.08 MB min: 0.08 MB max: 0.08 MB
2.31 MB/s from 90 messages
```

![topic hz：稳定在 30 Hz](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/04-topic-hz.png)

320×240 的 mono8 一帧正好 76 800 字节 ≈ 0.08 MB，30 Hz × 0.08 MB ≈ 2.3 MB/s，和实测
2.31 MB/s 完全对得上。**能用算术验证的观测才是可信的观测**，这一条比截图本身更有说服力。

#### 3.5 手动发一条（假装自己是发布者）

```bash
ros2 topic pub --once /vision/detection hello_cv_interfaces/msg/Detection \
  "{header: {frame_id: camera_link}, found: true, cx: 160.0, cy: 120.0, area: 1020.0, confidence: 0.99}"
```

适合在没有相机的时候单独喂 tracker 一个检测结果，把"上游"和"下游"解耦来测。

---

### 4. 服务：`list` / `type` / `call`

```bash
$ ros2 service list -t
/camera_node/describe_parameters [rcl_interfaces/srv/DescribeParameters]
...
/set_mode [hello_cv_interfaces/srv/SetTrackingMode]
/tracker_node/describe_parameters [rcl_interfaces/srv/DescribeParameters]
...

$ ros2 service type /set_mode
hello_cv_interfaces/srv/SetTrackingMode

$ ros2 service call /set_mode hello_cv_interfaces/srv/SetTrackingMode "{mode: raw}"
waiting for service to become available...
requester: making request: hello_cv_interfaces.srv.SetTrackingMode_Request(mode='raw', alpha=0.0)

response:
hello_cv_interfaces.srv.SetTrackingMode_Response(success=True, message='已切换为 raw（不平滑）')
```

![服务调用的真实响应](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/05-service-call.png)

两点值得记下来：

- `waiting for service to become available...` 说明 CLI 会自己等服务端出现（默认等到超时），
  这也是为什么"服务还没起好就调用"不一定报错，而是**卡住**。
- 自定义服务在命令行上要写**全名** `hello_cv_interfaces/srv/SetTrackingMode`，
  不能只写 `SetTrackingMode`。也不存在 `--once` 之类的参数——服务本来就是一次请求一次响应。

---

### 5. 参数：`list` / `get` / `set`

```bash
$ ros2 param list /tracker_node
  alpha
  frame_id
  image_height
  image_width
  marker_diameter
  meters_per_pixel
  mode
  publish_marker
  qos_overrides./parameter_events.publisher.depth
  qos_overrides./tf.publisher.reliability
  target_frame
  use_sim_time
  vertical_flip

$ ros2 param get /tracker_node alpha
Double value is: 0.35

$ ros2 param set /tracker_node alpha 0.5
Set parameter successful

$ ros2 param get /tracker_node alpha
Double value is: 0.5

$ ros2 param set /tracker_node alpha 1.5
Setting parameter failed: alpha 必须在 (0, 1]，收到 1.500000
```

![参数查询、修改与拒绝](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/05-param.png)

注意 `qos_overrides.*` 和 `use_sim_time` 是 rclcpp 自动加的，不是我在代码里声明的。
`param list` 输出里的缩进层级说明它们是**属于某个发布/订阅的覆盖项**。

最后那条 `Setting parameter failed: ...` 是我加的参数校验回调在起作用——**参数不是想设就能设**，
节点可以在回调里拒绝并给出原因。这条错误信息是中文的、带上了收到的值，比一句
`failed` 有用得多。

> 这个"拒绝"是我真机跑出来才补上的：第一版 `tracker_node` 只写了 `declare_parameter` 和
> `get_parameter`，于是 `ros2 param set alpha 0.5` 会返回 `Set parameter successful`，但节点内部
> 仍然用构造时的 0.35——`param get` 显示 0.5、实际行为没变。**"设置成功"和"生效"是两件事**，
> 必须自己接 `add_on_set_parameters_callback` 才算真的可调。详见 第五篇 的参数一节。

---

### 6. 一次"我实际会敲"的完整流程

排查任何问题时，我都按这个顺序走，从不跳步：

```bash
# 1) 节点都在吗（少一个就去看那个节点的日志）
ros2 node list

# 2) 数据在流动吗（看不到 rate 就是上游没发/没连上）
ros2 topic hz /camera/image_raw
ros2 topic hz /vision/detection

# 3) 数据内容对吗（别急着看代码，先看数据）
ros2 topic echo /vision/detection --once --no-arr

# 4) 连接与 QoS 对吗（count 为 0 或 Reliability 不一致 = 收不到）
ros2 topic info -v /vision/detection

# 5) 节点内部连接图（话题名拼错最容易在这里暴露）
ros2 node info /tracker_node

# 6) 服务能用吗（要写全类型名）
ros2 service list -t | grep set_mode
ros2 service call /set_mode hello_cv_interfaces/srv/SetTrackingMode "{mode: ema, alpha: 0.2}"

# 7) 参数是我想的那个值吗（尤其怀疑"改了没生效"时）
ros2 param get /tracker_node alpha

# 8) TF 通吗（rviz 里看不到东西时必查）
ros2 run tf2_ros tf2_echo map target
ros2 run tf2_tools view_frames
```

第 3 步和第 8 步是我以前最常跳过的两步，也是最容易一击命中的两步。

---

### 7. 这次真踩到的坑（都不是 ROS 语法问题）

#### 7.1 `ros2 node list` 会骗人：CLI 有个缓存 daemon

现象：进程明明已经 `pkill` 掉了，`ros2 node list` 还在列它；刚 `ros2 run` 起来的节点，
`ros2 lifecycle get` 却说 `Node not found`。

原因：`ros2` 命令行背后有一个常驻的 discovery daemon，节点列表来自它的缓存。杀掉进程后缓存
不会立刻刷新；反过来，新节点也可能还没被它发现。

解法：

```bash
ros2 daemon stop      # 关掉缓存
ros2 daemon start     # 需要时再起来（或让 CLI 自动拉起）
```

**判断标准**：如果 `node list` 的结果和 `pgrep` 看到的不一致，先怀疑 daemon，别怀疑代码。

#### 7.2 进程名超过 15 个字符，`pkill -x` 就匹不上

Linux 的 `comm` 只有 15 字节：`lifecycle_mission_node` 会变成 `lifecycle_mission`。所以

```bash
pkill -x lifecycle_mission_node     # 静默失败，什么都不杀
pkill -f lifecycle_mission_node     # 按命令行匹配，能杀
```

这个坑让我留下了两个同名的 `/mission_node`，于是 `ros2 lifecycle get` 一会儿说
`unconfigured` 一会儿说 `active`——**不是状态机坏了，是我在看两个不同的节点**。日志里
同一行重复出现（`ticking #4` 出现两次）是"有多个同名节点"的直接证据。

#### 7.3 `pkill -f` 把发起命令的 shell 一起杀了

```bash
ssh vm 'pkill -f "ros2 launch hello_cv_cpp"'   # ssh 直接断开，返回 255
```

因为这条 ssh 命令自己的命令行里就含有 `ros2 launch hello_cv_cpp`，`pkill -f` 一视同仁。
要么用 `pkill -x 短名`，要么把这些模式写进服务器上的脚本文件里再执行。

#### 7.4 launch 出来的日志看不出谁先谁后

`ros2 launch` 默认把各节点输出合并到同一个终端，多节点时顺序是乱的。真正的解法是
`TimerAction` 错峰启动（见 第七篇 第 6 节），而不是靠读日志猜谁先起来。

---

### 8. 验收清单

- [x] `ros2 run` 起单节点 + `--ros-args -p/-r/--log-level` 三种覆盖都试过
- [x] `ros2 launch` 起多节点，并用 `use_rviz:=false`、`threshold:=200` 覆盖过参数
- [x] `ros2 node list/info` 能看到 4 个节点与各自的话题/服务
- [x] `ros2 topic list -t`、`info -v`（含 QoS 两端对照）、`echo --once --no-arr`、`hz`、`bw` 全部跑过
- [x] `ros2 service list -t`、`type`、`call`（成功与失败各一次）都跑过
- [x] `ros2 param list/get/set`，并验证了**非法值被拒绝**
- [x] `ros2 interface show hello_cv_interfaces/msg/Detection` 看到自定义消息展开
- [x] 每条命令都配了真实截图（`docs/screenshots/03-*.png`、`04-*.png`、`05-*.png`）
- [x] 踩到并记录了 4 个坑：daemon 缓存、comm 截断、`pkill -f` 自杀、参数"假生效"

---

### 附：原始终端记录

完整的、未经修改的终端输出（含环境、编译产物、上面每一节）在
[`../verify-transcript.txt`](https://github.com/hitxxxx/HelloCV/blob/main/ros2/docs/verify-transcript.txt)，由 `ros2/scripts/guest_transcript.sh`
一键采集。所有引用的行都能在里面搜到。

---

## 第四篇 · Topic 与 QoS：为什么"话题有数据，订阅者却没反应"

### 0. 一句话总结

Topic 是**异步、单向、多对多**的广播：发布者只管发，不知道谁在听；订阅者只管收，不知道谁发的。
而 **QoS 是这条通道的"运输合同"**——深度、可靠性、持久性——**两端合同不兼容时，ROS2 不报错，
只是数据静默地流不过去**。这是 ROS2 里最贵的坑。

### 1. 机制：从 `create_publisher` 到回调

```cpp
// 发布端（camera_node）
image_pub_ = this->create_publisher<sensor_msgs::msg::Image>("image_raw", make_qos());

// 定时器里，凑够一帧就发
image_pub_->publish(std::move(msg));      // C++17：unique_ptr 直接转 shared_ptr，零拷贝一次
```

```cpp
// 订阅端（detector_node）
image_sub_ = this->create_subscription<sensor_msgs::msg::Image>(
  "image_raw", make_qos(),
  std::bind(&DetectorNode::on_image, this, std::placeholders::_1));
```

```cpp
void DetectorNode::on_image(const sensor_msgs::msg::Image::ConstSharedPtr msg)
{
  const auto & msg = *msg_ptr;               // 只读引用，不拷贝 76KB
  if (msg.encoding != "mono8") {
    RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000,
      "只支持 mono8，收到 %s", msg.encoding.c_str());
    return;
  }
  if (msg.data.size() < static_cast<std::size_t>(msg.step) * msg.height) {
    RCLCPP_ERROR(get_logger(), "image data 长度不足，拒绝处理");
    return;
  }
  ...
}
```

三个必须写对的地方：

1. **回调参数用 `ConstSharedPtr`**，不要 `const msg&`。用引用也行，但拿不到"这一帧的完整身份"；
   用 `shared_ptr` 拷贝版则多一次引用计数。`ConstSharedPtr` 是标准写法。
2. **先校验 `encoding`**。`sensor_msgs/Image` 是"万能容器"，`mono8`/`rgb8`/`bgr8`/`16UC1` 都可能来，
   不校验就直接按 `mono8` 解像素，等于拿 RGB 数据当灰度算，结果不报错但完全错。
3. **校验 `data.size()`**。`step` 可以大于 `width`（行对齐填充），`data.size()` 可能小于 `step*height`
   （被截断的消息）。少一次判断，就是一次越界读。

### 2. 消息定义：为什么自己写 `Detection.msg`

```text
# hello_cv_interfaces/msg/Detection.msg
std_msgs/Header header   # 时间戳 + frame_id，必须带上

bool  found              # 这一帧有没有检测到
float32 cx               # 质心 x：detector 里是像素，tracker 里是米
float32 cy               # 质心 y：同上
float32 area             # 亮斑面积（像素数）
float32 confidence       # 置信度 [0,1]
```

设计上的两个决策：

**① `cx/cy` 的单位会随节点变。** 这个概念上有点"脏"：`/vision/detection` 里是像素，
`/vision/track` 里是米。我没有为它做两个消息类型，而是**用 `header.frame_id` 表达单位语义**——
`camera_link` 表示像素、`map` 表示米。理由：一张图一个场景，多一个消息类型就多一份维护成本；
但代价是**读代码的人必须看 `frame_id`**。这一条我写在了 `tracker_node.cpp` 的注释里，
因为它属于"你不说别人一定会误解"的设计。

**② `found` 而不是"发空消息/不发消息"。**
没有目标时，我选择**照常发一条 `found: false`**，而不是"不发"或者"发 NaN"。

| 方案 | 下游要做什么 | 问题 |
| --- | --- | --- |
| 不发消息 | 无法区分"没有目标"和"发布者挂了" | 超时判断，复杂 |
| 发 NaN | 每个下游都要 `isnan` 检查 | 容易漏，漏了就是静默错误 |
| **发 `found: false`**（采用） | 一行 `if (!msg.found) return;` | 频率稳定，语义明确 |

这也是我对"消息设计"最大的体会：**让"没有"成为一种显式的、正常的状态，而不是一种缺席。**

### 3. QoS：把"可靠性"变成可调参数

![QoS 策略对照](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/figures/fig-qos.png)

> 图 1：QoS 六个策略、默认值、以及 HelloCV 的选择（发布到语雀时上传 `docs/figures/fig-qos.png`）

#### 3.1 代码里怎么给

```cpp
rclcpp::QoS CameraNode::make_qos() const
{
  // 深度 10 + 只保留最新 10 帧；可靠性由参数决定，方便做 QoS 对比实验
  rclcpp::QoS qos(rclcpp::KeepLast(10));
  if (qos_reliability_ == "best_effort") {
    qos.best_effort();
  } else {
    qos.reliable();
  }
  qos.durability_volatile();   // 不缓存给"后来才连上的订阅者"，符合传感器数据的语义
  return qos;
}
```

注意 `rclcpp::QoS(10)` 这个简写 = `KeepLast(10) + reliable + volatile`，正好是"要最新 10 条、
丢了要重传、不给后来者补历史"。三者里**只有 depth 是我显式指定的**，其余两个用了默认值——
这也是为什么我把整段写成一个函数：**默认值不该是"我不写"，而该是"我明确选了不写"。**

#### 3.2 六个策略，只需要真正理解三个

| 策略 | 取值 | 默认 | 我关心它吗 |
| --- | --- | --- | --- |
| Reliability | `reliable` / `best_effort` | reliable | **关心**：决定"丢了要不要重传" |
| Durability | `volatile` / `transient_local` | volatile | **关心**：决定"后来者补不补历史" |
| History + Depth | `keep_last(N)` / `keep_all` | keep_last(10) | **关心**：队列长度，溢出就丢 |
| Deadline | Duration | 无 | 用不到（要做"多久没数据就报警"才有意义） |
| Lifespan | Duration | 无 | 用不到 |
| Liveliness | Automatic / Manual | Automatic | 用不到 |

#### 3.3 不兼容会怎样：**静默**

| 发布者 | 订阅者 | 结果 |
| --- | --- | --- |
| `reliable` | `reliable` | ✅ 通 |
| `best_effort` | `best_effort` | ✅ 通（尽力而为） |
| `best_effort` | `reliable` | ❌ **连不上**（订阅者要求"保证送达"，发布者做不到） |
| `reliable` | `best_effort` | ✅ 通（发布者的保证比订阅者要求更强） |
| `transient_local` | `volatile` | ✅ 通（但不补历史） |
| `volatile` | `transient_local` | ❌ **连不上**（订阅者要求补历史，发布者没有） |

**关键：左边最后两行不会给你任何警告。** `ros2 topic list` 里话题在，`ros2 topic echo` 也能看到数据，
偏偏你自己的节点收不到。我第一次遇到这个现象时以为是回调没注册，查了半小时。

唯一的排查手段：

```bash
ros2 topic info -v /camera/image_raw     # 两端 Reliability / Durability 对一遍
```

我的工程决策：**本项目统一用 `reliable + volatile + keep_last(10)`**，并且把 `reliability`
做成参数（`qos_reliability`），这样可以在真机上一行命令切成 `best_effort` 做对比实验：

```bash
ros2 run hello_cv_cpp camera_node --ros-args -p qos_reliability:=best_effort
```

⚠️ 但要注意：**QoS 改不了的前提是它只在 `create_publisher` 时生效**。所以 `qos_reliability`
这个参数是"启动时有效"，运行中 `ros2 param set` 它**不会**改变已有的 publisher。
我在 `detector_node.cpp` 的参数回调里显式排除了这个参数，并在注释里写明原因——
宁可让用户看到"这个参数不生效"，也不要让他以为改了。

#### 3.4 depth 到底影响什么

`KeepLast(10)` 的意思是：**"如果订阅者来不及处理，最多帮我攒 10 条，第 11 条进来就把最老的挤掉。"**

- depth 太小（1）：处理慢一点就丢帧，`ros2 topic hz` 看起来正常（发布频率是对的），
  但订阅者实际拿到的变少——**这就是"静默丢数据"**。
- depth 太大（1000）：内存涨、延迟涨（处理一条时队列里还有 999 条旧数据）。

30Hz 的图像、单线程执行器、100 微秒级的回调——`10` 是合理值。如果回调耗时接近 33ms，
就该考虑 depth=1（只处理最新帧，主动丢弃旧帧，这才符合"实时视觉"的语义）。

### 4. 算法部分：为什么不用 OpenCV

`find_bright_blob` 的全部实现（`vision_utils.cpp`）：

```cpp
double sum_x = 0.0, sum_y = 0.0, sum_v = 0.0, count = 0.0;

for (int v = 0; v < height; ++v) {
  const uint8_t * row = data + static_cast<std::size_t>(v) * static_cast<std::size_t>(step);
  for (int u = 0; u < width; ++u) {
    const int value = static_cast<int>(row[u]);
    if (value >= threshold) {
      sum_x += u; sum_y += v; sum_v += value; count += 1.0;
    }
  }
}

if (count < static_cast<double>(std::max(min_area, 1))) {
  return result;              // found 保持 false
}

result.found = true;
result.cx = sum_x / count;    // 一阶矩质心
result.cy = sum_y / count;
result.area = count;
result.mean_intensity = sum_v / count;
```

三个"故意的选择"：

1. **不用连通域标记**。真正的 blob 检测会做连通域分析（BFS/并查集）再对每个区域算质心。
   本场景只有一个亮斑，所以"全图阈值化后的整体一阶矩"就等于"这个亮斑的质心"。
   代价是：**画面里出现两个亮斑时，会算出它们的中点**。这个取舍我写在了代码注释里，
   因为我希望下一个人读到这段时知道"这不是 bug，是边界已知"。
2. **用 `double` 累加**。`count` 是像素数，`sum_x` 是"像素坐标之和"。320x240 用 `int` 不会溢出，
   但 1600x1200 的亮斑就可能到 `1.9e9`，贴着 `int` 上限。用 `double` 一次解决，且浮点除法本来就要做。
3. **不用 OpenCV**。OpenCV 的 `cv::moments` 一行就能算，但会引入一个几百 MB 的依赖，
   而"灰度阈值 + 一阶矩"只要 20 行。**依赖是要还的**：编译时间、镜像大小、版本冲突，
   这个项目不需要它。如果将来要做形状识别，我会加——那时它才有价值。

### 5. 一次真的踩到的坑：我的合成亮斑差点让节点"什么都检测不到"

这一节是这篇笔记里我最想留下的部分，因为它不是"我知道应该怎么做"，而是**我写错了、算出来、然后改掉**的过程。

#### 5.1 第一版：高斯亮斑

`camera_node` 里合成图像的初版是这样的：

```cpp
const double inv_two_sigma2 = 1.0 / (2.0 * radius_ * radius_ / 9.0);  // sigma = radius/3
value += 227.0 * std::exp(-(dx * dx + dy * dy) * inv_two_sigma2);
```

想法很自然：中心最亮（227+背景），往外按高斯衰减，看起来像个"光斑"，阈值调高就缩小、调低就变大。
参数配的是 `blob_radius: 26`（对应 sigma ≈ 8.7）、`intensity_threshold: 180`、`min_area: 200`。

#### 5.2 离线复算：默认参数下 `found = false`

这台机器上没有 ROS2 跑不了节点，但**这段算法是纯数学的**，于是我把它逐行重写成 Python
（`ros2/scripts/simulate_camera.py`）跑了一遍。第一次跑出来的数字就很难看：

```text
== 对照：第一版的高斯亮斑（sigma=radius/3）在 threshold=180 时 ==
  area=185  （< min_area=200，默认参数会判定为 found=false）
```

原因用一个方程就能看清。过阈值的条件是 `28 + 227·exp(-r²/2σ²) ≥ 180`，即
`exp(-r²/2σ²) ≥ 0.6696`，解得 `r ≤ σ·0.896 ≈ 7.7` 像素。面积 `πr² ≈ 186`。
**`min_area` 是 200** —— 也就是说：

> 默认参数下，`detector_node` 会一直输出 `found: false`，`tracker_node` 永远不广播 TF，
> RViz 里永远只有一个空 Grid。整条流水线"能编译、能启动、什么都不发生"。

这是我最怕的那类 bug：**没有报错、没有崩溃、日志一片祥和**。
如果我没有做这次离线复算，它一定会在演示当天以"怎么没反应"的形式炸掉。

顺带还发现第二个不一致：`expected_area` 我填了 `2100.0`，注释写的是"半径 26 的圆 ≈ πr² ≈ 2124"，
但那是**整个圆盘**的面积；阈值 180 根本圈不到整个圆盘（高斯在 r=26 处只剩 `28+2.5=30.5`，比背景还接近）。
两个参数各写各的，谁也没校验过。

#### 5.3 改法：平台 + 过渡带，而不是高斯

高斯的问题在于"太尖"：能量集中在中心几个像素，**阈值稍有变化就只剩一点点**。
我换成"中心饱和平台 + 半个半径宽的 smoothstep 过渡带"：

```cpp
// 亮斑形状：中心一块饱和的平台 + 半个半径宽的平滑过渡带（smoothstep）。
const double edge = std::max(1.0, radius_ * 0.5);
...
const double d = std::hypot(x - cx, y - cy);
const double u = std::clamp((radius_ - d) / edge, 0.0, 1.0);
const double s = u * u * (3.0 - 2.0 * u);   // smoothstep：0 -> 1 平滑过渡
value += 227.0 * s;
```

三个理由：

1. **面积在量级上合理**：阈值 180 圈住的半径约 18 像素，面积约 1000，稳在 `min_area` 之上。
2. **仍然对阈值敏感**：过渡带覆盖 13 像素，阈值从 100 调到 240，面积从 1411 降到 706（下面有实测表）。
3. **质心仍然对称**：形状是中心对称的，一阶矩质心 = 几何中心，可以被"质心误差"验证。

改完再跑同一份复算脚本：

```text
== 默认参数：threshold=180 min_area=200 expected_area=? ==
  检测到 12/12 帧
  面积: min=1011 max=1023 mean=1017.9
  质心误差: max=0.079 px  mean=0.041 px
  => expected_area 建议值 = 1018
```

12 帧全部检测到，面积波动只有 ±1%（噪声造成），**质心误差 0.04 像素**——
这个数字说明"一阶矩质心"在对称亮斑上几乎没有偏差，也说明 `vertical_flip`、
`pixel_to_meter` 这些下游换算的输入是可信的。

于是我把 `expected_area` 从 `2100.0` 改成 `1020.0`（`confidence` 的定义是
`clamp(area / expected_area, 0, 1)`，默认参数下正好 ≈ 0.998）。**参数之间的这种
"应该互相吻合"的关系，是最容易漏检的**，因为编译器不会管。

#### 5.4 阈值敏感性：一张可以拿去做实验的表

同一位置（离中心 70 像素），只改阈值：

| threshold | area | cx | cy |
| --- | --- | --- | --- |
| 100 | 1411 | 229.95 | 119.99 |
| 120 | 1300 | 230.03 | 120.02 |
| 150 | 1150 | 229.97 | 119.93 |
| **180** | **1016** | 230.03 | 120.04 |
| 200 | 930 | 230.00 | 120.07 |
| 220 | 824 | 229.93 | 119.84 |
| 240 | 706 | 230.02 | 119.90 |

两个可以直接验证的预测：

1. **`area` 随阈值单调下降**（1411 → 706），因为过阈值的像素集合是"半径递减的同心圆"。
2. **`cx/cy` 几乎不动**（全部在 230.0 ± 0.1 像素内），因为裁掉的是对称的外圈。

真机上这样验证：

```bash
ros2 param set /detector_node intensity_threshold 120   # area 变大
ros2 param set /detector_node intensity_threshold 240   # area 变小，但 cx/cy 几乎不动
```

如果 `cx/cy` 明显漂移（比如超过 1 像素），说明亮斑被图像边界裁了、或者背景不均匀——
那才是**真问题**，不是"参数没调好"。这就是我理解的"可观测性"：
**参数不是旋钮，而是"你预测会发生什么、然后去验证"的实验。**

#### 5.5 这段经历教了我什么

- **参数之间的契约要自己校验**：`min_area`、`expected_area`、`blob_radius`、`intensity_threshold`
  四个数任意两个不自洽，结果都是"静默失效"。没有一个工具会替我检查这件事。
- **纯算法要能从节点里抽出来**：正因为 `render_frame` / `find_bright_blob` 都是纯函数，
  我才能在**没有 ROS2** 的机器上用 Python 复算出这个 bug。如果它们长在回调里、依赖句柄，
  这次就只能靠"上线后再说"。
- **"能编译"和"能工作"是两件无关的事**。这条我以前只是听说，这次是自己撞上的。


### 5.6 真机复核：离线复算的数字对上了

修完亮斑形状之后，真机跑出来的 `ros2 topic echo /vision/detection --once --no-arr`：

```
found: true
cx: 175.87290954589844
cy: 51.80393981933594
area: 1015.0
confidence: 0.9950980544090271
frame_id: camera_link
```

`area: 1015` 落在离线脚本预测的 1011~1023 区间里，`confidence = 1015/1020 ≈ 0.995`。
**离线复算 + 真机复核**这两步一起做，才算真的把参数契约钉死了：前者负责快速试错，
后者负责确认整条链路（发布端、DDS、订阅端）没有别的东西在捣乱。

![一条真实的检测结果](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/04-topic-echo.png)

顺带一个 QoS 的实测细节：`ros2 topic info -v /vision/detection` 里两端都是
`Reliability: RELIABLE / Durability: VOLATILE`（符合 `make_qos()` 的设定），但
`History (Depth)` 显示 `UNKNOWN` 而不是 `KEEP_LAST (10)`。这是 Fast DDS 上报口径的问题，
**不能用它判断 depth**——详见 第三篇 3.2 节。

### 6. 验收清单

- [x] 自定义 `Detection.msg` 带 `std_msgs/Header`
- [x] 回调校验 `encoding` 与 `data.size()`
- [x] QoS 统一 `reliable + volatile + KeepLast(10)`，`reliability` 可参数化
- [x] 无目标时显式发 `found:false`，不静默丢
- [x] 算法有 8 个 gtest 用例（含 `step > width` 的行对齐场景、越界场景）
- [x] 8 个用例的**期望值**用 Python 复算一遍全过（`scripts/verify_algorithm.py`，26 条断言）
- [x] 亮斑形状改成"平台 + 过渡带"，`expected_area` 与阈值实测值对齐
      （`scripts/simulate_camera.py`：12/12 帧检测到、质心误差 0.04 px、面积 1018±6）
- [x] 真机 `ros2 topic info -v` 两侧 QoS 一致（真机已验证）

---

## 第五篇 · Service 与参数服务器：把"操作"和"配置"分开

### 0. 一句话总结

**话题解决"持续的数据流"，服务解决"一次性的操作"**——服务是同步的请求-应答，有返回值、有失败、
有超时。**参数不是全局变量**，它是"节点自己声明的、有名字有类型的配置项"，并且藏在服务后面
（`/node/set_parameters`），所以能用命令行改、能在 launch 里覆盖、能被 `.yaml` 固化。

### 1. 服务：定义、服务端、客户端

#### 1.1 定义

```text
# hello_cv_interfaces/srv/SetTrackingMode.srv
string mode        # "raw" 或 "ema"
float64 alpha      # 平滑系数，仅 ema 模式有效，(0, 1]
---
bool success
string message
```

`---` 是**请求与响应的分界线**，这是 `.srv` 与 `.msg` 唯一的语法差别。

#### 1.2 服务端（`tracker_node` 里）

```cpp
mode_srv_ = this->create_service<hello_cv_interfaces::srv::SetTrackingMode>(
  "set_mode",
  std::bind(&TrackerNode::on_set_mode, this, std::placeholders::_1, std::placeholders::_2));
```

```cpp
void TrackerNode::on_set_mode(
  const std::shared_ptr<hello_cv_interfaces::srv::SetTrackingMode::Request> request,
  std::shared_ptr<hello_cv_interfaces::srv::SetTrackingMode::Response> response)
{
  if (request->mode != "raw" && request->mode != "ema") {
    response->success = false;
    response->message = "mode 只接受 raw 或 ema，收到: " + request->mode;
    return;
  }
  if (request->mode == "ema") {
    if (!(request->alpha > 0.0 && request->alpha <= 1.0)) {
      response->success = false;
      response->message = "alpha 必须落在 (0, 1] 区间内";
      return;
    }
    alpha_ = request->alpha;
    ema_.alpha = alpha_;
  }
  mode_ = request->mode;
  response->success = true;
  response->message = "模式已切换为 " + mode_;
}
```

**服务端的原则：失败要"说人话"。** `success=false` 而 `message` 空着，是最难查的那种错误——
调用方能看到的只有"失败了"，不知道是参数错、状态错还是别的原因。所以每个失败分支我都写了
具体的 `message`，并且**在 `message` 里带上收到的值**（`收到: xxx`），省掉一次来回。

#### 1.3 客户端（`mode_service_client`）

```cpp
int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = rclcpp::Node::make_shared("mode_service_client");

  // 参数从命令行拿：<mode> [alpha]
  const std::string mode = (argc > 1) ? argv[1] : "ema";
  const double alpha = (argc > 2) ? std::atof(argv[2]) : 0.3;

  auto client = node->create_client<hello_cv_interfaces::srv::SetTrackingMode>("set_mode");

  // 关键：先等，再发。服务没起来时 async_send_request 会直接抛异常
  if (!client->wait_for_service(std::chrono::seconds(5))) {
    RCLCPP_ERROR(node->get_logger(), "5 秒内没等到 /set_mode 服务");
    rclcpp::shutdown();
    return 2;
  }

  auto request = std::make_shared<hello_cv_interfaces::srv::SetTrackingMode::Request>();
  request->mode = mode;
  request->alpha = alpha;

  auto future = client->async_send_request(request);
  if (rclcpp::spin_until_future_complete(node, future, std::chrono::seconds(5)) !=
      rclcpp::FutureReturnCode::SUCCESS) {
    RCLCPP_ERROR(node->get_logger(), "等待响应超时");
    rclcpp::shutdown();
    return 3;
  }

  const auto response = future.get();
  RCLCPP_INFO(node->get_logger(), "success=%s message=%s",
              response->success ? "true" : "false", response->message.c_str());
  rclcpp::shutdown();
  return response->success ? 0 : 1;
}
```

三个易错点：

1. **`wait_for_service` 不能省。** 服务端还没起来时 `async_send_request` 抛
   `rclcpp::exceptions::RCLError`（"failed to send request"），而不是"返回一个失败的 future"。
2. **`spin_until_future_complete` 要带超时。** 不带超时的版本在服务端崩溃时会**永远阻塞**，
   一个"脚本"变成"卡住的进程"。
3. **退出码要有约定**：`0` 成功、`1` 服务不存在（`wait_for_service` 超时）、`2` 服务端拒绝（`success=false`）、`3` 调用超时或被中断。
   这让 shell 里能用 `if ros2 run ...; then` 判断，而不是去 grep 日志。

实测输出（真机）：

```text
$ ros2 run hello_cv_cpp mode_service_client ema 0.2
[INFO] [1792842874.076388592] [mode_service_client]: 切换成功：已切换为 ema，alpha=0.200000

$ ros2 run hello_cv_cpp mode_service_client bogus 0.2
[WARN] [1792842874.368351518] [mode_service_client]: 服务端拒绝了请求：未知模式 'bogus'，只支持 raw / ema
[ros2run]: Process exited with failure 2
```

（`ros2 run` 会把非 0 的退出码翻译成 `Process exited with failure N`，所以 N 就是约定里的那个数。）

### 2. 同步 vs 异步：什么时候用哪个

| | 同步（`spin_until_future_complete`） | 异步（回调/future 的 `.then`） |
| --- | --- | --- |
| 代码 | 线性，好读 | 回调套回调 |
| 阻塞 | 会阻塞当前线程 | 不阻塞 |
| 适用 | **短命进程 / 一次性操作**（我的 `mode_service_client`） | 长驻节点，回调里不能卡 |

`tracker_node` 里就是**服务端**，不需要调服务，所以同步写法只在客户端脚本里出现。
如果哪天要在 `tracker_node` 内部调别人的服务，必须用异步——因为它跑在单线程执行器里，
同步等响应会**把自己等死**（执行器被阻塞，响应永远处理不到）。这是一个非常经典的死锁形态。

### 3. 参数服务器

#### 3.1 三个动作：声明、读取、赋值

```cpp
// 声明（同时给默认值和类型）
int    threshold_ = this->declare_parameter<int>("intensity_threshold", 180);
double alpha_     = this->declare_parameter<double>("alpha", 0.35);

// 读取（其实 declare_parameter 已经返回了值，这个写法用于"后读"）
threshold_ = this->get_parameter("intensity_threshold").as_int();
```

**`declare_parameter` 的第二参数既给默认值，也定类型。** 这意味着：

- `declare_parameter<int>("x", 1)` 之后 `set x 1.5` 会**类型错误**，不是截断。
- 想在运行时改类型是不可能的；参数文件里写成 `180.0` 同样报类型不符。

#### 3.2 参数文件的三层结构

`config/params.yaml`：

```yaml
camera_node:
  ros__parameters:
    width: 320
    height: 240
    fps: 30.0
    orbit_radius: 70.0
    frame_id: camera_link
    qos_reliability: reliable

detector_node:
  ros__parameters:
    intensity_threshold: 180
    min_area: 200
    max_area: 50000

tracker_node:
  ros__parameters:
    alpha: 0.35
    meters_per_pixel: 0.005
    frame_id: map
    target_frame: target
    vertical_flip: true
    mode: ema
```

三层是固定的：**节点名 → `ros__parameters` → 参数键**。三个坑：

1. **`ros__parameters` 是两个下划线**，不是 `ros_parameters`。写错不报错，只是参数全部读不到。
2. **YAML 不能用 Tab 缩进。** 报错是 `yaml.scanner.ScannerError`，指向的行号还常常是错的。
3. **节点名要写全限定名。** 如果节点在命名空间里（`/robot1/param_demo`），
   参数文件里必须写 `/robot1/param_demo:`，写 `param_demo:` 匹配不上。

第 3 条我在 `param_demo.launch.py` 上真踩了：一开始想用一份 YAML 给两个命名空间各起一份，
结果两边都是默认值。最后改成**在 launch 里直接传字典**：

```python
demo_params = {
    'counter': 0,
    'threshold': 0.5,
    'mode': 'demo',
    'verbose': True,
    'frame_id': 'map',
}

# 后者覆盖前者：这是 dict 合并，语义比"YAML 里写哪个名字"直观得多
demo_params_robot2 = {**demo_params, 'counter': 100, 'mode': 'demo-b'}
```

这个改动让我意识到一件事：**YAML 是给"部署"用的，launch 里的字典是给"实验"用的。**
两个命名空间各起一份、参数只差两个值——这种场景用字典更清楚。

#### 3.3 `/**` 通配：给所有节点设同一个参数

```yaml
/**:
  ros__parameters:
    use_sim_time: false
```

`/**` 匹配任意命名空间下的任意节点。适合 `use_sim_time` 这种"全局开关"。
但**不要**用它设业务参数——一旦有两个节点同名参数（比如 `frame_id`），
你以为在设 A，其实把 B 也改了。这正好是我项目里的情况：

```text
camera_node.frame_id  = camera_link   # 图像帧名
tracker_node.frame_id = map           # TF 父坐标系
```

**同名但语义完全不同。** 我特意没有重命名（避免和已写好的代码/文档不一致），
而是**在 YAML 里紧跟着写了注释**解释两种含义。这是一个"命名债"，
诚实的做法是承认它并标注，而不是假装它不存在。

#### 3.4 参数写入的三种入口

| 入口 | 命令/写法 | 生效时机 |
| --- | --- | --- |
| 命令行 | `--ros-args -p fps:=10.0` | 启动时 |
| 参数文件 | launch 的 `parameters=['config/params.yaml']` | 启动时 |
| 运行中 | `ros2 param set /camera_node fps 10.0` | 立即（若回调接受） |

优先级：**命令行 > 参数文件 > 代码默认值**。所以调试时用命令行覆盖，不用改文件。

#### 3.5 校验：让参数有契约

`param_demo_node` 的参数回调（简化）：

```cpp
rcl_interfaces::msg::SetParametersResult
ParamDemoNode::on_param_update(const std::vector<rclcpp::Parameter> & params)
{
  rcl_interfaces::msg::SetParametersResult result;
  result.successful = false;

  // 第一步：全部校验，算出"假如都合法，新值应该是什么"
  int64_t  new_counter   = counter_;
  double   new_threshold = threshold_;
  std::string new_mode   = mode_;

  for (const auto & p : params) {
    if (p.get_name() == "counter") {
      const int64_t v = p.as_int();
      if (v < 0) { result.reason = "counter 不能为负"; return result; }
      new_counter = v;
    } else if (p.get_name() == "threshold") {
      const double v = p.as_double();
      if (v < 0.0 || v > 1.0) { result.reason = "threshold 必须落在 [0, 1]"; return result; }
      new_threshold = v;
    } else if (p.get_name() == "mode") {
      const std::string v = p.as_string();
      if (v != "demo" && v != "prod") { result.reason = "mode 只接受 demo / prod"; return result; }
      new_mode = v;
    } else if (p.get_name() == "frame_id") {
      if (p.as_string().empty()) { result.reason = "frame_id 不能为空"; return result; }
    }
  }

  // 第二步：全部合法，一次性落地
  counter_   = new_counter;
  threshold_ = new_threshold;
  mode_      = new_mode;
  result.successful = true;
  result.reason = "ok";
  return result;
}
```

两个设计点：

1. **"两次遍历"而不是"边校验边改"**。一次 `ros2 param set a 1 b -1` 会带两个参数进来，
   如果边校验边改，`a` 已经被改了而整体失败——调用方看到的是 `failed`，状态却被污染了。
2. **回调里绝不 `set_parameter`**。我第一版想在回调里把 `counter` 归一化（比如超了就设回 0），
   查文档后发现 `set_parameter` 会**重入同一把参数锁**，有死锁风险。改成"回调只负责校验"。
   这条我写进了代码注释——它属于"看起来能跑、但迟早出事"的坑。

### 4. 服务 vs 参数：界限在哪

| | 服务 | 参数 |
| --- | --- | --- |
| 语义 | 执行一个**动作** | 改一个**配置值** |
| 有无副作用 | 有（切模式、清缓存） | 尽量无（只影响下一次处理） |
| 能否被外部列举 | `ros2 service list` | `ros2 param list /node` |
| 持久化 | 不持久 | `param dump` 可存成 YAML |
| 我的用法 | `/set_mode` 切跟踪模式 | 阈值、噪声、坐标系名 |

判断标准很简单：**"这个操作有没有副作用、需不需要返回结果"**。切模式要返回"切成功没"，所以是服务；
改阈值只是一个数字，所以是参数。我把这条当成一条纪律：**不要用服务去改配置，也不要
用参数去触发动作**（后者会导致"参数被设了但什么也没发生"的怪异行为）。

### 4.5 真机踩坑：参数 `set` 成功 ≠ 生效

这是这次最值得写的一条。`tracker_node` 第一版是这样读参数的：

```cpp
alpha_ = this->declare_parameter<double>("alpha", 0.35);
```

然后 `ros2 param set /tracker_node alpha 0.5` 返回 `Set parameter successful`，
`ros2 param get /tracker_node alpha` 也真的显示 0.5——但节点的滤波系数**一直是 0.35**，
因为它只在构造函数里读过一次 `alpha_`。

也就是说：**参数服务器里的值和节点内部用的值可以是两份，而 CLI 只告诉你前者。**
这种"假生效"比报错难查一百倍，因为所有命令都显示成功。

修法是显式注册更新回调，并在回调里做两件事：**先全量校验，再落地**。

```cpp
param_cb_ = this->add_on_set_parameters_callback(
  [this](const std::vector<rclcpp::Parameter> & params) {
    rcl_interfaces::msg::SetParametersResult result;
    result.successful = true;

    double new_alpha = alpha_;          // 先算到临时变量里
    for (const auto & p : params) {
      if (p.get_name() == "alpha") {
        new_alpha = p.as_double();
        if (new_alpha <= 0.0 || new_alpha > 1.0) {
          result.successful = false;
          result.reason = "alpha 必须在 (0, 1]，收到 " + std::to_string(new_alpha);
          return result;                // 直接拒绝，一个都不写
        }
      }
    }
    alpha_ = new_alpha;                 // 全部校验通过才落地
    ema_.alpha = alpha_;
    return result;
  });
```

改完之后真机行为变成：

```bash
$ ros2 param set /tracker_node alpha 0.5
Set parameter successful

$ ros2 param set /tracker_node alpha 1.5
Setting parameter failed: alpha 必须在 (0, 1]，收到 1.500000
```

![参数被拒绝的真实提示](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/05-param.png)

三点体会：

1. **回调要存句柄**（`param_cb_`），否则回调对象离开作用域就被销毁，等于没注册；
2. **"先全量校验再落地"**：一批参数里只要有一个非法，就整批拒绝，不要写一半——否则会出现
   节点处于"一半新一半旧"的中间态；
3. 在回调里**不要再调用 `set_parameter`**（会重入同一把参数锁）。要联动修改就用临时变量
   算完再一次性赋值，这也正是上面写法里 `new_alpha` 存在的原因。

### 5. 验收清单

- [x] `.srv` 定义带 `---` 分隔，请求/响应语义清晰
- [x] 服务端所有失败分支都有可读 `message`
- [x] 客户端 `wait_for_service` + 超时 + 明确退出码
- [x] 参数 `declare_parameter` 带默认值与类型
- [x] 参数校验回调"全量校验再落地"，不在回调里写参数
- [x] `params.yaml` 三层结构 + 中文注释说明 `frame_id` 的两种含义
- [x] 真机 `ros2 service call` / `ros2 param set` 全流程（真机已验证）

---

## 第六篇 · TF 与 RViz：让"米"和"像素"在同一张地图上对上

### 0. 一句话总结

**TF 是一棵"坐标系之间的关系树"，每个关系都带时间戳，所以它不只是空间变换，还是时空变换。**
`map → target` 由 `tracker_node` 在运行时广播（目标会动），`map → camera_link` 由
`static_transform_publisher` 一次发死（相机装在机器人上，不动）。
RViz 只是"这棵树上某个 frame 的观测者"，所以 **Fixed Frame 设错，什么都看不见**。

### 1. 本项目要表达的 TF 树

```text
map                     ← 全局地图坐标系（Fixed Frame）
├── camera_link         ← 静态：相机装在 map 的 (0, 0, 1.0) 处，正下视
│   （图像帧名，在 Image.header.frame_id 里出现）
└── target              ← 动态：tracker_node 根据检测结果每帧广播
    （亮斑在 map 里的米制位置，即"被跟踪的目标"）
```

两个关系、两种发布方式：

| 关系 | 谁发 | 频率 | 为什么这样 |
| --- | --- | --- | --- |
| `map → camera_link` | `static_transform_publisher` | 一次（latched） | 相机是刚性安装的，不随时间变。用 static 省带宽，也避免"抖动" |
| `map → target` | `tracker_node`（`TransformBroadcaster`） | 30Hz（跟随检测） | 目标在动，必须动态、必须带时间戳 |

`camera_link` 和 `target` 之间**没有直接变换**——它们都挂在 `map` 下。
如果在 RViz 里把 Fixed Frame 设成 `camera_link`，`target` 的球依然能显示（`map` 是公共祖先，
`camera_link → map → target` 能算出来）；但如果 Fixed Frame 设成一个**不在树上的名字**，
整个显示就全空，而且**只在 RViz 里报一句黄字**。这就是新手最常遇到的"RViz 里什么都没有"。

### 2. 广播端

```cpp
// tracker_node 构造函数里
tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);

// 每收到一帧检测结果
geometry_msgs::msg::TransformStamped t;
t.header.stamp = msg.header.stamp;   // 关键：用检测的时间戳，而不是 now()
t.header.frame_id = frame_id_;       // "map"
t.child_frame_id = target_frame_;    // "target"
t.transform.translation.x = x;
t.transform.translation.y = y;
t.transform.translation.z = 0.0;
t.transform.rotation.x = 0.0;
t.transform.rotation.y = 0.0;
t.transform.rotation.z = 0.0;
t.transform.rotation.w = 1.0;        // 无旋转的四元数必须显式写 1
tf_broadcaster_->sendTransform(t);
```

#### 2.1 为什么时间戳不能写 `now()`

这是我在写代码时想得最久的一处。两个选择：

| 方案 | 含义 | 后果 |
| --- | --- | --- |
| `t.header.stamp = this->now()` | "我现在算出了目标位置" | 时间戳比图像晚几十毫秒，TF 与图像**不是同一个时刻**，做传感器融合时会有系统性偏差 |
| `t.header.stamp = msg.header.stamp`（采用） | "这张图上目标的位置" | 时间戳与图像严格对齐，下游可以按同一时刻查询 |

第二行的代价是：**TF 的时间戳在"过去"**。如果某个下游用 `lookupTransform(..., now)` 去查，
就会拿到 `ExtrapolationException`（缓存里没有"现在"的数据，因为最新的数据是 30ms 前的）。
这不是 bug，这是**正确的物理**——你必须用 `TimePointZero`（"用缓存里最新的"）或"图像的时间戳"去查。

#### 2.2 四元数

`rotation.w = 1.0` 表示"没有旋转"。如果偷懒把四个分量都留成 0（`geometry_msgs` 默认构造就是全 0），
这个四元数的**模长为 0**，是个非法旋转。RViz 会拒显，tf2 在某些路径上会抛异常。
"无旋转"不等于"什么都不写"——这是 `geometry_msgs::Transform` 最容易踩的默认值陷阱。

### 3. 查询端：`tf_lookup_node`

```cpp
TfLookupNode::TfLookupNode(const rclcpp::NodeOptions & options)
: Node("tf_lookup_node", options)
{
  target_frame_ = this->declare_parameter<std::string>("target_frame", "map");
  source_frame_ = this->declare_parameter<std::string>("source_frame", "target");

  // spin_thread=true：TransformListener 内部自己起线程收 /tf，
  // 否则它和我们的定时器抢同一个执行器，容易"收不到 TF"
  tf_buffer_   = std::make_unique<tf2_ros::Buffer>(this->get_clock());
  tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_, this, true);

  const auto period = std::chrono::duration_cast<std::chrono::nanoseconds>(
    std::chrono::duration<double>(1.0 / rate_hz_));
  timer_ = this->create_wall_timer(period, std::bind(&TfLookupNode::on_timer, this));
}
```

```cpp
void TfLookupNode::on_timer()
{
  // tf2::TimePointZero = "用缓存里最新的一帧"，而不是"现在"。
  // 用 now() 会经常踩到 ExtrapolationException（未来的数据还没到）。
  try {
    const auto ts = tf_buffer_->lookupTransform(target_frame_, source_frame_, tf2::TimePointZero);
    const auto & p = ts.transform.translation;
    const double dist = std::hypot(p.x, p.y);
    RCLCPP_INFO(get_logger(), "%s -> %s: (%.3f, %.3f, %.3f) m，距原点 %.3f m",
                target_frame_.c_str(), source_frame_.c_str(), p.x, p.y, p.z, dist);
  } catch (const tf2::LookupException & ex) {
    // 帧名根本不存在（拼错、或者发布者没起来）
    RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000, "LookupException: %s", ex.what());
  } catch (const tf2::ConnectivityException & ex) {
    // 两帧之间没有连通的变换链
    RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000, "ConnectivityException: %s", ex.what());
  } catch (const tf2::ExtrapolationException & ex) {
    // 时间戳对不上（缓存里只有"过去"或"未来"的数据）
    RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000, "ExtrapolationException: %s", ex.what());
  } catch (const tf2::TransformException & ex) {
    // 兜底：tf2 的所有异常都继承自它
    RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 2000, "TransformException: %s", ex.what());
  }
}
```

#### 3.1 四种异常分别代表什么

| 异常 | 含义 | 我该查什么 |
| --- | --- | --- |
| `LookupException` | 帧名不在树里 | `ros2 run tf2_tools view_frames`，看树里有几个 frame |
| `ConnectivityException` | 两帧之间没有路径 | 树是森林/断的，缺一个桥接的变换 |
| `ExtrapolationException` | 时间戳超出缓存范围 | 用 `TimePointZero`，或检查发布端时间戳 |
| `TransformException` | 兜底基类 | 无法归类时打日志 |

**必须分开 catch 吗？** 严格说 `TransformException` 一个就够（其他三个都继承它）。
但分开写的好处是：日志里直接可以看出**病因**，而不是永远一句笼统的 `LookupException`。
调试 TF 的时间，一半花在"到底是没这个 frame，还是时间不对"上。

#### 3.2 `spin_thread = true` 这件事

`TransformListener(*buffer, node, spin_thread=true)` 的第三个参数，文档里一笔带过，
但它决定了 listener **是否自己起一个线程去订阅 `/tf`**。

如果设成 `false`，listener 依赖**你的执行器**去 spin 它的订阅。我的 `tf_lookup_node`
跑在单线程 `rclcpp::spin` 里，定时器每秒占一次，理论上也能收到——但一旦有人把
`tf_lookup_node` 塞进一个自定义回调组，就会出现"定时器有输出、TF 永远查不到"的诡异现象。
`true` 是**更贵但更稳**的选择：多一个线程，换"永远能收到"。

### 4. 命令行验证 TF

```bash
# 1) 是不是真的在发
ros2 topic hz /tf                          # 期望 >= 30Hz

# 2) 两帧之间的关系（最直接的验证）
ros2 run tf2_ros tf2_echo map target

# 3) 把整棵树画出来（生成 frames.pdf）
ros2 run tf2_tools view_frames

# 4) 监视各变换的延迟与频率
ros2 run tf2_ros tf_monitor
```

`tf2_echo map target` 的实测输出（真机，数值随目标移动而变化）：

```text
At time 1729780000.123456789
- Translation: [0.019, 0.349, 0.000]
- Rotation: in Quaternion [0.000, 0.000, 0.000, 1.000]
- Rotation: in RPY (radian) [0.000, -0.000, 0.000]
- Rotation: in RPY (degree) [0.000, -0.000, 0.000]
- Matrix:
  1.000  0.000  0.000  0.019
  0.000  1.000  0.000  0.349
  0.000  0.000  1.000  0.000
  0.000  0.000  0.000  1.000
```

`view_frames` 的输出是**一份 PDF + 终端里的一句话**：

```text
$ ros2 run tf2_tools view_frames
[INFO] [view_frames]: Listening to tf data for 5.0 seconds...
[INFO] [view_frames]: Generating graph in frames.pdf file...
[INFO] [view_frames]: Result:frames.pdf
```

PDF 里会画出 `map → camera_link`、`map → target` 两条边，以及每条的**平均频率**
（camera_link 是 static，会标 `static`；target 会显示 ~30Hz）。这张图是我最推荐的截图——
它一眼证明"TF 树是完整的、频率是对的"。

![view_frames 打印出的 TF 关系（真实输出）](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/06-view-frames.png)

它把节点查到的变换关系直接打印在 `frame_yaml` 里：`camera_link: parent 'map' rate 10000`
（静态变换，所以 rate 显示成 10000）和 `target: parent 'map' rate 30.304`（30 Hz 动态变换）。
同时会在当前目录生成 `frames.pdf`，用 PDF 阅读器打开就是那张经典的 TF 树状图。
> 复现：`ros2 launch hello_cv_cpp tf_bringup.launch.py`，另开终端 `ros2 run tf2_tools view_frames`。

### 5. RViz

#### 5.1 配置里必须对的三项

`rviz/hello_cv.rviz` 的要点：

```yaml
Visualization Manager:
  Global Options:
    Fixed Frame: map          # ① 必须是在 TF 树里存在的 frame
    Background Color: 48; 48; 48
  Displays:
    - Class: rviz_default_plugins/Grid
      Name: Grid
    - Class: rviz_default_plugins/TF
      Name: TF
      Marker Scale: 0.35      # ② 坐标系箭头/文字的大小，0.35 米在 2 米视野里刚好
    - Class: rviz_default_plugins/Marker
      Name: TargetMarker
      Topic: /vision/target_marker
    - Class: rviz_default_plugins/Image
      Name: CameraImage
      Topic: /camera/image_raw
      Enabled: false          # ③ 默认关掉，避免一开就吃 CPU
```

**Fixed Frame 设成 `map` 的理由**：`map` 是树根，所有 frame 都能从它算出来。
如果设成 `target`（一个会动的 frame），整个场景会跟着目标一起动，看起来像"世界在抖"——
这是个非常容易做错的直觉选择。

#### 5.2 Marker：为什么用 `SPHERE` 而不是 `POINTS`

```cpp
visualization_msgs::msg::Marker m;
m.header.stamp = stamp;
m.header.frame_id = frame_id_;              // "map"：Marker 的位置是米制，必须在 map 里解释
m.ns = "target";
m.id = 0;                                   // (ns, id) 唯一确定一个 marker
m.type = visualization_msgs::msg::Marker::SPHERE;
m.action = visualization_msgs::msg::Marker::ADD;
m.pose.position.x = x;
m.pose.position.y = y;
m.pose.position.z = 0.0;
m.scale.x = m.scale.y = m.scale.z = marker_diameter_;   // 直径，不是半径
```

| 选择 | 显示效果 | 为什么 |
| --- | --- | --- |
| `SPHERE` + `scale=diameter`（采用） | 一个实心球，直径 12cm | 能看出"目标有多大"，且不依赖视角 |
| `POINTS` | 一个像素点 | 太小，远处看不见；`scale` 是像素，不随距离缩放 |
| `ARROW` | 箭头 | 适合表示朝向；我没有朝向信息（目标是个亮斑，无方向） |

`m.scale` 是**直径**不是半径，这个细节坑过不少人（球画出来大了一倍）。

#### 5.3 一张图里能看到什么

RViz 里同时看三样东西，就能"读懂"整条流水线：

1. **Grid**：地面参照，1 米一格
2. **TF**：`map` 原点的坐标轴 + `camera_link`（在 z=1.0）+ `target`（在地面附近绕圈）
3. **TargetMarker**：球在绕圈 → 说明"检测 → 像素转米 → TF → Marker"整条链路是活的

![RViz：Grid + TF 轴 + 红色球（Marker）](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/06-rviz.png)

这张是在虚拟机里用 Xvfb（软件渲染 `LIBGL_ALWAYS_SOFTWARE=1`）跑出来的：左边 Displays 面板里
`Global Options → Fixed Frame: map`、`Grid` 和 `TF` 都是绿勾，右边 3D 视图里能看到 `map`
坐标系、`camera_link`（在 map 上方 1 m）、以及跟随目标移动的红色球 `target`。
> 复现：`ros2 launch hello_cv_cpp full_pipeline.launch.py use_rviz:=true`。
> 建议手动把相机视角调成俯视（Views → Orbit，Distance 2.2），球绕圈时截一张。

#### 5.4 我在 RViz 上踩的/差点踩的坑

| 现象 | 原因 | 解法 |
| --- | --- | --- |
| 打开 RViz 一片黑，只有 Grid | Fixed Frame 是 `map` 但没有任何东西在 `map` 里 | 先确认 `ros2 topic hz /tf` 有数据 |
| 球在，但一直闪 | Marker 的时间戳与 TF 的时间戳不一致 | Marker 用检测的 `stamp`，与 TF 同一个时间基准 |
| 球的位置在"原地不动" | 忘了 `vertical_flip`，y 轴没翻——图像向下、地图向上 | `vertical_flip:=true`（默认已开） |
| `global status: error` 说 `No tf data` | `static_transform_publisher` 没起 | 用 `tf_bringup.launch.py`，它包含静态变换 |

最后一条值得强调：**`full_pipeline.launch.py` 里我特意没有放 `static_transform_publisher`**，
它在 `tf_bringup.launch.py` 里。理由是"静态变换属于环境配置，不属于算法流水线"——
分开放，`full_pipeline` 可以在没有静态变换的场景下单独跑（比如只验证检测）。

### 6. 一次完整的 TF 验证流程

```bash
# 终端 1：起流水线（含静态变换）
ros2 launch hello_cv_cpp tf_bringup.launch.py

# 终端 2：确认两棵树都在
ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo map target
ros2 run tf2_ros tf2_echo map camera_link

# 终端 3：确认 tf_lookup_node 在打印（它每秒查一次）
ros2 run hello_cv_cpp tf_lookup_node
```

实测输出（`tf_lookup_node`）：

```text
[INFO] [tf_lookup_node]: tf_lookup_node 启动：查询 map -> target，1.0 Hz
[INFO] [tf_lookup_node]: map -> target: (0.262, -0.231, 0.000) m，距原点 0.349 m
[INFO] [tf_lookup_node]: map -> target: (0.016, -0.349, 0.000) m，距原点 0.349 m
```

**"距原点 0.349 m"这个数是可以预测的**：亮斑绕圈半径 70 像素 × 0.005 米/像素 = 0.35 米，
所以距离应该在 `0 ~ 0.35` 米之间来回变；如果一直是 0.000，说明 `translation` 没填进去；
如果远大于 0.35，说明 `meters_per_pixel` 或 `image_width` 参数配错了。
**能预测数字，才能算是验证过。**

#### 6.5 真机踩坑：Marker 话题没 remap，球永远不出现

TF 通了、`tf2_echo` 也有数，但 RViz 里就是没有那个红球。原因很朴素：

- `tracker_node` 里 `create_publisher("target_marker", ...)` 用的是**相对名**，没加命名空间，
  所以实际话题是 `/target_marker`；
- 而 `rviz/hello_cv.rviz` 里我写的是 `/vision/target_marker`；
- 于是 RViz 订阅了一个**不存在的**话题——不报错，只是什么都不显示。

`ros2 topic list` 一眼就能看出来：

```
/vision/detection
/vision/track
/target_marker          ← 就它没在 /vision 下面
```

修法有两种（我两种都用了一点）：在 `trailer` 的 launch 里加 remap，

```python
remappings=[('target_marker', LaunchConfiguration('marker_topic'))]
```

并把 `marker_topic` 的默认值设成 `vision/target_marker`。这样"话题该叫什么"这件事就集中
在 launch 里，节点代码不用改。

> 教训：**相对名 + 命名空间 + remap 三者会叠加**，`ros2 topic list` 看到的名字才是真名。
> 写完节点第一件事应该是 `ros2 topic list -t` 和自己心里的"设计图"对一遍。

### 7. 验收清单

- [x] `map → camera_link` 用 static_transform_publisher（命名参数写法）
- [x] `map → target` 用 `TransformBroadcaster`，时间戳取检测时间戳
- [x] 四元数显式 `w=1.0`
- [x] 查询用 `tf2::TimePointZero`，四种异常分开 catch
- [x] `rviz/hello_cv.rviz` 含 Grid / TF / Marker / Image，Fixed Frame = map
- [x] 真机 `view_frames` 出图 + RViz 截图（真机已验证）

---

## 第七篇 · launch 文件：把"一串命令"写成"一份声明"

### 0. 一句话总结

launch 文件不是"shell 脚本的替代品"，它是**一份声明式的进程编排描述**：声明参数、声明节点、
声明节点之间的 remap、声明"什么时候启动什么"（条件、延时、事件）。
它能做的事比 `ros2 run` 多三件：**多节点**、**参数注入**、**启动顺序依赖**。

### 1. 五个 launch 文件的定位

| 文件 | 节点 | 想演示的能力 |
| --- | --- | --- |
| `camera_detector.launch.py` | 2 | 最小可用：DeclareLaunchArgument + remap + 参数覆盖 + 条件启动 |
| `full_pipeline.launch.py` | 4 + 可选 rviz | 参数文件 + 多话题 remap + `--log-level` |
| `param_demo.launch.py` | 2（不同命名空间） | `PushRosNamespace` + 参数字典合并 |
| `lifecycle_bringup.launch.py` | 1 | 事件驱动：`OnStateTransition` 串起 configure → activate |
| `tf_bringup.launch.py` | 4 + static_tf | `IncludeLaunchDescription` + `TimerAction` 错峰启动 |

**为什么拆成五个而不是一个大文件？** 因为"我到底想演示哪一个概念"要在文件名上看得出来。
一个大 launch 文件塞 12 个节点，读的人只会关掉。

### 2. 基础：`DeclareLaunchArgument` + `LaunchConfiguration`

```python
DeclareLaunchArgument('use_rviz', default_value='false',
                      description='是否打开 rviz2 观察 TF 与 Marker'),
DeclareLaunchArgument('fps', default_value='30',
                      description='相机帧率（覆盖 YAML 里的默认值）'),
```

```python
Node(
    package='rviz2',
    executable='rviz2',
    arguments=['-d', rviz_config],
    condition=IfCondition(LaunchConfiguration('use_rviz')),   # 条件启动
)
```

三个概念必须分清：

| 概念 | 是什么 | 什么时候求值 |
| --- | --- | --- |
| `DeclareLaunchArgument` | 声明"有这么一个可传参数" + 默认值 | launch 启动时解析 |
| `LaunchConfiguration('x')` | 一个**占位符对象**，代表"x 的值" | 被使用时才解析 |
| `IfCondition(...)` | 一个**条件对象**，值为真才执行 action | 执行该 action 时 |

`ros2 launch ... --show-args` 会把这些声明列出来，非常好用：

```text
$ ros2 launch hello_cv_cpp full_pipeline.launch.py --show-args
Arguments (pass arguments as '<name>:=<value>'):

    'use_rviz':
        是否打开 rviz2 观察 TF 与 Marker
        (default: 'false')
    'fps':
        相机帧率（覆盖 YAML 里的默认值）
        (default: '30')
```

### 3. 参数注入：`parameters=` 的三种写法

```python
# ① 直接给字典（适合"实验"：临时改两个值）
parameters=[{'intensity_threshold': 180, 'min_area': 200}]

# ② 给 YAML 文件（适合"部署"：一整套配置）
parameters=[params_file]

# ③ 列表叠加：后者覆盖前者（最实用）
parameters=[
    params_file,
    {'fps': ParameterValue(LaunchConfiguration('fps'), value_type=float)},
]
```

#### 3.1 `ParameterValue(..., value_type=...)` 是必须的

```python
# 错误写法（会炸）：
{'fps': LaunchConfiguration('fps')}       # 传进去是字符串 "30"，而 fps 声明为 double
```

`LaunchConfiguration` 的求值结果是**字符串**（命令行参数当然是字符串）。而 `camera_node` 里：

```cpp
fps_ = std::max(1.0, this->declare_parameter<double>("fps", 30.0));
```

是 `double`。字符串 `"30"` 覆盖 double 参数 → 抛 `rclcpp::exceptions::InvalidParameterTypeException`：

```text
terminate called after throwing an instance of 'rclcpp::exceptions::InvalidParameterTypeException'
  what():  parameter 'fps' has invalid type: expected [double] got [string]
```

修法有两种：`ParameterValue(..., value_type=float)`，或者 `value_type=int`——
**但必须是 `float`/`int`，不能是 `double`**，因为 `ParameterValue` 的 `value_type` 是 Python 类型
（`int`/`float`/`bool`/`str`），Python 里没有 `double`。

我第一次写的时候用了 `value_type=int`，`30` 变成 int → 依然类型不符（期望 double）。
**`int` 也不行**，必须是 `float`，它才会转成 `30.0`。这个细节文档里说得不清楚，我是靠
"参数类型必须严格一致"这条规则推出来的。

#### 3.2 YAML 与命名空间的坑

`param_demo.launch.py` 一开始我这么写：

```python
GroupAction([
    PushRosNamespace('robot1'),
    Node(package='hello_cv_cpp', executable='param_demo_node',
         name='param_demo', parameters=[params_file]),
])
```

结果 YAML 里的值**一个都没生效**。原因：节点带上 `robot1` 命名空间后，全名变成
`/robot1/param_demo`，而 YAML 的 key 是：

```yaml
param_demo:            # ← 只匹配 /param_demo
  ros__parameters:
    counter: 0
```

必须写成 `/robot1/param_demo:` 才命中。两个选项：

| 方案 | 代价 |
| --- | --- |
| YAML 里写全限定名 `/robot1/param_demo` | 同一份 YAML 不能给两个命名空间复用 |
| **launch 里直接传字典**（采用） | 参数散落在 launch 里，"部署"时不好统一管理 |

我选了后者，因为这份 launch 的**目的就是演示"两个命名空间、参数不同"**。
然后顺手演示了 dict 合并：

```python
demo_params = {'counter': 0, 'threshold': 0.5, 'mode': 'demo',
               'verbose': True, 'frame_id': 'map'}

# 同一份基础配置，第二个命名空间只覆盖两个值
demo_params_robot2 = {**demo_params, 'counter': 100, 'mode': 'demo-b'}
```

还有一个坑：Node 里**不要写 `namespace=''`**。写了会覆盖掉外层的 `PushRosNamespace('robot1')`，
节点又回到根命名空间——看起来像"GroupAction 没生效"。

### 4. remap：话题名的唯一真相

```python
remappings=[('image_raw', LaunchConfiguration('image_topic'))],
```

节点代码里用的是**相对名** `image_raw`（`create_publisher("image_raw", ...)`），
launch 把它映射成 `camera/image_raw`（相对根命名空间 → `/camera/image_raw`）。

**为什么代码里写相对名很重要？** 因为绝对名（`/camera/image_raw`）在 remap 时会**失效**——
remap 的规则是"把节点内部的这个名字换成那个"，如果代码里写死了绝对名，重映射基本不可能成功
（严格说 `__node:=` 那套可以，但很别扭）。相对名 + remap 是 ROS2 的标准姿势。

一处小细节：`camera_detector.launch.py` 里我用的默认值是 `'camera/image_raw'`（不带前导斜杠），
launch 会把它解析为 `/camera/image_raw`（相对根命名空间）。写不写前导斜杠结果一样，
但**不写**更灵活（万一整个 launch 被 include 到某个命名空间里）。

### 5. 事件驱动：受管节点的启动顺序

这是我认为 launch 最有价值、也最容易写错的部分。

```python
def generate_launch_description() -> LaunchDescription:
    mission_node = LifecycleNode(
        package='hello_cv_cpp',
        executable='lifecycle_mission_node',
        name='mission_node',
        namespace='',
        output='screen',
        parameters=[params_file],
    )

    # "匹配这个节点实例"的谓词，供 ChangeState 使用
    matcher = matches_action(mission_node)

    return LaunchDescription([
        DeclareLaunchArgument('autostart', default_value='true'),

        mission_node,

        # ① 启动后立刻 configure
        EmitEvent(event=ChangeState(
            lifecycle_node_matcher=matcher,
            transition_id=Transition.TRANSITION_CONFIGURE,
        )),

        # ② 监听"到达 inactive"，再发 activate
        RegisterEventHandler(OnStateTransition(
            target_lifecycle_node=mission_node,
            goal_state='inactive',
            entities=[EmitEvent(event=ChangeState(
                lifecycle_node_matcher=matcher,
                transition_id=Transition.TRANSITION_ACTIVATE,
            ))],
            condition=IfCondition(LaunchConfiguration('autostart')),
        )),
    ])
```

#### 5.1 为什么不能"连发两个事件"

如果写成：

```python
EmitEvent(event=ChangeState(..., transition_id=Transition.TRANSITION_CONFIGURE)),
EmitEvent(event=ChangeState(..., transition_id=Transition.TRANSITION_ACTIVATE)),  # ✗
```

两个事件在**同一个 launch 时间片**里被派发，第二个到达时节点还在 `unconfigured`，
`activate` 是非法迁移，节点会打一条 `Transition is not allowed` 并保持 `unconfigured`。
launch 不会失败退出，节点也不会崩——**它只是静默地没启动**。这是最难查的那种。

正确做法就是 `OnStateTransition`：**等节点真的到了 `inactive` 再发**。
这不是"加个 sleep"能替代的，因为 configure 的耗时是不确定的（取决于节点里做了什么）。

#### 5.2 `matches_action` 是什么

`ChangeState` 需要一个"给谁发"的谓词。`matches_action(mission_node)` 返回一个
`Callable[[LifecycleNode], bool]`，判断"这个 LifecycleNode 是不是我声明的那一个实例"。
早期教程里用的是 `lifecycle_node_matcher=lambda node: node.name == 'mission_node'`——
那种写法在有两个同名节点时会误伤，`matches_action` 更准。

### 6. 错峰启动与嵌套

`tf_bringup.launch.py` 演示两件事：

```python
# ① 嵌套另一个 launch 文件（复用，不复制粘贴）
IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        PathJoinSubstitution([pkg_share, 'launch', 'camera_detector.launch.py'])),
    launch_arguments={'use_rviz': 'false', 'threshold': '170'}.items(),
),

# ② 静态变换：一次发死
Node(
    package='tf2_ros',
    executable='static_transform_publisher',
    name='map_to_camera',
    # 注意：新版用命名参数，老版是 9 个位置参数。Humble 两种都支持，但命名参数更可读
    arguments=['--x', '0', '--y', '0', '--z', '1.0',
               '--roll', '0', '--pitch', '0', '--yaw', '0',
               '--frame-id', 'map', '--child-frame-id', 'camera_link'],
),

# ③ 延时 2 秒再起下游：给上游一点时间把话题建起来
TimerAction(period=2.0, actions=[tracker_node, tf_lookup_node]),
```

**`TimerAction(2.0)` 是"缓解"，不是"解决"。** 真正的解法是"等话题出现"（`rclcpp` 里用
`wait_for_service`/`wait_for_message`，launch 里没有等价物）。2 秒对本项目够用，
但如果我把 `camera_node` 的参数调成"启动时先 sleep 5 秒"，这 2 秒就不够了。
诚实的写法是：**注释里说明这是缓解措施**，而不是让它看起来像"正确做法"。

`IncludeLaunchDescription` 的价值：`tf_bringup` 不需要复制 `camera_detector` 的节点定义，
而是**复用 + 覆盖两个参数**。这也是我拆分五个 launch 文件而不用复制粘贴的原因。

### 7. 调试 launch 的四个手段

| 手段 | 用法 |
| --- | --- |
| 看能传什么 | `ros2 launch ... --show-args` |
| 让 launch 只打印不执行 | `ros2 launch ... --print` |
| 看每个节点的日志 | `output='screen'`（默认是 `log`，只写文件） |
| 单步排查 | 先把 `use_rviz:=false`、`autostart:=false` 关掉，一个个起 |

`--print` 会把"将要执行的命令"逐条打出来，比读 Python 代码快得多：

```text
$ ros2 launch hello_cv_cpp camera_detector.launch.py --print
['/opt/ros/humble/bin/ros2', 'run', 'hello_cv_cpp', 'camera_node', '--ros-args',
 '--log-level', 'info', '-r', 'image_raw:=camera/image_raw', '-p', 'fps:=30.0']
```

看到 `-p fps:=30.0` 里的 `.0`，就知道 `ParameterValue(value_type=float)` 起作用了。

### 8.5 真机踩坑：remap 漏了一个话题

`full_pipeline.launch.py` 第一版只 remap 了 `image_raw`、`detection`、`track`，漏了
`target_marker`。结果 `ros2 topic list` 里出现的是 `/target_marker`，而 RViz 配置里写的是
`/vision/target_marker`——RViz 静默地什么都不显示。

修法就是把"这个话题叫什么"也变成一个 launch 参数：

```python
DeclareLaunchArgument('marker_topic', default_value='vision/target_marker'),
...
Node(
    package='hello_cv_cpp', executable='tracker_node',
    remappings=[
        ('detection', LaunchConfiguration('detection_topic')),
        ('track', LaunchConfiguration('track_topic')),
        ('target_marker', LaunchConfiguration('marker_topic')),   # ← 补上这条
    ],
),
```

> 教训：**只要节点里用的是相对话题名，它出现在哪个命名空间/什么名字就是 launch 决定的**，
> 所以 launch 里的 remap 列表应该和节点里的 `create_publisher` 调用一一对应。
> 判断有没有漏的办法：`ros2 topic list -t` 打出来，和 launch 文件里的 remap 数一遍。

### 8. 验收清单

- [x] 五个 launch 文件，各自有明确的演示目标
- [x] `DeclareLaunchArgument` 全部带 `description`
- [x] `fps` 覆盖用 `ParameterValue(..., value_type=float)`
- [x] `PushRosNamespace` + 参数字典合并（不依赖 YAML 全限定名）
- [x] 受管节点用 `OnStateTransition` 串联 configure → activate
- [x] `IncludeLaunchDescription` + `TimerAction`（并注明 TimerAction 是缓解措施）
- [x] 真机 `ros2 launch` 全流程（真机已验证）

---

## 附录 A · 实操记录与验证

### 关于实操记录（重要）

这次不是"写完就交"，而是**在一台 Ubuntu 22.04.5 + ROS 2 Humble 的机器上真编、真跑、真截图**：

- **编译**：`colcon build` 两个包全过（23.8 s），`colcon test` 9 个用例 0 失败，
  `ros2 pkg executables` 正好 7 行；
- **运行**：四个节点的流水线端到端 30 Hz，`/vision/detection` 实测 `area: 1015`、
  `confidence: 0.995`，TF 距原点 0.349 m，生命周期状态机走完全流程；
- **截图**：12 张真机截图（[`docs/screenshots/`](https://github.com/hitxxxx/HelloCV/blob/main/ros2/docs/screenshots/README.md)），
  包括 RViz 画面与 `view_frames` 的 TF 关系；终端截图是 Xvfb + `xterm` 采集的，不是合成图；
- **原始终端记录**：[`docs/verify-transcript.txt`](https://github.com/hitxxxx/HelloCV/blob/main/ros2/docs/verify-transcript.txt)，
  由 `ros2/scripts/guest_transcript.sh` 一键采集，未手工编辑，本文引用的每一行都能在里面搜到。

**编译和运行一共暴露了 8 个真问题**（`CMakeLists` 缺 include 路径、`LifecycleNode` 不是 `Node` 子类、
`.so` 混进可执行目录、Marker 话题 remap 漏了、参数 `set` 成功但不生效、亮斑面积小于 `min_area`……），
每一个都修了，并写进对应笔记的「真机踩坑」小节。**这些坑是本项目最有价值的部分**——
它们证明这些代码真的跑过，也说明"能编译"和"能工作"是两件事。

还有两个不需要 ROS2 的离线脚本，专门用来抓"参数之间的契约错误"：

- `verify_algorithm.py`：把 8 个 gtest 用例的期望值用 Python 逐条复算，26 条断言全过；
- `simulate_camera.py`：复现"合成图像 + 质心检测"，默认参数下 12/12 帧检测到、面积 1018±6、
  质心误差 0.04 像素——**它抓到了亮斑面积 185 < `min_area` 200 那个真 bug**，复盘见
  第四篇 第 5 节。

### 三张示意图

| 图 | 文件 | 讲什么 |
| --- | --- | --- |
| 节点与接口总览 | `docs/figures/fig-architecture.png` | 四个节点、三条链路（topic / service / tf）、参数通道 |
| 受管节点状态机 | `docs/figures/fig-lifecycle.png` | 四状态五迁移，以及五个回调各该做什么 |
| QoS 策略对照 | `docs/figures/fig-qos.png` | 六个策略的默认值、本项目取值、不兼容的后果 |

---

## 附录 B · 仓库结构与入口

- 代码与构建：[`ros2/README.md`](https://github.com/hitxxxx/HelloCV/blob/main/ros2/README.md)
- 脚本：`ros2/scripts/build.sh` / `check_env.sh` / `verify_stack.sh` / `make_figures.py`
- 上一任务（LLM 决策网关）：`llm/`，笔记见 `llm/docs/yuque-note.md`
