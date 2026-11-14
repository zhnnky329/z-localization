# Z-LIO

Z-LIO 是 Z-Localization 的前端激光惯性里程计，输入带逐点时间的 LiDAR 点云和 IMU，输出局部里程计、去畸变点云，以及随 IMU 更新的高频预测。

前端维护自己的局部平面地图，不加载先验地图。启动时用多帧点云和 IMU 联合估计初始状态，可以在非静止情况下初始化；正常运行后，通过迭代误差状态滤波更新位姿、速度和 IMU 零偏；观测间隔与点云采样分辨率会随运动和场景调整。

## 编译

当前目标环境是 **Ubuntu 24.04 / ROS 2 Jazzy**
 C++17、Eigen ≥ 3.3、yaml-cpp、nanoflann ≥ 1.5、OpenMP，以及 ROS 2 的开发和测试依赖

在工作区根目录执行：

```bash
source /opt/ros/jazzy/setup.bash
rosdep update --rosdistro jazzy
rosdep install --from-paths src --ignore-src --rosdistro jazzy -r -y
colcon --packages-select z_lio --cmake-args -DCMAKE_BUILD_TYPE=Release
source install-jazzy/setup.bash
```

## 运行

先启动自己的 LiDAR 和 IMU 数据源，再启动里程计：

```bash
ros2 launch z_lio lio.launch.py \
  input_type:=pointcloud2 lidar_topic:=/points imu_topic:=/imu \
  imu_acceleration_scale:=1.0
```

需要看点云和轨迹时：

```bash
ros2 launch z_lio z_lio.launch.py \
  input_type:=pointcloud2 lidar_topic:=/points imu_topic:=/imu \
  imu_acceleration_scale:=1.0 rviz:=true
```

Mid-360 的 CustomMsg 输入使用：

```bash
ros2 launch z_lio lio.launch.py input_type:=livox \
  lidar_topic:=/livox/lidar imu_topic:=/livox/imu imu_acceleration_scale:=9.81
```

这里的加速度倍率取决于数据源：已经是 m/s² 时用 `1.0`，以 g 为单位时用 `9.81`。
launch 保留了原 Mid-360 的默认话题和 `9.81` 倍率，换传感器时要一起检查。
自定义算法参数通过 `config:=/absolute/path/to/lio.yaml` 传入，默认配置在 [config/lio.yaml](config/lio.yaml)。
其中的 LiDAR → IMU 外参来自原机，使用前请换成自己的标定结果。

回放 bag 时加上 `use_sim_time:=true`，另一个终端执行 `ros2 bag play /path/to/bag --clock`。
从头重播前重新启动节点。

## 输入和输出

PointCloud2 必须包含 `x/y/z` 和逐点时间。节点默认读取纳秒相对时间字段 `offset_time`；
其他格式通过节点参数 `point_time_field`、`point_time_scale`、`point_time_absolute` 配置。
没有逐点时间的点云不能直接当作正常去畸变输入。

默认坐标系是 `odom → imu`，里程计位姿在 odom 系表达，速度在 IMU 系表达。
输入消息的 `frame_id` 不会触发自动 TF 转换；LiDAR → IMU 使用配置里的固定外参。

| 话题 | 内容 |
| --- | --- |
| `/odometry` | 随 IMU 更新的标准 Odometry |
| `/lidar_odometry` | 每次激光观测端点的后验 Odometry |
| `/frontend/frame` | 同一观测端点的里程计、去畸变点云和更新状态 |
| `/frontend/odometry` | 带进程身份和重置代次的高频预测 |
| `/frontend/session` | 当前会话、输入中断和处理失败通知 |

去畸变点云在本次观测结束时的 IMU 坐标系中，只导出 float32 XYZ。
完整话题、QoS、服务和坐标约定见 [ROS 接口](docs/ros-interface.md)，参数见 [调参说明](docs/parameters.md)。

## 重置与后端接口

共享消息和重置服务直接由这个包生成：`z_lio/msg/FrontendFrame`、`FrontendOdometry`、`FrontendSession`
以及 `z_lio/srv/ResetFrontend`。[协议说明](docs/interfaces.md) 包含字段、事务去重和暖重置边界的约定。

