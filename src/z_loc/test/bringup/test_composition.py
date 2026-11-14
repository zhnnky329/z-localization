"""验证组合启动入口对子节点参数的声明与传递。"""

import importlib.util
from pathlib import Path

from launch import LaunchContext
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.utilities import normalize_to_list_of_substitutions, perform_substitutions
import pytest

_spec = importlib.util.spec_from_file_location(
    'bringup_launch', Path(__file__).resolve().parents[2] / 'launch/bringup.launch.py')
bringup = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bringup)


@pytest.mark.parametrize('mode', ['mapping', 'localization'])
def test_overrides_reach_correct_package_without_starting_processes(mode):
    description = bringup.generate_launch_description()
    context = LaunchContext()
    overrides = {
        'frontend_config': '/tmp/frontend.yaml', 'backend_config': '/tmp/backend.yaml',
        'input_type': 'pointcloud2', 'lidar_topic': '/test/lidar', 'imu_topic': '/test/imu',
        'imu_acceleration_scale': '1.0', 'use_sim_time': 'true', 'wait_for_start': 'true',
        'reset_mode': 'cold', 'mode': mode, 'prior_map': '/tmp/map', 'rviz': 'false',
        'coordinated_reset': 'false',
    }
    context.launch_configurations.update(overrides)
    for action in description.entities:
        if isinstance(action, DeclareLaunchArgument):
            if action.name == 'coordinated_reset':
                assert perform_substitutions(context, action.default_value) == 'true'
            action.execute(context)
    children = [action for action in description.entities
                if isinstance(action, IncludeLaunchDescription)
                and (action.condition is None or action.condition.evaluate(context))]
    assert len(children) == 2
    frontend = {name: perform_substitutions(context, normalize_to_list_of_substitutions(value))
                for name, value in children[0].launch_arguments}
    backend = {name: perform_substitutions(context, normalize_to_list_of_substitutions(value))
               for name, value in children[1].launch_arguments}
    assert frontend == {
        'config': overrides['frontend_config'],
        **{key: overrides[key] for key in ('input_type', 'lidar_topic', 'imu_topic',
                                         'imu_acceleration_scale', 'use_sim_time',
                                         'wait_for_start', 'reset_mode', 'coordinated_reset')},
    }
    assert backend == {'config_file': overrides['backend_config'],
                       **{key: overrides[key]
                          for key in ('use_sim_time', 'mode', 'prior_map', 'rviz')}}
    # 解析子 launch 的声明，保证组合入口传递的参数仍被目标包接受。
    for child, passed in zip(children, (frontend, backend)):
        child_description = child.launch_description_source.get_launch_description(context)
        declared = {argument.name for argument in child_description.get_launch_arguments()}
        assert set(passed) <= declared


def test_bringup_only_starts_localization_packages():
    description = bringup.generate_launch_description()
    context = LaunchContext()
    arguments = {action.name for action in description.entities
                 if isinstance(action, DeclareLaunchArgument)}
    assert 'driver' not in arguments
    for action in description.entities:
        if isinstance(action, DeclareLaunchArgument):
            action.execute(context)

    children = [action for action in description.entities
                if isinstance(action, IncludeLaunchDescription)]
    assert len(children) == 2
    for child in children:
        child.launch_description_source.get_launch_description(context)
        location = child.launch_description_source.location
        assert '/share/z_lio/' in location or '/share/z_loc/' in location
