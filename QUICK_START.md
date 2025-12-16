# 快速开始指南

## 5分钟上手

### 1. 安装依赖
```bash
make install
# 或
pip install -r requirements.txt
```

### 2. 配置环境
创建 `.env` 文件：
```bash
echo "HYPERLIQUID_PRIVATE_KEY=your_key_here" > .env
```

### 3. 运行（模拟模式）
```bash
make run
# 或
python scripts/run_trader.py
```

### 4. 运行（实盘模式）
```bash
make run-live
# 或
python scripts/run_trader.py --live
```

## 常用命令

| 命令 | 说明 |
|------|------|
| `make help` | 显示帮助信息 |
| `make run` | 运行模拟模式 |
| `make run-live` | 运行实盘模式 |
| `make clean` | 清理临时文件 |

## 目录说明

```
src/core/          # 核心交易逻辑
src/config/        # 配置文件
scripts/           # 启动和分析脚本
data/logs/         # 交易日志
docs/              # 详细文档
```

## 重要配置

编辑 `src/config/arbitrage_config.py`：

```python
# 交易模式
DRY_RUN = False  # False=实盘

# 仓位大小
INITIAL_POSITION_SIZE = 100  # USDC

# 开仓阈值
MIN_NET_PROFIT = 0.10  # 最小净利润

# 平仓条件
TAKE_PROFIT_TARGET = 0.35  # 止盈目标
POSITION_TIMEOUT_HOURS = 2.5  # 超时时间
```

## 查看日志

```bash
# 交易记录
cat data/logs/arbitrage_trades.csv

# 价差历史
cat data/logs/spread_profit_log.csv
```

## 数据分析

```bash
# 分析价差
python scripts/analysis/analyze_spread.py

# 分析交易表现
python scripts/analysis/analyze_trading_performance.py

# 优化策略
python scripts/analysis/optimize_strategy.py
```

## 安全提示

⚠️ **首次使用必读**：
1. 先在模拟模式下测试
2. 使用小额资金开始
3. 理解所有风险参数
4. 定期检查持仓状态

## 获取帮助

- 📖 详细文档：`docs/`
- 🔧 配置说明：`src/config/arbitrage_config.py`
- 📝 迁移指南：`MIGRATION_GUIDE.md`
- 📋 更新日志：`CHANGELOG.md`

## 故障排查

### 导入错误
```bash
# 确保在项目根目录
pwd

# 测试导入
python -c "from src.core import ArbitrageTrader; print('OK')"
```

### 找不到数据文件
数据文件在 `data/logs/`，配置已自动更新。

### 持仓恢复问题
程序会自动从交易日志恢复持仓，包括正确的开仓时间。

## 下一步

1. 阅读 [完整文档](README.md)
2. 查看 [套利策略说明](docs/ARBITRAGE_README.md)
3. 了解 [实盘交易准备](docs/LIVE_TRADING_READY.md)
