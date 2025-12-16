#!/usr/bin/env python3
"""
检查两个市场的余额和持仓情况
包括主账户和 builder DEX 子账户
"""
import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from hyperliquid.info import Info
from eth_account import Account

def get_balance_info():
    """获取所有账户的余额和持仓信息"""
    
    private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY')
    if not private_key:
        print("❌ 未配置 HYPERLIQUID_PRIVATE_KEY")
        return None
    
    account = Account.from_key(private_key)
    wallet_address = account.address
    info = Info(skip_ws=True)
    
    print("=" * 70)
    print(f"钱包地址: {wallet_address}")
    print("=" * 70)
    
    result = {
        'wallet': wallet_address,
        'main': {},
        'flx': {},
        'xyz': {}
    }
    
    # 1. 获取主账户余额（Spot/Perps）
    print("\n【主账户余额】")
    try:
        # 获取现货余额
        spot_balances = info.spot_user_state(wallet_address)
        if spot_balances and 'balances' in spot_balances:
            print("  现货余额:")
            for balance in spot_balances['balances']:
                coin = balance.get('coin', '')
                total = float(balance.get('total', 0))
                hold = float(balance.get('hold', 0))
                if total > 0:
                    print(f"    {coin}: {total:.6f} (锁定: {hold:.6f})")
        
        # 获取永续合约账户状态（主DEX）
        perp_state = info.user_state(wallet_address)
        if perp_state:
            margin_summary = perp_state.get('marginSummary', {})
            account_value = float(margin_summary.get('accountValue', 0))
            total_margin_used = float(margin_summary.get('totalMarginUsed', 0))
            withdrawable = float(perp_state.get('withdrawable', 0))
            
            print(f"\n  永续账户价值: ${account_value:.2f}")
            print(f"  已用保证金: ${total_margin_used:.2f}")
            print(f"  可提取: ${withdrawable:.2f}")
            
            result['main'] = {
                'account_value': account_value,
                'margin_used': total_margin_used,
                'withdrawable': withdrawable
            }
    except Exception as e:
        print(f"  获取主账户失败: {e}")
    
    # 2. 获取所有 perp DEX 列表
    print("\n【Builder DEX 列表】")
    try:
        perp_dexs = info.perp_dexs()
        print(f"  发现 {len(perp_dexs)} 个 DEX:")
        for i, dex in enumerate(perp_dexs):
            if dex:
                name = dex.get('name', f'DEX_{i}')
                print(f"    - {name}")
    except Exception as e:
        print(f"  获取DEX列表失败: {e}")
    
    # 3. 获取 FLX DEX 状态
    print("\n【FLX DEX】")
    try:
        flx_state = info.user_state(wallet_address, 'flx')
        result['flx'] = parse_dex_state(flx_state, 'FLX')
    except Exception as e:
        print(f"  获取失败: {e}")
    
    # 4. 获取 XYZ DEX 状态
    print("\n【XYZ DEX】")
    try:
        xyz_state = info.user_state(wallet_address, 'xyz')
        result['xyz'] = parse_dex_state(xyz_state, 'XYZ')
    except Exception as e:
        print(f"  获取失败: {e}")
    
    # 5. 尝试获取清算信息
    print("\n【清算风险检查】")
    try:
        # 检查 FLX
        if result['flx'].get('positions'):
            flx_leverage = result['flx'].get('leverage', 0)
            print(f"  FLX 杠杆率: {flx_leverage:.2f}x", end='')
            if flx_leverage > 8:
                print(" ⚠️ 高风险")
            elif flx_leverage > 5:
                print(" ⚡ 中等风险")
            else:
                print(" ✅ 安全")
        
        # 检查 XYZ
        if result['xyz'].get('positions'):
            xyz_leverage = result['xyz'].get('leverage', 0)
            print(f"  XYZ 杠杆率: {xyz_leverage:.2f}x", end='')
            if xyz_leverage > 8:
                print(" ⚠️ 高风险")
            elif xyz_leverage > 5:
                print(" ⚡ 中等风险")
            else:
                print(" ✅ 安全")
    except Exception as e:
        print(f"  检查失败: {e}")
    
    # 6. 汇总
    print("\n" + "=" * 70)
    print("【汇总】")
    print("=" * 70)
    
    flx_value = result['flx'].get('account_value', 0)
    xyz_value = result['xyz'].get('account_value', 0)
    main_value = result['main'].get('account_value', 0)
    
    total_value = flx_value + xyz_value + main_value
    total_margin_used = result['flx'].get('margin_used', 0) + result['xyz'].get('margin_used', 0)
    total_position = result['flx'].get('position_value', 0) + result['xyz'].get('position_value', 0)
    
    print(f"  主账户价值: ${main_value:.2f}")
    print(f"  FLX 账户价值: ${flx_value:.2f}")
    print(f"  XYZ 账户价值: ${xyz_value:.2f}")
    print(f"  总账户价值: ${total_value:.2f}")
    print(f"  总已用保证金: ${total_margin_used:.2f}")
    print(f"  总持仓价值: ${total_position:.2f}")
    
    if total_value > 0 and total_position > 0:
        overall_leverage = total_position / total_value
        print(f"  综合杠杆率: {overall_leverage:.2f}x")
    
    return result


