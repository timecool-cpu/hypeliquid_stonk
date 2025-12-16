# TSLA FLX vs XYZ 套利交易系统使用指南

## 📋 系统概述

这是一个自动化套利交易系统，用于在 Hyperliquid 的 `flx:TSLA` 和 `xyz:TSLA` 两个市场之间进行套利交易。

### 核心特性

- ✅ **盈利导向**: 只在扣除手续费后有净利润时才开仓
- ✅ **智能平仓**: 优先等待价差反转（Zero Cost平仓），配合止盈和超时兜底
- ✅ **多仓位支持**: 价差扩大时自动加仓，最多5个仓位
- ✅ **无止损**: 利用两标的强相关性（0.9944），价差扩大时加仓而非止损
- ✅ **干运行模式**: 先模拟测试，验证策略后再实盘

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 运行模拟模式（强烈推荐）

```bash
python3 arbitrage_trader.py
```

或显式指定干运行模式：

```bash
python3 arbitrage_trader.py --dry-run
```

### 3. 运行实盘模式（需先配置API密钥）

```bash
python3 arbitrage_trader.py --live
```

**⚠️ 警告**: 实盘模式需要配置私钥并承担真实交易风险！

## ⚙️ 配置参数

所有策略参数在 `arbitrage_config.py` 中配置：

### 核心参数

```python
# 交易模式
DRY_RUN = True  # True=模拟，False=实盘

# 仓位管理
INITIAL_POSITION_SIZE = 100  # USDC，初始仓位
MAX_POSITIONS = 5  # 最多同时持有的仓位数

# 开仓条件
MIN_NET_PROFIT = 0.30  # USDC，最小净利润阈值

# 平仓条件
REVERSAL_MIN_SPREAD = 0.20  # 价差反转最小阈值
TAKE_PROFIT_TARGET = 0.50  # 止盈目标
POSITION_TIMEOUT_HOURS = 3  # 超时兜底（小时）

# 加仓条件
ADD_POSITION_SPREAD_INCREASE = 0.20  # 价差增加阈值
ADD_POSITION_MIN_SPREAD = 0.60  # 加仓时最小总价差
```

## 📊 套利逻辑说明

### 开仓条件

系统会检查以下条件后才开仓：

1. **净利润检查**: `可执行价差 - 开仓手续费($0.43) > $0.30`
2. **价差稳定**: 连续3次采样确认价差稳定（避免瞬时波动）
3. **仓位限制**: 未达到最大仓位数量（5个）和总仓位上限（$1000）
4. **加仓条件**（如有持仓）: 价差扩大 > $0.20 且总价差 > $0.60

### 平仓逻辑（优先级排序）

| 优先级 | 条件 | 执行方式 | 手续费 |
|-------|------|---------|--------|
| 🥇 **价差反转** | 反向价差 > $0.20 | 反向开仓自动对冲 | 仅新仓$0.43 |
| 🥈 **止盈** | 浮盈 > $0.50 | 挂单3秒+市价兜底 | $0.34-0.86 |
| 🥉 **超时兜底** | 持仓 > 3小时 | 挂单3秒+市价兜底 | $0.34-0.86 |

### 手续费说明

- **开仓**: 使用Taker市价单，固定成本 $0.43（双边）
- **平仓（反转）**: Zero Cost（反向开仓即完成平仓）
- **平仓（常规）**: 先挂Maker限价单，3秒未成交则市价兜底

## 📁 文件结构

```
hypeliquid_stonk/
├── arbitrage_trader.py         # 主程序：套利交易引擎
├── arbitrage_config.py          # 配置：策略参数
├── arbitrage_calculator.py     # 计算器：利润计算、手续费
├── position_manager.py          # 仓位管理：持仓跟踪、平仓判断
├── arbitrage_logger.py          # 日志：交易记录
│
├── config.py                    # 基础配置（市场、API等）
├── utils.py                     # 辅助函数
├── spread_monitor.py            # 价差监控（数据收集）
│
├── arbitrage_trades.csv         # 交易日志（自动生成）
└── spread_history.csv           # 历史价差数据
```

## 📈 监控界面说明

运行后会显示：

```
────────────────────────────────────────────────────────────────────────────────
2025-12-01 14:30:15 | 市场监控
────────────────────────────────────────────────────────────────────────────────

💰 市场价格:
  FLX: Bid $423.00 | Ask $423.06 | Mid $423.03
  XYZ: Bid $423.01 | Ask $423.25 | Mid $423.13

✅ 套利机会:
  方向: FLX_TO_XYZ
  可执行价差: $0.4500
  预期净利润: $0.0269

📊 持仓摘要:
  持仓数量: 1
  总仓位: $100
  总浮盈: $0.35
    - FLX_TO_XYZ: $100 | 持仓15分钟 | 浮盈 $0.35

📈 交易统计:
  总交易: 5 | 胜率: 80.0%
  总盈亏: $1.85
  平均盈亏: $0.37
```

## 📝 交易日志

所有交易会自动记录到 `arbitrage_trades.csv`：

```csv
timestamp,action,position_id,direction,position_size,entry_spread,...,realized_pnl
2025-12-01 14:30:15,OPEN,FLX_TO_XYZ_20251201143015,FLX_TO_XYZ,100,0.4500,...,
2025-12-01 14:45:22,CLOSE,FLX_TO_XYZ_20251201143015,FLX_TO_XYZ,100,0.4500,...,0.3524
```

## 🔧 高级使用

### 自定义策略参数

编辑 `arbitrage_config.py` 中的参数，例如：

```python
# 更激进的策略
MIN_NET_PROFIT = 0.20  # 降低利润阈值
REVERSAL_MIN_SPREAD = 0.15  # 更容易触发反转平仓

# 更保守的策略
MIN_NET_PROFIT = 0.50  # 提高利润阈值
MAX_POSITIONS = 2  # 减少最大仓位数
```

### 回测历史数据

使用已收集的历史数据进行策略回测：

```bash
python3 optimize_strategy.py  # 查看优化建议
python3 analyze_spread.py      # 分析价差模式
```

## ⚠️ 风险提示

1. **模拟测试**: 实盘前务必在干运行模式下充分测试
2. **小额开始**: 首次实盘建议从$10-50小仓位开始
3. **实时监控**: 盯盘前几笔交易，确认逻辑正确
4. **网络延迟**: 注意API延迟和滑点影响
5. **资金费率**: 持仓过夜需支付资金费率
6. **市场风险**: 历史数据不代表未来表现

## 📞 故障排查

### 问题：无法获取市场数据

```bash
# 检查网络连接
ping api.hyperliquid.xyz

# 检查API是否正常
python3 test_api_direct.py
```

### 问题：一直没有套利机会

- 检查 `MIN_NET_PROFIT` 是否设置过高
- 查看 `spread_monitor.py` 确认当前价差水平
- 价差可能确实不满足盈利条件

### 问题：程序卡住

- 按 Ctrl+C 安全退出
- 检查持仓状态和交易日志
- 超时兜底会在3小时后自动平仓

## 🎯 下一步

1. ✅ 在干运行模式下运行至少1小时，观察策略表现
2. ✅ 查看 `arbitrage_trades.csv` 确认交易逻辑
3. ✅ 根据需要调整 `arbitrage_config.py` 参数
4. ⚠️ 配置API密钥后小额实盘测试
5. 🚀 逐步增加仓位规模

---

**祝交易顺利！** 🎉
