#pragma once

// GCC 13 对 Eigen 3.4 的 FromTwoVectors/SVD 分支有未初始化误报。
// 只在解析第三方几何模板时豁免，项目代码仍使用完整的 -Werror。
#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ == 13
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wmaybe-uninitialized"
#endif

#include <Eigen/Geometry>

#if defined(__GNUC__) && !defined(__clang__) && __GNUC__ == 13
#pragma GCC diagnostic pop
#endif
