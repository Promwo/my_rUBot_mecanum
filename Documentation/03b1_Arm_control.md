# **Arm control**

This document describes the basic procedure for testing the 6-DOF robot arm controlled by SG90 servos and an Arduino Nano ESP32 within the `my_rUBot_mecanum` repository.

The main package is:

```text
src/Robot_drivers/my_arm_driver
```

The objective is to verify the complete control pipeline:

```text
ROS 2 command or test nodes
        ↓
trajectory_msgs/JointTrajectory
        ↓
/arm_controller/joint_trajectory
        ↓
serial_trajectory_bridge_node.py
        ↓
Arduino Nano ESP32
        ↓
SG90 Servos
```

---

# 1. General Architecture

The robot arm does not use a standard `joint_trajectory_controller` from `ros2_control`. Instead, it relies on a custom Python driver that listens for ROS 2 trajectories and converts them into serial commands sent to the Arduino.

The main ROS interface is:

```text
Topic:
  /arm_controller/joint_trajectory

Message:
  trajectory_msgs/msg/JointTrajectory
```

The recommended node for controlling the real hardware is:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

This node receives `JointTrajectory` messages, converts each joint position from radians to servo angles in degrees, and sends a single line of text to the Arduino using the following format:

```text
servo1,servo2,servo3,servo4,servo5,servo6
```

For example:

```text
90,120,60,90,90,90
```

---

# 2. Available ROS 2 Nodes in `my_arm_driver`

The package provides the following ROS 2 executables:

| Executable | Python File | Main Function |
|---|---|---|
| `serial_bridge_node` | `serial_bridge_node.py` | Simple serial driver. Receives a trajectory and sends only the final trajectory point to the robot. |
| `serial_trajectory_bridge_node` | `serial_trajectory_bridge_node.py` | Complete serial driver. Executes all trajectory points according to their `time_from_start` values and publishes `/joint_states`. |
| `send_joint_target_node` | `send_joint_target_node.py` | Sends a single target joint configuration. |
| `send_joint_trajectory_node` | `send_joint_trajectory_node.py` | Sends a manually defined multi-point trajectory. |
| `send_smooth_joint_target_node` | `send_smooth_joint_target_node.py` | Generates an interpolated trajectory between two configurations. This is the recommended node for smooth arm motions. |

---

# 3. Connecting to the Arduino

Before launching the driver, identify the serial port assigned to the Arduino:

```bash
ls /dev/ttyUSB*
ls /dev/ttyACM*
```

Usually the device connectd for mecanum arm is:

```text
/dev/ttyUSB1
```

If the serial port is not accessible, add your user to the `dialout` group:

```bash
sudo usermod -a -G dialout $USER
```

Afterward, log out and log back in for the changes to take effect.

---

# 4. Main Driver: `serial_trajectory_bridge_node`

## 4.1 Purpose

This is the recommended node for controlling the physical robot arm.

It subscribes to trajectories published on:

```text
/arm_controller/joint_trajectory
```

and sends every trajectory point to the Arduino.

Unlike `serial_bridge_node`, it does not simply execute the final trajectory point. Instead, it processes the complete trajectory while respecting the `time_from_start` specified for each point.

The node also publishes the estimated joint positions on:

```text
/joint_states
```

This allows the arm to be visualized in RViz2 and provides a ROS-compatible joint state interface for other nodes.

---

## 4.2 Main Parameters

| Parameter | Default Value | Description |
|---|---:|---|
| `serial_port` | `/dev/ttyUSB0` | Arduino serial port. |
| `baudrate` | `115200` | Serial communication speed. |
| `servo_center_deg` | `[90,90,90,90,90,90]` | Servo angle corresponding to a joint position of `0 rad`. |
| `servo_sign` | `[1,1,1,1,1,1]` | Conversion sign for each joint. Used to invert servo direction if required. |
| `servo_min_deg` | `[0,0,0,0,0,0]` | Minimum servo angle. |
| `servo_max_deg` | `[180,180,180,180,180,180]` | Maximum servo angle. |
| `joint_names` | `arm_joint1` ... `arm_joint6` | Robot arm joint names. |
| `publish_joint_states` | `True` | Enables publishing of `/joint_states`. |
| `joint_state_rate` | `20.0` | Publishing frequency of `/joint_states`. |

---

## 4.3 Basic Usage

Launch the driver:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Specify a serial port:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p serial_port:=/dev/ttyUSB1 \
  -p baudrate:=115200
```

Invert one or more servos:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p serial_port:=/dev/ttyUSB1 \
  -p servo_sign:="[1,-1,1,1,1,1]"
```

Use custom servo limits:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p servo_min_deg:="[10,10,10,10,10,10]" \
  -p servo_max_deg:="[170,170,170,170,170,170]"
