#!/usr/bin/env python3
"""
验证项目结构是否正确
"""
import os
import sys

def check_file(path, description):
    """检查文件是否存在"""
    exists = os.path.exists(path)
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {path}")
    return exists

def check_import(module_path, description):
    """检查模块是否可以导入"""
    try:
        exec(f"from {module_path} import *")
        print(f"✅ {description}: {module_path}")
        return True
    except Exception as e:
        print(f"❌ {description}: {module_path} - {e}")
        return False

print("=" * 60)
print("项目结构验证")
print("=" * 60)

all_passed = True

# 检查目录结构
print("\n【目录结构】")
dirs = [
    ('src', '源代码目录'),
    ('src/core', '核心模块'),
    ('src/monitors', '监控模块'),
    ('src/config', '配置模块'),
    ('src/utils', '工具模块'),
    ('scripts', '脚本目录'),
    ('scripts/analysis', '分析脚本'),
    ('scripts/debug', '调试脚本'),
    ('data', '数据目录'),
    ('data/logs', '日志目录'),
    ('docs', '文档目录'),
    ('tests', '测试目录'),
]

for dir_path, desc in dirs:
    all_passed &= check_file(dir_path, desc)

# 检查核心文件
print("\n【核心文件】")
files = [
    ('src/core/trader.py', '交易引擎'),
    ('src/core/calculator.py', '利润计算器'),
    ('src/core/position_manager.py', '仓位管理'),
    ('src/core/logger.py', '日志记录'),
    ('src/monitors/spread_monitor.py', '价差监控'),
    ('src/monitors/spread_profit_monitor.py', '利润监控'),
    ('src/config/config.py', '基础配置'),
    ('src/config/arbitrage_config.py', '套利配置'),
    ('src/utils/utils.py', '工具函数'),
    ('src/utils/hip3_trading.py', 'HIP3交易'),
]

for file_path, desc in files:
    all_passed &= check_file(file_path, desc)

# 检查脚本
print("\n【脚本文件】")
scripts = [
    ('scripts/run_trader.py', '主启动脚本'),
    ('scripts/analysis/analyze_spread.py', '价差分析'),
    ('scripts/debug/debug_markets.py', '市场调试'),
]

for script_path, desc in scripts:
    all_passed &= check_file(script_path, desc)

# 检查文档
print("\n【文档文件】")
docs = [
    ('README.md', '主README'),
    ('QUICK_START.md', '快速开始'),
    ('MIGRATION_GUIDE.md', '迁移指南'),
    ('CHANGELOG.md', '更新日志'),
    ('Makefile', 'Makefile'),
]

for doc_path, desc in docs:
    all_passed &= check_file(doc_path, desc)

# 检查导入
print("\n【模块导入】")
imports = [
    ('src.core', '核心模块'),
    ('src.monitors', '监控模块'),
    ('src.config', '配置模块'),
    ('src.utils', '工具模块'),
]

for import_path, desc in imports:
    all_passed &= check_import(import_path, desc)

# 检查主类导入
print("\n【主类导入】")
classes = [
    ('src.core.trader', 'ArbitrageTrader'),
    ('src.core.calculator', 'ArbitrageCalculator'),
    ('src.core.position_manager', 'PositionManager'),
    ('src.core.logger', 'ArbitrageLogger'),
]

for module, cls in classes:
    try:
        exec(f"from {module} import {cls}")
        print(f"✅ {cls}: {module}")
    except Exception as e:
        print(f"❌ {cls}: {module} - {e}")
        all_passed = False

# 总结
print("\n" + "=" * 60)
if all_passed:
    print("✅ 所有检查通过！项目结构正确。")
    sys.exit(0)
else:
    print("❌ 部分检查失败，请检查上述错误。")
    sys.exit(1)
