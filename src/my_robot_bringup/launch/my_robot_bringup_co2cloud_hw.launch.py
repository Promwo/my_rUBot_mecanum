"""Hardware bringup for the current rUBot plus Valeria's ENS160/eCO2 pipeline.

This launch deliberately reuses the repository's current my_robot_bringup_hw.launch.py
instead of copying Valeria's older motor/LiDAR/camera bringup.
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # Current robot bringup arguments
    robot_model = LaunchConfiguration('robot_model')
    mecanum_serial_port = LaunchConfiguration('mecanum_serial_port')
    rplidar_serial_port = LaunchConfiguration('rplidar_serial_port')
    rplidar_frame_id = LaunchConfiguration('rplidar_frame_id')
    camera_width = LaunchConfiguration('camera_width')
    camera_height = LaunchConfiguration('camera_height')
    usb_video_device = LaunchConfiguration('usb_video_device')
    camera_pixel_format = LaunchConfiguration('camera_pixel_format')
    camera_output_encoding = LaunchConfiguration('camera_output_encoding')

    # ENS160 arguments
    sensor_serial_port = LaunchConfiguration('sensor_serial_port')
    sensor_baud_rate = LaunchConfiguration('sensor_baud_rate')
    sensor_timer_period = LaunchConfiguration('sensor_timer_period')
    enable_csv_logger = LaunchConfiguration('enable_csv_logger')
    enable_eco2_cloud = LaunchConfiguration('enable_eco2_cloud')

    declarations = [
        DeclareLaunchArgument(
            'robot_model',
            default_value='rubot_arm/my_simple_robot.urdf',
            description='URDF/XACRO path inside my_robot_description/urdf',
        ),
        DeclareLaunchArgument(
            'mecanum_serial_port',
            default_value='/dev/ttyACM0',
            description='Serial port for the mecanum motor controller',
        ),
        DeclareLaunchArgument(
            'rplidar_serial_port',
            default_value='/dev/ttyUSB0',
            description='Serial port for RPLidar',
        ),
        DeclareLaunchArgument(
            'rplidar_frame_id',
            default_value='base_scan',
            description='Frame ID used by the RPLidar driver',
        ),
        DeclareLaunchArgument('camera_width', default_value='640'),
        DeclareLaunchArgument('camera_height', default_value='480'),
        DeclareLaunchArgument('usb_video_device', default_value='/dev/video0'),
        DeclareLaunchArgument('camera_pixel_format', default_value='YUYV'),
        DeclareLaunchArgument('camera_output_encoding', default_value='rgb8'),
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
            description='ENS160 serial polling period in seconds',
        ),
        DeclareLaunchArgument(
            'enable_csv_logger',
            default_value='true',
            description='Start the CSV logger node (logging itself starts via service)',
        ),
        DeclareLaunchArgument(
            'enable_eco2_cloud',
            default_value='true',
            description='Start the eCO2 PointCloud2 node',
        ),
    ]

    # Reuse the CURRENT repository hardware bringup.
    base_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('my_robot_bringup'),
                'launch',
                'my_robot_bringup_hw.launch.py',
            )
        ),
        launch_arguments={
            'robot_model': robot_model,
            'mecanum_serial_port': mecanum_serial_port,
            'rplidar_serial_port': rplidar_serial_port,
            'rplidar_frame_id': rplidar_frame_id,
            'camera_width': camera_width,
            'camera_height': camera_height,
            'usb_video_device': usb_video_device,
            'camera_pixel_format': camera_pixel_format,
            'camera_output_encoding': camera_output_encoding,
        }.items(),
    )

    sensor_node = Node(
        package='ens160_sensors',
        executable='ens160_sensors_hw_exec',
        name='sensor_pose_node_hw',
        output='screen',
        parameters=[{
            'serial_port': sensor_serial_port,
            'baud_rate': ParameterValue(sensor_baud_rate, value_type=int),
            'timer_period': ParameterValue(sensor_timer_period, value_type=float),
            'odom_topic': '/odom',
        }],
    )

    csv_logger_node = Node(
        package='ens160_sensors',
        executable='csv_logger_co2cloud_exec',
        name='csv_logger_co2cloud',
        output='screen',
        condition=IfCondition(enable_csv_logger),
    )

    eco2_cloud_node = Node(
        package='ens160_sensors',
        executable='eco2_cloud_exec',
        name='eco2_cloud',
        output='screen',
        condition=IfCondition(enable_eco2_cloud),
    )

    return LaunchDescription(
        declarations + [
            base_bringup,
            sensor_node,
            csv_logger_node,
            eco2_cloud_node,
        ]
    )
