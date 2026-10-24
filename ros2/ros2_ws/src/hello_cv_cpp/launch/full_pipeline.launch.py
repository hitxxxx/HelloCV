#!/usr/bin/env python3
"""完整流水线：camera → detector → tracker → tf_lookup，可选 rviz2。

这里演示 launch 的几件"正经事"：
  1. 用 YAML 参数文件统一管理参数（config/params.yaml），launch 里只做少量覆盖；
  2. 用 remap 把所有话题收进 camera/ 与 vision/ 两个"命名空间"，避免话题名满天飞；
  3. 用 condition 控制可选节点（rviz 需要 GUI，服务器上可以不启动）；
  4. 用 arguments 给节点传 --log-level，调试时不必改代码。

用法：
  ros2 launch hello_cv_cpp full_pipeline.launch.py
  ros2 launch hello_cv_cpp full_pipeline.launch.py use_rviz:=true fps:=15
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    pkg_share = FindPackageShare('hello_cv_cpp')
    params_file = PathJoinSubstitution([pkg_share, 'config', 'params.yaml'])
    rviz_config = PathJoinSubstitution([pkg_share, 'rviz', 'hello_cv.rviz'])

    return LaunchDescription([
        DeclareLaunchArgument('use_rviz', default_value='false',
                              description='是否打开 rviz2 观察 TF 与 Marker'),
        DeclareLaunchArgument('fps', default_value='30',
                              description='相机帧率（覆盖 YAML 里的默认值）'),
        DeclareLaunchArgument('log_level', default_value='info',
                              description='日志级别：debug / info / warn / error'),
        DeclareLaunchArgument('image_topic', default_value='camera/image_raw'),
        DeclareLaunchArgument('detection_topic', default_value='vision/detection'),
        DeclareLaunchArgument('track_topic', default_value='vision/track'),

        # ---------------- 相机：合成图像源 ----------------
        Node(
            package='hello_cv_cpp',
            executable='camera_node',
            name='camera_node',
            output='screen',
            parameters=[
                params_file,
                # value_type=float 不能写成 int：camera_node 里 fps 声明的是 double，
                # 用 int 覆盖会抛 InvalidParameterTypeException（类型必须严格一致）
                {'fps': ParameterValue(LaunchConfiguration('fps'), value_type=float)},
            ],
            remappings=[('image_raw', LaunchConfiguration('image_topic'))],
            arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')],
        ),

        # ---------------- 检测：亮斑质心 ----------------
        Node(
            package='hello_cv_cpp',
            executable='detector_node',
            name='detector_node',
            output='screen',
            parameters=[params_file],
            remappings=[
                ('image_raw', LaunchConfiguration('image_topic')),
                ('detection', LaunchConfiguration('detection_topic')),
            ],
            arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')],
        ),

        # ---------------- 跟踪：EMA + TF + Marker ----------------
        Node(
            package='hello_cv_cpp',
            executable='tracker_node',
            name='tracker_node',
            output='screen',
            parameters=[params_file],
            remappings=[
                ('detection', LaunchConfiguration('detection_topic')),
                ('track', LaunchConfiguration('track_topic')),
            ],
            arguments=['--ros-args', '--log-level', LaunchConfiguration('log_level')],
        ),

        # ---------------- TF 查询：验证 map->target 真的在发 ----------------
        Node(
            package='hello_cv_cpp',
            executable='tf_lookup_node',
            name='tf_lookup_node',
            output='screen',
            parameters=[params_file],
        ),

        # ---------------- 可视化（可选） ----------------
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            output='screen',
            arguments=['-d', rviz_config],
            condition=IfCondition(LaunchConfiguration('use_rviz')),
        ),
    ])
