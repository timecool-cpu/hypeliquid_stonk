"""
仓位管理模块
跟踪持仓状态、计算盈亏、判断平仓时机
"""
from datetime import datetime, timedelta
from typing import List, Optional
import arbitrage_config


class Position:
    """持仓信息"""
    
    def __init__(self, direction, entry_spread, entry_prices, position_size, entry_time=None):
        """
        初始化持仓
        
        Args:
            direction: 'FLX_TO_XYZ' 或 'XYZ_TO_FLX'
            entry_spread: 开仓时的可执行价差
            entry_prices: {'flx_bid', 'flx_ask', 'xyz_bid', 'xyz_ask'}
            position_size: 仓位大小（USDC）
            entry_time: 开仓时间（datetime对象）
        """
        self.direction = direction
        self.entry_spread = entry_spread
        self.entry_prices = entry_prices
        self.position_size = position_size
        self.entry_time = entry_time or datetime.now()
        self.unrealized_pnl = 0.0
        self.position_id = f"{direction}_{self.entry_time.strftime('%Y%m%d%H%M%S')}"
    
    def get_holding_duration(self):
        """获取持仓时长（秒）"""
        return (datetime.now() - self.entry_time).total_seconds()
    
    def get_holding_hours(self):
        """获取持仓时长（小时）"""
        return self.get_holding_duration() / 3600
    
    def is_timeout(self):
        """检查是否超时"""
        return self.get_holding_hours() > arbitrage_config.POSITION_TIMEOUT_HOURS
    
    def __repr__(self):
        return (f"Position(id={self.position_id}, direction={self.direction}, "
                f"spread={self.entry_spread:.4f}, size={self.position_size}, "
                f"duration={self.get_holding_duration():.0f}s, pnl={self.unrealized_pnl:.4f})")


