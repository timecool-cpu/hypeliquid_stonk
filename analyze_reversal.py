"""
价差反转与收敛分析
检查价差是否会反转，以及持仓风险
"""
import pandas as pd
import sys

def analyze_spread_reversal(csv_file='spread_history.csv'):
    """分析价差反转情况"""
    
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"错误：{e}")
        return
    
    if len(df) < 100:
        print("数据量太少，无法分析")
        return
    
    print("=" * 80)
    print("价差反转与收敛分析".center(80))
    print("=" * 80)
    print()
    
    # 计算可执行价差
    df['exec_flx_to_xyz'] = df['xyz_bid'] - df['flx_ask']
    df['exec_xyz_to_flx'] = df['flx_bid'] - df['xyz_ask']
    
    # 判断哪个方向有优势
    df['best_direction'] = df.apply(
        lambda row: 'FLX->XYZ' if row['exec_flx_to_xyz'] > row['exec_xyz_to_flx'] else 'XYZ->FLX',
        axis=1
    )
    
    # 统计方向分布
    direction_counts = df['best_direction'].value_counts()
    
    print("【价差方向分布】")
    print(f"  FLX->XYZ 优势: {direction_counts.get('FLX->XYZ', 0)} 次 ({direction_counts.get('FLX->XYZ', 0)/len(df)*100:.2f}%)")
    print(f"  XYZ->FLX 优势: {direction_counts.get('XYZ->FLX', 0)} 次 ({direction_counts.get('XYZ->FLX', 0)/len(df)*100:.2f}%)")
    print()
    
    # 检测方向切换
    df['direction_change'] = (df['best_direction'] != df['best_direction'].shift(1))
    direction_changes = df['direction_change'].sum()
    
    print("【价差反转分析】")
    print(f"  方向切换次数: {direction_changes}")
    print(f"  平均每次切换间隔: {len(df) / (direction_changes or 1):.1f} 条记录 "
          f"(约 {len(df) / (direction_changes or 1) * 2:.1f} 秒)")
    print()
    
    # 分析连续同方向的持续时间
    df['direction_group'] = (df['best_direction'] != df['best_direction'].shift(1)).cumsum()
    direction_durations = df.groupby('direction_group').size()
    
    print("【单向持续时间统计】")
    print(f"  最短持续: {direction_durations.min()} 条记录 (约 {direction_durations.min() * 2} 秒)")
    print(f"  最长持续: {direction_durations.max()} 条记录 (约 {direction_durations.max() * 2 / 60:.1f} 分钟)")
    print(f"  平均持续: {direction_durations.mean():.1f} 条记录 (约 {direction_durations.mean() * 2 / 60:.1f} 分钟)")
    print()
    
    # 分析FLX->XYZ方向的价差变化
    flx_to_xyz_groups = df[df['best_direction'] == 'FLX->XYZ'].groupby('direction_group')
    
    if len(flx_to_xyz_groups) > 0:
        print("【FLX->XYZ 方向价差演变】")
        
        convergence_count = 0
        divergence_count = 0
        
        for group_id, group_data in flx_to_xyz_groups:
            if len(group_data) < 5:  # 太短的序列跳过
                continue
            
            start_spread = group_data.iloc[0]['exec_flx_to_xyz']
            end_spread = group_data.iloc[-1]['exec_flx_to_xyz']
            
            if end_spread < start_spread:
                convergence_count += 1
            else:
                divergence_count += 1
        
        total_analyzed = convergence_count + divergence_count
        if total_analyzed > 0:
            print(f"  价差收窄（好）: {convergence_count} 次 ({convergence_count/total_analyzed*100:.1f}%)")
            print(f"  价差扩大（坏）: {divergence_count} 次 ({divergence_count/total_analyzed*100:.1f}%)")
        print()
    
    # 关键风险分析
    print("【持仓风险评估】")
    
    # 检查最长的FLX->XYZ优势期
    flx_dominance = df[df['best_direction'] == 'FLX->XYZ'].groupby('direction_group').size()
    if len(flx_dominance) > 0:
        max_flx_duration = flx_dominance.max()
        max_duration_minutes = max_flx_duration * 2 / 60
        
        print(f"  最长FLX->XYZ优势期: {max_flx_duration} 条记录 (约 {max_duration_minutes:.1f} 分钟)")
        
        if max_duration_minutes > 30:
            print(f"  ⚠️  警告：存在超过30分钟的单向价差期，持仓风险较高！")
        elif max_duration_minutes > 10:
            print(f"  ⚠️  注意：存在超过10分钟的单向价差期")
        else:
            print(f"  ✓ 价差反转较频繁，风险相对可控")
    
    print()
    
    # 计算如果持有仓位的P&L模拟
    print("【仓位P&L模拟】假设在有盈利机会时开仓")
    
    fee_cost = df['flx_mid'].mean() * 0.001  # 0.1% 双边手续费
    
    # 找到所有盈利机会
    profitable = df[df['exec_flx_to_xyz'] > fee_cost].copy()
    
    if len(profitable) > 0:
        print(f"  盈利机会数: {len(profitable)}")
        
        # 模拟：如果在每个盈利机会开仓，然后持有到价差反转
        total_pnl = 0
        open_positions = []
        
        for idx, row in df.iterrows():
            current_spread = row['exec_flx_to_xyz']
            
            # 如果当前有盈利机会，开仓
            if current_spread > fee_cost and not open_positions:
                open_positions.append({
                    'entry_spread': current_spread,
                    'entry_time': idx
                })
            
            # 如果持有仓位，且价差反转了（变负或接近0）
            elif open_positions and current_spread < 0:
                for pos in open_positions:
                    pnl = current_spread - pos['entry_spread']
                    total_pnl += pnl
                    hold_duration = idx - pos['entry_time']
                    
                    if len(open_positions) <= 5:  # 只打印前几个
                        print(f"    平仓 #{len(open_positions)}: "
                              f"入场{pos['entry_spread']:.3f} -> 出场{current_spread:.3f}, "
                              f"P&L=${pnl:.3f}, 持有{hold_duration}条记录")
                
                open_positions = []
        
        if len(open_positions) > 0:
            print(f"\n  ⚠️  警告：还有 {len(open_positions)} 个仓位未平仓（价差未反转）")
    
    print()
    print("【结论】")
    
    reversal_rate = direction_changes / len(df) * 100
    
    if reversal_rate < 0.1:
        print("  ❌ 价差几乎不反转，单向套利风险极高！")
        print("  💡 建议：此策略不适合，因为无法平仓")
    elif reversal_rate < 1:
        print("  ⚠️  价差反转较少，风险较高")
        print("  💡 建议：只在价差很大时开仓，并设置严格止损")
    else:
        print("  ✓ 价差有一定反转性，可以考虑交易")
        print("  💡 建议：设置最大持仓时间限制（如30分钟强制平仓）")
    
    print()
    print("=" * 80)


if __name__ == "__main__":
    csv_file = sys.argv[1] if len(sys.argv) > 1 else 'spread_history.csv'
    analyze_spread_reversal(csv_file)
