#!/usr/bin/env python3
"""受管节点（LifecycleNode）启动示例：让 launch 替我们驱动状态机。

LifecycleNode 的四个约定动作是 configure / activate / deactivate / cleanup，
它们**不会被自动调用**。想开机就跑，必须由外面把事件打进去，这就是本文件的全部内容：

  1. EmitEvent + ChangeState  —— "请把 mission_node 切到 inactive"
  2. OnStateTransition         —— "等它真的到了 inactive，再触发下一步"
  3. Transition.TRANSITION_*   —— 用常量而不是手写数字/字符串，避免打错

关键点：configure 之后节点是 inactive（话题/定时器都在但发布被压住），
必须 activate 才真正工作。这两步之间如果不加 OnStateTransition 直接连发两个
事件，会因为"节点还没到 inactive"而失败——事件是有先后依赖的。

用法：
  ros2 launch hello_cv_cpp lifecycle_bringup.launch.py            # 自动 configure+activate
  ros2 launch hello_cv_cpp lifecycle_bringup.launch.py autostart:=false   # 只 configure
  ros2 lifecycle get /mission_node
  ros2 lifecycle set /mission_node deactivate
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, RegisterEventHandler
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import LifecycleNode
from launch_ros.actions.lifecycle import matches_action
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from lifecycle_msgs.msg import Transition


def generate_launch_description() -> LaunchDescription:
    # LifecycleNode 是 Node 的子类，多出来的只是"状态机"这一层
    mission_node = LifecycleNode(
        package='hello_cv_cpp',
        executable='lifecycle_mission_node',
        name='mission_node',
        output='screen',
        # 节点对象要先建出来，下面的 ChangeState 才能通过 matches_action 认出它
    )

    # matches_action 生成一个"匹配器"：事件只投递给这个具体的节点对象
    matcher = matches_action(mission_node)

    configure = EmitEvent(event=ChangeState(
        lifecycle_node_matcher=matcher,
        transition_id=Transition.TRANSITION_CONFIGURE,
    ))

    # 只有当节点真的进入 inactive 之后，才继续发 activate
    activate = RegisterEventHandler(OnStateTransition(
        target_lifecycle_node=mission_node,
        goal_state='inactive',
        entities=[EmitEvent(event=ChangeState(
            lifecycle_node_matcher=matcher,
            transition_id=Transition.TRANSITION_ACTIVATE,
        ))],
        condition=IfCondition(LaunchConfiguration('autostart')),
    ))

    return LaunchDescription([
        DeclareLaunchArgument('autostart', default_value='true',
                              description='配置完成后是否自动进入 active'),
        mission_node,
        configure,
        activate,
    ])
