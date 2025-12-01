"""
Hyperliquid TSLA 套利监控系统配置
"""

# API 配置
HYPERLIQUID_API_URL = "https://api.hyperliquid.xyz"

# 监控的资产对
# HIP-3 builder-deployed 永续合约使用 {dex}:{coin} 格式
ASSET_PAIR_1 = "xyz:TSLA"  # xyz 平台的 TSLA
ASSET_PAIR_2 = "flx:TSLA"  # flx (Felix) 平台的 TSLA


# 监控参数
REFRESH_INTERVAL = 2  # 秒，价格刷新间隔
SPREAD_THRESHOLD = 0.1  # 百分比，触发套利提醒的最小价差

# 显示参数
SHOW_ORDERBOOK_DEPTH = 5  # 显示订单簿的档位数
DECIMAL_PLACES = 4  # 价格显示的小数位数

# 手续费配置（TSLA标的实际费率 - 有减免）
MAKER_FEE = 0.000081  # 0.0081% maker fee
TAKER_FEE = 0.00003   # 0.0030% taker fee

# 日志配置
LOG_FILE = "spread_history.csv"
ENABLE_LOGGING = True

# 交易参数（可选，仅在启用交易时使用）
DEFAULT_POSITION_SIZE = 100  # USDC
MAX_POSITION_SIZE = 1000  # USDC
STOP_LOSS_PERCENTAGE = 2.0  # 止损百分比
