# Z-Localization

东北大学 T-DT 实验室 2026 年 RoboMaster 哨兵定位项目，按前端里程计和后端全局定位定位拆分为两个 独立的ros包，方便解耦调试：

| 包 | 作用 | 说明 |
| --- | --- | --- |
| [Z-LIO](src/z_lio/README.md) / `z_lio` | 激光惯性里程计 | LiDAR/IMU 初始化、去畸变、局部地图和高频预测 |
| [Z-LOC](src/z_loc/README.md) / `z_loc` | 全局定位 | 先验地图、回环、重定位、UWB、地图处理与标定工具 |

原有的算法、参数文档、地图工具和测试都保留在对应包中。
前后端消息与重置事务缓存归入 `z_lio`，统一启动入口归入 `z_loc`。
Livox 驱动已移除，如需要Livox驱动的 CustomMsg ，可自行单独安装驱动并启用前端适配。

## 使用

当前目标环境为 **Ubuntu 24.04 / ROS 2 Jazzy**。各包 README 包含依赖、编译命令和运行示例。
Z-LIO 可以单独使用；运行整套定位时，从 Z-LOC 的联合启动入口进入。

- [前端安装与运行](src/z_lio/README.md)
- [后端安装与运行](src/z_loc/README.md)
- [地图制作流程](src/z_loc/docs/map-workflow.md)
- [前端参数](src/z_lio/docs/parameters.md) / [后端参数](src/z_loc/docs/parameters.md)
- [前后端协议](src/z_lio/docs/interfaces.md)
- [设计思路与取舍](docs/design.md)

## 迁移

| 原入口 | 当前入口 |
| --- | --- |
| `frontend` / `lio.launch.py` | `z_lio` / `lio.launch.py` |
| `frontend` / `frontend.launch.py` | `z_lio` / `z_lio.launch.py` |
| `backend` / `backend.launch.py` | `z_loc` / `z_loc.launch.py` |
| `bringup` / `bringup.launch.py` | `z_loc` / `bringup.launch.py` |
| `localization_interfaces/msg/*`、`srv/*` | `z_lio/msg/*`、`srv/*` |
| 顶层 `config/` | 各包内的 `config/` |

节点名、话题名、服务名和 C++ 算法命名空间保持原样。自定义消息的包名已改变，接入程序需要重新编译；
联合启动不再提供 `driver` 参数，雷达驱动另行启动。

## 原作者与许可

mozihe · [zhujunheng2005@gmail.com](mailto:zhujunheng2005@gmail.com) · QQ：820288431

采用 [GPL-2.0-only](LICENSE)，第三方组件保留各自许可证。
