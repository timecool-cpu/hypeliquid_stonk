#!/usr/bin/env python3
"""
分析价差净利润数据，为两个方向提供独立的阈值建议
"""
import pandas as pd
import numpy as np
from datetime import datetime


def analyze_spread_profits(log_file='spread_profit_log.csv'):
    """分析价差净利润数据"""
    
    try:
        df = pd.read_csv(log_file)
    except Exception as e:
        print(f"读取文件失败: {e}")
        print("请先运行交易系统生成数据")
        return
    
    if len(df) == 0:
        print("暂无数据")
        return
    
    print("=" * 100)
    print("价差净利润分析报告".center(100))
    print("=" * 100)
    print()
    
    # 基本信息
    print("【数据概况】")
    print(f"总记录数: {len(df)}")
    print(f"时间范围: {df['timestamp'].iloc[0]} 至 {df['timestamp'].iloc[-1]}")
    print()
    
    # FLX→XYZ方向分析
    print("【FLX→XYZ 方向分析】")
    flx_to_xyz = df['flx_to_xyz_net_profit']
    print(f"平均净利润: ${flx_to_xyz.mean():.4f}")
    print(f"中位数净利润: ${flx_to_xyz.median():.4f}")
    print(f"最大净利润: ${flx_to_xyz.max():.4f}")
    print(f"最小净利润: ${flx_to_xyz.min():.4f}")
    print(f"标准差: ${flx_to_xyz.std():.4f}")
    
    profitable_rate = (flx_to_xyz > 0).sum() / len(df) * 100
    print(f"盈利概率: {profitable_rate:.2f}% ({(flx_to_xyz > 0).sum()}/{len(df)})")
    
    # 分位数
    print(f"\n分位数分析:")
    for q in [0.25, 0.50, 0.75, 0.90, 0.95]:
        val = flx_to_xyz.quantile(q)
        print(f"  {int(q*100)}%分位数: ${val:.4f}")
    
    # 建议阈值
    if profitable_rate > 0:
        profitable_data = flx_to_xyz[flx_to_xyz > 0]
        recommended_threshold = profitable_data.quantile(0.25)
        print(f"\n💡 建议阈值: ${recommended_threshold:.4f} (盈利数据25分位数)")
    print()
    
    # XYZ→FLX方向分析
    print("【XYZ→FLX 方向分析】")
    xyz_to_flx = df['xyz_to_flx_net_profit']
    print(f"平均净利润: ${xyz_to_flx.mean():.4f}")
    print(f"中位数净利润: ${xyz_to_flx.median():.4f}")
    print(f"最大净利润: ${xyz_to_flx.max():.4f}")
    print(f"最小净利润: ${xyz_to_flx.min():.4f}")
    print(f"标准差: ${xyz_to_flx.std():.4f}")
    
    profitable_rate = (xyz_to_flx > 0).sum() / len(df) * 100
    print(f"盈利概率: {profitable_rate:.2f}% ({(xyz_to_flx > 0).sum()}/{len(df)})")
    
    # 分位数
    print(f"\n分位数分析:")
    for q in [0.25, 0.50, 0.75, 0.90, 0.95]:
        val = xyz_to_flx.quantile(q)
        print(f"  {int(q*100)}%分位数: ${val:.4f}")
    
    # 建议阈值
    if profitable_rate > 0:
        profitable_data = xyz_to_flx[xyz_to_flx > 0]
        recommended_threshold = profitable_data.quantile(0.25)
        print(f"\n💡 建议阈值: ${recommended_threshold:.4f} (盈利数据25分位数)")
    print()
    
    # 对比分析
    print("【双向对比】")
    
    # 哪个方向更强
    flx_better = (flx_to_xyz > xyz_to_flx).sum()
    xyz_better = (xyz_to_flx > flx_to_xyz).sum()
    print(f"FLX→XYZ更优: {flx_better} 次 ({flx_better/len(df)*100:.1f}%)")
    print(f"XYZ→FLX更优: {xyz_better} 次 ({xyz_better/len(df)*100:.1f}%)")
    
    # 平均优势
    flx_avg = flx_to_xyz.mean()
    xyz_avg = xyz_to_flx.mean()
    if flx_avg > xyz_avg:
        print(f"\n总体而言: FLX→XYZ平均高 ${flx_avg - xyz_avg:.4f}")
    else:
        print(f"\n总体而言: XYZ→FLX平均高 ${xyz_avg - flx_avg:.4f}")
    print()
    
    # 相关性分析
    correlation = flx_to_xyz.corr(xyz_to_flx)
    print(f"两方向相关性: {correlation:.4f}")
    if correlation < -0.5:
        print("  → 强负相关，一个方向好时另一个通常不好")
    elif correlation > 0.5:
        print("  → 强正相关，两个方向趋同")
    else:
        print("  → 相关性较弱，两个方向独立性较高")
    print()
    
    # 推荐配置
    print("=" * 100)
    print("【推荐配置】")
    print("=" * 100)
    print()
    
    # 判断是否需要分别设置阈值
    flx_profitable = flx_to_xyz[flx_to_xyz > 0]
    xyz_profitable = xyz_to_flx[xyz_to_flx > 0]
    
    if len(flx_profitable) > 0 and len(xyz_profitable) > 0:
        flx_threshold = flx_profitable.quantile(0.25)
        xyz_threshold = xyz_profitable.quantile(0.25)
        
        diff = abs(flx_threshold - xyz_threshold)
        avg_threshold = (flx_threshold + xyz_threshold) / 2
        
        if diff / avg_threshold > 0.2:  # 差异超过20%
            print("⚠️  两个方向特征差异较大，建议分别设置阈值:")
            print(f"MIN_NET_PROFIT_FLX_TO_XYZ = {flx_threshold:.2f}")
            print(f"MIN_NET_PROFIT_XYZ_TO_FLX = {xyz_threshold:.2f}")
        else:
            print("✅ 两个方向特征相近，可使用统一阈值:")
            unified = min(flx_threshold, xyz_threshold)  # 取较小值保守一点
            print(f"MIN_NET_PROFIT = {unified:.2f}")
    
    print()
    print("=" * 100)
    
    # 时间序列分析（可选）
    print("\n【时间趋势】")
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    
    hourly = df.groupby('hour').agg({
        'flx_to_xyz_net_profit': 'mean',
        'xyz_to_flx_net_profit': 'mean'
    })
    
    print("不同时段平均净利润:")
    print(hourly.to_string())
    print()
    print("=" * 100)


if __name__ == '__main__':
    analyze_spread_profits()
