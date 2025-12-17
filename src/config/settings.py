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
    
    # 手续费配置（HIP-3 TSLA 实际费率）
    TAKER_FEE = 0.000086  # 0.0086%
    MAKER_FEE = 0.000029  # 0.0029%
    
    # 交易对配置
    FLX_SYMBOL = 'TSLA'  # Hyperliquid上的TSLA永续合约
    XYZ_SYMBOL = 'TSLA'  # 另一个交易所的TSLA
    
    # HIP-3 资产对配置
    ASSET_PAIR_1 = "xyz:TSLA"  # xyz 平台的 TSLA
    ASSET_PAIR_2 = "flx:TSLA"  # flx (Felix) 平台的 TSLA


# 创建配置实例
config = Config()
