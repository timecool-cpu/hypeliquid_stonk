"""
价差收敛分析工具
分析 spread_history.csv 中的历史数据，评估价差收敛模式
"""
import pandas as pd
import sys
from datetime import datetime

def analyze_spread_convergence(csv_file='spread_history.csv'):
    """分析价差收敛情况"""
    
    try:
        df = pd.read_csv(csv_file)
    except FileNotFoundError:
        print(f"错误：找不到文件 {csv_file}")
        return
    except Exception as e:
        print(f"错误：读取文件失败 - {e}")
        return
    
    if len(df) == 0:
        print("没有历史数据")
        return
    
    print("=" * 80)
    print("TSLA 价差收敛分析报告".center(80))
    print("=" * 80)
    print()
    
    # 基本统计
    print("【数据概览】")
    print(f"  总记录数: {len(df)}")
    print(f"  时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")
    print()
    
    # 价差统计
    print("【价差统计】")
    print(f"  平均价差: {df['spread_abs'].mean():.4f} ({df['spread_pct'].mean():.4f}%)")
    print(f"  最小价差: {df['spread_abs'].min():.4f} ({df['spread_pct'].min():.4f}%)")
    print(f"  最大价差: {df['spread_abs'].max():.4f} ({df['spread_pct'].max():.4f}%)")
    print(f"  标准差: {df['spread_abs'].std():.4f} ({df['spread_pct'].std():.4f}%)")
    print()
    
    # 计算可交易价差（考虑实际买卖价）
    # FLX买->XYZ卖: xyz_bid - flx_ask
    df['spread_flx_to_xyz'] = df['xyz_bid'] - df['flx_ask']
    # XYZ买->FLX卖: flx_bid - xyz_ask
    df['spread_xyz_to_flx'] = df['flx_bid'] - df['xyz_ask']
    
    print("【可交易价差分析】")
    print("\n  方向1: FLX买入 -> XYZ卖出")
    print(f"    平均价差: {df['spread_flx_to_xyz'].mean():.4f}")
    print(f"    最大价差: {df['spread_flx_to_xyz'].max():.4f}")
    print(f"    最小价差: {df['spread_flx_to_xyz'].min():.4f}")
    positive_flx_to_xyz = (df['spread_flx_to_xyz'] > 0).sum()
    print(f"    正价差次数: {positive_flx_to_xyz} ({positive_flx_to_xyz/len(df)*100:.2f}%)")
    
    print("\n  方向2: XYZ买入 -> FLX卖出")
    print(f"    平均价差: {df['spread_xyz_to_flx'].mean():.4f}")
    print(f"    最大价差: {df['spread_xyz_to_flx'].max():.4f}")
    print(f"    最小价差: {df['spread_xyz_to_flx'].min():.4f}")
    positive_xyz_to_flx = (df['spread_xyz_to_flx'] > 0).sum()
    print(f"    正价差次数: {positive_xyz_to_flx} ({positive_xyz_to_flx/len(df)*100:.2f}%)")
    print()
    
    # 手续费成本分析
    taker_fee = 0.0005  # 0.05%
    print("【手续费成本分析】(Taker fee: 0.05%)")
    avg_price = (df['flx_mid'] + df['xyz_mid']).mean() / 2
    fee_cost_per_trade = avg_price * taker_fee * 2  # 买入和卖出都要手续费
    print(f"  平均价格: ${avg_price:.2f}")
    print(f"  单次往返手续费成本: ${fee_cost_per_trade:.4f} (约 {taker_fee*2*100:.2f}%)")
    print()
    
    # 计算扣除手续费后的净价差
    df['net_spread_flx_to_xyz'] = df['spread_flx_to_xyz'] - fee_cost_per_trade
    df['net_spread_xyz_to_flx'] = df['spread_xyz_to_flx'] - fee_cost_per_trade
    
    print("【扣除手续费后的净价差】")
    profitable_flx_to_xyz = (df['net_spread_flx_to_xyz'] > 0).sum()
    profitable_xyz_to_flx = (df['net_spread_xyz_to_flx'] > 0).sum()
    
    print(f"  FLX->XYZ 盈利机会: {profitable_flx_to_xyz} 次 ({profitable_flx_to_xyz/len(df)*100:.2f}%)")
    if profitable_flx_to_xyz > 0:
        print(f"    最大净利润: ${df['net_spread_flx_to_xyz'].max():.4f}")
        print(f"    平均净利润: ${df[df['net_spread_flx_to_xyz'] > 0]['net_spread_flx_to_xyz'].mean():.4f}")
    
    print(f"\n  XYZ->FLX 盈利机会: {profitable_xyz_to_flx} 次 ({profitable_xyz_to_flx/len(df)*100:.2f}%)")
    if profitable_xyz_to_flx > 0:
        print(f"    最大净利润: ${df['net_spread_xyz_to_flx'].max():.4f}")
        print(f"    平均净利润: ${df[df['net_spread_xyz_to_flx'] > 0]['net_spread_xyz_to_flx'].mean():.4f}")
    print()
    
    # 价差收敛分析
    print("【价差波动分析】")
    df['spread_change'] = df['spread_abs'].diff()
    df['spread_direction'] = df['spread_change'].apply(lambda x: 'expand' if x > 0 else ('contract' if x < 0 else 'stable'))
    
    expand_count = (df['spread_direction'] == 'expand').sum()
    contract_count = (df['spread_direction'] == 'contract').sum()
    
    print(f"  价差扩大次数: {expand_count} ({expand_count/len(df)*100:.2f}%)")
    print(f"  价差收窄次数: {contract_count} ({contract_count/len(df)*100:.2f}%)")
    print()
    
    # 最近的价差趋势（最后100条记录）
    if len(df) > 100:
        recent_df = df.tail(100)
        recent_trend = recent_df['spread_abs'].iloc[-1] - recent_df['spread_abs'].iloc[0]
        print("【最近趋势】(最后100条记录)")
        print(f"  起始价差: {recent_df['spread_abs'].iloc[0]:.4f}")
        print(f"  当前价差: {recent_df['spread_abs'].iloc[-1]:.4f}")
        print(f"  价差变化: {recent_trend:.4f} ({'扩大' if recent_trend > 0 else '收窄'})")
        print()
    
    # 结论和建议
    print("【结论与建议】")
    if profitable_flx_to_xyz + profitable_xyz_to_flx == 0:
        print("  ❌ 未发现盈利套利机会")
        print("  💡 建议：两个市场价格高度同步，价差小于手续费成本")
    else:
        total_opportunities = profitable_flx_to_xyz + profitable_xyz_to_flx
        opportunity_rate = total_opportunities / len(df) * 100
        print(f"  ✅ 发现 {total_opportunities} 次盈利机会 ({opportunity_rate:.2f}%)")
        
        if opportunity_rate < 5:
            print("  ⚠️  套利机会较少，可能不值得自动化交易")
        elif opportunity_rate < 20:
            print("  💡 套利机会适中，可以考虑自动化交易")
        else:
            print("  🚀 套利机会频繁，适合自动化交易")
    
    print()
    print("=" * 80)
    
    # 返回统计数据供进一步分析
    return {
        'total_records': len(df),
        'avg_spread': df['spread_abs'].mean(),
        'profitable_flx_to_xyz': profitable_flx_to_xyz,
        'profitable_xyz_to_flx': profitable_xyz_to_flx,
        'opportunity_rate': (profitable_flx_to_xyz + profitable_xyz_to_flx) / len(df) * 100
    }


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'spread_history.csv'
    analyze_spread_convergence(csv_file)
