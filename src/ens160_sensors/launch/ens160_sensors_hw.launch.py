"""Minimal hardware launch for testing only the ENS160 acquisition node."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    sensor_serial_port = LaunchConfiguration('sensor_serial_port')
    sensor_baud_rate = LaunchConfiguration('sensor_baud_rate')
    sensor_timer_period = LaunchConfiguration('sensor_timer_period')
    odom_topic = LaunchConfiguration('odom_topic')

    return LaunchDescription([
        DeclareLaunchArgument(
            'sensor_serial_port',
            default_value='/dev/ttyACM1',
            description='Serial port for the Arduino Nano 33 IoT / ENS160 array',
        ),
        DeclareLaunchArgument(
            'sensor_baud_rate',
            default_value='9600',
            description='Serial baud rate for the ENS160 controller',
        ),
        DeclareLaunchArgument(
            'sensor_timer_period',
            default_value='0.1',
            description='Serial polling period in seconds',
        ),
        DeclareLaunchArgument(
            'odom_topic',
            default_value='/odom',
            description='Odometry topic used to fill pose fields in SensorData',
        ),
        Node(
            package='ens160_sensors',
            executable='ens160_sensors_hw_exec',
            name='sensor_pose_node_hw',
            output='screen',
            parameters=[{
                'serial_port': sensor_serial_port,
                'baud_rate': ParameterValue(sensor_baud_rate, value_type=int),
                'timer_period': ParameterValue(sensor_timer_period, value_type=float),
                'odom_topic': odom_topic,
            }],
        ),
    ])
