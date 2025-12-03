"""
分析套利交易历史数据，提供优化建议
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def analyze_trading_performance(csv_file='arbitrage_trades.csv'):
    """分析交易表现并提供优化建议"""
    
    try:
        df = pd.read_csv(csv_file)
    except Exception as e:
        print(f"读取文件失败: {e}")
        return
    
    # 筛选出平仓记录
    closed_trades = df[df['action'] == 'CLOSE'].copy()
    
    if len(closed_trades) == 0:
        print("没有已完成的交易记录")
        return
    
    print("=" * 100)
    print("套利交易性能分析报告".center(100))
    print("=" * 100)
    print()
    
    # 基本统计
    print("【交易概况】")
    print(f"总交易笔数: {len(closed_trades)}")
    print(f"总盈亏: ${closed_trades['realized_pnl'].sum():.4f}")
    print(f"平均盈亏: ${closed_trades['realized_pnl'].mean():.4f}")
    print(f"中位数盈亏: ${closed_trades['realized_pnl'].median():.4f}")
    print()
    
    # 盈亏分析
    profitable = closed_trades[closed_trades['realized_pnl'] > 0]
    losing = closed_trades[closed_trades['realized_pnl'] <= 0]
    
    print("【盈亏分布】")
    print(f"盈利交易: {len(profitable)} 笔 ({len(profitable)/len(closed_trades)*100:.1f}%)")
    if len(profitable) > 0:
        print(f"  平均盈利: ${profitable['realized_pnl'].mean():.4f}")
        print(f"  最大盈利: ${profitable['realized_pnl'].max():.4f}")
    
    print(f"亏损交易: {len(losing)} 笔 ({len(losing)/len(closed_trades)*100:.1f}%)")
    if len(losing) > 0:
        print(f"  平均亏损: ${losing['realized_pnl'].mean():.4f}")
        print(f"  最大亏损: ${losing['realized_pnl'].min():.4f}")
    print()
    
    # 平仓方式分析
    print("【平仓方式分析】")
    for method in closed_trades['exit_method'].unique():
        method_trades = closed_trades[closed_trades['exit_method'] == method]
        avg_pnl = method_trades['realized_pnl'].mean()
        count = len(method_trades)
        pct = count / len(closed_trades) * 100
        
        print(f"\n{method} ({count}笔, {pct:.1f}%):")
        print(f"  平均盈亏: ${avg_pnl:.4f}")
        print(f"  平均持仓时间: {method_trades['holding_seconds'].mean()/60:.1f} 分钟")
        
        if len(method_trades[method_trades['realized_pnl'] > 0]) > 0:
            success_rate = len(method_trades[method_trades['realized_pnl'] > 0]) / len(method_trades) * 100
            print(f"  盈利率: {success_rate:.1f}%")
    print()
    
    # 持仓时间分析
    print("【持仓时间分析】")
    closed_trades['holding_minutes'] = closed_trades['holding_seconds'] / 60
    print(f"平均持仓时间: {closed_trades['holding_minutes'].mean():.1f} 分钟")
    print(f"中位数持仓时间: {closed_trades['holding_minutes'].median():.1f} 分钟")
    print(f"最短持仓: {closed_trades['holding_minutes'].min():.1f} 分钟")
    print(f"最长持仓: {closed_trades['holding_minutes'].max():.1f} 分钟")
    print()
    
    # 不同持仓时长的盈亏
    bins = [0, 15, 30, 60, 120, float('inf')]
    labels = ['0-15分钟', '15-30分钟', '30-60分钟', '1-2小时', '2小时以上']
    closed_trades['time_bucket'] = pd.cut(closed_trades['holding_minutes'], bins=bins, labels=labels)
    
    print("不同持仓时长的表现:")
    for label in labels:
        bucket_trades = closed_trades[closed_trades['time_bucket'] == label]
        if len(bucket_trades) > 0:
            avg_pnl = bucket_trades['realized_pnl'].mean()
            count = len(bucket_trades)
            profitable_pct = len(bucket_trades[bucket_trades['realized_pnl'] > 0]) / count * 100
            print(f"  {label}: {count}笔, 平均${avg_pnl:.4f}, 盈利率{profitable_pct:.1f}%")
    print()
    
    # 方向分析
    print("【交易方向分析】")
    for direction in closed_trades['direction'].unique():
        dir_trades = closed_trades[closed_trades['direction'] == direction]
        avg_pnl = dir_trades['realized_pnl'].mean()
        count = len(dir_trades)
        pct = count / len(closed_trades) * 100
        profitable_pct = len(dir_trades[dir_trades['realized_pnl'] > 0]) / count * 100
        
        print(f"{direction} ({count}笔, {pct:.1f}%):")
        print(f"  平均盈亏: ${avg_pnl:.4f}")
        print(f"  盈利率: {profitable_pct:.1f}%")
    print()
    
    # 开仓价差分析
    print("【开仓价差分析】")
    print(f"平均开仓价差: ${closed_trades['entry_spread'].mean():.4f}")
    print(f"中位数开仓价差: ${closed_trades['entry_spread'].median():.4f}")
    print(f"最小开仓价差: ${closed_trades['entry_spread'].min():.4f}")
    print(f"最大开仓价差: ${closed_trades['entry_spread'].max():.4f}")
    print()
    
    # 价差与盈亏的关系
    correlation = closed_trades['entry_spread'].corr(closed_trades['realized_pnl'])
    print(f"开仓价差与盈亏的相关性: {correlation:.4f}")
    if correlation > 0.5:
        print("  → 价差越大，盈利越多，建议提高最小价差阈值")
    elif correlation < 0:
        print("  → 负相关，可能价差大的反而容易亏损")
    print()
    
    # ===== 优化建议 =====
    print("=" * 100)
    print("【优化建议】")
    print("=" * 100)
    print()
    
    suggestions = []
    
    # 1. 基于平仓方式的建议
    if 'reversal' in closed_trades['exit_method'].values:
        reversal_trades = closed_trades[closed_trades['exit_method'] == 'reversal']
        reversal_success_rate = len(reversal_trades[reversal_trades['realized_pnl'] > 0]) / len(reversal_trades) * 100
        reversal_avg_time = reversal_trades['holding_minutes'].mean()
        
        if reversal_success_rate > 50:
            suggestions.append({
                'priority': '高',
                'category': '平仓策略',
                'suggestion': f'价差反转平仓效果好（成功率{reversal_success_rate:.1f}%），建议继续优先等待反转',
                'action': '保持当前策略，可考虑适当延长超时时间'
            })
    
    if 'timeout' in closed_trades['exit_method'].values:
        timeout_trades = closed_trades[closed_trades['exit_method'] == 'timeout']
        timeout_avg_pnl = timeout_trades['realized_pnl'].mean()
        
        if timeout_avg_pnl < 0:
            suggestions.append({
                'priority': '高',
                'category': '超时设置',
                'suggestion': f'超时平仓平均亏损${abs(timeout_avg_pnl):.4f}，建议优化超时策略',
                'action': f'当前{timeout_trades["holding_minutes"].mean():.0f}分钟超时，考虑缩短或增加止损条件'
            })
    
    # 2. 基于持仓时间的建议
    short_term = closed_trades[closed_trades['holding_minutes'] <= 30]
    if len(short_term) > 0:
        short_term_success = len(short_term[short_term['realized_pnl'] > 0]) / len(short_term) * 100
        if short_term_success > 60:
            suggestions.append({
                'priority': '中',
                'category': '持仓时间',
                'suggestion': f'短期（≤30分钟）交易成功率{short_term_success:.1f}%，效果好',
                'action': '可以降低超时时间到30-60分钟，减少资金占用'
            })
    
    # 3. 基于开仓价差的建议
    if correlation > 0.3:
        optimal_spread = closed_trades[closed_trades['realized_pnl'] > 0]['entry_spread'].median()
        suggestions.append({
            'priority': '高',
            'category': '开仓阈值',
            'suggestion': f'盈利交易的中位开仓价差为${optimal_spread:.4f}',
            'action': f'建议调整MIN_NET_PROFIT到${optimal_spread * 0.8:.2f}以获得更好的盈利质量'
        })
    
    # 4. 基于胜率的建议
    win_rate = len(profitable) / len(closed_trades) * 100
    if win_rate < 50:
        suggestions.append({
            'priority': '高',
            'category': '整体策略',
            'suggestion': f'胜率仅{win_rate:.1f}%，低于50%',
            'action': '建议提高开仓阈值或优化平仓条件'
        })
    elif win_rate > 75:
        suggestions.append({
            'priority': '中',
            'category': '整体策略',
            'suggestion': f'胜率{win_rate:.1f}%很高，可能错过一些机会',
            'action': '可以适当降低开仓阈值以增加交易频率'
        })
    
    # 5. 交易频率建议
    total_opens = len(df[df['action'] == 'OPEN'])
    if total_opens < 10:
        suggestions.append({
            'priority': '中',
            'category': '交易频率',
            'suggestion': f'22小时内仅开仓{total_opens}次，频率较低',
            'action': '降低MIN_NET_PROFIT以捕获更多机会，当前手续费很低(0.003%)，可以交易更频繁'
        })
    
    # 打印建议
    if suggestions:
        for i, sug in enumerate(suggestions, 1):
            print(f"{i}. 【{sug['category']}】优先级: {sug['priority']}")
            print(f"   发现: {sug['suggestion']}")
            print(f"   建议: {sug['action']}")
            print()
    else:
        print("当前策略表现良好，暂无明显优化建议")
        print()
    
    # 具体参数建议
    print("=" * 100)
    print("【推荐配置参数】")
    print("=" * 100)
    print()
    
    if len(profitable) > 0:
        recommended_min_profit = max(0.05, profitable['realized_pnl'].quantile(0.25))
        print(f"MIN_NET_PROFIT = {recommended_min_profit:.2f}  # 基于盈利交易25分位数")
    
    if 'reversal' in closed_trades['exit_method'].values:
        reversal_spread = abs(closed_trades[closed_trades['exit_method'] == 'reversal']['exit_spread'].median())
        if not np.isnan(reversal_spread):
            print(f"REVERSAL_MIN_SPREAD = {max(0.10, reversal_spread):.2f}  # 基于实际反转价差中位数")
    
    optimal_timeout = closed_trades['holding_minutes'].quantile(0.75) / 60
    if not np.isnan(optimal_timeout):
        print(f"POSITION_TIMEOUT_HOURS = {max(1, optimal_timeout):.1f}  # 基于75分位持仓时间")
    
    print()
    print("=" * 100)

if __name__ == "__main__":
    analyze_trading_performance()
