# 更新日志

## [2.0.0] - 2025-12-16

### 重大变更 - 项目重组
- 🏗️ 将扁平结构重组为模块化结构
- 📁 创建 `src/`, `scripts/`, `data/`, `docs/`, `tests/` 目录
- 🔧 更新所有 import 语句以适应新结构
- 📝 添加详细的迁移指南

### 新增
- ✨ 添加 `scripts/run_trader.py` 主启动脚本
- 📚 创建新的主 README.md
- 🛠️ 添加 Makefile 用于快速命令
- 📖 添加 MIGRATION_GUIDE.md
- 📋 添加 PROJECT_STRUCTURE.md

### 修复
- 🐛 修复持仓恢复时开仓时间丢失的问题
  - `PositionManager.open_position()` 现在支持 `entry_time` 参数
  - `detect_existing_positions()` 从交易日志恢复正确的开仓时间
  - 超时机制现在能正确工作

- 🐛 修复属性名不一致的问题
  - `Position` 类添加 `size` 属性作为 `position_size` 的别名
  - 修复 `execute_close()` 中的属性引用

- 🐛 修复 `display_status()` 中的变量作用域问题
  - 修正循环中错误使用外部变量的问题

### 改进
- 📊 配置文件现在使用绝对路径
- 🗂️ 数据文件统一存放在 `data/logs/`
- 📄 文档统一存放在 `docs/`
- 🧪 分析脚本统一存放在 `scripts/analysis/`

## [1.0.0] - 2025-12-03

### 初始版本
- ⚡ 实现基本的套利交易功能
- 📈 支持 FLX 和 XYZ 两个方向的套利
- 🛡️ 实现风险控制机制
- 📊 添加数据分析工具
