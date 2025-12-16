# Hyperliquid TSLA 套利交易系统

一个用于在 Hyperliquid 平台上进行 TSLA 资产套利交易的自动化系统，监控 `flx:TSLA` 和 `xyz:TSLA` 之间的价差机会。

## 项目结构

```
hyperliquid_arbitrage/
├── src/                         # 源代码
│   ├── core/                    # 核心交易逻辑
│   │   ├── trader.py           # 交易引擎
│   │   ├── calculator.py       # 利润计算器
│   │   ├── position_manager.py # 仓位管理
│   │   └── logger.py           # 日志记录
│   ├── monitors/                # 监控模块
│   ├── config/                  # 配置文件
│   └── utils/                   # 工具函数
│
├── scripts/                     # 脚本
│   ├── run_trader.py           # 主启动脚本
│   ├── analysis/               # 数据分析脚本
│   └── debug/                  # 调试工具
│
├── data/                        # 数据文件
│   └── logs/                   # 交易日志
│
├── docs/                        # 文档
└── tests/                       # 测试文件
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件并添加你的私钥：

```
HYPERLIQUID_PRIVATE_KEY=your_private_key_here
```

### 3. 运行交易引擎

**模拟模式（推荐先测试）：**
```bash
python scripts/run_trader.py
```

**实盘模式：**
```bash
python scripts/run_trader.py --live
```

## 核心功能

### 交易策略
- **价差套利**：监控 FLX 和 XYZ 两个 DEX 之间的 TSLA 价差
- **双向交易**：支持 FLX→XYZ 和 XYZ→FLX 两个方向
- **自动平仓**：价差反转、止盈、超时三种平仓机制

### 风险控制
- 仓位大小限制
- 最大持仓数量限制
- 超时强制平仓（2.5小时）
- 价差稳定性检查

### 平仓条件
1. **价差反转**：反向价差达到阈值（FLX→XYZ: $0.05, XYZ→FLX: $0.10）
2. **止盈**：浮盈达到 $0.35
3. **超时兜底**：持仓超过 2.5 小时

## 配置说明

主要配置文件：`src/config/arbitrage_config.py`

```python
# 交易模式
DRY_RUN = False  # True=模拟，False=实盘

# 仓位管理
INITIAL_POSITION_SIZE = 100  # USDC
MAX_POSITIONS = 2

# 开仓条件
MIN_NET_PROFIT = 0.10  # 最小净利润阈值

# 平仓条件
REVERSAL_MIN_SPREAD_FLX_TO_XYZ = 0.05
REVERSAL_MIN_SPREAD_XYZ_TO_FLX = 0.10
TAKE_PROFIT_TARGET = 0.35
POSITION_TIMEOUT_HOURS = 2.5
```

## 数据分析

项目包含多个分析脚本，位于 `scripts/analysis/`：

- `analyze_spread.py` - 价差分析
- `analyze_reversal.py` - 反转机会分析
- `analyze_trading_performance.py` - 交易表现分析
- `optimize_strategy.py` - 策略优化

## 监控和日志

### 交易日志
所有交易记录保存在 `data/logs/arbitrage_trades.csv`

### 价差日志
价差历史数据保存在 `data/logs/spread_profit_log.csv`

## 安全提示

⚠️ **重要**：
- 首次使用请在模拟模式下充分测试
- 确保理解所有风险控制参数
- 实盘交易前请仔细检查配置
- 建议使用小额资金开始

## 最近修复

- ✅ 修复持仓恢复时开仓时间丢失的问题
- ✅ 修复属性名不一致导致的bug
- ✅ 修复变量作用域问题
- ✅ 改进项目结构，符合软件开发规范

## 文档

详细文档请查看 `docs/` 目录：
- [套利策略说明](docs/ARBITRAGE_README.md)
- [数据收集指南](docs/DATA_COLLECTION.md)
- [实盘交易准备](docs/LIVE_TRADING_READY.md)

## 许可证

MIT License

## 免责声明

本软件仅供学习和研究使用。使用本软件进行实盘交易的所有风险由用户自行承担。
