# Z-Localization

东北大学 T-DT 实验室 2026 年 RoboMaster 哨兵定位项目。现在按前端和后端分成两个 ROS 2 包：

| 包 | 作用 | 说明 |
| --- | --- | --- |
| [Z-LIO](src/z_lio/README.md) / `z_lio` | 激光惯性里程计 | LiDAR/IMU 初始化、去畸变、局部地图和高频预测 |
| [Z-LOC](src/z_loc/README.md) / `z_loc` | 全局定位 | 先验地图、回环、重定位、UWB、地图处理与标定工具 |

原有的算法、参数文档、地图工具和测试都保留在对应包中。
前后端消息与重置事务缓存归入 `z_lio`，统一启动入口归入 `z_loc`。
Livox 驱动源码已移除；需要 CustomMsg 输入时，单独安装驱动并启用前端适配。

## 使用

原项目实机环境为 Ubuntu 22.04 / ROS 2 Humble。各包 README 包含依赖、编译命令和运行示例。
Z-LIO 可以单独使用；运行整套定位时，从 Z-LOC 的联合启动入口进入。

- [前端安装与运行](src/z_lio/README.md)
- [后端安装与运行](src/z_loc/README.md)
- [地图制作流程](src/z_loc/docs/map-workflow.md)
- [前端参数](src/z_lio/docs/parameters.md) / [后端参数](src/z_loc/docs/parameters.md)
- [前后端协议](src/z_lio/docs/interfaces.md)
- [设计思路与取舍](docs/design.md)

## 从原包名迁移

| 原入口 | 当前入口 |
| --- | --- |
| `frontend` / `lio.launch.py` | `z_lio` / `lio.launch.py` |
| `frontend` / `frontend.launch.py` | `z_lio` / `z_lio.launch.py` |
| `backend` / `backend.launch.py` | `z_loc` / `z_loc.launch.py` |
| `bringup` / `bringup.launch.py` | `z_loc` / `bringup.launch.py` |
| `localization_interfaces/msg/*`、`srv/*` | `z_lio/msg/*`、`srv/*` |
| 顶层 `config/` | 各包内的 `config/` |

节点名、话题名、服务名和 C++ 算法命名空间保持原样。自定义消息的包名已改变，接入程序需要重新编译；
旧 bag 中的自定义前端消息不能直接当作新类型使用，原始 LiDAR/IMU bag 可以按对应输入格式重新回放。
联合启动不再提供 `driver` 参数，雷达驱动另行启动。

## 验证环境

本次拆分在 Ubuntu 24.04 / ROS 2 Jazzy 下完成了两个包的构建，25 个不依赖 ROS 通信的测试目标通过。
构建使用 GTSAM 4.2.0；后端使用 nanoflann 1.4.3，前端另验证了 1.5.4。
GCC 13 下存在原代码及依赖库的编译警告，本次验证设置了 `-DLOCALIZATION_WARNINGS_AS_ERRORS=OFF`。

ROS 启动测试在申请本地通信端口时被沙箱拒绝（`Operation not permitted`），未完成节点通信和实机验证。
Livox 可选分支用原驱动的消息定义生成临时消息包做了编译检查，未连接真实驱动。
原有 Humble 实机数据不等同于 Jazzy 实机验证。

## 作者与许可

mozihe · [zhujunheng2005@gmail.com](mailto:zhujunheng2005@gmail.com) · QQ：820288431

采用 [GPL-2.0-only](LICENSE)，第三方组件保留各自许可证。
