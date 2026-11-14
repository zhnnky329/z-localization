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

当前目标环境为 **Ubuntu 24.04 / ROS 2 Jazzy**。各包 README 包含依赖、编译命令和运行示例。
Z-LIO 可以单独使用；运行整套定位时，从 Z-LOC 的联合启动入口进入。

- [前端安装与运行](src/z_lio/README.md)
- [后端安装与运行](src/z_loc/README.md)
- [地图制作流程](src/z_loc/docs/map-workflow.md)
- [前端参数](src/z_lio/docs/parameters.md) / [后端参数](src/z_loc/docs/parameters.md)
- [前后端协议](src/z_lio/docs/interfaces.md)
- [设计思路与取舍](docs/design.md)

从 Humble 迁移时，在干净终端中只加载 Jazzy，使用单独的构建目录：

```bash
source /opt/ros/jazzy/setup.bash
rosdep update --rosdistro jazzy
rosdep install --from-paths src --ignore-src --rosdistro jazzy -r -y
colcon --log-base log-jazzy build --build-base build-jazzy --install-base install-jazzy \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DLOCALIZATION_WARNINGS_AS_ERRORS=ON
source install-jazzy/setup.bash
colcon --log-base log-jazzy test --build-base build-jazzy --install-base install-jazzy \
  --return-code-on-test-failure
colcon test-result --test-result-base build-jazzy --verbose
```

首次使用 rosdep 的机器需要先执行 `sudo rosdep init`。GTSAM 保持 4.2.x，nanoflann 使用 1.5 或更新版本。
不要复用 Humble 的构建产物、Python 环境或外部驱动二进制。

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

两个包已在 Ubuntu 24.04 / Jazzy、GCC 13.3、Eigen 3.4、GTSAM 4.2.0、nanoflann 1.5.4 下完成
Release 构建，`LOCALIZATION_WARNINGS_AS_ERRORS=ON`。Eigen 3.4 几何模板的 GCC 13 未初始化误报
只在两处使用该模板的编译单元中局部豁免，项目代码仍保留完整的 `-Werror`。

25 个不依赖 ROS 通信的测试目标通过，共 240 个测试用例，包含输入队列混合事件的新增回归测试。
其余 6 个 ROS 启动测试目标因沙箱禁止申请本地通信端口而失败（`Operation not permitted`），
尚未完成节点通信、bag 回归和 Jazzy 实机验证。原项目在 Humble 下的实机记录继续保留。

Livox 可选分支也通过了严格编译，使用原驱动消息定义生成的临时消息包，未连接真实驱动。
[Jazzy CI](.github/workflows/jazzy.yml) 使用官方 ROS 容器和 rosdep 安装依赖，执行严格构建及完整测试；
工作流文件已加入仓库，远端运行结果以 GitHub Actions 为准。

## 作者与许可

mozihe · [zhujunheng2005@gmail.com](mailto:zhujunheng2005@gmail.com) · QQ：820288431

采用 [GPL-2.0-only](LICENSE)，第三方组件保留各自许可证。
