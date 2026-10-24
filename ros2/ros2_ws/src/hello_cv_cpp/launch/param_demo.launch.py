#!/usr/bin/env python3
"""参数专题演示：同一条 launch 命令起两个实例，参数完全靠 launch 注入。

想讲清楚的三个点：
  1. parameters=[字典A, 字典B] —— **列表里后面的覆盖前面的**。
     所以"团队默认值写在前、现场要改的写在后"，优先级关系一眼可见。
     （这里不用 YAML 文件，是因为节点带命名空间后，YAML 的 key 必须写成
       /robot1/param_demo 这种全限定名才会命中——初学者最容易踩的坑之一。）
  2. PushRosNamespace —— 同一个节点起两份，靠命名空间隔离，
     话题/服务名自动变成 /robot1/param_demo/...，不用手改代码。
  3. 参数类型必须对得上：ParameterValue(..., value_type=int) 用来把
     launch 的字符串参数强转成正确的类型，否则 /param_demo 上会变成字符串。

用法：
  ros2 launch hello_cv_cpp param_demo.launch.py
  ros2 param get /robot1/param_demo threshold
  ros2 param set /robot1/param_demo threshold 0.9
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.parameter_descriptions import ParameterValue


def make_demo_node(threshold: str) -> Node:
    """构造一个参数演示节点：先给默认值，再用 launch 参数覆盖 threshold。"""
    return Node(
        package='hello_cv_cpp',
        executable='param_demo_node',
        name='param_demo',
        output='screen',
        parameters=[
            # ① 默认值（相当于 YAML 里的"团队约定"）
            {
                'counter': 0,
                'threshold': 0.5,
                'mode': 'demo',
                'verbose': False,
                'frame_id': 'map',
            },
            # ② 现场覆盖（后写的赢）
            {
                'threshold': ParameterValue(threshold, value_type=float),
                'mode': 'launch_override',
                'verbose': ParameterValue(LaunchConfiguration('verbose'), value_type=bool),
            },
        ],
    )


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument('verbose', default_value='true',
                              description='是否打印每次参数变更'),
        DeclareLaunchArgument('robot1_threshold', default_value='0.5'),
        DeclareLaunchArgument('robot2_threshold', default_value='0.9'),

        # 两个实例放在不同命名空间下：参数、话题、服务互不打架
        GroupAction([
            PushRosNamespace('robot1'),
            make_demo_node(LaunchConfiguration('robot1_threshold')),
        ]),
        GroupAction([
            PushRosNamespace('robot2'),
            make_demo_node(LaunchConfiguration('robot2_threshold')),
        ]),
    ])
