"""
套利利润计算模块
提供精确的利润计算、手续费估算、开仓条件验证等功能
"""
import config
import arbitrage_config


class ArbitrageCalculator:
    """套利计算器"""
    
    def __init__(self):
        self.taker_fee = config.TAKER_FEE
        self.maker_fee = config.MAKER_FEE
    
    def calculate_open_fee(self, avg_price):
        """
        计算开仓手续费（使用Taker市价单）
        
        Args:
            avg_price: 平均价格
        
        Returns:
            开仓手续费（USDC）
        """
        # 开仓需要2笔交易（FLX和XYZ），都使用Taker
        return avg_price * self.taker_fee * 2
    
    def calculate_executable_spreads(self, flx_bid, flx_ask, xyz_bid, xyz_ask):
        """
        计算双向可执行价差
        
        Args:
            flx_bid: FLX最佳买价
            flx_ask: FLX最佳卖价
            xyz_bid: XYZ最佳买价
            xyz_ask: XYZ最佳卖价
        
        Returns:
            (flx_to_xyz_spread, xyz_to_flx_spread) 元组
            - flx_to_xyz_spread: FLX买→XYZ卖的可执行价差 (xyz_bid - flx_ask)
            - xyz_to_flx_spread: XYZ买→FLX卖的可执行价差 (flx_bid - xyz_ask)
        """
        flx_to_xyz = xyz_bid - flx_ask
        xyz_to_flx = flx_bid - xyz_ask
        return flx_to_xyz, xyz_to_flx
    
    def calculate_net_profit(self, executable_spread, avg_price, include_close_fee=False):
        """
        计算净利润（扣除手续费）
        
        Args:
            executable_spread: 可执行价差
            avg_price: 平均价格
            include_close_fee: 是否包含平仓费（保守估算用）
        
        Returns:
            净利润（USDC）
        """
        # 开仓费用（固定）
        open_fee = self.calculate_open_fee(avg_price)
        
        # 平仓费用（可选）
        close_fee = 0
        if include_close_fee:
            # 保守估算：假设使用Taker平仓
            close_fee = avg_price * self.taker_fee * 2
        
        total_fee = open_fee + close_fee
        return executable_spread - total_fee
    
    def check_profit_condition(self, executable_spread, avg_price):
        """
        检查是否满足开仓盈利条件
        
        Args:
            executable_spread: 可执行价差
            avg_price: 平均价格
        
        Returns:
            (is_profitable, net_profit, open_fee) 元组
        """
        open_fee = self.calculate_open_fee(avg_price)
        net_profit = executable_spread - open_fee
        
        # 判断是否满足最小利润阈值
        is_profitable = net_profit > arbitrage_config.MIN_NET_PROFIT
        
        return is_profitable, net_profit, open_fee
    
    def find_best_direction(self, flx_bid, flx_ask, xyz_bid, xyz_ask, flx_mid, xyz_mid):
        """
        找出最优套利方向
        
        Args:
            flx_bid, flx_ask: FLX买卖价
            xyz_bid, xyz_ask: XYZ买卖价
            flx_mid, xyz_mid: FLX和XYZ中间价
        
        Returns:
            {
                'direction': 'FLX_TO_XYZ' 或 'XYZ_TO_FLX' 或 None,
                'spread': 可执行价差,
                'net_profit': 净利润,
                'open_fee': 开仓手续费,
                'is_profitable': 是否盈利,
                'details': {...}  # 详细信息
            }
        """
        avg_price = (flx_mid + xyz_mid) / 2
        
        # 计算双向价差
        flx_to_xyz, xyz_to_flx = self.calculate_executable_spreads(
            flx_bid, flx_ask, xyz_bid, xyz_ask
        )
        
        # 检查双向是否盈利
        is_profitable_ftx, net_profit_ftx, open_fee = self.check_profit_condition(
            flx_to_xyz, avg_price
        )
        is_profitable_xtf, net_profit_xtf, _ = self.check_profit_condition(
            xyz_to_flx, avg_price
        )
        
        # 选择最优方向
        if is_profitable_ftx and is_profitable_xtf:
            # 两个方向都盈利，选择利润更大的
            if net_profit_ftx >= net_profit_xtf:
                direction = 'FLX_TO_XYZ'
                spread = flx_to_xyz
                net_profit = net_profit_ftx
                is_profitable = True
            else:
                direction = 'XYZ_TO_FLX'
                spread = xyz_to_flx
                net_profit = net_profit_xtf
                is_profitable = True
        elif is_profitable_ftx:
            direction = 'FLX_TO_XYZ'
            spread = flx_to_xyz
            net_profit = net_profit_ftx
            is_profitable = True
        elif is_profitable_xtf:
            direction = 'XYZ_TO_FLX'
            spread = xyz_to_flx
            net_profit = net_profit_xtf
            is_profitable = True
        else:
            # 都不盈利，返回价差较大的方向（用于监控）
            if flx_to_xyz >= xyz_to_flx:
                direction = 'FLX_TO_XYZ'
                spread = flx_to_xyz
                net_profit = net_profit_ftx
            else:
                direction = 'XYZ_TO_FLX'
                spread = xyz_to_flx
                net_profit = net_profit_xtf
            is_profitable = False
        
        return {
            'direction': direction if is_profitable else None,
            'spread': spread,
            'net_profit': net_profit,
            'open_fee': open_fee,
            'is_profitable': is_profitable,
            'details': {
                'flx_to_xyz_spread': flx_to_xyz,
                'xyz_to_flx_spread': xyz_to_flx,
                'flx_to_xyz_profit': net_profit_ftx,
                'xyz_to_flx_profit': net_profit_xtf,
                'avg_price': avg_price
            }
        }
    
    def check_reversal_opportunity(self, current_direction, flx_bid, flx_ask, xyz_bid, xyz_ask):
        """
        检查是否存在价差反转平仓机会
        
        Args:
            current_direction: 当前持仓方向 ('FLX_TO_XYZ' 或 'XYZ_TO_FLX')
            flx_bid, flx_ask, xyz_bid, xyz_ask: 当前市场价格
        
        Returns:
            (has_reversal, reverse_spread) 元组
        """
        flx_to_xyz, xyz_to_flx = self.calculate_executable_spreads(
            flx_bid, flx_ask, xyz_bid, xyz_ask
        )
        
        if current_direction == 'FLX_TO_XYZ':
            # 原来是FLX买XYZ卖，现在检查反向（XYZ买FLX卖）是否有利
            reverse_spread = xyz_to_flx
            has_reversal = reverse_spread > arbitrage_config.REVERSAL_MIN_SPREAD
        elif current_direction == 'XYZ_TO_FLX':
            # 原来是XYZ买FLX卖，现在检查反向（FLX买XYZ卖）是否有利
            reverse_spread = flx_to_xyz
            has_reversal = reverse_spread > arbitrage_config.REVERSAL_MIN_SPREAD
        else:
            has_reversal = False
            reverse_spread = 0
        
        return has_reversal, reverse_spread
    
    def calculate_unrealized_pnl(self, position, current_flx_bid, current_flx_ask, 
                                  current_xyz_bid, current_xyz_ask):
        """
        计算持仓的未实现盈亏
        
        Args:
            position: Position对象
            current_flx_bid, current_flx_ask, current_xyz_bid, current_xyz_ask: 当前价格
        
        Returns:
            未实现盈亏（USDC）
        """
        # 检查反转机会
        has_reversal, reverse_spread = self.check_reversal_opportunity(
            position.direction,
            current_flx_bid, current_flx_ask,
            current_xyz_bid, current_xyz_ask
        )
        
        if has_reversal:
            # 如果有反转机会，未实现盈亏 = 反向价差 - 开仓费
            # （因为反转平仓只需支付新开仓的手续费）
            avg_price = (current_flx_bid + current_flx_ask + 
                        current_xyz_bid + current_xyz_ask) / 4
            open_fee = self.calculate_open_fee(avg_price)
            unrealized_pnl = reverse_spread - open_fee
        else:
            # 没有反转机会，计算常规平仓的盈亏
            # 未实现盈亏 = 当前价差 - 原开仓价差 - 平仓费
            if position.direction == 'FLX_TO_XYZ':
                current_spread = current_xyz_bid - current_flx_ask
            else:
                current_spread = current_flx_bid - current_xyz_ask
            
            # 计算平仓费（保守使用Taker）
            avg_price = (current_flx_bid + current_flx_ask + 
                        current_xyz_bid + current_xyz_ask) / 4
            close_fee = avg_price * self.taker_fee * 2
            
            # 盈亏 = (当前价差 - 开仓价差) - 平仓费
            spread_change = current_spread - position.entry_spread
            unrealized_pnl = spread_change - close_fee
        
        return unrealized_pnl


# 示例用法
if __name__ == "__main__":
    calc = ArbitrageCalculator()
    
    # 示例价格
    flx_bid, flx_ask = 423.00, 423.06
    xyz_bid, xyz_ask = 423.01, 423.25
    flx_mid = (flx_bid + flx_ask) / 2
    xyz_mid = (xyz_bid + xyz_ask) / 2
    
    # 找出最优方向
    result = calc.find_best_direction(flx_bid, flx_ask, xyz_bid, xyz_ask, flx_mid, xyz_mid)
    
    print("=== 套利机会分析 ===")
    print(f"最优方向: {result['direction']}")
    print(f"可执行价差: ${result['spread']:.4f}")
    print(f"开仓手续费: ${result['open_fee']:.4f}")
    print(f"净利润: ${result['net_profit']:.4f}")
    print(f"是否盈利: {result['is_profitable']}")
    print(f"\n详细信息:")
    print(f"  FLX→XYZ价差: ${result['details']['flx_to_xyz_spread']:.4f} (净利润: ${result['details']['flx_to_xyz_profit']:.4f})")
    print(f"  XYZ→FLX价差: ${result['details']['xyz_to_flx_spread']:.4f} (净利润: ${result['details']['xyz_to_flx_profit']:.4f})")
