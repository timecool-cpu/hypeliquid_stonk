# 项目结构重组计划

## 新的目录结构

```
hyperliquid_arbitrage/
├── README.md                    # 主README
├── requirements.txt             # 依赖
├── .env                         # 环境变量
├── .gitignore                   # Git忽略文件
│
├── src/                         # 源代码
│   ├── __init__.py
│   ├── core/                    # 核心交易逻辑
│   │   ├── __init__.py
│   │   ├── trader.py           # arbitrage_trader.py
│   │   ├── calculator.py       # arbitrage_calculator.py
│   │   ├── position_manager.py # position_manager.py
│   │   └── logger.py           # arbitrage_logger.py
│   │
│   ├── monitors/                # 监控模块
│   │   ├── __init__.py
│   │   ├── spread_monitor.py   # spread_monitor.py
│   │   └── spread_profit_monitor.py # spread_profit_monitor.py
│   │
│   ├── config/                  # 配置文件
│   │   ├── __init__.py
│   │   ├── config.py           # config.py
│   │   └── arbitrage_config.py # arbitrage_config.py
│   │
│   └── utils/                   # 工具函数
│       ├── __init__.py
│       ├── utils.py            # utils.py
│       └── hip3_trading.py     # hip3_trading.py
│
├── scripts/                     # 分析和测试脚本
│   ├── analysis/               # 数据分析
│   │   ├── analyze_spread.py
│   │   ├── analyze_reversal.py
│   │   ├── analyze_spread_profits.py
│   │   ├── analyze_trading_performance.py
│   │   ├── detailed_analysis.py
│   │   └── optimize_strategy.py
│   │
│   ├── debug/                  # 调试工具
│   │   ├── debug_markets.py
│   │   ├── test_api_direct.py
│   │   └── quick_reversal_check.py
│   │
│   └── run_trader.py           # 主启动脚本
│
├── data/                        # 数据文件
│   ├── logs/                   # 日志
│   │   ├── arbitrage_trades.csv
│   │   ├── spread_history.csv
│   │   └── spread_profit_log.csv
│   │
│   └── archive/                # 归档数据
│       └── spread_history copy.csv
│
├── docs/                        # 文档
│   ├── ARBITRAGE_README.md
│   ├── DATA_COLLECTION.md
│   └── LIVE_TRADING_READY.md
│
└── tests/                       # 测试文件
    ├── __init__.py
    ├── test_calculator.py
    ├── test_position_manager.py
    └── test_trader.py
```

## 迁移步骤

1. 创建新的目录结构
2. 移动文件到对应目录
3. 更新所有import语句
4. 创建主启动脚本
5. 更新README和文档
