# 地图制作与运行

配置入口为 [lio.yaml](../../z_lio/config/lio.yaml) 和 [backend.yaml](../config/backend.yaml)。
默认配置中的安装外参、场地路径和 UWB 设置来自作者的设备，不是通用标定结果。

请先看[前端调参指南](../../z_lio/docs/parameters.md#调参建议)和[后端调参指南](parameters.md#调参建议)，尤其是传感器、外参与时间相关的部分。

bag 建图流程以 **Mid-360 + Livox CustomMsg、关闭 UWB、使用 Scan Context** 为例。
场地配置 `pcd/site.yaml`：

```yaml
extends: ../src/z_loc/config/backend.yaml
uwb:
  enabled: false
trajectory:
  save_directory: pcd/site_raw
  save_global_pcd: true
  save_on_shutdown: false
```

## 无先验地图的实时定位

没有先验地图、又需要实时全局位姿时，使用 `mode:=mapping`，将场地配置中的 `uwb.enabled` 设为 `true` 并接入 UWB。
实机运行使用 `use_sim_time:=false`，雷达驱动单独运行。

正式使用定位前，先启动程序并让机器人移动几米（默认需要至少 `3 m` 的水平位移跨度），
待定位状态进入 `NORMAL` 后再使用全局位姿。UWB 配置见[调参指南](parameters.md#uwb-参数)。

## 从 bag 建图到先验定位

**回放建图 → 保存地图 → 自动清理 → CloudCompare 精修 → 网格生成地图包与描述子 → 先验定位。**

以下命令在项目根目录执行，使用上面的 `pcd/site.yaml`。

### 1. 建图与回放

```bash
ros2 launch z_loc bringup.launch.py \
  frontend_config:="$PWD/src/z_lio/config/lio.yaml" \
  backend_config:="$PWD/pcd/site.yaml" \
  mode:=mapping input_type:=livox lidar_topic:=/livox/lidar use_sim_time:=true rviz:=true
```

另一个终端播放 bag：

```bash
ros2 bag play /absolute/path/to/bag --clock
```

从头重播前，重新启动定位程序。

### 2. 保存地图

回放结束后停止输入，待末尾观测和地图更新完成再保存：

```bash
ros2 service call /stop std_srvs/srv/Trigger "{}"

# 地图更新完成后执行
ros2 service call /backend_node/save_map std_srvs/srv/Trigger "{}"
```

返回 `success: true` 后再退出节点，结果在 `pcd/site_raw/`。
保留完整地图包，后续清理需要其中的关键帧和局部点云；同一目录再次保存会更新原有结果。

### 3. 自动清理动态残影

```bash
ros2 run z_loc clean_map_bundle \
  --in "$PWD/pcd/site_raw" \
  --out "$PWD/pcd/site_auto_clean" \
  --lidar-origin -0.011 -0.02329 0.04412
```

这里的雷达光心位置对应默认 Mid-360 外参，在 IMU 系中表达。
清理及后续生成工具的输出目录须不存在或为空。

过滤思路参考 [FreeDOM](https://github.com/LC-Robotics/FreeDOM)。按作者的实测体验，这一步非常有效，
能大幅减少手工清理的工作量，但结果仍不足以直接使用（尤其是在适应性训练阶段如此恶劣的环境下）。

### 4. CloudCompare 手工收尾

用 [CloudCompare](https://www.cloudcompare.org/) 打开 `pcd/site_auto_clean/map.pcd`，去掉剩余动态残影和噪点，
调平地图并调整世界系原点，另存为 `pcd/site_refined.pcd`。

### 5. 网格生成地图包与描述子

**雷达水平安装时，作者建议精修后重新按网格生成。** 按作者的使用经验，这样生成的描述子通常比建图时直接保存的质量更好。

下面以 X：`0–28 m`、Y：`0–15 m`、采样 Z 坐标 `0 m`、雷达离地高度 `0.35 m` 为例，范围和高度按调整后的地图填写。

```bash
ros2 run z_loc build_pcd_map_bundle \
  --input "$PWD/pcd/site_refined.pcd" \
  --out-bundle "$PWD/pcd/site_prior" \
  --x-min 0 --x-max 28 --y-min 0 --y-max 15 \
  --sensor-z 0.0 --bundle-step 1.5 \
  --map-voxel 0.15 --scan-voxel 0.4 \
  --descriptor-type scan_context --sc-lidar-height 0.35
```

`--sensor-z` 是地图中的采样高度坐标，`--sc-lidar-height` 是离地高度，两者不一定相等。
本例按水平姿态、固定高度生成；描述子配置须与定位时一致，其余选项见[工具参数](parameters.md#离线工具参数)。

### 6. 先验地图定位

```bash
ros2 launch z_loc bringup.launch.py \
  frontend_config:="$PWD/src/z_lio/config/lio.yaml" \
  backend_config:="$PWD/pcd/site.yaml" \
  mode:=localization input_type:=livox lidar_topic:=/livox/lidar prior_map:="$PWD/pcd/site_prior" \
  use_sim_time:=true rviz:=true
```

另一个终端回放验证：

```bash
ros2 bag play /absolute/path/to/bag --clock
```

实机运行时使用 `use_sim_time:=false`。Livox 驱动需要单独安装和启动，回放 bag 时不要再启动驱动。
使用本例的 CustomMsg 输入前，先在 Z-LIO 中启用 `Z_LIO_WITH_LIVOX`。