def parse_dex_state(state, dex_name):
    """解析 DEX 状态"""
    result = {
        'account_value': 0,
        'margin_used': 0,
        'position_value': 0,
        'withdrawable': 0,
        'available_margin': 0,
        'leverage': 0,
        'positions': []
    }
    
    if not state:
        print("  无法获取状态（可能未在此DEX开户）")
        return result
    
    # 账户余额
    margin_summary = state.get('marginSummary', {})
    account_value = float(margin_summary.get('accountValue', 0))
    total_margin_used = float(margin_summary.get('totalMarginUsed', 0))
    total_ntl_pos = float(margin_summary.get('totalNtlPos', 0))
    withdrawable = float(state.get('withdrawable', 0))
    
    print(f"  账户价值: ${account_value:.2f}")
    print(f"  已用保证金: ${total_margin_used:.2f}")
    print(f"  持仓名义价值: ${total_ntl_pos:.2f}")
    print(f"  可提取余额: ${withdrawable:.2f}")
    
    # 计算可用保证金
    available_margin = account_value - total_margin_used
    print(f"  可用保证金: ${available_margin:.2f}")
    
    # 计算杠杆率
    leverage = 0
    if account_value > 0:
        leverage = total_ntl_pos / account_value
        print(f"  当前杠杆率: {leverage:.2f}x")
    
    result.update({
        'account_value': account_value,
        'margin_used': total_margin_used,
        'position_value': total_ntl_pos,
        'withdrawable': withdrawable,
        'available_margin': available_margin,
        'leverage': leverage
    })
    
    # 持仓详情
    positions = state.get('assetPositions', [])
    if positions:
        print("\n  持仓详情:")
        for pos in positions:
            details = pos.get('position', {})
            coin = details.get('coin', '')
            szi = float(details.get('szi', 0))
            if szi == 0:
                continue
            
            entry_px = float(details.get('entryPx', 0))
            unrealized_pnl = float(details.get('unrealizedPnl', 0))
            margin_used = float(details.get('marginUsed', 0))
            liquidation_px = details.get('liquidationPx')
            leverage = float(details.get('leverage', {}).get('value', 0))
            
            side = 'LONG' if szi > 0 else 'SHORT'
            position_value = abs(szi) * entry_px
            
            print(f"    {coin}: {side} {abs(szi):.4f} @ ${entry_px:.2f}")
            print(f"      持仓价值: ${position_value:.2f}")
            print(f"      未实现盈亏: ${unrealized_pnl:.4f}")
            print(f"      占用保证金: ${margin_used:.2f}")
            print(f"      杠杆: {leverage:.1f}x")
            if liquidation_px:
                liq_px = float(liquidation_px)
                # 计算距离强平的百分比
                if side == 'LONG':
                    liq_distance = (entry_px - liq_px) / entry_px * 100
                else:
                    liq_distance = (liq_px - entry_px) / entry_px * 100
                print(f"      强平价格: ${liq_px:.2f} (距离 {liq_distance:.1f}%)")
            
            result['positions'].append({
                'coin': coin,
                'side': side,
                'size': abs(szi),
                'entry_px': entry_px,
                'unrealized_pnl': unrealized_pnl,
                'margin_used': margin_used,
                'liquidation_px': float(liquidation_px) if liquidation_px else None,
                'leverage': leverage
            })
    else:
        print("\n  无持仓")
    
    return result


if __name__ == "__main__":
    get_balance_info()