```

---

# 5. Simple Driver: `serial_bridge_node`

## 5.1 Purpose

This node is the first and simplest implementation of the serial bridge.

It subscribes to a `JointTrajectory` message but only processes the last trajectory point:

```python
point = msg.points[-1]
```

Consequently, it is useful for quick position tests but is not suitable for smooth trajectory execution.

---

## 5.2 Usage

```bash
ros2 run my_arm_driver serial_bridge_node
```

Specify a serial port:

```bash
ros2 run my_arm_driver serial_bridge_node --ros-args \
  -p serial_port:=/dev/ttyUSB1 \
  -p baudrate:=115200
```

---

## 5.3 When to Use It

Use this node only for:

- Verifying serial communication.
- Checking that the Arduino correctly receives servo angles.
- Performing simple tests involving a single target position.

For normal operation of the robot arm, it is recommended to use:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

---
## 6. `send_joint_target_node`

### 6.1 Purpose

This node publishes a single target configuration for the robot arm by generating a `JointTrajectory` message containing one `JointTrajectoryPoint`.

It is useful for moving the arm directly to a desired joint configuration.

---

### 6.2 Parameters

| Parameter           |                      Default Value | Description                                  |
| ------------------- | ---------------------------------: | -------------------------------------------- |
| `topic_name`        | `/arm_controller/joint_trajectory` | Topic where the trajectory is published.     |
| `joint_names`       |              `joint1` ... `joint6` | Joint names.                                 |
| `target_joints_deg` |                    `[0,0,0,0,0,0]` | Target joint configuration in degrees.       |
| `duration`          |                              `2.0` | Time assigned to the final trajectory point. |

> **Note:** By default, this node uses the joint names `joint1`, `joint2`, etc. If your robot model uses `arm_joint1`, `arm_joint2`, etc., it is recommended to override the `joint_names` parameter.

---

### 6.3 Example Using the Correct Joint Names

Terminal 1:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Terminal 2:

```bash
ros2 run my_arm_driver send_joint_target_node --ros-args \
  -p joint_names:="[arm_joint1,arm_joint2,arm_joint3,arm_joint4,arm_joint5,arm_joint6]" \
  -p target_joints_deg:="[0.0,30.0,-30.0,0.0,0.0,0.0]" \
  -p duration:=2.0
```

Expected behaviour:

* A trajectory containing a single point is published.
* The driver converts joint angles from radians to servo angles.
* The robot arm moves directly to the target configuration.

This movement may be abrupt if the angular displacement is large.

---

# 7. `send_joint_trajectory_node`

## 7.1 Purpose

This node publishes a manually defined trajectory composed of multiple waypoints.

Each waypoint is specified in degrees through the parameter:

```text
trajectory_points_deg
```

The execution times are defined using:

```text
point_times_sec
```

The times are absolute with respect to the beginning of the trajectory and are assigned to each point as `time_from_start`.

---

## 7.2 Parameters

| Parameter               | Default Value                      | Description                                |
| ----------------------- | ---------------------------------- | ------------------------------------------ |
| `topic_name`            | `/arm_controller/joint_trajectory` | Output topic.                              |
| `joint_names`           | `joint1` ... `joint6`              | Joint names.                               |
| `trajectory_points_deg` | List of waypoints                  | Trajectory waypoints expressed in degrees. |
| `point_times_sec`       | `[0,1,2,3,4]`                      | Absolute execution time for each waypoint. |

---

## 7.3 Example

Terminal 1:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Terminal 2:

```bash
ros2 run my_arm_driver send_joint_trajectory_node --ros-args \
  -p joint_names:="[arm_joint1,arm_joint2,arm_joint3,arm_joint4,arm_joint5,arm_joint6]" \
  -p trajectory_points_deg:="[
    [0.0,0.0,0.0,0.0,0.0,0.0],
    [0.0,20.0,0.0,0.0,0.0,0.0],
    [0.0,20.0,-20.0,0.0,0.0,0.0],
    [0.0,0.0,0.0,0.0,0.0,0.0]
  ]" \
  -p point_times_sec:="[0.0,2.0,4.0,6.0]"
