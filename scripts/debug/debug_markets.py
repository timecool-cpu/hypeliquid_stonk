"""
测试脚本：获取现货市场信息
"""
from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.MAINNET_API_URL, skip_ws=True)

# 获取现货市场的元数据
try:
    spot_meta = info.spot_meta()
    print("=== Hyperliquid 现货市场 ===\n")
    
    if 'tokens' in spot_meta:
        print(f"总共有 {len(spot_meta['tokens'])} 个代币\n")
        
        # 查找 TSLA 相关市场
        print("=== 查找 TSLA 相关现货市场 ===\n")
        for idx, token in enumerate(spot_meta['tokens']):
            if 'TSLA' in token['name'].upper():
                print(f"Index: {idx}")
                print(f"Token: {token}")
                print()
    
    if 'universe' in spot_meta:
        print(f"\n总共有 {len(spot_meta['universe'])} 个现货市场\n")
        
        # 查找 TSLA 相关市场对
        print("=== 查找 TSLA 相关交易对 ===\n")
        for idx, market in enumerate(spot_meta['universe']):
            if 'TSLA' in market['name'].upper():
                print(f"Index: {idx}")
                print(f"Market: {market}")
                print()
        
        # 显示一些示例市场名称
        print("\n=== 前10个市场示例 ===\n")
        for idx, market in enumerate(spot_meta['universe'][:10]):
            print(f"{idx}: {market['name']}")

except Exception as e:
    print(f"获取现货市场失败: {e}")

# 尝试获取所有中间价
try:
    print("\n\n=== 尝试获取所有中间价 (allMids) ===\n")
    mids = info.all_mids()
    
    # 查找 TSLA 相关价格
    tsla_mids = {k: v for k, v in mids.items() if 'TSLA' in k.upper()}
    if tsla_mids:
        print("找到 TSLA 相关价格:")
        for name, price in tsla_mids.items():
            print(f"  {name}: {price}")
    else:
        print("未找到 TSLA 相关价格")
        print("\n一些示例价格:")
        for idx, (name, price) in enumerate(list(mids.items())[:20]):
            print(f"  {name}: {price}")
            if idx >= 19:
                break

except Exception as e:
    print(f"获取中间价失败: {e}")
