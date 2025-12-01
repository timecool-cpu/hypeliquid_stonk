"""
套利交易日志记录模块
"""
import csv
from datetime import datetime
from pathlib import Path
import arbitrage_config


class ArbitrageLogger:
    """套利交易日志记录器"""
    
    def __init__(self, log_file=None):
        """
        初始化日志记录器
        
        Args:
            log_file: 日志文件路径，默认使用配置中的路径
        """
        self.log_file = log_file or arbitrage_config.TRADE_LOG_FILE
        self._initialize_log_file()
    
    def _initialize_log_file(self):
        """初始化日志文件，如果不存在则创建并写入表头"""
        if not Path(self.log_file).exists():
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'action',  # 'OPEN' or 'CLOSE'
                    'position_id',
                    'direction',
                    'position_size',
                    'entry_spread',
                    'entry_flx_bid',
                    'entry_flx_ask',
                    'entry_xyz_bid',
                    'entry_xyz_ask',
                    'exit_spread',
                    'exit_flx_bid',
                    'exit_flx_ask',
                    'exit_xyz_bid',
                    'exit_xyz_ask',
                    'exit_method',
                    'holding_seconds',
                    'realized_pnl',
                    'notes'
                ])
    
    def log_open_position(self, position, notes=''):
        """
        记录开仓
        
        Args:
            position: Position对象
            notes: 备注信息
        """
        if not arbitrage_config.LOG_TRADES:
            return
        
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                position.entry_time.strftime('%Y-%m-%d %H:%M:%S'),
                'OPEN',
                position.position_id,
                position.direction,
                position.position_size,
                f"{position.entry_spread:.4f}",
                f"{position.entry_prices.get('flx_bid', 0):.2f}",
                f"{position.entry_prices.get('flx_ask', 0):.2f}",
                f"{position.entry_prices.get('xyz_bid', 0):.2f}",
                f"{position.entry_prices.get('xyz_ask', 0):.2f}",
                '',  # exit_spread
                '',  # exit_flx_bid
                '',  # exit_flx_ask
                '',  # exit_xyz_bid
                '',  # exit_xyz_ask
                '',  # exit_method
                '',  # holding_seconds
                '',  # realized_pnl
                notes
            ])
    
    def log_close_position(self, close_record, notes=''):
        """
        记录平仓
        
        Args:
            close_record: 平仓记录字典
            notes: 备注信息
        """
        if not arbitrage_config.LOG_TRADES:
            return
        
        # 计算平仓时的价差
        if close_record['direction'] == 'FLX_TO_XYZ':
            exit_spread = (close_record['exit_prices'].get('xyz_bid', 0) - 
                          close_record['exit_prices'].get('flx_ask', 0))
        else:
            exit_spread = (close_record['exit_prices'].get('flx_bid', 0) - 
                          close_record['exit_prices'].get('xyz_ask', 0))
        
        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                close_record['exit_time'].strftime('%Y-%m-%d %H:%M:%S'),
                'CLOSE',
                close_record['position_id'],
                close_record['direction'],
                close_record['position_size'],
                f"{close_record['entry_spread']:.4f}",
                f"{close_record['entry_prices'].get('flx_bid', 0):.2f}",
                f"{close_record['entry_prices'].get('flx_ask', 0):.2f}",
                f"{close_record['entry_prices'].get('xyz_bid', 0):.2f}",
                f"{close_record['entry_prices'].get('xyz_ask', 0):.2f}",
                f"{exit_spread:.4f}",
                f"{close_record['exit_prices'].get('flx_bid', 0):.2f}",
                f"{close_record['exit_prices'].get('flx_ask', 0):.2f}",
                f"{close_record['exit_prices'].get('xyz_bid', 0):.2f}",
                f"{close_record['exit_prices'].get('xyz_ask', 0):.2f}",
                close_record['exit_method'],
                f"{close_record['holding_seconds']:.0f}",
                f"{close_record['realized_pnl']:.4f}",
                notes
            ])
    
    def print_trade_summary(self, close_record):
        """
        打印交易摘要
        
        Args:
            close_record: 平仓记录字典
        """
        print("\n" + "=" * 80)
        print(f"交易完成 - {close_record['position_id']}")
        print("=" * 80)
        print(f"方向: {close_record['direction']}")
        print(f"仓位大小: ${close_record['position_size']}")
        print(f"持仓时长: {close_record['holding_seconds'] / 60:.1f} 分钟")
        print(f"开仓价差: ${close_record['entry_spread']:.4f}")
        print(f"平仓方式: {close_record['exit_method']}")
        print(f"实现盈亏: ${close_record['realized_pnl']:.4f}")
        print("=" * 80 + "\n")
    
    def print_statistics(self, stats):
        """
        打印统计信息
        
        Args:
            stats: 统计字典（从PositionManager.get_statistics()获取）
        """
        print("\n" + "=" * 80)
        print("交易统计")
        print("=" * 80)
        print(f"总交易次数: {stats['total_trades']}")
        print(f"盈利交易: {stats.get('profitable_trades', 0)}")
        print(f"亏损交易: {stats.get('losing_trades', 0)}")
        print(f"胜率: {stats['win_rate']:.1f}%")
        print(f"总盈亏: ${stats['total_realized_pnl']:.2f}")
        print(f"平均盈亏: ${stats['avg_pnl']:.4f}")
        print(f"平均持仓时间: {stats['avg_holding_time'] / 60:.1f} 分钟")
        print("=" * 80 + "\n")


# 示例用法
if __name__ == "__main__":
    logger = ArbitrageLogger('test_trades.csv')
    print("日志记录器已初始化")
    print(f"日志文件: {logger.log_file}")
