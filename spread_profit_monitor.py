"""
价差净利润监控模块
记录FLX→XYZ和XYZ→FLX两个方向的净利润，便于后续分析是否需要设置不同阈值
"""
import csv
import os
from datetime import datetime


class SpreadProfitMonitor:
    """价差净利润监控器"""
    
    def __init__(self, log_file='spread_profit_log.csv'):
        """
        初始化监控器
        
        Args:
            log_file: 日志文件路径
        """
        self.log_file = log_file
        self._init_log_file()
    
    def _init_log_file(self):
        """初始化日志文件（如果不存在则创建表头）"""
        if not os.path.exists(self.log_file):
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'flx_bid', 'flx_ask', 'flx_mid',
                    'xyz_bid', 'xyz_ask', 'xyz_mid',
                    'flx_to_xyz_spread', 'flx_to_xyz_net_profit',
                    'xyz_to_flx_spread', 'xyz_to_flx_net_profit',
                    'open_fee',
                    'best_direction', 'best_net_profit'
                ])
    
    def log_spread_profit(self, market_data, calculator):
        """
        记录当前价差和净利润
        
        Args:
            market_data: 市场数据字典 {flx_bid, flx_ask, xyz_bid, xyz_ask, ...}
            calculator: ArbitrageCalculator实例
        """
        # 计算两个方向的价差和净利润
        flx_to_xyz_spread = market_data['xyz_bid'] - market_data['flx_ask']
        xyz_to_flx_spread = market_data['flx_bid'] - market_data['xyz_ask']
        
        avg_price = (market_data['flx_mid'] + market_data['xyz_mid']) / 2
        open_fee = calculator.calculate_open_fee(avg_price)
        
        flx_to_xyz_net = flx_to_xyz_spread - open_fee
        xyz_to_flx_net = xyz_to_flx_spread - open_fee
        
        # 确定最佳方向
        if flx_to_xyz_net > xyz_to_flx_net:
            best_direction = 'FLX_TO_XYZ'
            best_net_profit = flx_to_xyz_net
        else:
            best_direction = 'XYZ_TO_FLX'
            best_net_profit = xyz_to_flx_net
        
        # 写入日志
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                f"{market_data['flx_bid']:.2f}",
                f"{market_data['flx_ask']:.2f}",
                f"{market_data['flx_mid']:.2f}",
                f"{market_data['xyz_bid']:.2f}",
                f"{market_data['xyz_ask']:.2f}",
                f"{market_data['xyz_mid']:.2f}",
                f"{flx_to_xyz_spread:.4f}",
                f"{flx_to_xyz_net:.4f}",
                f"{xyz_to_flx_spread:.4f}",
                f"{xyz_to_flx_net:.4f}",
                f"{open_fee:.4f}",
                best_direction,
                f"{best_net_profit:.4f}"
            ])
    
    def get_statistics(self):
        """
        获取统计信息
        
        Returns:
            包含两个方向统计信息的字典
        """
        if not os.path.exists(self.log_file):
            return None
        
        try:
            import pandas as pd
            df = pd.read_csv(self.log_file)
            
            if len(df) == 0:
                return None
            
            return {
                'total_records': len(df),
                'flx_to_xyz': {
                    'avg_net_profit': df['flx_to_xyz_net_profit'].mean(),
                    'max_net_profit': df['flx_to_xyz_net_profit'].max(),
                    'min_net_profit': df['flx_to_xyz_net_profit'].min(),
                    'profitable_rate': (df['flx_to_xyz_net_profit'] > 0).sum() / len(df) * 100,
                },
                'xyz_to_flx': {
                    'avg_net_profit': df['xyz_to_flx_net_profit'].mean(),
                    'max_net_profit': df['xyz_to_flx_net_profit'].max(),
                    'min_net_profit': df['xyz_to_flx_net_profit'].min(),
                    'profitable_rate': (df['xyz_to_flx_net_profit'] > 0).sum() / len(df) * 100,
                },
                'best_direction_count': {
                    'FLX_TO_XYZ': (df['best_direction'] == 'FLX_TO_XYZ').sum(),
                    'XYZ_TO_FLX': (df['best_direction'] == 'XYZ_TO_FLX').sum(),
                }
            }
        except ImportError:
            # 如果没有pandas，返回简化版本
            return {'error': 'pandas not installed, cannot generate statistics'}


if __name__ == '__main__':
    """测试和分析脚本"""
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'stats':
        # 显示统计信息
        monitor = SpreadProfitMonitor()
        stats = monitor.get_statistics()
        
        if stats is None:
            print("暂无数据")
        elif 'error' in stats:
            print(f"错误: {stats['error']}")
        else:
            print("=" * 80)
            print("价差净利润统计报告")
            print("=" * 80)
            print(f"\n总记录数: {stats['total_records']}")
            
            print("\n【FLX→XYZ方向】")
            print(f"  平均净利润: ${stats['flx_to_xyz']['avg_net_profit']:.4f}")
            print(f"  最大净利润: ${stats['flx_to_xyz']['max_net_profit']:.4f}")
            print(f"  最小净利润: ${stats['flx_to_xyz']['min_net_profit']:.4f}")
            print(f"  盈利概率: {stats['flx_to_xyz']['profitable_rate']:.2f}%")
            
            print("\n【XYZ→FLX方向】")
            print(f"  平均净利润: ${stats['xyz_to_flx']['avg_net_profit']:.4f}")
            print(f"  最大净利润: ${stats['xyz_to_flx']['max_net_profit']:.4f}")
            print(f"  最小净利润: ${stats['xyz_to_flx']['min_net_profit']:.4f}")
            print(f"  盈利概率: {stats['xyz_to_flx']['profitable_rate']:.2f}%")
            
            print("\n【最佳方向分布】")
            print(f"  FLX→XYZ最佳: {stats['best_direction_count']['FLX_TO_XYZ']} 次")
            print(f"  XYZ→FLX最佳: {stats['best_direction_count']['XYZ_TO_FLX']} 次")
            print("=" * 80)
    else:
        print("用法: python3 spread_profit_monitor.py stats")
