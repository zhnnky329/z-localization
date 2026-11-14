# Z-LOC

Z-LOC 是 Z-Localization 的定位后端
它接收前端里程计和去畸变点云，结合先验地图、回环与 UWB 观测，输出全局位姿、速度、协方差和定位状态，同时也包含地图制作、动态残影清理和车体外参标定工具。

前端负责短时间的连续运动估计，后端负责 `map → odom`。先验地图匹配和 UWB 作为观测加入 GTSAM 因子图，通过一致性检验后才用于校正。定位不可信时会冻结已有可信位姿，再尝试重定位或协调重置前端。

## 编译

当前目标环境是 **Ubuntu 24.04 / ROS 2 Jazzy**。 C++17、GTSAM **4.2.x**、Eigen、PCL、
nanoflann **≥ 1.5**、oneTBB 和 OpenMP。后端已使用 nanoflann 1.5 的查询 API，1.4.x 不再支持。

这个包依赖 `z_lio` 提供的消息和服务类型。将两个包放进同一个工作区的 `src/` 后，在工作区根目录执行：

```bash
source /opt/ros/jazzy/setup.bash
colcon --packages-up-to z_loc --cmake-args -DCMAKE_BUILD_TYPE=Release
source install-jazzy/setup.bash
```

## 验证

没有先验地图、暂时也不用 UWB 时，可以先验证完整链路。
新建一个场地配置，例如工作区下的 `pcd/site.yaml`：

```yaml
extends: ../src/z_loc/config/backend.yaml
uwb:
  enabled: false
trajectory:
  save_directory: pcd/site_raw
  save_global_pcd: true
  save_on_shutdown: false
```

`extends` 相对于当前 YAML 所在目录解析；地图读取和保存目录相对于节点工作目录解析。
然后启动前后端，传感器驱动另行运行：

```bash
ros2 launch z_loc bringup.launch.py \
  backend_config:="$PWD/pcd/site.yaml" mode:=mapping \
  input_type:=pointcloud2 lidar_topic:=/points imu_topic:=/imu \
  imu_acceleration_scale:=1.0 rviz:=true
```

有先验地图包时改用定位模式：

```bash
ros2 launch z_loc bringup.launch.py \
  backend_config:="$PWD/pcd/site.yaml" \
  mode:=localization prior_map:="$PWD/pcd/site_prior" \
  input_type:=pointcloud2 lidar_topic:=/points imu_topic:=/imu \
  imu_acceleration_scale:=1.0 rviz:=true
```

Mid-360 CustomMsg 输入改为 `input_type:=livox`，并填写实际话题与加速度倍率；
需要先在编译 Z-LIO 时启用外部驱动消息适配。这里不会启动或配置雷达驱动。
回放 bag 时添加 `use_sim_time:=true`，另一个终端执行 `ros2 bag play /path/to/bag --clock`。

如果前端已经单独运行，只启动后端即可：

```bash
ros2 launch z_loc z_loc.launch.py \
  config_file:=/absolute/path/to/site.yaml mode:=mapping rviz:=true
```

默认配置在 [config/backend.yaml](config/backend.yaml)。其中的场地路径、车体外参和 UWB 参数来自原机，
不能直接当作自己的标定结果。尤其注意：默认先验地图和 UWB 都已开启，前面的例子用启动参数及场地配置覆盖了它们。
全部参数与调参建议见 [参数文档](docs/parameters.md)。

## 定位状态与输出

| 状态 | 含义 | 位姿是否可信 |
| --- | --- | --- |
| `INITIALIZING` | 等待首次全局定位 | 否 |
| `NORMAL` | 正常定位 | 是 |
| `OBS_DEGRADED` | 观测与预测冲突，暂时继续沿用前端运动 | 是 |
| `SUSPECT` | 当前估计可疑，正在恢复 | 否 |
| `LOST` | 定位丢失，等待或尝试重定位 | 否 |

主要输出为 `/localization/odometry`、`/backend_node/localization_pose` 和
`/backend_node/localization_state`。进入 `SUSPECT` 或 `LOST` 后，若已有可信位姿，就冻结在该位姿。
使用方应同时读取状态消息中的 `pose_trusted`，不要只看位姿话题是否还在发布。
完整话题、QoS、兼容输出与服务见 [ROS 接口](docs/ros-interface.md)。

