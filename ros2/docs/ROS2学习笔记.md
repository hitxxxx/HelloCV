# HelloCV · ROS 2 学习笔记

> 这篇笔记记录我**从零把一条视觉流水线跑起来**的过程：
> 每一步在干什么、为什么这么干、哪里摔了一跤。
>
> 环境：Ubuntu 22.04.5 + ROS 2 Humble。文中所有截图和终端输出都是真机跑出来的，
> 代码在仓库 [`ros2/ros2_ws/src/`](https://github.com/hitxxxx/HelloCV/tree/main/ros2/ros2_ws/src)。

## 目录

1. 先看全貌：这条流水线在干什么
2. 装环境、建工作空间、建第一个包
3. 最小的节点：20 行代码
4. 话题（Topic）：一个发、一个收
5. QoS：ROS 2 最容易踩的坑
6. 服务（Service）：要一个明确答复
7. 参数（Parameter）：不改代码改行为
8. TF 与 RViz：让"像素"和"米"对上
9. launch：一条命令起全套
10. 受管节点（LifecycleNode）：为什么需要它
11. 我踩过的 8 个坑
12. 完整复现步骤
13. 学完之后的几句实话

---

## 1. 先看全貌：这条流水线在干什么

任务书要求把 ROS 2 的几个知识点都摸一遍。我不想写七个互不相干的 demo，就串成一条**能自圆其说的流水线**：

![节点与接口总览](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/figures/fig-architecture.png)

四个节点，各干一件事：

| 节点 | 干什么 | 用到什么 |
| --- | --- | --- |
| `camera_node` | 假装是相机，每秒造 30 张 320×240 的黑白图，图上有一个绕圈转的白点 | 定时器、发布者 |
| `detector_node` | 找出白点中心，算出坐标和面积，发出去 | 订阅者 + 发布者、参数 |
| `tracker_node` | 平滑坐标、换算成米、广播"目标在哪"，并在 RViz 里画个球 | 订阅者、TF 广播、服务端 |
| `tf_lookup_node` | 每秒查一次"目标离原点多远"，打印出来验证 | TF 查询 |

一句话：**相机发图 → 检测器找点 → 跟踪器算位置 → 用 TF 和 RViz 看见它**。

为什么不用 OpenCV？因为这里只需要"最亮的点在哪"，几个 for 循环就够了。
少一个依赖，就少一个装不上的理由 —— 最怕的就是环境装不起来。

## 2. 装环境、建工作空间、建第一个包

### 2.1 装 ROS 2 Humble

```bash
# Ubuntu 22.04 对应 Humble；24.04 要换成 Jazzy
sudo apt install ros-humble-desktop
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc   # 每个新终端都要有这一行
```

装完验证一下（能打印出版本号就说明装好了）：

```bash
ros2 --version
```

### 2.2 工作空间：ROS 2 的"项目文件夹"

ROS 2 有一个固定约定，记住这张表就不会迷路：

| 目录 | 是什么 | 要不要提交到 git |
| --- | --- | --- |
| `ros2_ws/src/` | **你写的源码** | 要 |
| `ros2_ws/build/` | 编译中间产物 | 不要 |
| `ros2_ws/install/` | 编译好的结果，`ros2 run` 从这里找东西 | 不要 |
| `ros2_ws/log/` | 编译日志 | 不要 |

```bash
mkdir -p ~/ros2_ws/src && cd ~/ros2_ws
```

这里有一个很容易踩的点：**`colcon build` 必须在 `ros2_ws` 下执行，不能进 `src` 里执行**。
在 `src` 里执行它会另建一套 `build/install`，然后你就再也找不到自己编的东西了。

### 2.3 造两个包

包 = 一份 `package.xml`（我是谁、我依赖谁）+ 一份 `CMakeLists.txt`（怎么编、装到哪）。
ROS 2 里一次任务的代码常常拆成两个包：

```bash
cd ~/ros2_ws/src

# ① 接口包：只放消息和服务定义（.msg / .srv），谁都能依赖它
ros2 pkg create --build-type ament_cmake hello_cv_interfaces

# ② 实现包：真正的 C++ 代码
ros2 pkg create --build-type ament_cmake hello_cv_cpp \
    --dependencies rclcpp rclcpp_lifecycle std_msgs sensor_msgs \
    geometry_msgs visualization_msgs tf2 tf2_ros hello_cv_interfaces
```

**为什么要拆两个包？** 因为依赖只能单向：实现包依赖接口包，接口包不依赖任何人。
如果消息和代码塞在一个包里，以后别人想复用你的消息，就得连你的实现代码一起拖进来。

### 2.4 编译

```bash
cd ~/ros2_ws
colcon build --symlink-install
```

![colcon build 真实输出](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/01-colcon-build.png)

`--symlink-install` 的意思是"装过去的是链接不是拷贝"，改 launch / yaml / rviz 不用重编。

编译完**必须**做这一步，否则 `ros2 run` 会说找不到包：

```bash
source install/setup.bash     # 或者 source ~/ros2_ws/install/setup.bash
```

看看到底编出了几个能跑的程序：

```bash
$ ros2 pkg executables hello_cv_cpp
hello_cv_cpp camera_node
hello_cv_cpp detector_node
hello_cv_cpp lifecycle_mission_node
hello_cv_cpp mode_service_client
hello_cv_cpp param_demo_node
hello_cv_cpp tf_lookup_node
hello_cv_cpp tracker_node
```

![7 个可执行文件](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/01-pkg-executables.png)

> **这里我踩过一个坑**：一开始编译出的可执行文件有 8 行，多了一个 `libhello_cv_vision.so`
> —— 因为我把"共享库"和"可执行文件"都装到了 `lib/<包名>/`，而 `ros2 pkg executables`
> 会把那个目录下所有文件都当成可执行文件列出来。改法：可执行文件装 `lib/<包名>/`，
> 库单独装 `lib/`。详见第 11 节。

## 3. 最小的节点：20 行代码

节点（node）就是"一个能干活的程序"。最小版本长这样：

```cpp
#include <rclcpp/rclcpp.hpp>

class MyNode : public rclcpp::Node
{
public:
  MyNode() : Node("my_node")           // ① 起个名字，必须全局唯一
  {
    timer_ = create_wall_timer(std::chrono::seconds(1), [this]() {
      RCLCPP_INFO(this->get_logger(), "还在运行");   // ② 每秒打一行日志
    });
  }
private:
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);                              // ③ 初始化
  rclcpp::spin(std::make_shared<MyNode>());              // ④ 转起来，卡在这里
  rclcpp::shutdown();                                    // ⑤ Ctrl+C 之后收尾
  return 0;
}
```

三个地方必须理解：

1. **`Node("my_node")` 的名字是唯一的**。起两个同名节点，ROS 2 不会报错，但你会看到日志混在一起，查问题时非常费劲。
2. **`rclcpp::spin()` 是个死循环**。它不停地"看看有没有消息要处理、有没有定时器到点了"，你的回调都是它调用的。所以 `spin` 之后写任何代码都不会执行，除非先 `Ctrl+C` 退出。
3. **`create_wall_timer` 是"墙上时钟"定时器**，即使开了仿真时间（`use_sim_time`）也按真实时间走。要跟着仿真时钟走，得用 `create_timer(clock_)`。

真实的 `camera_node` 就在这个骨架上加了三段：读参数、建发布者、定时器里造图。

## 4. 话题（Topic）：一个发、一个收

**话题是广播**：发布者只管往频道里喊，不知道谁在听；订阅者只管听，不知道谁在喊。
好处是"谁都不认识谁"，加一个新的分析节点不用改发布者的代码。

### 4.1 先定义消息

自定义消息要写在 `.msg` 文件里，一行一个字段：

```
# hello_cv_interfaces/msg/Detection.msg
std_msgs/Header header      # 时间戳 + 坐标系名
bool   found                # 这一帧到底有没有找到
float32 cx                  # 找到的点在图像里的 x（像素）
float32 cy                  # y（像素）
float32 area                # 亮斑面积，用来判断"是不是真的目标"
float32 confidence          # 0~1，面积的相对可信度（我自己算的）
```

写完 `.msg` 不用手写任何 C++ 代码，编译时会自动生成头文件，`#include "hello_cv_interfaces/msg/detection.hpp"` 就能用。

> `CX / CY 的单位是什么？`
> 检测器发出来是**像素**，跟踪器发出来是**米**。我在 `header.frame_id` 里区分：
> 前者是 `camera_link`，后者是 `map`。同一个消息类型在链路不同位置表达不同单位，
> 靠字段本身分不清，这是个隐患 —— 后文第 8 节会讲到怎么换算。

### 4.2 发布者和订阅者

```cpp
// 发布端（camera_node）
image_pub_ = create_publisher<sensor_msgs::msg::Image>("image_raw", make_qos());
// 订阅端（detector_node）
image_sub_ = create_subscription<sensor_msgs::msg::Image>(
    "image_raw", make_qos(),
    std::bind(&DetectorNode::on_image, this, std::placeholders::_1));
```

**话题名是唯一的对接口**。你在 launch 里写 `remappings=[('image_raw', 'camera/image_raw')]`，
两边的名字就都变成后者了 —— 不用改一行 C++。

### 4.3 看看它真的在跑

```bash
$ ros2 topic list -t
/camera/image_raw        [sensor_msgs/msg/Image]
/vision/detection        [hello_cv_interfaces/msg/Detection]
/vision/track            [hello_cv_interfaces/msg/Detection]
/vision/target_marker    [visualization_msgs/msg/Marker]
/tf                      [tf2_msgs/msg/TFMessage]
```

看频率、看内容：

```bash
$ ros2 topic hz /camera/image_raw
average rate: 30.007

$ ros2 topic echo /vision/detection --once --no-arr
header:
  stamp: {sec: 1792841212, nanosec: 906014267}
  frame_id: camera_link
found: true
cx: 175.87290954589844
cy: 51.80393981933594
area: 1015.0
confidence: 0.9950980544090271
```

![检测结果的真实输出](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/04-topic-echo.png)

`--no-arr` 这个参数救过我：图像那种带几万个数组元素的消息，不加它终端会被刷几百行。

## 5. QoS：ROS 2 最容易踩的坑

QoS = "这条通道的运输合同"。六个策略里，日常只需要记住三个：

| 策略 | 取值 | 意思 |
| --- | --- | --- |
| Reliability | `reliable` / `best_effort` | 丢了要不要重发 |
| Durability | `volatile` / `transient_local` | 后来的订阅者要不要补历史消息 |
| History | `keep_last(N)` / `keep_all` | 缓存多少条 |

![QoS 策略对照](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/figures/fig-qos.png)

**关键规则：两端不兼容时，ROS 2 不报错，只是数据静默地流不过去。**

- 发布者 `best_effort` + 订阅者 `reliable` → **连不上**，而且没有任何错误提示；
- 反向（发布 `reliable` + 订阅 `best_effort`）→ 能连上，降级工作。

我用一个参数统一控制两端的可靠性：

```cpp
rclcpp::QoS make_qos(const std::string & reliability)
{
  rclcpp::QoS qos(rclcpp::KeepLast(10));
  qos.durability_volatile();
  if (reliability == "best_effort") {
    qos.best_effort();
  } else {
    qos.reliable();          // 默认
  }
  return qos;
}
```

排查时用这条命令，看两端到底对不对得上：

```bash
$ ros2 topic info -v /vision/detection
Publisher count: 1
  Node name: detector_node
  QoS profile:
    Reliability: RELIABLE
    Durability: VOLATILE
Subscription count: 1
  Node name: tracker_node
  QoS profile:
    Reliability: RELIABLE
    Durability: VOLATILE
```

![两端 QoS 实测](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/03-topic-info-v.png)

> 截图里 `History (Depth)` 显示 `UNKNOWN`，一开始我以为是自己写错了，后来查明白：
> 这是底层 DDS 上报口径的问题，不影响实际收发。判断深度只能看代码或参数，
> 不能指望这条命令。**很容易被这种"看起来像报错"的输出带偏。**

## 6. 服务（Service）：要一个明确答复

话题是"喊一声就完"，服务是"打电话要答案"。定义分两半，中间用 `---` 隔开：

```
# hello_cv_interfaces/srv/SetTrackingMode.srv
string mode      # 请求：raw 或 ema
float64 alpha    # 平滑系数，0 < alpha <= 1
---
bool   success   # 响应：成不成
string message   # 失败时说清楚为什么
```

### 6.1 服务端

```cpp
mode_srv_ = create_service<hello_cv_interfaces::srv::SetTrackingMode>(
    "set_mode",
    [this](const std::shared_ptr<hello_cv_interfaces::srv::SetTrackingMode::Request> req,
           std::shared_ptr<hello_cv_interfaces::srv::SetTrackingMode::Response> res) {
      if (req->mode != "raw" && req->mode != "ema") {
        res->success = false;
        res->message = "未知模式 '" + req->mode + "'，只支持 raw / ema";  // 把收到的值写回去
        return;
      }
      // …切换逻辑…
      res->success = true;
      res->message = "已切换为 " + req->mode;
    });
```

**每个失败分支都要写一句人话**，而且要带上"收到的值"。否则调用方只看到 `success: false`，
还得回来翻你的代码。

### 6.2 客户端：一定要有超时

```cpp
if (!client_->wait_for_service(std::chrono::seconds(5))) {
  RCLCPP_ERROR(node->get_logger(), "服务不存在：set_mode 没起来");
  return 1;                                   // 退出码 1
}
auto future = client_->async_send_request(request);   // 异步发出
if (rclcpp::spin_until_future_complete(node, future, std::chrono::seconds(5)) !=
    rclcpp::FutureReturnCode::SUCCESS) {
  return 3;                                   // 退出码 3：超时
}
```

> **为什么不用同步调用？** 在单线程执行器里"同步等服务返回"会把执行器自己卡死，
> 服务端永远没机会处理你的请求 —— 自己把自己等死。

### 6.3 命令行里试一试

```bash
$ ros2 service list -t | grep set_mode
/set_mode [hello_cv_interfaces/srv/SetTrackingMode]

$ ros2 service call /set_mode hello_cv_interfaces/srv/SetTrackingMode "{mode: raw}"
response:
hello_cv_interfaces.srv.SetTrackingMode_Response(success=True, message='已切换为 raw（不平滑）')
```

![服务调用实测](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/05-service-call.png)

调用时**要写全类型名**（`hello_cv_interfaces/srv/SetTrackingMode`），只写服务名会报错。

## 7. 参数（Parameter）：不改代码改行为

参数 = 节点的"设置项"，可以在启动时给、运行时改。三步走：

```cpp
// ① 声明（必须带默认值和类型，否则 get 会抛异常）
alpha_ = declare_parameter<double>("alpha", 0.35);

// ② 读取
double a = get_parameter("alpha").as_double();

// ③ 运行时改
// ros2 param set /tracker_node alpha 0.5
```

三种写入入口，**优先级从高到低**：命令行 `-p` > 参数文件 YAML > 代码里的默认值。

### 7.1 参数文件长什么样

```yaml
# config/params.yaml
tracker_node:            # 节点名，注意不是包名
  ros__parameters:       # 固定写法，两个下划线
    alpha: 0.35
    meters_per_pixel: 0.005
```

三个常犯的错：

1. **少写 `ros__parameters`** → 参数完全不生效，也不报错；
2. **用了 Tab 缩进** → YAML 只认空格，会直接解析失败；
3. **节点带命名空间后还用原名** → `PushRosNamespace('robot1')` 之后，key 必须写 `/robot1/tracker_node`。

### 7.2 坑：`ros2 param set` 成功 ≠ 生效

我一开始只在构造函数里 `declare_parameter` 了一下，结果：

```bash
$ ros2 param set /tracker_node alpha 0.5
Set parameter successful        # 看起来成功了
$ ros2 param get /tracker_node alpha
Double value is: 0.5            # 读出来也是 0.5
```

但节点内部用的还是旧的 0.35 —— **参数值变了，代码里那个变量没变**。
要真的生效，必须注册回调：

```cpp
param_cb_ = add_on_set_parameters_callback(
    [this](const std::vector<rclcpp::Parameter> & params) {
      rcl_interfaces::msg::SetParametersResult result;
      result.successful = true;

      // 先把新值全算出来，全合法了再落地 —— 避免"改了一半"
      double new_alpha = alpha_;
      for (const auto & p : params) {
        if (p.get_name() == "alpha") {
          if (p.as_double() <= 0.0 || p.as_double() > 1.0) {
            result.successful = false;
            result.reason = "alpha 必须在 (0, 1]，收到 " + std::to_string(p.as_double());
            return result;
          }
          new_alpha = p.as_double();
        }
      }
      alpha_ = new_alpha;
      ema_.alpha = new_alpha;      // 别忘了同步给真正干活的成员
      return result;
    });
```

改完之后，非法值会被挡下来并给出中文原因：

```bash
$ ros2 param set /tracker_node alpha 1.5
Setting parameter failed: alpha 必须在 (0, 1]，收到 1.500000
```

![参数校验实测](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/05-param.png)

> 还有一个更隐蔽的坑：**不要在参数回调里 `set_parameter`**。回调执行时已经持有参数锁，
> 再往里改同一个参数有重入死锁的风险。我第一版就是这么写的，幸好查文档时看到了。

## 8. TF 与 RViz：让"像素"和"米"对上

TF 是 ROS 2 的**坐标变换系统**：它维护一棵树，每个节点是一条"从父坐标系到子坐标系"的变换。
我的树很简单：

```
map（世界坐标系）
├── camera_link   静态，z = 1.0 m（相机挂在天花板上）
└── target        动态，30 Hz 更新（检测到的目标）
```

### 8.1 广播：把"目标在哪"发出去

```cpp
geometry_msgs::msg::TransformStamped t;
t.header.stamp = msg->header.stamp;   // ← 用消息自己的时间，不是 now()
t.header.frame_id = "map";
t.child_frame_id  = "target";
t.transform.translation.x = x_m;      // 像素 → 米
t.transform.translation.y = y_m;
t.transform.translation.z = 0.0;
t.transform.rotation.w = 1.0;         // 不旋转；四元数四个都写 0 是非法值
tf_broadcaster_->sendTransform(t);
```

换算只有两行：`x_m = (cx - width/2) * meters_per_pixel`，y 轴要翻一下（图像 y 向下，地图 y 向上）。

> **为什么用 `msg->header.stamp` 而不是 `now()`？** 如果用 `now()`，这条变换描述的是"现在"，而数据
> 是几毫秒前采的。数据一慢，RViz 里球就会滞后甚至抖动。用消息自己的时间，TF 记录的就是那帧图像
> 拍摄时刻的位置 —— 这是做传感器融合的正确姿势。

### 8.2 查询：命令行走一遍

```bash
$ ros2 run tf2_ros tf2_echo map target
- Translation: [0.019, 0.349, 0.000]
- Rotation: in Quaternion [0.000, 0.000, 0.000, 1.000]
```

![tf2_echo 实测](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/06-tf2-echo.png)

这个 `0.349 m` 是可以预先算出来的：目标绕圈半径 70 像素 × 0.005 m/像素 = 0.35 m。
**能预测的数字对上了，才说明链路是对的**，这比"看起来差不多"可靠得多。

整棵树长什么样：

```bash
$ ros2 run tf2_tools view_frames
[INFO] Listening to tf data for 5.0 seconds...
[INFO] Generating graph in frames.pdf file...
```

![view_frames 实测](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/06-view-frames.png)

它的输出里能看到两条边：`camera_link` 的父是 `map`（rate 10000，静态），
`target` 的父是 `map`（rate 30.3，跟得上）。

### 8.3 RViz：把坐标变成眼睛能看的东西

RViz 不是"画图工具"，它是**TF 树的观察器**：你告诉它以哪个坐标系为准（Fixed Frame），
它就把所有能挂上去的东西画出来。

![RViz：Grid + TF 轴 + 红色球](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/06-rviz.png)

三个必须对的地方：

| 设置 | 值 | 不对会怎样 |
| --- | --- | --- |
| Fixed Frame | `map` | 写错成 `world`，整个画面空白并报 "Fixed Frame [world] does not exist" |
| TF → Marker Scale | 0.35 | 太大就把球埋了，太小看不见坐标轴 |
| Marker 的 Topic | `/vision/target_marker` | 名字差一个字母，球永远不出现（**我就踩了这个**） |

## 9. launch：一条命令起全套

四个节点、一个静态变换、一堆参数 —— 每次都手敲 `ros2 run` 是不可能的。launch 文件就是
"把这些写下来，一次执行"。

```python
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    threshold = DeclareLaunchArgument('threshold', default_value='180')
    params = PathJoinSubstitution([FindPackageShare('hello_cv_cpp'), 'config', 'params.yaml'])

    return LaunchDescription([
        threshold,
        Node(package='hello_cv_cpp', executable='camera_node', name='camera_node',
             parameters=[params],
             remappings=[('image_raw', 'camera/image_raw')]),
        Node(package='hello_cv_cpp', executable='detector_node', name='detector_node',
             parameters=[params, {'intensity_threshold':
                                  ParameterValue(LaunchConfiguration('threshold'), value_type=int)}]),
        Node(package='hello_cv_cpp', executable='tracker_node', name='tracker_node',
             parameters=[params]),
    ])
```

```bash
ros2 launch hello_cv_cpp full_pipeline.launch.py
```

![一条命令起全套](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/03-launch-full.png)

三个容易翻车的点：

1. **`parameters=[文件, 字典]` 是"后者覆盖前者"**。想临时改一个值，不用新建 YAML，往后追加一个字典就行。
2. **类型要显式指定**。`fps` 在代码里是 `double`，用 `value_type=int` 覆盖会抛
   `InvalidParameterTypeException` —— Python 里没有 `double`，只能用 `float`。
3. **`remappings` 里写的是"包内话题名 → 实际话题名"**，写反了不会报错，只是两边连不上。
   我的 Marker 就是这么丢的：tracker 发 `/target_marker`，RViz 等 `/vision/target_marker`。

调试 launch 的四个手段：`ros2 launch <包> <文件> --show-args`（看有哪些参数）、
`--print`（看展开后到底起了什么）、`output='screen'`（子进程日志直接打到终端）、
逐个节点单独 `ros2 run`（定位到底哪个起不来）。

## 10. 受管节点（LifecycleNode）：为什么需要它

普通节点一启动就干活。但真实系统里，"启动了"和"准备好了"不是一回事：
传感器还没就绪、地图还没加载，这时候开始发布是有害的。

受管节点把生命周期拆成四个状态：

![受管节点状态机](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/figures/fig-lifecycle.png)

```cpp
using CallbackReturn = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;

CallbackReturn on_configure(const rclcpp_lifecycle::State &) override
{
  status_pub_ = create_publisher<std_msgs::msg::String>("mission_status", 10);  // 只是建好
  timer_ = create_wall_timer(1s, [this]() { publish_status(); });
  return CallbackReturn::SUCCESS;
}

CallbackReturn on_activate(const rclcpp_lifecycle::State &) override
{
  status_pub_->on_activate();     // ← 不加这句，publish 会被静默丢弃
  return CallbackReturn::SUCCESS;
}
```

手动走一遍状态机：

```bash
$ ros2 lifecycle get /mission_node
unconfigured [1]
$ ros2 lifecycle set /mission_node configure
Transitioning successful
$ ros2 lifecycle get /mission_node
inactive [2]
$ ros2 lifecycle set /mission_node activate
Transitioning successful
```

![状态切换实测](https://cdn.jsdelivr.net/gh/hitxxxx/HelloCV@main/ros2/docs/screenshots/07-lifecycle.png)

截图里那几行 `[WARN] ... but the publisher is not activated` 就是证据：
在 `inactive` 状态下定时器还在跑，但发布被压住了 —— **这正是受管节点想要的效果**。

三个坑：

1. `on_configure` 不会自动 `on_activate`，必须显式切换；
2. **连续发两条切换命令会失败**（`Unknown transition requested`），因为状态切换是异步的，
   第二条发出时第一条还没完成。要等，或者用事件驱动；
3. `rclcpp_lifecycle::LifecycleNode` **不是** `rclcpp::Node` 的子类，
   所以 `rclcpp::spin(node)` 编译不过，要改成 `rclcpp::spin(node->get_node_base_interface())`。

## 11. 我踩过的 8 个坑

这张表是这篇笔记最值钱的部分 —— 每一条都是真机上撞出来的，不是想象出来的。

| # | 现象 | 原因 | 怎么修 |
| --- | --- | --- | --- |
| 1 | `fatal error: hello_cv_cpp/camera_node.hpp: 没有那个文件或目录` | `CMakeLists.txt` 只有链接了库的目标才继承 include 路径，其余目标找不到头文件 | 加一行 `include_directories(include)` |
| 2 | `'spin' is not a member of 'rclcpp'` | `rclcpp_lifecycle/lifecycle_node.hpp` 不带 `rclcpp::init/spin` | 该文件里补 `#include <rclcpp/rclcpp.hpp>` |
| 3 | `no matching function for call to 'spin(shared_ptr<LifecycleMissionNode>)'` | `LifecycleNode` 不是 `Node` 的子类 | `rclcpp::spin(node->get_node_base_interface())` |
| 4 | `ros2 pkg executables` 多出一行 `libhello_cv_vision.so` | 共享库和可执行文件装到了同一个目录 | 库改 `DESTINATION lib`，可执行文件仍装 `lib/<包名>/` |
| 5 | RViz 里红色球永远不出现 | tracker 发 `/target_marker`，RViz 配的是 `/vision/target_marker` | launch 里加 `marker_topic` 参数 + remap |
| 6 | `ros2 param set` 成功，但节点行为没变 | 只在构造函数 `declare_parameter`，没有 `add_on_set_parameters_callback` | 注册回调，校验后再写回成员变量 |
| 7 | 节点都起来了，但 `found` 永远是 `false`，还不报错 | 合成亮斑是高斯分布，过阈值后面积只有 185，小于 `min_area` 200 | 亮斑改成"平台 + 平滑过渡"，`expected_area` 从 2100 改为 1020 |
| 8 | 文档写着退出码 0/1/2/3，跟代码对不上 | 写文档时凭印象，没对着代码核 | 以代码为准改文档（1=服务不存在，2=服务端拒绝，3=超时） |

第 7 条最值得说。我一开始画的是高斯亮斑：

```cpp
value += 227.0 * std::exp(-(dx*dx + dy*dy) / (2.0 * radius_ * radius_ / 9.0));  // 旧版
```

看起来没问题，跑起来却"什么都没发生"。因为阈值是 180，能过阈值的地方只有亮斑中心半径 7.7 像素
的一小块，面积 ≈ 185 —— 比 `min_area` 还小，检测器直接把它当噪声丢掉了。
**而且它不报错**：流水线照常 30 Hz，只是每一帧都是 `found: false`。

修法是把亮斑改成"中间饱和、边缘平滑"：

```cpp
const double edge = std::max(1.0, radius_ * 0.5);          // 半个半径宽的过渡带
const double u = std::clamp((radius_ - d) / edge, 0.0, 1.0);
const double s = u * u * (3.0 - 2.0 * u);                  // smoothstep
value += 227.0 * s;
```

改完面积稳定在 1018 左右（阈值 180），`confidence` 0.995，和真机实测完全对得上。

**这件事教给我三件事**：

1. 参数之间是有契约的（`blob_radius` ↔ 阈值 ↔ `min_area` ↔ `expected_area`），代码不会替你检查；
2. 纯算法要能从节点里抽出来，否则没有 ROS 环境就没法复算 —— 我为此写了 `simulate_camera.py`，
   用 Python 把成像和检测逐行复现，一跑就露馅；
3. **"能编译"和"能工作"是两件事**。前 6 个坑是编译期和配置期的问题，第 7 个是逻辑问题，
   但它比编译错误危险得多，因为它不报错。

## 12. 完整复现步骤

```bash
# ① 装环境（Ubuntu 22.04）
sudo apt install ros-humble-desktop

# ② 拿代码
git clone https://github.com/hitxxxx/HelloCV.git
cd HelloCV/ros2/ros2_ws

# ③ 编译
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash

# ④ 自检（会检查依赖包、工作空间、节点数量）
bash ../scripts/check_env.sh

# ⑤ 起全套
ros2 launch hello_cv_cpp full_pipeline.launch.py

# ⑥ 另开终端，逐个验证
ros2 node list
ros2 topic hz /camera/image_raw
ros2 topic echo /vision/detection --once --no-arr
ros2 run tf2_ros tf2_echo map target
ros2 run tf2_tools view_frames
ros2 param set /tracker_node alpha 0.5
ros2 service call /set_mode hello_cv_interfaces/srv/SetTrackingMode "{mode: raw}"

# ⑦ 跑测试
colcon test --packages-select hello_cv_cpp && colcon test-result --verbose

# ⑧ 看画面
rviz2 -d install/hello_cv_cpp/share/hello_cv_cpp/rviz/hello_cv.rviz
```

## 13. 学完之后的几句实话

- **ROS 2 的难点不在语法，在"看不见"**。话题有没有通、QoS 对不对、TF 时间戳新不新，
  这些都没有编译错误提醒你，只能靠四条命令去看：`node info`、`topic info -v`、`topic hz`、`tf2_echo`。
- **先让数据流起来，再让它算得对**。我一开始就想把算法写漂亮，结果卡在"到底有没有数据"上。
  后来改成"先打印 found 和 area，确认有数了再谈精度"，效率高很多。
- **踩坑要立刻记**。第 11 节那张表是我边修边写的，如果等全部做完再回忆，细节全忘了 ——
  而细节恰恰是"自己做过"和"抄了一遍"的区别。
- **参数、服务、话题的界限是"语义"不是"技术"**。话题用于连续的数据流，服务用于一次性的动作，
  参数用于配置。我一开始用服务去改"平滑系数"，后来才想明白那属于配置，应该用参数。

---

*环境：Ubuntu 22.04.5 LTS + ROS 2 Humble · 编译 23.8 s · 测试 9 个用例全绿 · 流水线 30 Hz ·
完整代码与另外七篇分篇笔记见 [仓库](https://github.com/hitxxxx/HelloCV)。*
