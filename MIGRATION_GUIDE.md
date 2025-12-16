# 项目重组迁移指南

## 变更概述

项目已从扁平结构重组为模块化结构，所有文件已移动到相应的目录中。

## 主要变更

### 1. 目录结构

**旧结构**（所有文件在根目录）：
```
.
├── arbitrage_trader.py
├── arbitrage_calculator.py
├── position_manager.py
├── config.py
└── ...
```

**新结构**（模块化组织）：
```
.
├── src/
│   ├── core/          # 核心交易逻辑
│   ├── monitors/      # 监控模块
│   ├── config/        # 配置
│   └── utils/         # 工具
├── scripts/           # 脚本
├── data/             # 数据
└── docs/             # 文档
```

### 2. 启动方式变更

**旧方式**：
```bash
python arbitrage_trader.py --live
```

**新方式**：
```bash
python scripts/run_trader.py --live
```

### 3. Import 语句变更

**旧代码**：
```python
import config
import arbitrage_config
from arbitrage_calculator import ArbitrageCalculator
from position_manager import PositionManager
```

**新代码**：
```python
from src.config import config, arbitrage_config
from src.core.calculator import ArbitrageCalculator
from src.core.position_manager import PositionManager
```

### 4. 文件路径变更

**配置文件**：
- `config.py` → `src/config/config.py`
- `arbitrage_config.py` → `src/config/arbitrage_config.py`

**核心模块**：
- `arbitrage_trader.py` → `src/core/trader.py`
- `arbitrage_calculator.py` → `src/core/calculator.py`
- `position_manager.py` → `src/core/position_manager.py`
- `arbitrage_logger.py` → `src/core/logger.py`

**监控模块**：
- `spread_monitor.py` → `src/monitors/spread_monitor.py`
- `spread_profit_monitor.py` → `src/monitors/spread_profit_monitor.py`

**工具模块**：
- `utils.py` → `src/utils/utils.py`
- `hip3_trading.py` → `src/utils/hip3_trading.py`

**数据文件**：
- `*.csv` → `data/logs/*.csv`

**文档**：
- `*README.md` → `docs/`

**分析脚本**：
- `analyze_*.py` → `scripts/analysis/`
- `debug_*.py` → `scripts/debug/`

## 迁移步骤

### 如果你有自定义脚本

1. **更新 import 语句**：
   ```python
   # 旧
   from arbitrage_trader import ArbitrageTrader
   
   # 新
   from src.core.trader import ArbitrageTrader
   ```

2. **更新文件路径**：
   ```python
   # 旧
   log_file = 'arbitrage_trades.csv'
   
   # 新
   log_file = 'data/logs/arbitrage_trades.csv'
   ```

3. **添加项目根目录到 Python 路径**：
   ```python
   import sys
   import os
   project_root = os.path.dirname(os.path.abspath(__file__))
   sys.path.insert(0, project_root)
   ```

### 如果你在使用旧的启动方式

直接使用新的启动脚本：
```bash
python scripts/run_trader.py --live
```

## 兼容性说明

- ✅ 所有核心功能保持不变
- ✅ 配置参数保持不变
- ✅ 数据格式保持不变
- ✅ API 接口保持不变

## 清理旧文件

旧的根目录文件已被复制到新位置，你可以安全删除它们：

```bash
# 删除旧的核心文件（已移动到 src/）
rm arbitrage_trader.py arbitrage_calculator.py position_manager.py
rm arbitrage_logger.py spread_monitor.py spread_profit_monitor.py
rm config.py arbitrage_config.py utils.py hip3_trading.py

# 删除旧的分析脚本（已移动到 scripts/）
rm analyze_*.py detailed_analysis.py optimize_strategy.py
rm debug_*.py test_api_direct.py quick_reversal_check.py
```

**注意**：删除前请确保新结构运行正常！

## 测试新结构

1. **测试导入**：
   ```bash
   python -c "from src.core import ArbitrageTrader; print('OK')"
   ```

2. **测试启动**：
   ```bash
   python scripts/run_trader.py --help
   ```

3. **运行模拟模式**：
   ```bash
   python scripts/run_trader.py
   ```

## 问题排查

### ImportError: No module named 'src'

确保你在项目根目录运行脚本，或者添加项目根目录到 Python 路径。

### 找不到数据文件

数据文件已移动到 `data/logs/`，配置已自动更新。如果有问题，检查 `src/config/arbitrage_config.py` 中的 `DATA_DIR` 设置。

### 旧脚本无法运行

更新 import 语句和文件路径，参考上面的"迁移步骤"。

## 获取帮助

如果遇到问题，请检查：
1. 是否在项目根目录
2. Python 路径是否正确
3. 所有依赖是否已安装

## 回滚方案

如果需要回滚到旧结构，旧文件仍然保留在根目录（如果你还没删除）。