```

Expected behaviour:

* The robot arm moves through the specified waypoints.
* Each waypoint is executed at the programmed time.
* Motion is smoother than sending a single target position, although the smoothness depends on the number of trajectory points.

---

# 8. Recommended Node for Smooth Motion: `send_smooth_joint_target_node`

## 8.1 Purpose

This node automatically generates an interpolated trajectory between an initial configuration and a target configuration.

It is the recommended node for controlling SG90 servos because these hobby servos do not provide direct speed control through ROS.

Instead, smooth motion is achieved by dividing the overall movement into many small increments.

The node generates:

```text
steps + 1
```

trajectory points.

For example:

```text
steps = 50  →  51 trajectory points
steps = 100 → 101 trajectory points
```

All joints are interpolated using the same number of steps so that they start and finish simultaneously.

---

## 8.2 Parameters

| Parameter           |                      Default Value | Description                            |
| ------------------- | ---------------------------------: | -------------------------------------- |
| `topic_name`        | `/arm_controller/joint_trajectory` | Output topic.                          |
| `joint_names`       |      `arm_joint1` ... `arm_joint6` | Robot arm joint names.                 |
| `start_joints_deg`  |                    `[0,0,0,0,0,0]` | Initial joint configuration (degrees). |
| `target_joints_deg` |                 `[0,30,-30,0,0,0]` | Target joint configuration (degrees).  |
| `duration`          |                              `5.0` | Total execution time.                  |
| `steps`             |                               `50` | Number of interpolation steps.         |

---

## 8.3 Example: Moving a Single Joint

Terminal 1:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Terminal 2:

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[0.0,30.0,0.0,0.0,0.0,0.0]" \
  -p duration:=5.0 \
  -p steps:=50
```

Expected behaviour:

* Only `arm_joint2` moves.
* The movement lasts approximately five seconds.
* Motion is significantly smoother than sending a single target position.

---

## 8.4 Example: Moving All Joints

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[30.0,45.0,-30.0,20.0,-15.0,10.0]" \
  -p duration:=6.0 \
  -p steps:=60
```

Expected behaviour:

* All joints move simultaneously.
* The complete movement lasts approximately six seconds.
* Motion should be smooth, continuous and coordinated.

---

## 8.5 Example: Slower Motion

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[30.0,45.0,-30.0,20.0,-15.0,10.0]" \
  -p duration:=10.0 \
  -p steps:=100
```

Expected behaviour:

* The arm reaches the same target configuration.
* Motion is slower.
* Additional intermediate trajectory points produce smoother movement.

---

## 8.6 Returning to the Home Position

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[30.0,45.0,-30.0,20.0,-15.0,10.0]" \
  -p target_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p duration:=6.0 \
  -p steps:=60
```

---

# 9. Publishing Trajectories Manually with `ros2 topic pub`

Trajectories can also be published directly from the terminal without using any of the provided test nodes.

## 9.1 Publishing a Single Target Position

```bash
ros2 topic pub /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "
joint_names:
- arm_joint1
- arm_joint2
- arm_joint3
- arm_joint4
- arm_joint5
- arm_joint6
points:
- positions: [0.0, 0.5, -0.5, 0.0, 0.0, 0.0]
  time_from_start:
    sec: 2
    nanosec: 0
" --once
```

The values in `positions` are expressed in **radians**.

---

## 9.2 Publishing a Two-Point Trajectory

```bash
ros2 topic pub /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "
joint_names:
- arm_joint1
- arm_joint2
- arm_joint3
- arm_joint4
- arm_joint5
- arm_joint6
points:
- positions: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  time_from_start:
    sec: 0
    nanosec: 0
- positions: [0.0, 0.5, -0.5, 0.0, 0.0, 0.0]
  time_from_start:
    sec: 4
    nanosec: 0
" --once
```

---

# 10. Monitoring

## 10.1 Listing the Available Topics

```bash
ros2 topic list
```

You should see at least:

```text
/arm_controller/joint_trajectory
/joint_states
```

---

## 10.2 Displaying the Published Trajectory

```bash
ros2 topic echo /arm_controller/joint_trajectory
```

---

## 10.3 Displaying the Joint States

```bash
ros2 topic echo /joint_states
```

---

## 10.4 Checking the Publishing Frequency

```bash
ros2 topic hz /joint_states
```

If `joint_state_rate` is configured to `20.0`, the expected publishing frequency is approximately:

```text
20 Hz
```

---

# 11. Visualizing the Robot Arm in RViz2

If the robot is launched together with `robot_state_publisher`, and the URDF/Xacro model defines the following joints:

```text
arm_joint1
arm_joint2
arm_joint3
arm_joint4
arm_joint5
arm_joint6
```

the `/joint_states` topic published by `serial_trajectory_bridge_node` allows RViz2 to continuously update the arm configuration.

Recommended procedure:

**Terminal 1**

```bash
ros2 launch my_robot_bringup my_robot_arm_bringup_hw.launch.py
```
> This launch also the python arn driver


**Terminal 2**

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p target_joints_deg:="[0.0,30.0,-30.0,0.0,0.0,0.0]" \
  -p duration:=5.0 \
  -p steps:=50
```

If the URDF model and joint names match, the arm movement should be visualized correctly in RViz2.

Open rviz2 and show here the picture of the joint configuration you obtain in rviz

![](./Images/03_Control/arm_rviz1.png)

---

# 12. Safety Recommendations

Before testing the physical robot arm:

