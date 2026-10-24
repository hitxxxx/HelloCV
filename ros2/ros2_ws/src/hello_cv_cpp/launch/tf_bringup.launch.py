#!/usr/bin/env python3
"""TF 专题：把 /tf 这棵树搭起来，并验证 tf2 查询能走通。

TF 的本质是"一棵树 + 一条时间轴"：每个坐标系只有一个父节点，每一帧变换都带时间戳。
本文件搭出的树形如下：

    map
    ├── camera_link      ← static_transform_publisher（静态变换，只发一次）
    └── target           ← tracker_node 动态广播（每帧一次，带图像时间戳）

演示的 launch 技巧：
  * StaticTransformBroadcaster 用 tf2_ros 自带的 static_transform_publisher 节点，
    命令行参数写成 --x/--frame-id 形式（Humble 起支持，Jazzy 里是唯一写法）；
  * IncludeLaunchDescription 复用已有的 launch 文件，而不是复制粘贴；
  * TimerAction 错峰启动：相机先跑 2 秒，再起跟踪，日志更好读。

用法：
  ros2 launch hello_cv_cpp tf_bringup.launch.py
  ros2 run tf2_tools view_frames          # 生成 frames.pdf，看树形结构
  ros2 run tf2_ros tf2_echo map target    # 实时看 map->target
"""
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription, TimerAction)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg_share = FindPackageShare('hello_cv_cpp')

    # ---------- 复用"相机 + 检测"这一段，避免 launch 文件之间复制粘贴 ----------
    camera_detector = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([pkg_share, 'launch', 'camera_detector.launch.py'])),
        launch_arguments={
            'use_rviz': 'false',       # rviz 由本文件统一控制，别开两份
            'threshold': '170',
        }.items(),
    )

    # ---------- 静态变换：map -> camera_link ----------
    # 静态变换只发一次、永远有效，用来描述"传感器装在哪"这种不动的位姿。
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='map_to_camera_link',
        arguments=[
            '--x', '0.0', '--y', '0.0', '--z', '1.0',
            '--roll', '0.0', '--pitch', '0.0', '--yaw', '0.0',
            '--frame-id', 'map', '--child-frame-id', 'camera_link',
        ],
    )

    tracker = Node(
        package='hello_cv_cpp',
        executable='tracker_node',
        name='tracker_node',
        output='screen',
        remappings=[
            ('detection', 'vision/detection'),
            ('track', 'vision/track'),
        ],
    )

    tf_lookup = Node(
        package='hello_cv_cpp',
        executable='tf_lookup_node',
        name='tf_lookup_node',
        output='screen',
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', PathJoinSubstitution([pkg_share, 'rviz', 'hello_cv.rviz'])],
        condition=IfCondition(LaunchConfiguration('use_rviz')),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_rviz', default_value='true'),
        static_tf,
        camera_detector,
        # 错峰：等相机和检测先把话题建立起来，tracker 的日志里就不会刷一堆"还没数据"
        TimerAction(period=2.0, actions=[tracker, tf_lookup]),
        rviz,
    ])
