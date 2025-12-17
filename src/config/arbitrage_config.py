"""
套利交易配置文件
包含交易策略参数、风险控制参数等
"""

# ==================== 交易模式 ====================
DRY_RUN = False  # True=模拟模式，False=实盘模式

# ==================== 路径配置 ====================
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'logs')

# ==================== 仓位管理 ====================
# 每边余额约25U，10倍杠杆，最大名义仓位约$250
# 为安全起见使用较小仓位，留余量防止爆仓
INITIAL_POSITION_SIZE = 50  # USDC，初始仓位大小（名义价值）
MAX_SINGLE_POSITION = 150  # USDC，单笔最大仓位
MAX_TOTAL_POSITION = 200  # USDC，总仓位上限
MAX_POSITIONS = 2  # 最多同时持有的仓位数量（余额有限，减少仓位数量）
ALLOW_POSITION_STACKING = True  # 当已有持仓时是否允许继续开新仓

# ==================== 开仓条件 ====================
# 基于历史数据分析优化（2025-12-05）
# $0.10阈值有30%触发率，每日预期$2.82利润
# $0.15阈值只有24%触发率，每日预期$1.80利润
MIN_NET_PROFIT = 0.10  # USDC，最小净利润阈值
SPREAD_STABILITY_CHECKS = 2  # 价差稳定性检查次数（从3优化到2，加快反应）
SPREAD_STABILITY_INTERVAL = 2  # 秒，价差稳定性检查间隔

# ==================== 加仓条件 ====================
ADD_POSITION_SPREAD_INCREASE = 0.20  # USDC，价差增加阈值
ADD_POSITION_MIN_SPREAD = 0.60  # USDC，加仓时的最小总价差

# ==================== 平仓条件 ====================
# 价差反转平仓（不对称阈值，基于2025-12-05历史数据分析）
# FLX→XYZ方向: 24%时间>$0.15，容易达到
# XYZ→FLX方向: 仅7%时间>$0.04，很难达到
REVERSAL_MIN_SPREAD_FLX_TO_XYZ = 0.05  # 平FLX_TO_XYZ仓位需要XYZ→FLX反转，难度大，用低阈值
REVERSAL_MIN_SPREAD_XYZ_TO_FLX = 0.10  # 平XYZ_TO_FLX仓位需要FLX→XYZ反转，容易，用高阈值
REVERSAL_MIN_SPREAD = 0.10  # 保留兼容性

# 止盈平仓
TAKE_PROFIT_TARGET = 0.35  # USDC，止盈目标（2025-12-03优化：从0.40降至0.35，更快锁定利润）

# 超时兜底（基于数据分析：XYZ→FLX方向最长无正值期255分钟≈4.3小时）
POSITION_TIMEOUT_HOURS = 2.5  # 小时，最大持仓时间

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
MONITOR_INTERVAL = 5  # 秒，市场数据监控间隔
LOG_TRADES = True  # 是否记录交易日志
TRADE_LOG_FILE = os.path.join(DATA_DIR, "arbitrage_trades.csv")  # 交易日志文件

# ==================== 安全检查 ====================
MAX_SLIPPAGE = 0.01  # 1%，最大滑点容忍度
ENABLE_SAFETY_CHECKS = True  # 是否启用安全检查

# ==================== 风控参数 ====================
LEVERAGE = 10  # 杠杆倍数
MARGIN_BUFFER = 1.1  # 保证金安全边际 (预留10%缓冲)
LIQUIDATION_WARNING_THRESHOLD = 2.5  # 清算预警阈值 (距离清算2.5%)
LIQUIDATION_EMERGENCY_THRESHOLD = 1.0  # 紧急平仓阈值 (距离清算1%)

# ==================== API 配置 ====================
# Hyperliquid API 配置从环境变量读取
# 需要在 .env 文件中配置:
# HYPERLIQUID_PRIVATE_KEY=your_private_key_here
