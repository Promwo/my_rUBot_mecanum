#!/usr/bin/env python3
"""Read the ENS160 array from a serial port and publish SensorData messages."""

import serial
import transforms3d.euler as t3d_euler

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Odometry

from ens160_interfaces.msg import SensorData


class SensorPoseNode(Node):
    def __init__(self):
        super().__init__('sensor_pose_node_hw')

        # Robot pose from odometry (kept in the message for compatibility with
        # Valeria's pipeline; the map-frame logger/cloud use TF separately).
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_theta = 0.0

        # Runtime-configurable hardware parameters.  Valeria's original node
        # hard-coded /dev/ttyACM1, so launch arguments could not actually
        # change the sensor port.
        self.declare_parameter('serial_port', '/dev/ttyACM1')
        self.declare_parameter('baud_rate', 9600)
        self.declare_parameter('timer_period', 0.1)
        self.declare_parameter('odom_topic', '/odom')

        serial_port_name = self.get_parameter('serial_port').value
        serial_baud = int(self.get_parameter('baud_rate').value)
        timer_period = float(self.get_parameter('timer_period').value)
        odom_topic = self.get_parameter('odom_topic').value

        if timer_period <= 0.0:
            raise ValueError('timer_period must be greater than 0 seconds')

        self.publisher_ = self.create_publisher(SensorData, 'ens160_data', 10)
        self.create_subscription(Odometry, odom_topic, self.odom_callback, 10)

        self.ser = None
        try:
            self.ser = serial.Serial(serial_port_name, serial_baud, timeout=1)
            self.get_logger().info(
                f'Connected to ENS160 controller on {serial_port_name} at {serial_baud} baud'
            )
        except (serial.SerialException, OSError) as exc:
            self.get_logger().error(
                f'Cannot open ENS160 serial port {serial_port_name}: {exc}'
            )
            raise

        self.create_timer(timer_period, self.read_sensor)
        self.get_logger().info(
            f'ENS160 reader ready: topic=/ens160_data, odom={odom_topic}, period={timer_period:.3f}s'
        )

    def odom_callback(self, msg: Odometry):
        self.robot_x = msg.pose.pose.position.x
        self.robot_y = msg.pose.pose.position.y

        q = msg.pose.pose.orientation
        quat_array = [q.w, q.x, q.y, q.z]
        try:
            _, _, yaw = t3d_euler.quat2euler(quat_array, axes='sxyz')
            self.robot_theta = yaw
        except (ValueError, ZeroDivisionError):
            self.robot_theta = 0.0

    @staticmethod
    def parse_sensor_line(decoded: str):
        """Parse: timestamp,CHn,eCO2=...,TVOC=...,AQI=...,R0=...,R1=...,R2=...,R3=..."""
        parts = [part.strip() for part in decoded.split(',')]
        if len(parts) < 9:
            raise ValueError(f'expected at least 9 comma-separated fields, got {len(parts)}')

        channel_field = parts[1]
        if not channel_field.upper().startswith('CH'):
            raise ValueError(f'invalid channel field: {channel_field!r}')

        channel = int(channel_field[2:])
        readings = []
        for field in parts[2:9]:
            if '=' not in field:
                raise ValueError(f'invalid sensor field: {field!r}')
            _, value = field.split('=', 1)
            readings.append(float(value))

        return channel, readings

    def read_sensor(self):
        if self.ser is None or not self.ser.is_open:
            return

        try:
            if self.ser.in_waiting <= 0:
                return
            raw_line = self.ser.readline()
        except (serial.SerialException, OSError) as exc:
            self.get_logger().error(f'Error reading ENS160 serial port: {exc}')
            return

        if not raw_line:
            return

        decoded = raw_line.decode('utf-8', errors='ignore').strip()
        if not decoded:
            return

        try:
            channel, readings = self.parse_sensor_line(decoded)
        except (ValueError, IndexError) as exc:
            self.get_logger().warning(f'Ignoring malformed sensor line: {decoded!r} ({exc})')
            return

        msg = SensorData()
        msg.pose_x = self.robot_x
        msg.pose_y = self.robot_y
        msg.pose_theta = self.robot_theta
        msg.channels = [channel]
        msg.sensor_readings = readings
        self.publisher_.publish(msg)
        self.get_logger().debug(f'Published CH{channel}: {readings}')

    def close_serial(self):
        if self.ser is not None and self.ser.is_open:
            self.ser.close()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = SensorPoseNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.close_serial()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
