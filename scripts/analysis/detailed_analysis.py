"""
详细套利数据分析
生成价格走势、收敛模式、反转情况的综合报告
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def analyze_data(csv_file='spread_history.csv'):
    """综合分析套利数据"""
    
    df = pd.read_csv(csv_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print("=" * 100)
    print("TSLA FLX vs XYZ 套利数据综合分析".center(100))
    print("=" * 100)
    print()
    
    # ==================== 基本信息 ====================
    print("【数据基本信息】")
    print(f"  📊 总记录数: {len(df):,} 条")
    print(f"  📅 开始时间: {df['timestamp'].iloc[0]}")
    print(f"  📅 结束时间: {df['timestamp'].iloc[-1]}")
    duration = df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]
    duration_hours = duration.total_seconds() / 3600
    print(f"  ⏱️  数据时长: {duration_hours:.1f} 小时 ({duration_hours/24:.1f} 天)")
    print()
    
    # ==================== 价格走势分析 ====================
    print("【价格走势分析】")
    
    # FLX市场
    flx_start = df['flx_mid'].iloc[0]
    flx_end = df['flx_mid'].iloc[-1]
    flx_change = flx_end - flx_start
    flx_change_pct = (flx_change / flx_start) * 100
    flx_high = df['flx_mid'].max()
    flx_low = df['flx_mid'].min()
    flx_volatility = ((flx_high - flx_low) / flx_start) * 100
    
    print(f"\n  🔷 FLX 市场:")
    print(f"     起始价格: ${flx_start:.2f}")
    print(f"     当前价格: ${flx_end:.2f}")
    print(f"     价格变化: ${flx_change:+.2f} ({flx_change_pct:+.2f}%)")
    print(f"     最高价格: ${flx_high:.2f}")
    print(f"     最低价格: ${flx_low:.2f}")
    print(f"     波动幅度: {flx_volatility:.2f}%")
    
    # XYZ市场
    xyz_start = df['xyz_mid'].iloc[0]
    xyz_end = df['xyz_mid'].iloc[-1]
    xyz_change = xyz_end - xyz_start
    xyz_change_pct = (xyz_change / xyz_start) * 100
    xyz_high = df['xyz_mid'].max()
    xyz_low = df['xyz_mid'].min()
    xyz_volatility = ((xyz_high - xyz_low) / xyz_start) * 100
    
    print(f"\n  🔶 XYZ 市场:")
    print(f"     起始价格: ${xyz_start:.2f}")
    print(f"     当前价格: ${xyz_end:.2f}")
    print(f"     价格变化: ${xyz_change:+.2f} ({xyz_change_pct:+.2f}%)")
    print(f"     最高价格: ${xyz_high:.2f}")
    print(f"     最低价格: ${xyz_low:.2f}")
    print(f"     波动幅度: {xyz_volatility:.2f}%")
    
    # 价格相关性
    correlation = df['flx_mid'].corr(df['xyz_mid'])
    print(f"\n  📊 价格相关性: {correlation:.4f}")
    if correlation > 0.99:
        print(f"     ✅ 极强正相关 - 两市场高度同步")
    elif correlation > 0.95:
        print(f"     ✅ 强正相关 - 两市场同步良好")
    else:
        print(f"     ⚠️  相关性一般 - 存在价格分化")
    print()
    
    # ==================== 价差详细分析 ====================
    print("【价差详细分析】")
    
    # 绝对价差统计
    spread_mean = df['spread_abs'].mean()
    spread_median = df['spread_abs'].median()
    spread_std = df['spread_abs'].std()
    spread_max = df['spread_abs'].max()
    spread_min = df['spread_abs'].min()
    
    print(f"\n  绝对价差 (|XYZ - FLX|):")
    print(f"     平均值: ${spread_mean:.4f}")
    print(f"     中位数: ${spread_median:.4f}")
    print(f"     标准差: ${spread_std:.4f}")
    print(f"     最大值: ${spread_max:.4f}")
    print(f"     最小值: ${spread_min:.4f}")
    
    # 可执行价差统计
    print(f"\n  可执行价差 (考虑买卖价):")
    print(f"\n     方向1: FLX买 → XYZ卖 (xyz_bid - flx_ask)")
    flx_to_xyz_mean = df['exec_spread_flx_to_xyz'].mean()
    flx_to_xyz_positive = (df['exec_spread_flx_to_xyz'] > 0).sum()
    flx_to_xyz_positive_pct = (flx_to_xyz_positive / len(df)) * 100
    print(f"        平均价差: ${flx_to_xyz_mean:.4f}")
    print(f"        正价差: {flx_to_xyz_positive:,} 次 ({flx_to_xyz_positive_pct:.2f}%)")
    if flx_to_xyz_positive > 0:
        flx_to_xyz_max = df[df['exec_spread_flx_to_xyz'] > 0]['exec_spread_flx_to_xyz'].max()
        flx_to_xyz_avg = df[df['exec_spread_flx_to_xyz'] > 0]['exec_spread_flx_to_xyz'].mean()
        print(f"        最大正价差: ${flx_to_xyz_max:.4f}")
        print(f"        平均正价差: ${flx_to_xyz_avg:.4f}")
    
    print(f"\n     方向2: XYZ买 → FLX卖 (flx_bid - xyz_ask)")
    xyz_to_flx_mean = df['exec_spread_xyz_to_flx'].mean()
    xyz_to_flx_positive = (df['exec_spread_xyz_to_flx'] > 0).sum()
    xyz_to_flx_positive_pct = (xyz_to_flx_positive / len(df)) * 100
    print(f"        平均价差: ${xyz_to_flx_mean:.4f}")
    print(f"        正价差: {xyz_to_flx_positive:,} 次 ({xyz_to_flx_positive_pct:.2f}%)")
    if xyz_to_flx_positive > 0:
        xyz_to_flx_max = df[df['exec_spread_xyz_to_flx'] > 0]['exec_spread_xyz_to_flx'].max()
        xyz_to_flx_avg = df[df['exec_spread_xyz_to_flx'] > 0]['exec_spread_xyz_to_flx'].mean()
        print(f"        最大正价差: ${xyz_to_flx_max:.4f}")
        print(f"        平均正价差: ${xyz_to_flx_avg:.4f}")
    print()
    
    # ==================== 盈利机会分析 ====================
    print("【盈利机会分析】(扣除手续费后)")
    
    profitable_flx_to_xyz = (df['net_profit_flx_to_xyz'] > 0).sum()
    profitable_xyz_to_flx = (df['net_profit_xyz_to_flx'] > 0).sum()
    total_profitable = profitable_flx_to_xyz + profitable_xyz_to_flx
    profitable_pct = (total_profitable / len(df)) * 100
    
    print(f"\n  总盈利机会: {total_profitable:,} 次 ({profitable_pct:.2f}%)")
    print(f"     FLX→XYZ: {profitable_flx_to_xyz:,} 次 ({profitable_flx_to_xyz/len(df)*100:.2f}%)")
    print(f"     XYZ→FLX: {profitable_xyz_to_flx:,} 次 ({profitable_xyz_to_flx/len(df)*100:.2f}%)")
    
    if profitable_flx_to_xyz > 0:
        max_profit_flx = df['net_profit_flx_to_xyz'].max()
        avg_profit_flx = df[df['net_profit_flx_to_xyz'] > 0]['net_profit_flx_to_xyz'].mean()
        median_profit_flx = df[df['net_profit_flx_to_xyz'] > 0]['net_profit_flx_to_xyz'].median()
        print(f"\n  FLX→XYZ 盈利统计:")
        print(f"     最大利润: ${max_profit_flx:.4f}")
        print(f"     平均利润: ${avg_profit_flx:.4f}")
        print(f"     中位利润: ${median_profit_flx:.4f}")
    
    if profitable_xyz_to_flx > 0:
        max_profit_xyz = df['net_profit_xyz_to_flx'].max()
        avg_profit_xyz = df[df['net_profit_xyz_to_flx'] > 0]['net_profit_xyz_to_flx'].mean()
        median_profit_xyz = df[df['net_profit_xyz_to_flx'] > 0]['net_profit_xyz_to_flx'].median()
        print(f"\n  XYZ→FLX 盈利统计:")
        print(f"     最大利润: ${max_profit_xyz:.4f}")
        print(f"     平均利润: ${avg_profit_xyz:.4f}")
        print(f"     中位利润: ${median_profit_xyz:.4f}")
    print()
    
    # ==================== 价差收敛分析 ====================
    print("【价差收敛与波动分析】")
    
    # 计算价差变化
    df['spread_change'] = df['spread_abs'].diff()
    
    # 收窄和扩大统计
    contracting = (df['spread_change'] < 0).sum()
    expanding = (df['spread_change'] > 0).sum()
    stable = (df['spread_change'] == 0).sum()
    
    print(f"\n  价差变化统计:")
    print(f"     收窄: {contracting:,} 次 ({contracting/len(df)*100:.2f}%)")
    print(f"     扩大: {expanding:,} 次 ({expanding/len(df)*100:.2f}%)")
    print(f"     不变: {stable:,} 次 ({stable/len(df)*100:.2f}%)")
    
    # 分析趋势
    if contracting > expanding * 1.2:
        print(f"\n  📉 趋势: 价差整体呈收窄趋势")
    elif expanding > contracting * 1.2:
        print(f"\n  📈 趋势: 价差整体呈扩大趋势")
    else:
        print(f"\n  ↔️  趋势: 价差波动较为均衡")
    
    # 分时段分析（最近几小时）
    for hours in [1, 4, 12]:
        cutoff_time = df['timestamp'].iloc[-1] - timedelta(hours=hours)
        recent_df = df[df['timestamp'] >= cutoff_time]
        
        if len(recent_df) > 10:
            recent_start_spread = recent_df['spread_abs'].iloc[0]
            recent_end_spread = recent_df['spread_abs'].iloc[-1]
            recent_change = recent_end_spread - recent_start_spread
            recent_change_pct = (recent_change / recent_start_spread) * 100 if recent_start_spread > 0 else 0
            
            print(f"\n  最近 {hours} 小时:")
            print(f"     起始价差: ${recent_start_spread:.4f}")
            print(f"     当前价差: ${recent_end_spread:.4f}")
            print(f"     变化: ${recent_change:+.4f} ({recent_change_pct:+.2f}%)")
            print(f"     趋势: {'收窄' if recent_change < 0 else '扩大' if recent_change > 0 else '稳定'}")
    print()
    
    # ==================== 价差反转分析 ====================
    print("【价差方向反转分析】")
    
    # 判断哪个方向更优
    df['best_direction'] = df.apply(
        lambda row: 'FLX→XYZ' if row['exec_spread_flx_to_xyz'] > row['exec_spread_xyz_to_flx'] else 'XYZ→FLX',
        axis=1
    )
    
    # 统计方向
    flx_to_xyz_count = (df['best_direction'] == 'FLX→XYZ').sum()
    xyz_to_flx_count = (df['best_direction'] == 'XYZ→FLX').sum()
    
    print(f"\n  最优价差方向统计:")
    print(f"     FLX→XYZ: {flx_to_xyz_count:,} 次 ({flx_to_xyz_count/len(df)*100:.1f}%)")
    print(f"     XYZ→FLX: {xyz_to_flx_count:,} 次 ({xyz_to_flx_count/len(df)*100:.1f}%)")
    
    # 检测方向反转
    df['direction_change'] = (df['best_direction'] != df['best_direction'].shift(1))
    reversals = df['direction_change'].sum()
    
    print(f"\n  方向反转情况:")
    print(f"     反转次数: {reversals} 次")
    
    if reversals > 0:
        avg_interval = len(df) / reversals
        avg_time_interval = (duration.total_seconds() / reversals) / 60  # 分钟
        print(f"     平均间隔: {avg_interval:.1f} 条记录 (~{avg_time_interval:.1f} 分钟)")
        
        # 评估反转风险
        if reversals < 5:
            risk_level = "🔴 极高"
            risk_desc = "价差方向几乎不反转，进场后难以平仓"
        elif reversals < 20:
            risk_level = "🟠 高"
            risk_desc = "价差反转较少，平仓机会有限"
        elif reversals < 100:
            risk_level = "🟡 中等"
            risk_desc = "价差有规律反转，可以找到平仓机会"
        else:
            risk_level = "🟢 低"
            risk_desc = "价差频繁反转，平仓机会充足"
        
        print(f"\n  持仓风险: {risk_level}")
        print(f"     {risk_desc}")
    else:
        print(f"\n  持仓风险: 🔴 极高")
        print(f"     价差方向完全单向，无法平仓")
    print()
    
    # ==================== 套利建议 ====================
    print("=" * 100)
    print("【套利空间综合评估】")
    print("=" * 100)
    
    # 评分系统
    score = 0
    max_score = 100
    
    # 1. 盈利机会频率 (40分)
    if profitable_pct > 15:
        opportunity_score = 40
        opportunity_grade = "优秀"
    elif profitable_pct > 10:
        opportunity_score = 30
        opportunity_grade = "良好"
    elif profitable_pct > 5:
        opportunity_score = 20
        opportunity_grade = "一般"
    else:
        opportunity_score = 10
        opportunity_grade = "较差"
    score += opportunity_score
    
    print(f"\n1️⃣  盈利机会频率: {profitable_pct:.2f}% - {opportunity_grade} ({opportunity_score}/40分)")
    
    # 2. 平均利润水平 (30分)
    if total_profitable > 0:
        all_profits = pd.concat([
            df[df['net_profit_flx_to_xyz'] > 0]['net_profit_flx_to_xyz'],
            df[df['net_profit_xyz_to_flx'] > 0]['net_profit_xyz_to_flx']
        ])
        avg_all_profit = all_profits.mean()
        
        if avg_all_profit > 0.5:
            profit_score = 30
            profit_grade = "优秀"
        elif avg_all_profit > 0.3:
            profit_score = 20
            profit_grade = "良好"
        elif avg_all_profit > 0.2:
            profit_score = 10
            profit_grade = "一般"
        else:
            profit_score = 5
            profit_grade = "较低"
    else:
        avg_all_profit = 0
        profit_score = 0
        profit_grade = "无利润"
    score += profit_score
    
    print(f"2️⃣  平均利润水平: ${avg_all_profit:.4f} - {profit_grade} ({profit_score}/30分)")
    
    # 3. 风险水平 (30分)
    if reversals >= 100:
        risk_score = 30
        risk_grade = "低风险"
    elif reversals >= 20:
        risk_score = 20
        risk_grade = "中等风险"
    elif reversals >= 5:
        risk_score = 10
        risk_grade = "高风险"
    else:
        risk_score = 0
        risk_grade = "极高风险"
    score += risk_score
    
    print(f"3️⃣  持仓风险水平: {reversals}次反转 - {risk_grade} ({risk_score}/30分)")
    
    # 总分和建议
    print(f"\n{'='*100}")
    print(f"💯 综合评分: {score}/{max_score} 分")
    print(f"{'='*100}")
    
    if score >= 75:
        recommendation = "🚀 强烈推荐"
        action = "该套利机会盈利频率高、利润可观且风险可控，非常适合自动化交易"
    elif score >= 50:
        recommendation = "✅ 推荐"
        action = "该套利机会具有一定价值，可以考虑部署自动化策略，建议小仓位测试"
    elif score >= 30:
        recommendation = "⚠️  谨慎考虑"
        action = "套利机会存在但不够理想，建议继续观察或优化策略参数"
    else:
        recommendation = "❌ 不推荐"
        action = "当前套利条件不佳，不建议进行交易"
    
    print(f"\n📊 总体建议: {recommendation}")
    print(f"   {action}")
    
    # 具体操作建议
    print(f"\n📋 操作建议:")
    if score >= 50:
        print(f"   1. 可以部署自动化套利策略")
        print(f"   2. 建议设置止损：超过${avg_all_profit * 3:.2f}的价差变化时平仓")
        print(f"   3. 建议单次交易规模：小额测试后逐步增加")
        print(f"   4. 监控频率：每{avg_time_interval/2:.0f}分钟检查一次")
    else:
        print(f"   1. 当前不建议进行套利交易")
        print(f"   2. 继续收集数据，观察价差模式变化")
        print(f"   3. 考虑调整监控参数或寻找其他标的")
    
    print(f"\n⚠️  风险提示:")
    print(f"   • 历史数据不代表未来表现")
    print(f"   • 注意滑点和流动性风险") 
    print(f"   • 考虑资金费率的影响")
    print(f"   • 建议从小仓位开始测试")
    
    print(f"\n{'='*100}")
    print()

if __name__ == "__main__":
    analyze_data()
