"""
基于历史数据分析最优套利策略
重点分析：手续费优化、平仓时机、加仓策略
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def analyze_exit_strategies(csv_file='spread_history.csv'):
    """分析不同平仓策略的效果"""
    
    df = pd.read_csv(csv_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print("=" * 100)
    print("平仓策略优化分析".center(100))
    print("=" * 100)
    print()
    
    # 确定最优方向
    df['best_direction'] = df.apply(
        lambda row: 'FLX→XYZ' if row['exec_spread_flx_to_xyz'] > row['exec_spread_xyz_to_flx'] else 'XYZ→FLX',
        axis=1
    )
    df['best_spread'] = df.apply(
        lambda row: row['exec_spread_flx_to_xyz'] if row['best_direction'] == 'FLX→XYZ' else row['exec_spread_xyz_to_flx'],
        axis=1
    )
    
    # 分析手续费结构
    print("【手续费优化分析】")
    print()
    
    MAKER_FEE = 0.0002  # 0.02%
    TAKER_FEE = 0.0005  # 0.05%
    avg_price = (df['flx_mid'] + df['xyz_mid']).mean() / 2
    
    # 场景1: 全部使用Taker（快速成交）
    taker_open_fee = avg_price * TAKER_FEE * 2  # 开仓2笔
    taker_close_fee = avg_price * TAKER_FEE * 2  # 平仓2笔
    total_taker_fee = taker_open_fee + taker_close_fee
    
    # 场景2: 开仓使用Maker挂单，平仓使用Taker
    maker_open_fee = avg_price * MAKER_FEE * 2  # 开仓挂单
    taker_close_fee = avg_price * TAKER_FEE * 2  # 平仓吃单
    total_mixed_fee = maker_open_fee + taker_close_fee
    
    # 场景3: 只计算开仓费用（如果平仓时价差反转，手续费可由反向价差覆盖）
    only_open_fee = avg_price * TAKER_FEE * 2  # 仅开仓
    
    print(f"平均价格: ${avg_price:.2f}")
    print()
    print(f"场景1 - 全部Taker (开仓2笔 + 平仓2笔):")
    print(f"  开仓手续费: ${taker_open_fee:.4f}")
    print(f"  平仓手续费: ${taker_close_fee:.4f}")
    print(f"  总计: ${total_taker_fee:.4f}")
    print()
    print(f"场景2 - 混合模式 (开仓Maker挂单 + 平仓Taker):")
    print(f"  开仓手续费: ${maker_open_fee:.4f}")
    print(f"  平仓手续费: ${taker_close_fee:.4f}")
    print(f"  总计: ${total_mixed_fee:.4f}")
    print(f"  节省: ${total_taker_fee - total_mixed_fee:.4f} ({(total_taker_fee - total_mixed_fee)/total_taker_fee*100:.1f}%)")
    print()
    print(f"场景3 - 仅计算开仓 (假设平仓时价差反转):")
    print(f"  开仓手续费: ${only_open_fee:.4f}")
    print(f"  节省: ${total_taker_fee - only_open_fee:.4f} ({(total_taker_fee - only_open_fee)/total_taker_fee*100:.1f}%)")
    print()
    
    # 分析平仓时的价差情况
    print("【平仓时机分析】")
    print()
    
    # 模拟持仓场景：找到所有盈利机会点
    profitable_opportunities = df[
        (df['net_profit_flx_to_xyz'] > 0) | (df['net_profit_xyz_to_flx'] > 0)
    ].copy()
    
    print(f"总盈利机会: {len(profitable_opportunities)} 次")
    print()
    
    # 分析如果在这些点开仓，后续价差如何变化
    hold_durations = [5, 10, 15, 20, 30]  # 分钟
    sampling_interval = 2.3  # 秒/条记录
    
    for hold_minutes in hold_durations:
        hold_records = int(hold_minutes * 60 / sampling_interval)
        
        successful_exits = 0
        total_profit = 0
        reversal_exits = 0
        timeout_exits = 0
        
        for idx in profitable_opportunities.index:
            if idx + hold_records >= len(df):
                continue
            
            entry_direction = profitable_opportunities.loc[idx, 'best_direction']
            entry_spread = profitable_opportunities.loc[idx, 'best_spread']
            
            # 检查持仓期间的价差变化
            future_slice = df.iloc[idx:idx+hold_records+1]
            
            # 寻找平仓机会：价差反转或收敛
            exit_found = False
            exit_profit = 0
            
            for future_idx in range(1, len(future_slice)):
                future_row = future_slice.iloc[future_idx]
                
                # 检查价差是否反转（原来最优方向变成不利）
                if entry_direction == 'FLX→XYZ':
                    # 原来FLX买XYZ卖更优，现在检查是否反转为XYZ买FLX卖更优
                    current_flx_spread = future_row['exec_spread_flx_to_xyz']
                    current_xyz_spread = future_row['exec_spread_xyz_to_flx']
                    
                    # 反转：XYZ→FLX方向价差更大，且为正
                    if current_xyz_spread > current_flx_spread and current_xyz_spread > 0:
                        # 平仓可以获得反向价差
                        exit_profit = current_xyz_spread - only_open_fee  # 只需扣除开仓费
                        reversal_exits += 1
                        exit_found = True
                        break
                else:
                    # 原来XYZ买FLX卖更优
                    current_flx_spread = future_row['exec_spread_flx_to_xyz']
                    current_xyz_spread = future_row['exec_spread_xyz_to_flx']
                    
                    if current_flx_spread > current_xyz_spread and current_flx_spread > 0:
                        exit_profit = current_flx_spread - only_open_fee
                        reversal_exits += 1
                        exit_found = True
                        break
            
            if exit_found:
                successful_exits += 1
                total_profit += exit_profit
            else:
                timeout_exits += 1
        
        if successful_exits > 0:
            print(f"持仓 {hold_minutes} 分钟:")
            print(f"  成功反向平仓: {successful_exits} 次 ({successful_exits/len(profitable_opportunities)*100:.1f}%)")
            print(f"  超时未平仓: {timeout_exits} 次")
            print(f"  平均利润: ${total_profit/successful_exits:.4f}")
            print()
    
    # 分析加仓策略
    print("【加仓策略分析】")
    print()
    
    # 找到连续价差扩大的情况
    df['spread_increasing'] = df['best_spread'].diff() > 0.05  # 价差增加超过0.05
    
    consecutive_increases = 0
    max_consecutive = 0
    current_streak = 0
    
    for increasing in df['spread_increasing']:
        if increasing:
            current_streak += 1
            max_consecutive = max(max_consecutive, current_streak)
        else:
            if current_streak > 0:
                consecutive_increases += 1
            current_streak = 0
    
    print(f"价差连续扩大事件: {consecutive_increases} 次")
    print(f"最长连续扩大: {max_consecutive} 条记录 (~{max_consecutive * 2.3 / 60:.1f} 分钟)")
    print()
    
    # 分析价差扩大时加仓的潜在收益
    # 简单模拟：如果价差增加>0.1，加仓一次
    df['add_position_signal'] = (df['best_spread'].diff() > 0.1) & (df['best_spread'] > 0.3)
    add_position_opportunities = df['add_position_signal'].sum()
    
    print(f"潜在加仓机会（价差增加>$0.1 且总价差>$0.3）: {add_position_opportunities} 次")
    if add_position_opportunities > 0:
        avg_spread_at_add = df[df['add_position_signal']]['best_spread'].mean()
        print(f"加仓时平均价差: ${avg_spread_at_add:.4f}")
        print()
        print("💡 建议: 价差扩大时可以考虑加仓以扩大收益")
    else:
        print("💡 建议: 价差波动较小，单仓位即可")
    print()
    
    # 总结建议
    print("=" * 100)
    print("【优化建议总结】")
    print("=" * 100)
    print()
    
    print("1️⃣  手续费优化:")
    print(f"   • 推荐使用混合模式（开仓Maker + 平仓Taker）")
    print(f"   • 可节省约 {(total_taker_fee - total_mixed_fee)/total_taker_fee*100:.1f}% 手续费")
    print(f"   • 如果平仓时价差反转，实际只需承担开仓费用")
    print(f"   • 开仓净成本: ${only_open_fee:.4f} (vs 全Taker ${total_taker_fee:.4f})")
    print()
    
    print("2️⃣  平仓策略:")
    print(f"   • 优先等待价差反转平仓（可获得反向价差收益）")
    print(f"   • 建议持仓时长: 10-20分钟（反转概率较高）")
    print(f"   • 超时未反转时使用Taker强制平仓")
    print()
    
    print("3️⃣  仓位管理:")
    if add_position_opportunities > 50:
        print(f"   • 价差扩大机会较多，建议支持多仓位")
        print(f"   • 单次加仓条件: 价差增加>$0.1 且总价差>$0.3")
        print(f"   • 最大仓位: 3-5 个")
    else:
        print(f"   • 价差扩大机会较少，单仓位即可")
        print(f"   • 可选: 价差>$0.5 时考虑小幅加仓")
    print()
    
    print("=" * 100)

if __name__ == "__main__":
    analyze_exit_strategies()
