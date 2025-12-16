"""
简化版价差反转分析 - 适用于新CSV格式
"""
import pandas as pd

# 读取数据
df = pd.read_csv('spread_history.csv')

print("=" * 80)
print("价差反转风险分析报告".center(80))
print("=" * 80)
print()

print(f"数据量: {len(df)} 条记录")
print()

# 分析可执行价差的方向
df['favorable_direction'] = df.apply(
    lambda row: 'FLX->XYZ' if row['exec_spread_flx_to_xyz'] > row['exec_spread_xyz_to_flx'] else 'XYZ->FLX',
    axis=1
)

# 统计方向
flx_to_xyz_count = (df['favorable_direction'] == 'FLX->XYZ').sum()
xyz_to_flx_count = (df['favorable_direction'] == 'XYZ->FLX').sum()

print("【价差方向统计】")
print(f"FLX->XYZ 更优: {flx_to_xyz_count} 次 ({flx_to_xyz_count/len(df)*100:.1f}%)")
print(f"XYZ->FLX 更优: {xyz_to_flx_count} 次 ({xyz_to_flx_count/len(df)*100:.1f}%)")
print()

# 检测方向切换
df['direction_changed'] = (df['favorable_direction'] != df['favorable_direction'].shift(1))
direction_changes = df['direction_changed'].sum()

print("【价差反转情况】")
print(f"方向切换次数: {direction_changes}")

if direction_changes > 0:
    avg_interval = len(df) / direction_changes
    print(f"平均切换间隔: {avg_interval:.1f} 条记录 (约 {avg_interval * 2:.0f} 秒 = {avg_interval * 2 / 60:.1f} 分钟)")
else:
    print("⚠️  数据期间内价差方向从未反转！")

print()

# 分析价差数值
print("【FLX->XYZ 方向价差数值】")
print(f"平均值: ${df['exec_spread_flx_to_xyz'].mean():.4f}")
print(f"最大值: ${df['exec_spread_flx_to_xyz'].max():.4f}")
print(f"最小值: ${df['exec_spread_flx_to_xyz'].min():.4f}")
print()

print("【XYZ->FLX 方向价差数值】")
print(f"平均值: ${df['exec_spread_xyz_to_flx'].mean():.4f}")
print(f"最大值: ${df['exec_spread_xyz_to_flx'].max():.4f}")
print(f"最小值: ${df['exec_spread_xyz_to_flx'].min():.4f}")
print()

# 关键风险评估
print("=" * 80)
print("【核心风险评估】")
print("=" * 80)
print()

if direction_changes == 0:
    print("❌ 极高风险：价差完全单向，无反转")
    print()
    print("原因分析：")
    if flx_to_xyz_count > xyz_to_flx_count * 10:
        print("- FLX 市场买入价始终低于 XYZ 市场卖出价")
        print("- 表明 XYZ 市场整体价格显著高于 FLX")
        print("- 这是结构性价差，不是套利机会")
    print()
    print("❌ 不建议交易：")
    print("1. 开仓后无法平仓（价差不会反转）")
    print("2. 仓位会永久压在手上")
    print("3. 需要承担单边市场风险和资金费率")
elif direction_changes < 3:
    print("⚠️  高风险：价差很少反转")
    print(f"- 在{len(df) * 2}秒内只反转了{direction_changes}次")
    print("- 平仓机会很少")
else:
    print(f"✓ 中等风险：价差有反转")
    print(f"- 约每{avg_interval * 2 / 60:.1f}分钟反转一次")

print()
print("=" * 80)
