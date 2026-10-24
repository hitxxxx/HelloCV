#!/usr/bin/env python3
"""最小启动示例：只起 camera + detector 两个节点。

这个文件刻意写得"啰嗦"，把每个概念都摊开：
  * DeclareLaunchArgument —— 声明启动参数（就是 launch 文件自己的"命令行参数"）
  * LaunchConfiguration   —— 读取启动参数
  * Node(...)             —— 一个节点 = 一个动作
  * remappings            —— 不改 C++ 代码，只在这里换话题名
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        # ---------- 1) 声明启动参数 ----------
        DeclareLaunchArgument(
            'threshold', default_value='180',
            description='检测阈值：灰度 > 阈值的像素才算候选目标'),
        DeclareLaunchArgument(
            'image_topic', default_value='camera/image_raw',
            description='相机图像话题（remap 的目标名）'),
        DeclareLaunchArgument(
            'detection_topic', default_value='vision/detection',
            description='检测结果话题'),
        DeclareLaunchArgument(
            'use_rviz', default_value='false',
            description='是否顺便打开 rviz2'),

        # ---------- 2) 节点 ----------
        Node(
            package='hello_cv_cpp',
            executable='camera_node',
            name='camera_node',
            output='screen',
            # 注意：这里是"话题重映射"（remap），不是改参数。
            # 节点内部写死了 "image_raw"，这里把它改名成 camera/image_raw，
            # 好处是命名空间更规范，而 C++ 代码一行都不用动。
            remappings=[('image_raw', LaunchConfiguration('image_topic'))],
        ),
        Node(
            package='hello_cv_cpp',
            executable='detector_node',
            name='detector_node',
            output='screen',
            parameters=[{
                'intensity_threshold':
                    ParameterValue(LaunchConfiguration('threshold'), value_type=int),
            }],
            remappings=[
                ('image_raw', LaunchConfiguration('image_topic')),
                ('detection', LaunchConfiguration('detection_topic')),
            ],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            condition=IfCondition(LaunchConfiguration('use_rviz')),
        ),
    ])