单独运行时，已初始化后的输入中断默认自动冷启动。和 Z-LOC 配合时，由后端先冻结输出，再协调前端换代；
联合启动入口会设置 `coordinated_reset:=true`。
暖重置保留速度、倾角和 IMU 零偏，重设位置与航向，并返回新旧 odom 系的关系。
冷启动后需要后端重新通过地图或 UWB 找回全局位姿。

`/localization_start` 是可选的启动门，`/stop` 停止接收输入并排空可处理数据。
`/zlio/reset_internal` 是协调重置的内部服务，正常使用时交给后端调用。

## 目录与测试

- `include/zlio/`、`src/`：纯 C++ 算法库，导出目标仍为 `zlio::zlio`。
- `apps/`：ROS 输入、线程调度、发布和可视化。
- `msg/`、`srv/`、`include/z_lio/`：前后端协议与重置事务缓存。
- `config/`、`launch/`、`rviz/`：配置与启动资源。
- `test/`：状态数学、输入、初始化、估计、地图、协议序列化和 ROS 链路测试。

```bash
colcon --log-base log-jazzy test --build-base build-jazzy --install-base install-jazzy --packages-select z_lio
colcon test-result --test-result-base build-jazzy --verbose
```

启用 Livox 适配时，传感器链路测试还会覆盖 CustomMsg 输入。前后端联合重置测试放在 Z-LOC 中。

## 致谢

感谢以下开源项目与研究工作提供的算法思路和工程参考。

| 项目 / 研究工作 | 参考与启发 |
| --- | --- |
| [FAST-LIO / FAST-LIO2](https://github.com/hku-mars/FAST_LIO) | 高效激光惯性紧耦合、迭代滤波与直接点云配准的基础思路 |
| [Voxel-SLAM](https://github.com/hku-mars/Voxel-SLAM) | 多帧激光惯性初始化、重去畸变与联合优化 |
| [BALM / BALM 2.0](https://github.com/hku-mars/BALM) | 多帧平面统计与点云位姿联合优化 |
| [PV-LIO](https://github.com/HViktorTsoi/PV-LIO) / [VoxelMap](https://github.com/hku-mars/VoxelMap) | 概率体素平面地图、测量与平面不确定度建模，以及点面关联 |
| [Faster-LIO](https://github.com/gaoxiang12/faster-lio) | iVox 稀疏增量体素索引与高效邻域检索的思路 |
| [Eq-LIO](https://github.com/taoxiom/Eq-LIO) | 等变滤波与状态建模，尤其是导航状态和 IMU 零偏的耦合表达 |
| [DLIO](https://github.com/vectr-ucla/direct_lidar_inertial_odometry) | 连续时间运动轨迹构建与点云去畸变 |
| [Point-LIO](https://github.com/hku-mars/Point-LIO) | 按逐点采样时间组织 LiDAR–IMU 数据，逐点或按点组进行状态传播与更新 |
| [AS-LIO](https://arxiv.org/abs/2408.11426) | 基于空间重叠调整滑动窗口与更新步长的思路，为早期时间自适应设计提供参考 |
| [Coco-LIC](https://arxiv.org/abs/2309.09808) / [ASPIRE-VINS](https://arxiv.org/abs/2608.12840) | 根据运动变化调整时间分辨率的思路，为当前观测间隔调度提供参考 |
| [GenZ-LIO](https://arxiv.org/abs/2603.16273) | 场景尺度感知的空间自适应采样、点数反馈调节与双分辨率体素采样 |
| [Super-LIO](https://github.com/Liansheng-Wang/Super-LIO) | 体素内保留原始代表点、按中心距离进行降采样的思路 |

同时感谢 [Livox ROS Driver 2](https://github.com/Livox-SDK/livox_ros_driver2) 提供驱动与消息接口，
以及 ROS 2、Eigen、yaml-cpp、nanoflann 和 OpenMP 生态的维护者。

## 原作者与许可

mozihe · [zhujunheng2005@gmail.com](mailto:zhujunheng2005@gmail.com) · QQ：820288431

采用 [GPL-2.0-only](LICENSE)，第三方工作保留各自许可证。