1. Remove any obstacles from the workspace.
2. Start with small joint movements (typically **10°–20°**).
3. Verify that every servo rotates in the correct direction.
4. If a servo rotates in the opposite direction, modify the corresponding `servo_sign` parameter.
5. If a servo reaches its mechanical limits, reduce `servo_min_deg` and `servo_max_deg`.
6. Never begin with large movements before individually testing every joint.
7. Keep the USB cable easily accessible so the system can be disconnected immediately if necessary.

---

# 13. Smooth Motion Strategy for SG90 Servos

SG90 servos are inexpensive hobby servos with an internal position controller.

Typically, only a target angle can be commanded, while the internal electronics determine how the servo reaches that position. Consequently, ROS cannot directly control the actual servo speed.

The practical solution consists of:

```text
Large movement
      ↓
Divide it into many small increments
      ↓
Generate a trajectory with many points
      ↓
Execute the trajectory over a specified duration
```

For this reason, the recommended node is:

```bash
send_smooth_joint_target_node
```

The two most important parameters are:

```text
duration
steps
```

where:

* Increasing **`duration`** produces slower movements.
* Increasing **`steps`** increases the number of intermediate trajectory points, resulting in smoother motion.
* A good starting configuration is:

```text
duration := 5.0
steps    := 50
```

For slower and smoother movements, values such as:

```text
duration := 10.0
steps    := 100
```

are recommended.

---

# 14. Recommended Testing Procedure

## Step 1 — Build the Package

```bash
cd ~/my_rUBot_mecanum
colcon build --packages-select my_arm_driver
source install/setup.bash
```

---

## Step 2 — Launch the Driver

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p serial_port:=/dev/ttyUSB1
```

---

## Step 3 — Verify the ROS Topics

```bash
ros2 topic list | grep joint
```

---

## Step 4 — Execute a Smooth Motion on One Joint

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[15.0,0.0,0.0,0.0,0.0,0.0]" \
  -p duration:=4.0 \
  -p steps:=40
```

---

## Step 5 — Execute a Smooth Motion on Two Joints

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[15.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[15.0,25.0,-20.0,0.0,0.0,0.0]" \
  -p duration:=5.0 \
  -p steps:=50
```

---

## Step 6 — Return to the Home Position

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[15.0,25.0,-20.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p duration:=5.0 \
  -p steps:=50
```

---

# 15. Troubleshooting

## 15.1 Serial Port Not Detected

Verify that the Arduino is connected:

```bash
ls /dev/ttyUSB*
ls /dev/ttyACM*
```

Disconnect and reconnect the Arduino if necessary.

You can also inspect the latest kernel messages:

```bash
dmesg | tail
```

---

## 15.2 Permission Denied on the Serial Port

The most common solution is:

```bash
sudo usermod -a -G dialout $USER
```

Then log out and log back in.

---

## 15.3 The Robot Arm Does Not Move

Verify that trajectories are being published:

```bash
ros2 topic echo /arm_controller/joint_trajectory
```

If no messages appear, the command node is either not running or is publishing to a different topic.

Also verify that the driver node is active:

```bash
ros2 node list
```

You should see:

```text
/serial_trajectory_bridge_node
```

---

## 15.4 A Servo Rotates in the Wrong Direction

Invert the corresponding servo by modifying `servo_sign`:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p servo_sign:="[1,-1,1,1,1,1]"
```

---

## 15.5 A Servo Reaches Its Mechanical Limit

Reduce the allowed servo range:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p servo_min_deg:="[20,20,20,20,20,20]" \
  -p servo_max_deg:="[160,160,160,160,160,160]"
```

---

## 15.6 No Motion Is Displayed in RViz2

Verify that joint states are being published:

```bash
ros2 topic echo /joint_states
```

Also confirm that the joint names exactly match those defined in the URDF/Xacro model.

For the integrated robot arm, the expected joint names are:

```text
arm_joint1
arm_joint2
arm_joint3
arm_joint4
arm_joint5
arm_joint6
```

---

# 16. Summary

The recommended workflow for testing the physical robot arm is:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

followed by:

```bash
ros2 run my_arm_driver send_smooth_joint_target_node
```

The `send_smooth_joint_target_node` is the recommended motion generator for SG90 servos because it automatically creates trajectories composed of many intermediate points. Although SG90 servos do not provide direct velocity control, this interpolation strategy produces significantly smoother, slower, and more coordinated arm movements.

In future developments, this node can be replaced by a standard **MoveIt 2** motion planning pipeline. MoveIt automatically computes inverse kinematics, generates collision-aware trajectories, and performs time parameterization, providing a more efficient and scalable solution than manually generating interpolated trajectories. At that point, the `serial_trajectory_bridge_node` will simply execute the `JointTrajectory` messages generated by MoveIt, maintaining full compatibility with the existing hardware interface.
