"""
交易系统配置
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """基础配置"""
    # API配置
    HYPERLIQUID_PRIVATE_KEY = os.getenv('HYPERLIQUID_PRIVATE_KEY', '')
    
    # 手续费配置
    TAKER_FEE = 0.0005  # 0.05%
    MAKER_FEE = 0.0002  # 0.02%
    
    # 交易对配置
    FLX_SYMBOL = 'TSLA'  # Hyperliquid上的TSLA永续合约
    XYZ_SYMBOL = 'TSLA'  # 另一个交易所的TSLA
    
    # HIP-3 资产对配置
    ASSET_PAIR_1 = "xyz:TSLA"  # xyz 平台的 TSLA
    ASSET_PAIR_2 = "flx:TSLA"  # flx (Felix) 平台的 TSLA


class ArbitrageConfig:
    """套利策略配置"""
    # 运行模式
    DRY_RUN = True  # True=模拟模式，False=实盘模式
    
    # 仓位配置
    INITIAL_POSITION_SIZE = 100  # 初始仓位大小（USD）
    ALLOW_POSITION_STACKING = False  # 是否允许叠加仓位
    
    # 利润阈值
    MIN_NET_PROFIT = 0.10  # 最小净利润阈值（USD）
    TAKE_PROFIT_TARGET = 0.20  # 止盈目标（USD）
    
    # 价差反转配置
    REVERSAL_MIN_SPREAD = 0.15  # 反转最小价差
    REVERSAL_MIN_SPREAD_FLX_TO_XYZ = 0.15  # FLX→XYZ方向反转阈值
    REVERSAL_MIN_SPREAD_XYZ_TO_FLX = 0.10  # XYZ→FLX方向反转阈值
    
    # 监控配置
    MONITOR_INTERVAL = 1  # 监控间隔（秒）
    SPREAD_STABILITY_CHECKS = 3  # 价差稳定性检查次数
    
    # 超时配置
    POSITION_TIMEOUT_HOURS = 24  # 持仓超时时间（小时）
    
    # 日志配置
    LOG_TRADES = True  # 是否记录交易日志
    TRADE_LOG_FILE = 'trade_log.csv'  # 交易日志文件


# 创建配置实例
config = Config()
arbitrage_config = ArbitrageConfig()