class PositionManager:
    """仓位管理器"""
    
    def __init__(self, calculator):
        """
        初始化仓位管理器
        
        Args:
            calculator: ArbitrageCalculator实例
        """
        self.calculator = calculator
        self.positions: List[Position] = []
        self.closed_positions: List[dict] = []
        self.total_realized_pnl = 0.0
    
    def can_open_position(self):
        """检查是否可以开新仓"""
        # 检查仓位数量限制
        if len(self.positions) >= arbitrage_config.MAX_POSITIONS:
            return False, "已达到最大仓位数量"
        
        # 检查总仓位限制
        total_position_value = sum(pos.position_size for pos in self.positions)
        if total_position_value >= arbitrage_config.MAX_TOTAL_POSITION:
            return False, "已达到总仓位上限"
        
        return True, "可以开仓"
    
    def can_add_position(self, current_spread, best_spread):
        """
        检查是否可以加仓
        
        Args:
            current_spread: 当前最优价差
            best_spread: 历史最佳价差
        
        Returns:
            (can_add, reason) 元组
        """
        if len(self.positions) == 0:
            return True, "首次开仓"
        
        # 检查仓位限制
        can_open, reason = self.can_open_position()
        if not can_open:
            return False, reason
        
        # 检查价差扩大条件
        spread_increase = current_spread - best_spread
        if spread_increase < arbitrage_config.ADD_POSITION_SPREAD_INCREASE:
            return False, f"价差增加不足（需要>{arbitrage_config.ADD_POSITION_SPREAD_INCREASE}）"
        
        if current_spread < arbitrage_config.ADD_POSITION_MIN_SPREAD:
            return False, f"总价差不足（需要>{arbitrage_config.ADD_POSITION_MIN_SPREAD}）"
        
        return True, "满足加仓条件"
    
    def open_position(self, direction, entry_spread, entry_prices, position_size):
        """
        开仓
        
        Args:
            direction: 套利方向
            entry_spread: 开仓价差
            entry_prices: 开仓价格字典
            position_size: 仓位大小
        
        Returns:
            Position对象
        """
        position = Position(direction, entry_spread, entry_prices, position_size)
        self.positions.append(position)
        return position
    
    def close_position(self, position, exit_prices, exit_method, realized_pnl):
        """
        平仓
        
        Args:
            position: Position对象
            exit_prices: 平仓价格字典
            exit_method: 平仓方式 ('reversal', 'take_profit', 'timeout')
            realized_pnl: 实现盈亏
        """
        # 记录平仓信息
        close_record = {
            'position_id': position.position_id,
            'direction': position.direction,
            'entry_time': position.entry_time,
            'exit_time': datetime.now(),
            'holding_seconds': position.get_holding_duration(),
            'entry_spread': position.entry_spread,
            'entry_prices': position.entry_prices,
            'exit_prices': exit_prices,
            'position_size': position.position_size,
            'exit_method': exit_method,
            'realized_pnl': realized_pnl
        }
        
        self.closed_positions.append(close_record)
        self.total_realized_pnl += realized_pnl
        
        # 从持仓列表中移除
        self.positions.remove(position)
        
        return close_record
    
    def update_positions(self, current_flx_bid, current_flx_ask, 
                        current_xyz_bid, current_xyz_ask):
        """
        更新所有持仓的未实现盈亏
        
        Args:
            current_flx_bid, current_flx_ask, current_xyz_bid, current_xyz_ask: 当前市场价格
        """
        for position in self.positions:
            position.unrealized_pnl = self.calculator.calculate_unrealized_pnl(
                position,
                current_flx_bid, current_flx_ask,
                current_xyz_bid, current_xyz_ask
            )
    
    def check_exit_conditions(self, position, current_flx_bid, current_flx_ask,
                             current_xyz_bid, current_xyz_ask):
        """
        检查持仓的平仓条件
        
        Args:
            position: Position对象
            current prices: 当前价格
        
        Returns:
            {
                'should_exit': bool,
                'exit_reason': str,
                'exit_method': str,  # 'reversal', 'take_profit', 'timeout'
                'has_reversal': bool,
                'reverse_spread': float
            }
        """
        # 1. 检查价差反转（最优先）
        has_reversal, reverse_spread = self.calculator.check_reversal_opportunity(
            position.direction,
            current_flx_bid, current_flx_ask,
            current_xyz_bid, current_xyz_ask
        )
        
        if has_reversal:
            return {
                'should_exit': True,
                'exit_reason': f'价差反转，反向价差=${reverse_spread:.4f}',
                'exit_method': 'reversal',
                'has_reversal': True,
                'reverse_spread': reverse_spread
            }
        
        # 2. 检查止盈
        if position.unrealized_pnl > arbitrage_config.TAKE_PROFIT_TARGET:
            return {
                'should_exit': True,
                'exit_reason': f'达到止盈目标，浮盈=${position.unrealized_pnl:.4f}',
                'exit_method': 'take_profit',
                'has_reversal': False,
                'reverse_spread': 0
            }
        
        # 3. 检查超时
        if position.is_timeout():
            return {
                'should_exit': True,
                'exit_reason': f'持仓超时（{position.get_holding_hours():.1f}小时）',
                'exit_method': 'timeout',
                'has_reversal': False,
                'reverse_spread': 0
            }
        
        # 不需要平仓
        return {
            'should_exit': False,
            'exit_reason': None,
            'exit_method': None,
            'has_reversal': False,
            'reverse_spread': 0
        }
    
    def get_positions_summary(self):
        """获取持仓摘要"""
        if not self.positions:
            return {
                'count': 0,
                'total_size': 0,
                'total_unrealized_pnl': 0,
                'positions': []
            }
        
        return {
            'count': len(self.positions),
            'total_size': sum(pos.position_size for pos in self.positions),
            'total_unrealized_pnl': sum(pos.unrealized_pnl for pos in self.positions),
            'positions': [
                {
                    'id': pos.position_id,
                    'direction': pos.direction,
                    'size': pos.position_size,
                    'entry_spread': pos.entry_spread,
                    'holding_seconds': pos.get_holding_duration(),
                    'unrealized_pnl': pos.unrealized_pnl
                }
                for pos in self.positions
            ]
        }
    
    def get_statistics(self):
        """获取交易统计"""
        if not self.closed_positions:
            return {
                'total_trades': 0,
                'total_realized_pnl': 0,
                'win_rate': 0,
                'avg_pnl': 0,
                'avg_holding_time': 0
            }
        
        wins = sum(1 for p in self.closed_positions if p['realized_pnl'] > 0)
        total = len(self.closed_positions)
        
        return {
            'total_trades': total,
            'total_realized_pnl': self.total_realized_pnl,
            'win_rate': wins / total * 100 if total > 0 else 0,
            'avg_pnl': self.total_realized_pnl / total if total > 0 else 0,
            'avg_holding_time': sum(p['holding_seconds'] for p in self.closed_positions) / total if total > 0 else 0,
            'profitable_trades': wins,
            'losing_trades': total - wins
        }


# 示例用法
if __name__ == "__main__":
    from arbitrage_calculator import ArbitrageCalculator
    
    calc = ArbitrageCalculator()
    manager = PositionManager(calc)
    
    print("=== 仓位管理器测试 ===\n")
    
    # 测试开仓
    can_open, reason = manager.can_open_position()
    print(f"是否可以开仓: {can_open} - {reason}")
    
    # 开仓
    position = manager.open_position(
        direction='FLX_TO_XYZ',
        entry_spread=0.50,
        entry_prices={'flx_bid': 423.00, 'flx_ask': 423.06, 'xyz_bid': 423.56, 'xyz_ask': 423.66},
        position_size=100
    )
    print(f"已开仓: {position}\n")
    
    # 更新持仓
    manager.update_positions(423.02, 423.08, 423.58, 423.68)
    print(f"更新后浮盈: ${position.unrealized_pnl:.4f}\n")
    
    # 检查平仓条件
    exit_check = manager.check_exit_conditions(
        position,
        423.02, 423.08, 423.02, 423.20
    )
    print(f"平仓检查: {exit_check}\n")
    
    # 获取统计
    summary = manager.get_positions_summary()
    print(f"持仓摘要: {summary}")
