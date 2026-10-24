# 07 launch 文件：把"一串命令"写成"一份声明"

> ⚠️ 环境说明同 [01](01-工作空间与包结构.md)：launch 文件本机可读、语法按 Humble 文档核对，
> 但 `ros2 launch` 没有实跑，截图留占位。

## 0. 一句话总结

launch 文件不是"shell 脚本的替代品"，它是**一份声明式的进程编排描述**：声明参数、声明节点、
声明节点之间的 remap、声明"什么时候启动什么"（条件、延时、事件）。
它能做的事比 `ros2 run` 多三件：**多节点**、**参数注入**、**启动顺序依赖**。

## 1. 五个 launch 文件的定位

| 文件 | 节点 | 想演示的能力 |
| --- | --- | --- |
| `camera_detector.launch.py` | 2 | 最小可用：DeclareLaunchArgument + remap + 参数覆盖 + 条件启动 |
| `full_pipeline.launch.py` | 4 + 可选 rviz | 参数文件 + 多话题 remap + `--log-level` |
| `param_demo.launch.py` | 2（不同命名空间） | `PushRosNamespace` + 参数字典合并 |
| `lifecycle_bringup.launch.py` | 1 | 事件驱动：`OnStateTransition` 串起 configure → activate |
| `tf_bringup.launch.py` | 4 + static_tf | `IncludeLaunchDescription` + `TimerAction` 错峰启动 |

**为什么拆成五个而不是一个大文件？** 因为"我到底想演示哪一个概念"要在文件名上看得出来。
一个大 launch 文件塞 12 个节点，读的人只会关掉。

## 2. 基础：`DeclareLaunchArgument` + `LaunchConfiguration`

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

## 3. 参数注入：`parameters=` 的三种写法

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

### 3.1 `ParameterValue(..., value_type=...)` 是必须的

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

### 3.2 YAML 与命名空间的坑

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

## 4. remap：话题名的唯一真相

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

## 5. 事件驱动：受管节点的启动顺序

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

### 5.1 为什么不能"连发两个事件"

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

### 5.2 `matches_action` 是什么

`ChangeState` 需要一个"给谁发"的谓词。`matches_action(mission_node)` 返回一个
`Callable[[LifecycleNode], bool]`，判断"这个 LifecycleNode 是不是我声明的那一个实例"。
早期教程里用的是 `lifecycle_node_matcher=lambda node: node.name == 'mission_node'`——
那种写法在有两个同名节点时会误伤，`matches_action` 更准。

## 6. 错峰启动与嵌套

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

## 7. 调试 launch 的四个手段

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

## 8. 验收清单

- [x] 五个 launch 文件，各自有明确的演示目标
- [x] `DeclareLaunchArgument` 全部带 `description`
- [x] `fps` 覆盖用 `ParameterValue(..., value_type=float)`
- [x] `PushRosNamespace` + 参数字典合并（不依赖 YAML 全限定名）
- [x] 受管节点用 `OnStateTransition` 串联 configure → activate
- [x] `IncludeLaunchDescription` + `TimerAction`（并注明 TimerAction 是缓解措施）
- [ ] 真机 `ros2 launch` 全流程（**待补**）
