"""
套利交易配置文件
包含交易策略参数、风险控制参数等
"""

# ==================== 交易模式 ====================
DRY_RUN = False  # True=模拟模式，False=实盘模式

# ==================== 仓位管理 ====================
# 每边余额约25U，10倍杠杆，最大名义仓位约$250
# 为安全起见使用较小仓位，留余量防止爆仓
INITIAL_POSITION_SIZE = 100  # USDC，初始仓位大小（名义价值）
MAX_SINGLE_POSITION = 150  # USDC，单笔最大仓位
MAX_TOTAL_POSITION = 200  # USDC，总仓位上限
MAX_POSITIONS = 2  # 最多同时持有的仓位数量（余额有限，减少仓位数量）

# ==================== 开仓条件 ====================
MIN_NET_PROFIT = 0.15  # USDC，最小净利润阈值（2025-12-03优化：基于数据分析从0.18降至0.15，提高交易频率）
SPREAD_STABILITY_CHECKS = 2  # 价差稳定性检查次数（从3优化到2，加快反应）
SPREAD_STABILITY_INTERVAL = 2  # 秒，价差稳定性检查间隔

# ==================== 加仓条件 ====================
ADD_POSITION_SPREAD_INCREASE = 0.20  # USDC，价差增加阈值
ADD_POSITION_MIN_SPREAD = 0.60  # USDC，加仓时的最小总价差

# ==================== 平仓条件 ====================
# 价差反转平仓
REVERSAL_MIN_SPREAD = 0.15  # USDC，反向价差最小值（从0.20优化到0.15）

# 止盈平仓
TAKE_PROFIT_TARGET = 0.35  # USDC，止盈目标（2025-12-03优化：从0.40降至0.35，更快锁定利润）

# 超时兜底
POSITION_TIMEOUT_HOURS = 1.5  # 小时，最大持仓时间（2025-12-03优化：数据显示60分钟内的交易100%盈利，1.5小时超时可减少亏损）

# ==================== 平仓执行策略 ====================
# 混合平仓策略：先挂Maker限价单，超时后市价兜底
LIMIT_ORDER_TIMEOUT = 3  # 秒，限价单等待时间
LIMIT_ORDER_PRICE_IMPROVEMENT = 0.0001  # 限价单价格改善（相对于市价的优势）

# ==================== 手续费 ====================
# 实际费率（TSLA标的有减免）:
# MAKER_FEE = 0.000081  # 0.0081%
# TAKER_FEE = 0.00003   # 0.0030%
# 从 config.py 继承

# ==================== 监控与日志 ====================
MONITOR_INTERVAL = 2  # 秒，市场数据监控间隔
LOG_TRADES = True  # 是否记录交易日志
TRADE_LOG_FILE = "arbitrage_trades.csv"  # 交易日志文件

# ==================== 安全检查 ====================
MAX_SLIPPAGE = 0.01  # 1%，最大滑点容忍度
ENABLE_SAFETY_CHECKS = True  # 是否启用安全检查

# ==================== API 配置 ====================
# Hyperliquid API 配置从环境变量读取
# 需要在 .env 文件中配置:
# HYPERLIQUID_PRIVATE_KEY=your_private_key_here