无图但有 UWB 时，先让机器人形成足够的水平位移跨度，再使用全局位姿；默认门限为 `3 m`，以进入 `NORMAL` 为准。
原地停着不能从单个 UWB 位置解出 odom 与全局坐标系之间的航向。

## 地图与标定

完整的“bag 建图 → 清理 → CloudCompare 精修 → 生成地图包 → 先验定位”流程见
[地图制作](docs/map-workflow.md)。先验输入需要关键帧地图包，只有一个 PCD 文件还不够。

| 程序 | 用途 |
| --- | --- |
| `build_pcd_map_bundle` | 从全局 PCD 采样，生成关键帧和描述子地图包 |
| `transform_map_bundle` | 刚体变换、四点定轴或目标地图配准 |
| `filter_map_bundle` | 根据参考点云过滤关键帧，或导出参考地图 |
| `clean_map_bundle` | 根据多帧自由空间和可见性清理动态残影 |
| `rebuild_scan_context_descriptors` | 重建 Scan Context 描述子 |
| `body_calibration_node` | 标定传感器到车体的旋转和水平偏移 |

上述程序用 `ros2 run z_loc <程序名>` 调用。车体标定也可通过
`ros2 launch z_loc body_calibration.launch.py` 启动，选项见[工具参数](docs/parameters.md#离线工具参数)。

服务入口保留为 `/backend_node/save_map`、`/backend_node/relocalize` 和 `/localization_reset`。
手动重置若拿不到有效暖重置坐标边界，后端会按停车假设衔接位姿，因此整个重置期间需要停车。
自动冷恢复则要重新通过先验地图或 UWB 找回全局位置；没有绝对定位来源的已有建图轨迹会保持 `LOST`。

## 接入其他前端

默认 `common.frontend: zlio`，订阅 Z-LIO 的同步观测、高频预测和会话消息。
也保留 `legacy` 接口，通过标准 Odometry 与 PointCloud2 同步输入，适配其他 LIO 或奥丁之眼等模块。
点云坐标系、时间同步和重置协议要按 [接口说明](docs/ros-interface.md) 对齐，不能只改话题名。
即使运行其他前端，编译本包时仍需要安装 `z_lio` 的接口类型。

## 目录与测试

- `include/backend/`、`src/`：非 ROS 的定位核心；保留原有 C++ 命名空间。
- `apps/`：ROS 消息、参数、服务和输出适配。
- `tools/`：地图处理与标定。
- `launch/bringup.launch.py`：前后端联合启动。
- `test/`：因子图、配准、恢复、UWB、地图存储和工具测试。
- `test/bringup/`：联合启动参数与真实前后端重置测试。

```bash
colcon --log-base log-jazzy test --build-base build-jazzy --install-base install-jazzy --packages-select z_loc
colcon test-result --test-result-base build-jazzy --verbose
```

带标签数据集的清理验收仍通过 `LOCALIZATION_TEST_DATA_DIR` 显式启用。
Scan Context 适用于默认 Mid-360 场景；有限视场的 G-PROBE 实现也保留，但原作者未充分验证，使用前需要实测召回效果。

## 致谢

感谢以下开源项目与研究工作提供的算法思路和工程参考。

| 项目 / 研究工作 | 参考与启发 |
| --- | --- |
| [GTSAM / iSAM2](https://github.com/borglab/gtsam) | 因子图建模、增量求解与边缘协方差计算 |
| [Scan Context](https://github.com/gisbi-kim/scancontext) / [Scan Context++](https://github.com/gisbi-kim/scancontext_tro) | 地点描述子、航向匹配与平移增强检索 |
| [G-PROBE](https://arxiv.org/abs/2607.06782v1) | 跨视场地点识别、概率占据描述与航向候选验证 |
| [PCM](https://github.com/MIT-SPARK/Kimera-RPGO#related-publications) | 回环测量的成对一致性与一致集合筛选思路 |
| [FreeDOM](https://github.com/LC-Robotics/FreeDOM) | 基于保守自由空间与可见性证据的动态残影清理 |

同时感谢 ROS 2、PCL、Eigen、nanoflann、oneTBB 和 OpenMP 生态的维护者。

## 原作者与许可

mozihe · [zhujunheng2005@gmail.com](mailto:zhujunheng2005@gmail.com) · QQ：820288431

采用 [GPL-2.0-only](LICENSE)，第三方工作保留各自许可证。
