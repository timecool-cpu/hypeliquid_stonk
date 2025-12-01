"""
Hyperliquid TSLA 套利监控系统
监控 flx:TSLA 和 xyz:TSLA 之间的价差
"""
import sys
import time
import csv
import argparse
from datetime import datetime
from hyperliquid.info import Info
from hyperliquid.utils import constants
import config
import utils


class SpreadMonitor:
    """价差监控器"""
    
    def __init__(self, test_mode=False):
        """
        初始化监控器
        
        Args:
            test_mode: 测试模式，只抓取一次数据
        """
        self.test_mode = test_mode
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        self.spread_history = []  # 用于趋势分析
        self.last_analysis = None  # 上一次的分析结果
        self.direction_start_time = None  # 当前方向开始时间
        self.current_direction = None  # 当前优势方向
        self.direction_count = 0  # 当前方向持续次数
        
        # 初始化日志文件
        if config.ENABLE_LOGGING:
            self._initialize_log_file()
    
    def _initialize_log_file(self):
        """初始化CSV日志文件"""
        try:
            with open(config.LOG_FILE, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'flx_bid', 'flx_ask', 'flx_mid',
                    'xyz_bid', 'xyz_ask', 'xyz_mid',
                    'spread_abs', 'spread_pct',
                    'exec_spread_flx_to_xyz', 'exec_spread_xyz_to_flx',
                    'net_profit_flx_to_xyz', 'net_profit_xyz_to_flx',
                    'arbitrage_opportunity'
                ])
        except Exception as e:
            print(f"警告：无法创建日志文件 {config.LOG_FILE}: {e}")
    
    def log_data(self, analysis):
        """
        记录数据到CSV文件
        
        Args:
            analysis: 分析结果字典
        """
        if not config.ENABLE_LOGGING or not analysis:
            return
        
        try:
            with open(config.LOG_FILE, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    analysis['timestamp'],
                    analysis['flx']['bid'],
                    analysis['flx']['ask'],
                    analysis['flx']['mid'],
                    analysis['xyz']['bid'],
                    analysis['xyz']['ask'],
                    analysis['xyz']['mid'],
                    analysis['mid_spread'],
                    analysis['mid_spread_pct'],
                    analysis['executable_spread_flx_to_xyz'],
                    analysis['executable_spread_xyz_to_flx'],
                    analysis['net_profit_flx_to_xyz'],
                    analysis['net_profit_xyz_to_flx'],
                    'YES' if analysis['arbitrage'] else 'NO'
                ])
        except Exception as e:
            print(f"记录数据失败: {e}")

    
    def get_orderbook(self, coin):
        """
        获取订单簿数据
        
        Args:
            coin: 币种名称（例如 "xyz:TSLA"）
        
        Returns:
            订单簿数据字典
        """
        try:
            # 直接使用 SDK 的 post 方法，因为 l2_snapshot 不支持 HIP-3 资产名称
            # l2_snapshot 内部使用 name_to_coin 映射表，但 HIP-3 资产不在映射表中
            orderbook = self.info.post("/info", {"type": "l2Book", "coin": coin})
            return orderbook
        except Exception as e:
            print(f"获取 {coin} 订单簿失败: {e}")
            return None
    
    def fetch_market_data(self):
        """
        获取两个市场的数据
        
        Returns:
            (flx_data, xyz_data) 元组
        """
        flx_data = self.get_orderbook(config.ASSET_PAIR_1)
        xyz_data = self.get_orderbook(config.ASSET_PAIR_2)
        return flx_data, xyz_data
    
    def analyze_spread(self, flx_data, xyz_data):
        """
        分析价差 - 关注可执行价差而非中间价差异
        
        Args:
            flx_data: flx:TSLA 订单簿数据
            xyz_data: xyz:TSLA 订单簿数据
        
        Returns:
            分析结果字典
        """
        if not flx_data or not xyz_data:
            return None
        
        # 获取最佳买卖价
        flx_bid, flx_ask = utils.get_best_bid_ask(flx_data)
        xyz_bid, xyz_ask = utils.get_best_bid_ask(xyz_data)
        
        if not all([flx_bid, flx_ask, xyz_bid, xyz_ask]):
            return None
        
        # 计算中间价（仅供参考）
        flx_mid = (flx_bid + flx_ask) / 2
        xyz_mid = (xyz_bid + xyz_ask) / 2
        mid_spread = abs(flx_mid - xyz_mid)
        mid_spread_pct = utils.calculate_spread_percentage(flx_mid, xyz_mid)
        
        # 计算可执行价差（这才是真正的套利机会）
        # 方向1: 在 FLX 买入 (ask), 在 XYZ 卖出 (bid)
        executable_spread_flx_to_xyz = xyz_bid - flx_ask
        
        # 方向2: 在 XYZ 买入 (ask), 在 FLX 卖出 (bid)
        executable_spread_xyz_to_flx = flx_bid - xyz_ask
        
        # 估算手续费成本 (taker fee 双边)
        avg_price = (flx_mid + xyz_mid) / 2
        fee_cost = avg_price * config.TAKER_FEE * 2
        
        # 计算净利润
        net_profit_flx_to_xyz = executable_spread_flx_to_xyz - fee_cost
        net_profit_xyz_to_flx = executable_spread_xyz_to_flx - fee_cost
        
        # 确定最佳套利机会
        arbitrage_opportunity = None
        
        if net_profit_flx_to_xyz > 0:
            arbitrage_opportunity = {
                'direction': 'FLX买->XYZ卖',
                'buy_market': 'FLX',
                'sell_market': 'XYZ',
                'buy_price': flx_ask,
                'sell_price': xyz_bid,
                'gross_spread': executable_spread_flx_to_xyz,
                'fee_cost': fee_cost,
                'net_profit': net_profit_flx_to_xyz,
                'profit_pct': (net_profit_flx_to_xyz / avg_price) * 100,
                'position_size': config.DEFAULT_POSITION_SIZE
            }
        elif net_profit_xyz_to_flx > 0:
            arbitrage_opportunity = {
                'direction': 'XYZ买->FLX卖',
                'buy_market': 'XYZ',
                'sell_market': 'FLX',
                'buy_price': xyz_ask,
                'sell_price': flx_bid,
                'gross_spread': executable_spread_xyz_to_flx,
                'fee_cost': fee_cost,
                'net_profit': net_profit_xyz_to_flx,
                'profit_pct': (net_profit_xyz_to_flx / avg_price) * 100,
                'position_size': config.DEFAULT_POSITION_SIZE
            }
        
        return {
            'timestamp': utils.format_timestamp(),
            'flx': {
                'bid': flx_bid,
                'ask': flx_ask,
                'mid': flx_mid,
                'orderbook': flx_data
            },
            'xyz': {
                'bid': xyz_bid,
                'ask': xyz_ask,
                'mid': xyz_mid,
                'orderbook': xyz_data
            },
            'mid_spread': mid_spread,  # 仅供参考
            'mid_spread_pct': mid_spread_pct,  # 仅供参考
            'executable_spread_flx_to_xyz': executable_spread_flx_to_xyz,
            'executable_spread_xyz_to_flx': executable_spread_xyz_to_flx,
            'net_profit_flx_to_xyz': net_profit_flx_to_xyz,
            'net_profit_xyz_to_flx': net_profit_xyz_to_flx,
            'arbitrage': arbitrage_opportunity
        }
    
    def display_market_data(self, analysis):
        """
        在终端显示市场数据 - 重点显示可执行价差和趋势
        
        Args:
            analysis: 分析结果字典
        """
        if not analysis:
            print("无法获取市场数据")
            return
        
        utils.print_header(f"TSLA 套利监控 - {analysis['timestamp']}")
        
        # 显示 flx:TSLA 数据
        print(f"\n{utils.Fore.CYAN}【flx:TSLA】{utils.Style.RESET_ALL}")
        print(f"  买一(Bid): {utils.format_price(analysis['flx']['bid'])}")
        print(f"  卖一(Ask): {utils.format_price(analysis['flx']['ask'])}")
        print(f"  盘口价差: {utils.format_price(analysis['flx']['ask'] - analysis['flx']['bid'], 6)}")
        
        # 显示 xyz:TSLA 数据
        print(f"\n{utils.Fore.CYAN}【xyz:TSLA】{utils.Style.RESET_ALL}")
        print(f"  买一(Bid): {utils.format_price(analysis['xyz']['bid'])}")
        print(f"  卖一(Ask): {utils.format_price(analysis['xyz']['ask'])}")
        print(f"  盘口价差: {utils.format_price(analysis['xyz']['ask'] - analysis['xyz']['bid'], 6)}")
        
        # 显示可执行价差分析
        utils.print_separator()
        print(f"\n{utils.Fore.MAGENTA}【可执行价差分析】{utils.Style.RESET_ALL}")
        
        # 方向1: FLX买->XYZ卖
        spread1 = analysis['executable_spread_flx_to_xyz']
        profit1 = analysis['net_profit_flx_to_xyz']
        color1 = utils.Fore.GREEN if profit1 > 0 else utils.Fore.RED
        
        print(f"\n  方向1: FLX买入(${utils.format_price(analysis['flx']['ask'])}) -> "
              f"XYZ卖出(${utils.format_price(analysis['xyz']['bid'])})")
        print(f"    毛价差: {color1}${utils.format_price(spread1, 6)}{utils.Style.RESET_ALL}", end='')
        
        # 显示价差变化趋势
        if self.last_analysis:
            last_spread1 = self.last_analysis['executable_spread_flx_to_xyz']
            change1 = spread1 - last_spread1
            if abs(change1) > 0.001:
                trend_symbol = "📈" if change1 > 0 else "📉"
                trend_color = utils.Fore.GREEN if change1 > 0 else utils.Fore.RED
                print(f" {trend_symbol} {trend_color}{change1:+.4f}{utils.Style.RESET_ALL}", end='')
        print()
        
        print(f"    扣费后: {color1}${utils.format_price(profit1, 6)}{utils.Style.RESET_ALL}", end='')
        if profit1 > 0:
            print(f" {utils.Fore.GREEN}✓ 有利可图{utils.Style.RESET_ALL}")
        else:
            print(f" {utils.Fore.RED}✗ 无利润{utils.Style.RESET_ALL}")
        
        # 方向2: XYZ买->FLX卖
        spread2 = analysis['executable_spread_xyz_to_flx']
        profit2 = analysis['net_profit_xyz_to_flx']
        color2 = utils.Fore.GREEN if profit2 > 0 else utils.Fore.RED
        
        print(f"\n  方向2: XYZ买入(${utils.format_price(analysis['xyz']['ask'])}) -> "
              f"FLX卖出(${utils.format_price(analysis['flx']['bid'])})")
        print(f"    毛价差: {color2}${utils.format_price(spread2, 6)}{utils.Style.RESET_ALL}", end='')
        
        # 显示价差变化趋势
        if self.last_analysis:
            last_spread2 = self.last_analysis['executable_spread_xyz_to_flx']
            change2 = spread2 - last_spread2
            if abs(change2) > 0.001:
                trend_symbol = "📈" if change2 > 0 else "📉"
                trend_color = utils.Fore.GREEN if change2 > 0 else utils.Fore.RED
                print(f" {trend_symbol} {trend_color}{change2:+.4f}{utils.Style.RESET_ALL}", end='')
        print()
        
        print(f"    扣费后: {color2}${utils.format_price(profit2, 6)}{utils.Style.RESET_ALL}", end='')
        if profit2 > 0:
            print(f" {utils.Fore.GREEN}✓ 有利可图{utils.Style.RESET_ALL}")
        else:
            print(f" {utils.Fore.RED}✗ 无利润{utils.Style.RESET_ALL}")
        
        # 显示优势方向和持续时间
        utils.print_separator()
        current_favorable = 'FLX->XYZ' if spread1 > spread2 else 'XYZ->FLX'
        
        if self.current_direction != current_favorable:
            # 方向改变
            self.current_direction = current_favorable
            self.direction_start_time = analysis['timestamp']
            self.direction_count = 1
        else:
            # 方向持续
            self.direction_count += 1
        
        duration_seconds = self.direction_count * config.REFRESH_INTERVAL
        duration_str = f"{duration_seconds}秒" if duration_seconds < 60 else f"{duration_seconds/60:.1f}分钟"
        
        print(f"\n{utils.Fore.YELLOW}【当前优势方向】{utils.Style.RESET_ALL}")
        print(f"  {current_favorable} (已持续 {self.direction_count} 次, {duration_str})")
        
        # 策略建议
        print(f"\n{utils.Fore.CYAN}【策略信号】{utils.Style.RESET_ALL}")
        
        # 策略1：收敛信号
        if self.last_analysis:
            spread_diff = abs(spread1 - spread2)
            last_spread_diff = abs(self.last_analysis['executable_spread_flx_to_xyz'] - 
                                  self.last_analysis['executable_spread_xyz_to_flx'])
            
            if spread_diff < last_spread_diff:
                print(f"  💚 策略1(收敛): 价差正在缩小 (利好)")
            elif spread_diff > last_spread_diff:
                print(f"  💔 策略1(收敛): 价差正在扩大 (不利)")
            else:
                print(f"  ⚪ 策略1(收敛): 价差稳定")
        
        # 策略2：反转信号
        if self.direction_count == 1 and self.last_analysis:
            print(f"  🔄 策略2(反转): 刚发生方向反转！")
        elif self.direction_count > 10:
            print(f"  ⚠️  策略2(反转): 方向长期未变 ({duration_str})")
        else:
            print(f"  ⏳ 策略2(反转): 等待反转...")
        
        # 显示套利机会
        utils.print_separator()
        if analysis['arbitrage']:
            arb = analysis['arbitrage']
            print(f"\n{utils.Fore.GREEN}{utils.Style.BRIGHT}⚡ 套利机会！{utils.Style.RESET_ALL}")
            print(f"\n  策略: {arb['direction']}")
            print(f"  买入市场: {arb['buy_market']} @ ${utils.format_price(arb['buy_price'])}")
            print(f"  卖出市场: {arb['sell_market']} @ ${utils.format_price(arb['sell_price'])}")
            print(f"  毛价差: ${utils.format_price(arb['gross_spread'], 6)}")
            print(f"  手续费: ${utils.format_price(arb['fee_cost'], 6)}")
            print(f"  净利润: {utils.Fore.GREEN}${utils.format_price(arb['net_profit'], 6)}{utils.Style.RESET_ALL} "
                  f"({arb['profit_pct']:.4f}%)")
            print(f"  建议仓位: ${arb['position_size']}")
        else:
            print(f"\n  {utils.Fore.YELLOW}暂无套利机会（两个方向扣费后均无盈利）{utils.Style.RESET_ALL}")
        
        # 显示订单簿深度（可选）
        if self.test_mode:
            self._display_orderbook_depth(analysis)
        
        print()
        
        # 保存当前分析供下次比较
        self.last_analysis = analysis
    
    def _display_orderbook_depth(self, analysis):
        """显示订单簿深度"""
        utils.print_separator()
        print(f"\n{utils.Fore.CYAN}【订单簿深度】{utils.Style.RESET_ALL}")
        
        for market in ['flx', 'xyz']:
            print(f"\n{market.upper()}:TSLA")
            orderbook = analysis[market]['orderbook']
            
            if 'levels' in orderbook and len(orderbook['levels']) >= 2:
                bids = orderbook['levels'][0][:config.SHOW_ORDERBOOK_DEPTH]
                asks = orderbook['levels'][1][:config.SHOW_ORDERBOOK_DEPTH]
                
                print(f"  {'卖单' : <10} {'价格' : >12} {'数量' : >12}")
                for i, ask in enumerate(reversed(asks)):
                    print(f"  {utils.Fore.RED}Ask {len(asks)-i} {ask['px'] : >12} {ask['sz'] : >12}{utils.Style.RESET_ALL}")
                
                utils.print_separator()
                
                print(f"  {'买单' : <10} {'价格' : >12} {'数量' : >12}")
                for i, bid in enumerate(bids):
                    print(f"  {utils.Fore.GREEN}Bid {i+1} {bid['px'] : >12} {bid['sz'] : >12}{utils.Style.RESET_ALL}")
    
    def run(self):
        """运行监控"""
        print(f"{utils.Fore.GREEN}启动 Hyperliquid TSLA 套利监控...{utils.Style.RESET_ALL}")
        print(f"监控标的: {config.ASSET_PAIR_1} vs {config.ASSET_PAIR_2}")
        print(f"刷新间隔: {config.REFRESH_INTERVAL}秒")
        print(f"价差阈值: {config.SPREAD_THRESHOLD}%")
        
        if self.test_mode:
            print(f"\n{utils.Fore.YELLOW}【测试模式】仅获取一次数据{utils.Style.RESET_ALL}\n")
        else:
            print(f"\n按 Ctrl+C 停止监控\n")
        
        try:
            while True:
                # 获取市场数据
                flx_data, xyz_data = self.fetch_market_data()
                
                # 分析价差
                analysis = self.analyze_spread(flx_data, xyz_data)
                
                # 显示数据
                self.display_market_data(analysis)
                
                # 记录数据
                self.log_data(analysis)
                
                # 测试模式只运行一次
                if self.test_mode:
                    break
                
                # 等待下一次刷新
                time.sleep(config.REFRESH_INTERVAL)
        
        except KeyboardInterrupt:
            print(f"\n\n{utils.Fore.YELLOW}监控已停止{utils.Style.RESET_ALL}")
            sys.exit(0)
        except Exception as e:
            print(f"\n{utils.Fore.RED}错误: {e}{utils.Style.RESET_ALL}")
            sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Hyperliquid TSLA 套利监控')
    parser.add_argument('--test-mode', action='store_true', 
                       help='测试模式：仅获取一次数据并显示')
    
    args = parser.parse_args()
    
    monitor = SpreadMonitor(test_mode=args.test_mode)
    monitor.run()


if __name__ == "__main__":
    main()
