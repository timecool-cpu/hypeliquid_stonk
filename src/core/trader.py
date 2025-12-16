"""
套利交易引擎
核心交易执行模块，整合市场数据、利润计算、仓位管理和订单执行
"""
import time
import sys
import os
from datetime import datetime
from colorama import Fore, Style, init

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

# 导入现有模块
from src.config import config, arbitrage_config
from src.core.calculator import ArbitrageCalculator
from src.core.position_manager import PositionManager, Position
from src.core.logger import ArbitrageLogger
from src.monitors.spread_profit_monitor import SpreadProfitMonitor
from src.utils import utils
from src.utils import hip3_trading  # HIP-3资产交易工具

# 导入Hyperliquid SDK
from hyperliquid.info import Info

# 初始化colorama
init(autoreset=True)


class ArbitrageTrader:
    """套利交易引擎"""
    
    def __init__(self, dry_run=True):
        """
        初始化交易引擎
        
        Args:
            dry_run: True=模拟模式，False=实盘模式
        """
        self.dry_run = dry_run if dry_run is not None else arbitrage_config.DRY_RUN
        
        # 初始化API
        self.info = Info(skip_ws=True)
        
        # 实盘模式需要初始化Exchange API
        if not self.dry_run:
            from hyperliquid.exchange import Exchange
            from hyperliquid.utils import constants
            from eth_account import Account
            
            # 从环境变量读取私钥
            private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY')
            if not private_key:
                raise ValueError("实盘模式需要设置HYPERLIQUID_PRIVATE_KEY环境变量")
            
            # 初始化Exchange，添加spot_meta和perp_dexs支持HIP-3资产
            account = Account.from_key(private_key)
            # 获取spot meta信息
            _info = Info(skip_ws=True)
            spot_meta = _info.spot_meta()
            
            # 获取所有perp_dexs（包括xyz, flx等builder-deployed dex）
            perp_dexs_response = _info.perp_dexs()
            perp_dex_names = ['']  # 默认dex
            for dex in perp_dexs_response[1:]:
                if dex and 'name' in dex:
                    perp_dex_names.append(dex['name'])
            
            self.exchange = Exchange(account, spot_meta=spot_meta, perp_dexs=perp_dex_names)
            self.wallet_address = account.address
            
            print(f"{Fore.CYAN}钱包地址: {self.wallet_address}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}已加载perp dexs: {perp_dex_names}{Style.RESET_ALL}")
        else:
            self.exchange = None
            self.wallet_address = None
        
        # 初始化核心组件
        self.calculator = ArbitrageCalculator()
        self.position_manager = PositionManager(self.calculator)
        self.logger = ArbitrageLogger()
        self.profit_monitor = SpreadProfitMonitor()
        
        # 价差历史(用于加仓判断)
        self.best_spread_seen = 0
        
        # 价差稳定性检查缓冲
        self.recent_spreads = []
        
        print(f"\n{Fore.CYAN}{'=' * 80}")
        print(f"套利交易引擎已启动")
        print(f"{'=' * 80}{Style.RESET_ALL}\n")
        print(f"模式: {Fore.YELLOW if self.dry_run else Fore.RED}{'模拟 (DRY-RUN)' if self.dry_run else '实盘 (LIVE)'}{Style.RESET_ALL}")
        print(f"监控间隔: {arbitrage_config.MONITOR_INTERVAL}秒")
        print(f"最小利润阈值: ${arbitrage_config.MIN_NET_PROFIT:.2f}")
        print(f"止盈目标: ${arbitrage_config.TAKE_PROFIT_TARGET:.2f}")
        print(f"超时兜底: {arbitrage_config.POSITION_TIMEOUT_HOURS}小时")
        print(f"价差监控日志: spread_profit_log.csv\n")
        
        # 检测并恢复现有持仓
        if not self.dry_run:
            self.detect_existing_positions()
    
    def detect_existing_positions(self):
        """
        检测并恢复现有持仓到position_manager
        在启动时调用，确保持仓连续性
        """
        try:
            print(f"\n{Fore.CYAN}检测现有持仓...{Style.RESET_ALL}")
            
            # 查询两个DEX的持仓状态
            flx_state = self.info.user_state(self.wallet_address, 'flx')
            xyz_state = self.info.user_state(self.wallet_address, 'xyz')
            
            def parse_tsla_positions(state):
                """提取state中的TSLA持仓信息"""
                positions = []
                if state and 'assetPositions' in state:
                    for pos in state['assetPositions']:
                        details = pos.get('position') or {}
                        coin = details.get('coin', '')
                        szi = float(details.get('szi', 0))
                        if 'TSLA' not in coin.upper() or szi == 0:
                            continue
                        positions.append({
                            'coin': coin,
                            'size': abs(szi),
                            'side': 'long' if szi > 0 else 'short',
                            'entry_px': float(details.get('entryPx', 0))
                        })
                return positions
            
            flx_candidates = parse_tsla_positions(flx_state)
            xyz_candidates = parse_tsla_positions(xyz_state)
            
            flx_pos = next((p for p in flx_candidates if p['coin'] == config.ASSET_PAIR_2), None)
            xyz_pos = next((p for p in xyz_candidates if p['coin'] == config.ASSET_PAIR_1), None)
            
            # builder dex通常不会把dex名前缀放在coin字段里，因此需要回退到第一条匹配项
            if not flx_pos and flx_candidates:
                flx_pos = flx_candidates[0]
                print(f"{Fore.YELLOW}提示: FLX持仓标识为 {flx_pos['coin']}，与配置 {config.ASSET_PAIR_2} 不一致，已自动匹配{Style.RESET_ALL}")
            if not xyz_pos and xyz_candidates:
                xyz_pos = xyz_candidates[0]
                print(f"{Fore.YELLOW}提示: XYZ持仓标识为 {xyz_pos['coin']}，与配置 {config.ASSET_PAIR_1} 不一致，已自动匹配{Style.RESET_ALL}")
            
            # 检查是否有配对持仓
            if flx_pos and xyz_pos:
                
                if flx_pos and xyz_pos:
                    # 判断套利方向
                    # FLX_TO_XYZ = FLX买入(做多) + XYZ卖出(做空)
                    # XYZ_TO_FLX = XYZ买入(做多) + FLX卖出(做空)
                    if flx_pos['side'] == 'long' and xyz_pos['side'] == 'short':
                        direction = 'FLX_TO_XYZ'
                    elif flx_pos['side'] == 'short' and xyz_pos['side'] == 'long':
                        direction = 'XYZ_TO_FLX'
                    else:
                        print(f"{Fore.YELLOW}警告: 持仓方向不匹配，无法恢复{Style.RESET_ALL}")
                        print(f"  FLX: {flx_pos['side']}, XYZ: {xyz_pos['side']}")
                        return
                    
                    # 计算开仓价差和价格
                    flx_entry = flx_pos['entry_px']
                    xyz_entry = xyz_pos['entry_px']
                    
                    if direction == 'FLX_TO_XYZ':
                        entry_spread = xyz_entry - flx_entry
                        entry_prices = {
                            'flx_bid': flx_entry,
                            'flx_ask': flx_entry,
                            'xyz_bid': xyz_entry,
                            'xyz_ask': xyz_entry
                        }
                    else:
                        entry_spread = flx_entry - xyz_entry
                        entry_prices = {
                            'flx_bid': flx_entry,
                            'flx_ask': flx_entry,
                            'xyz_bid': xyz_entry,
                            'xyz_ask': xyz_entry
                        }
                    
                    # 计算仓位大小（使用平均size）
                    avg_size = (flx_pos['size'] + xyz_pos['size']) / 2
                    position_size = avg_size * flx_entry  # 近似USDC价值
                    
                    # 尝试从交易日志中恢复开仓时间
                    entry_time = self._get_entry_time_from_log(direction)
                    
                    # 恢复持仓到position_manager
                    restored_position = self.position_manager.open_position(
                        direction=direction,
                        entry_spread=entry_spread,
                        entry_prices=entry_prices,
                        position_size=position_size,
                        entry_time=entry_time
                    )
                    
                    print(f"{Fore.GREEN}✓ 已恢复现有持仓:{Style.RESET_ALL}")
                    print(f"  方向: {direction}")
                    print(f"  FLX持仓: {flx_pos['side']} {flx_pos['size']} @ ${flx_entry:.2f}")
                    print(f"  XYZ持仓: {xyz_pos['side']} {xyz_pos['size']} @ ${xyz_entry:.2f}")
                    print(f"  开仓价差: ${entry_spread:.4f}")
                    if entry_time:
                        holding_hours = (datetime.now() - entry_time).total_seconds() / 3600
                        print(f"  开仓时间: {entry_time.strftime('%Y-%m-%d %H:%M:%S')} (已持仓 {holding_hours:.1f} 小时)")
                    else:
                        print(f"  开仓时间: 未知 (使用当前时间)")
                    print(f"  仓位ID: {restored_position.position_id}\n")
                    
            elif not flx_candidates and not xyz_candidates:
                print(f"{Fore.GREEN}✓ 无现有持仓{Style.RESET_ALL}\n")
            else:
                print(f"{Fore.YELLOW}警告: 检测到单边持仓，请手动检查{Style.RESET_ALL}")
                if flx_candidates:
                    print(f"  FLX持仓: {flx_candidates}")
                if xyz_candidates:
                    print(f"  XYZ持仓: {xyz_candidates}\n")
                    
        except Exception as e:
            print(f"{Fore.RED}持仓检测失败: {e}{Style.RESET_ALL}")
            import traceback
            traceback.print_exc()
    
    def _get_entry_time_from_log(self, direction):
        """
        从交易日志中获取最近一次该方向的开仓时间
        
        Args:
            direction: 套利方向 ('FLX_TO_XYZ' 或 'XYZ_TO_FLX')
        
        Returns:
            datetime对象或None
        """
        try:
            import pandas as pd
            
            log_file = arbitrage_config.TRADE_LOG_FILE
            if not os.path.exists(log_file):
                return None
            
            df = pd.read_csv(log_file)
            
            # 筛选该方向的开仓记录
            open_trades = df[(df['action'] == 'OPEN') & (df['direction'] == direction)]
            
            if open_trades.empty:
                return None
            
            # 获取所有已平仓的position_id
            closed_ids = set(df[df['action'] == 'CLOSE']['position_id'])
            
            # 找出未平仓的开仓记录
            unclosed_trades = open_trades[~open_trades['position_id'].isin(closed_ids)]
            
            if unclosed_trades.empty:
                # 如果没有未平仓记录，返回最近的开仓时间
                latest = open_trades.iloc[-1]
            else:
                # 返回最早的未平仓记录时间
                latest = unclosed_trades.iloc[0]
            
            # 解析时间
            entry_time = datetime.strptime(latest['timestamp'], '%Y-%m-%d %H:%M:%S')
            return entry_time
            
        except Exception as e:
            print(f"{Fore.YELLOW}警告: 无法从日志恢复开仓时间: {e}{Style.RESET_ALL}")
            return None
    
    def get_market_data(self):
        """
        获取市场数据
        
        Returns:
            {
                'flx_bid', 'flx_ask', 'flx_mid',
                'xyz_bid', 'xyz_ask', 'xyz_mid',
                'timestamp'
            }
            或None（获取失败）
        """
        try:
            # 获取订单簿数据 - 使用post方法支持HIP-3资产
            # l2_snapshot不支持flx:TSLA这样的格式
            flx_data = self.info.post("/info", {"type": "l2Book", "coin": config.ASSET_PAIR_2})
            xyz_data = self.info.post("/info", {"type": "l2Book", "coin": config.ASSET_PAIR_1})
            
            if not flx_data or not xyz_data:
                return None
            
            # 提取最佳买卖价
            flx_bid, flx_ask = utils.get_best_bid_ask(flx_data)
            xyz_bid, xyz_ask = utils.get_best_bid_ask(xyz_data)
            
            if not all([flx_bid, flx_ask, xyz_bid, xyz_ask]):
                return None
            
            return {
                'flx_bid': flx_bid,
                'flx_ask': flx_ask,
                'flx_mid': (flx_bid + flx_ask) / 2,
                'xyz_bid': xyz_bid,
                'xyz_ask': xyz_ask,
                'xyz_mid': (xyz_bid + xyz_ask) / 2,
                'timestamp': datetime.now()
            }
        
        except Exception as e:
            print(f"{Fore.RED}获取市场数据失败: {e}{Style.RESET_ALL}")
            return None
    
    def check_spread_stability(self, current_spread):
        """
        检查价差稳定性（连续N次采样确认）
        
        Args:
            current_spread: 当前价差
        
        Returns:
            True如果价差稳定，False否则
        """
        self.recent_spreads.append(current_spread)
        
        # 保持最近N次采样
        if len(self.recent_spreads) > arbitrage_config.SPREAD_STABILITY_CHECKS:
            self.recent_spreads.pop(0)
        
        # 需要足够的采样
        if len(self.recent_spreads) < arbitrage_config.SPREAD_STABILITY_CHECKS:
            return False
        
        # 检查价差是否稳定（波动小）
        avg_spread = sum(self.recent_spreads) / len(self.recent_spreads)
        max_deviation = max(abs(s - avg_spread) for s in self.recent_spreads)
        
        # 允许10%的波动
        is_stable = max_deviation < avg_spread * 0.1
        
        return is_stable
    
    def find_arbitrage_opportunity(self, market_data):
        """
        寻找套利机会
        
        Args:
            market_data: 市场数据字典
        
        Returns:
            套利机会字典或None
        """
        result = self.calculator.find_best_direction(
            market_data['flx_bid'], market_data['flx_ask'],
            market_data['xyz_bid'], market_data['xyz_ask'],
            market_data['flx_mid'], market_data['xyz_mid']
        )
        
        if not result['is_profitable']:
            return None
        
        # 若已有持仓且禁止叠加新仓，则直接跳过避免重复开单
        if (len(self.position_manager.positions) > 0 and
                not arbitrage_config.ALLOW_POSITION_STACKING):
            print(f"{Fore.YELLOW}已有持仓{len(self.position_manager.positions)}笔，配置禁止叠加新仓，等待当前仓位处理完毕...{Style.RESET_ALL}")
            return None
        
        # 检查价差稳定性
        if not self.check_spread_stability(result['spread']):
            return None
        
        # 检查是否可以开仓或加仓
        if len(self.position_manager.positions) == 0:
            # 首次开仓
            can_trade, reason = self.position_manager.can_open_position()
        else:
            # 检查加仓条件
            can_trade, reason = self.position_manager.can_add_position(
                result['spread'],
                self.best_spread_seen
            )
        
        if not can_trade:
            return None
        
        return result
    
    def execute_open(self, opportunity, market_data):
        """
        执行开仓（市价单）
        
        Args:
            opportunity: 套利机会字典
            market_data: 市场数据
        
        Returns:
            Position对象或None
        """
        if self.dry_run:
            print(f"\n{Fore.GREEN}{'=' * 80}")
            print(f"[DRY-RUN] 模拟开仓")
            print(f"{'=' * 80}{Style.RESET_ALL}")
            print(f"方向: {opportunity['direction']}")
            print(f"可执行价差: ${opportunity['spread']:.4f}")
            print(f"开仓手续费: ${opportunity['open_fee']:.4f}")
            print(f"预期净利润: ${opportunity['net_profit']:.4f}")
            print(f"仓位大小: ${arbitrage_config.INITIAL_POSITION_SIZE}")
            
            # 模拟开仓
            position = self.position_manager.open_position(
                direction=opportunity['direction'],
                entry_spread=opportunity['spread'],
                entry_prices={
                    'flx_bid': market_data['flx_bid'],
                    'flx_ask': market_data['flx_ask'],
                    'xyz_bid': market_data['xyz_bid'],
                    'xyz_ask': market_data['xyz_ask']
                },
                position_size=arbitrage_config.INITIAL_POSITION_SIZE
            )
            
            # 记录日志
            self.logger.log_open_position(position, notes='DRY-RUN模拟交易')
            
            # 更新历史最佳价差
            if opportunity['spread'] > self.best_spread_seen:
                self.best_spread_seen = opportunity['spread']
            
            print(f"{Fore.GREEN}开仓成功: {position.position_id}{Style.RESET_ALL}\n")
            
            return position
        
        
        else:
            # 实盘交易逻辑
            print(f"\n{Fore.RED}{'=' * 80}")
            print(f"[LIVE] 实盘开仓")
            print(f"{'=' * 80}{Style.RESET_ALL}")
            print(f"方向: {opportunity['direction']}")
            print(f"可执行价差: ${opportunity['spread']:.4f}")
            print(f"预期净利润: ${opportunity['net_profit']:.4f}")
            print(f"仓位大小: ${arbitrage_config.INITIAL_POSITION_SIZE}")
            
            try:
                # 计算每个币种的数量
                position_size_usd = arbitrage_config.INITIAL_POSITION_SIZE
                
                # FLX和XYZ都用同一个价格（mid price）来计算数量
                avg_price = (market_data['flx_mid'] + market_data['xyz_mid']) / 2
                coin_quantity_raw = position_size_usd / avg_price
                
                # 获取每个资产的szDecimals
                flx_asset = self.exchange.info.name_to_asset(config.ASSET_PAIR_2)
                xyz_asset = self.exchange.info.name_to_asset(config.ASSET_PAIR_1)
                flx_sz_decimals = self.exchange.info.asset_to_sz_decimals.get(flx_asset, 2)
                xyz_sz_decimals = self.exchange.info.asset_to_sz_decimals.get(xyz_asset, 3)
                
                # 使用较小的szDecimals确保两边数量一致（FLX是2位，XYZ是3位，统一用2位）
                unified_decimals = min(flx_sz_decimals, xyz_sz_decimals)
                coin_quantity = round(coin_quantity_raw, unified_decimals)
                
                flx_quantity = coin_quantity
                xyz_quantity = coin_quantity
                
                # 根据方向下单
                if opportunity['direction'] == 'FLX_TO_XYZ':
                    # FLX买入（做多），XYZ卖出（做空）
                    flx_is_buy = True
                    xyz_is_buy = False
                    print(f"策略: 买入FLX做多 {flx_quantity}张, 卖出XYZ做空 {xyz_quantity}张")
                else:  # XYZ_TO_FLX
                    # XYZ买入（做多），FLX卖出（做空）
                    flx_is_buy = False
                    xyz_is_buy = True
                    print(f"策略: 卖出FLX做空 {flx_quantity}张, 买入XYZ做多 {xyz_quantity}张")
                
                # 下单FLX - 使用SDK原生market_open方法
                print(f"\n下单 {config.ASSET_PAIR_2} ({'买入' if flx_is_buy else '卖出'})...")
                flx_order = self.exchange.market_open(
                    name=config.ASSET_PAIR_2,
                    is_buy=flx_is_buy,
                    sz=flx_quantity,
                    slippage=0.03  # 3%滑点保护
                )
                print(f"FLX订单响应: {flx_order}")
                
                # 下单XYZ - 使用SDK原生market_open方法
                print(f"\n下单 {config.ASSET_PAIR_1} ({'买入' if xyz_is_buy else '卖出'})...")
                xyz_order = self.exchange.market_open(
                    name=config.ASSET_PAIR_1,
                    is_buy=xyz_is_buy,
                    sz=xyz_quantity,
                    slippage=0.03  # 3%滑点保护
                )
                print(f"XYZ订单响应: {xyz_order}")
                
                # 检查订单状态 - SDK返回格式: {'status': 'ok', 'response': {'type': 'order', 'data': {'statuses': [...]}}}
                def check_order_success(order_response):
                    """检查订单是否成功成交"""
                    if order_response.get('status') != 'ok':
                        return False, "status not ok"
                    statuses = order_response.get('response', {}).get('data', {}).get('statuses', [])
                    if not statuses:
                        return False, "no statuses"
                    first_status = statuses[0]
                    if 'filled' in first_status:
                        return True, first_status['filled']
                    elif 'error' in first_status:
                        return False, first_status['error']
                    return False, "unknown status"
                
                flx_success, flx_info = check_order_success(flx_order)
                xyz_success, xyz_info = check_order_success(xyz_order)
                
                if flx_success and xyz_success:
                    print(f"\n{Fore.GREEN}✓ 开仓成功！{Style.RESET_ALL}")
                    
                    # 创建仓位记录
                    position = self.position_manager.open_position(
                        direction=opportunity['direction'],
                        entry_spread=opportunity['spread'],
                        entry_prices={
                            'flx_bid': market_data['flx_bid'],
                            'flx_ask': market_data['flx_ask'],
                            'xyz_bid': market_data['xyz_bid'],
                            'xyz_ask': market_data['xyz_ask']
                        },
                        position_size=position_size_usd
                    )
                    
                    # 记录日志
                    self.logger.log_open_position(
                        position, 
                        notes=f'LIVE实盘交易 | FLX:{flx_order} | XYZ:{xyz_order}'
                    )
                    
                    # 更新历史最佳价差
                    if opportunity['spread'] > self.best_spread_seen:
                        self.best_spread_seen = opportunity['spread']
                    
                    return position
                else:
                    print(f"\n{Fore.RED}✗ 开仓失败{Style.RESET_ALL}")
                    if not flx_success:
                        print(f"FLX失败: {flx_info}")
                    if not xyz_success:
                        print(f"XYZ失败: {xyz_info}")
                    
                    # 回滚：如果一边成功另一边失败，需要平掉成功的那边
                    if flx_success and not xyz_success:
                        print(f"{Fore.YELLOW}回滚: 平掉FLX仓位...{Style.RESET_ALL}")
                        try:
                            rollback = self.exchange.market_close('flx:TSLA', slippage=0.05)
                            print(f"回滚结果: {rollback}")
                        except Exception as e:
                            print(f"{Fore.RED}回滚失败: {e}{Style.RESET_ALL}")
                    elif xyz_success and not flx_success:
                        print(f"{Fore.YELLOW}回滚: 平掉XYZ仓位...{Style.RESET_ALL}")
                        try:
                            rollback = self.exchange.market_close('xyz:TSLA', slippage=0.05)
                            print(f"回滚结果: {rollback}")
                        except Exception as e:
                            print(f"{Fore.RED}回滚失败: {e}{Style.RESET_ALL}")
                    
                    return None
                    
            except Exception as e:
                print(f"\n{Fore.RED}开仓异常: {e}{Style.RESET_ALL}")
                import traceback
                traceback.print_exc()
                return None
    
    def execute_close(self, position, market_data, exit_info):
        """
        执行平仓
        
        Args:
            position: Position对象
            market_data: 市场数据
            exit_info: 平仓信息字典
        
        Returns:
            平仓记录或None
        """
        if self.dry_run:
            print(f"\n{Fore.YELLOW}{'=' * 80}")
            print(f"[DRY-RUN] 模拟平仓")
            print(f"{'=' * 80}{Style.RESET_ALL}")
            print(f"仓位ID: {position.position_id}")
            print(f"平仓原因: {exit_info['exit_reason']}")
            print(f"平仓方式: {exit_info['exit_method']}")
            print(f"持仓时长: {position.get_holding_duration() / 60:.1f} 分钟")
            
            # 计算实际盈亏
            if exit_info['exit_method'] == 'reversal':
                # 反转平仓：零成本
                realized_pnl = exit_info['reverse_spread'] - self.calculator.calculate_open_fee(
                    (market_data['flx_mid'] + market_data['xyz_mid']) / 2
                )
                print(f"反转价差: ${exit_info['reverse_spread']:.4f}")
            else:
                # 常规平仓
                realized_pnl = position.unrealized_pnl
            
            print(f"实现盈亏: {utils.color_text(f'${realized_pnl:.4f}', realized_pnl > 0)}")
            
            # 平仓
            close_record = self.position_manager.close_position(
                position=position,
                exit_prices={
                    'flx_bid': market_data['flx_bid'],
                    'flx_ask': market_data['flx_ask'],
                    'xyz_bid': market_data['xyz_bid'],
                    'xyz_ask': market_data['xyz_ask']
                },
                exit_method=exit_info['exit_method'],
                realized_pnl=realized_pnl
            )
            
            # 记录日志
            self.logger.log_close_position(close_record, notes='DRY-RUN模拟交易')
            self.logger.print_trade_summary(close_record)
            
            return close_record
        
        
        else:
            # 实盘平仓逻辑
            print(f"\n{Fore.YELLOW}{'=' * 80}")
            print(f"[LIVE] 实盘平仓")
            print(f"{'=' * 80}{Style.RESET_ALL}")
            print(f"仓位ID: {position.position_id}")
            print(f"平仓原因: {exit_info['exit_reason']}")
            print(f"平仓方式: {exit_info['exit_method']}")
            print(f"持仓时长: {position.get_holding_duration() / 60:.1f} 分钟")
            
            try:
                # 计算币种数量（用于显示）
                avg_price = (market_data['flx_mid'] + market_data['xyz_mid']) / 2
                coin_quantity_raw = position.position_size / avg_price
                
                # 获取每个资产的szDecimals
                flx_asset = self.exchange.info.name_to_asset(config.ASSET_PAIR_2)
                xyz_asset = self.exchange.info.name_to_asset(config.ASSET_PAIR_1)
                flx_sz_decimals = self.exchange.info.asset_to_sz_decimals.get(flx_asset, 2)
                xyz_sz_decimals = self.exchange.info.asset_to_sz_decimals.get(xyz_asset, 3)
                
                # 使用较小的szDecimals确保两边数量一致
                unified_decimals = min(flx_sz_decimals, xyz_sz_decimals)
                coin_quantity = round(coin_quantity_raw, unified_decimals)
                
                flx_quantity = coin_quantity
                xyz_quantity = coin_quantity
                
                # 根据原方向平仓（反向操作）
                if position.direction == 'FLX_TO_XYZ':
                    # 原来是FLX多XYZ空，现在平仓：FLX卖出（平多），XYZ买入（平空）
                    print(f"平仓策略: 平FLX多头 {flx_quantity}张, 平XYZ空头 {xyz_quantity}张")
                else:  # XYZ_TO_FLX
                    # 原来是XYZ多FLX空，现在平仓：XYZ卖出（平多），FLX买入（平空）
                    print(f"平仓策略: 平FLX空头 {flx_quantity}张, 平XYZ多头 {xyz_quantity}张")
                
                # 平仓FLX - 使用SDK原生market_close方法（不指定sz，自动平全部仓位）
                print(f"\n平仓 {config.ASSET_PAIR_2}...")
                flx_close = self.exchange.market_close(
                    coin=config.ASSET_PAIR_2,
                    slippage=0.03  # 3%滑点保护
                )
                print(f"FLX平仓响应: {flx_close}")
                
                # 平仓XYZ - 使用SDK原生market_close方法（不指定sz，自动平全部仓位）
                print(f"\n平仓 {config.ASSET_PAIR_1}...")
                xyz_close = self.exchange.market_close(
                    coin=config.ASSET_PAIR_1,
                    slippage=0.03  # 3%滑点保护
                )
                print(f"XYZ平仓响应: {xyz_close}")
                
                # 检查平仓状态 - 平仓可能返回None（无仓位）或订单结果
                def check_close_success(close_response):
                    """检查平仓是否成功"""
                    if close_response is None:
                        return True, "no position to close"  # 无仓位视为成功
                    if close_response.get('status') != 'ok':
                        return False, "status not ok"
                    statuses = close_response.get('response', {}).get('data', {}).get('statuses', [])
                    if not statuses:
                        return True, "no statuses (likely no position)"
                    first_status = statuses[0]
                    if 'filled' in first_status:
                        return True, first_status['filled']
                    elif 'error' in first_status:
                        return False, first_status['error']
                    return False, "unknown status"
                
                flx_success, flx_info = check_close_success(flx_close)
                xyz_success, xyz_info = check_close_success(xyz_close)
                
                if flx_success and xyz_success:
                    print(f"\n{Fore.GREEN}✓ 平仓成功！{Style.RESET_ALL}")
                    
                    # 计算实际盈亏
                    if exit_info['exit_method'] == 'reversal':
                        realized_pnl = exit_info['reverse_spread'] - self.calculator.calculate_open_fee(avg_price)
                        print(f"反转价差: ${exit_info['reverse_spread']:.4f}")
                    else:
                        realized_pnl = position.unrealized_pnl
                    
                    print(f"实现盈亏: {utils.color_text(f'${realized_pnl:.4f}', realized_pnl > 0)}")
                    
                    # 记录平仓
                    close_record = self.position_manager.close_position(
                        position=position,
                        exit_prices={
                            'flx_bid': market_data['flx_bid'],
                            'flx_ask': market_data['flx_ask'],
                            'xyz_bid': market_data['xyz_bid'],
                            'xyz_ask': market_data['xyz_ask']
                        },
                        exit_method=exit_info['exit_method'],
                        realized_pnl=realized_pnl
                    )
                    
                    # 记录日志
                    self.logger.log_close_position(
                        close_record, 
                        notes=f'LIVE实盘交易 | FLX:{flx_close} | XYZ:{xyz_close}'
                    )
                    self.logger.print_trade_summary(close_record)
                    
                    return close_record
                else:
                    print(f"\n{Fore.RED}✗ 平仓失败{Style.RESET_ALL}")
                    if not flx_success:
                        print(f"FLX失败: {flx_info}")
                    if not xyz_success:
                        print(f"XYZ失败: {xyz_info}")
                    return None
                    
            except Exception as e:
                print(f"\n{Fore.RED}平仓异常: {e}{Style.RESET_ALL}")
                import traceback
                traceback.print_exc()
                return None
    
    def monitor_positions(self, market_data):
        """
        监控持仓并检查平仓条件
        
        Args:
            market_data: 市场数据
        """
        if not self.position_manager.positions:
            return
        
        # 更新所有持仓的未实现盈亏
        self.position_manager.update_positions(
            market_data['flx_bid'], market_data['flx_ask'],
            market_data['xyz_bid'], market_data['xyz_ask']
        )
        
        # 检查每个持仓的平仓条件
        positions_to_close = []
        for position in self.position_manager.positions:
            exit_info = self.position_manager.check_exit_conditions(
                position,
                market_data['flx_bid'], market_data['flx_ask'],
                market_data['xyz_bid'], market_data['xyz_ask']
            )
            
            if exit_info['should_exit']:
                positions_to_close.append((position, exit_info))
        
        # 执行平仓
        for position, exit_info in positions_to_close:
            self.execute_close(position, market_data, exit_info)
    
    def display_status(self, market_data, opportunity):
        """
        显示当前状态
        
        Args:
            market_data: 市场数据
            opportunity: 当前套利机会（可能为None）
        """
        # 清屏并将光标移到顶部
        print("\033[2J\033[H", end='')
        
        print(f"\n{Fore.CYAN}{'=' * 80}")
        print(f"TSLA 套利交易监控 | {utils.format_timestamp()}")
        print(f"{'=' * 80}{Style.RESET_ALL}\n")
        
        # 市场价格
        print(f"{Fore.YELLOW}【市场行情】{Style.RESET_ALL}")
        print(f"  FLX: Bid ${market_data['flx_bid']:.2f} | Ask ${market_data['flx_ask']:.2f} | Mid ${market_data['flx_mid']:.2f} | Spread ${market_data['flx_ask'] - market_data['flx_bid']:.2f}")
        print(f"  XYZ: Bid ${market_data['xyz_bid']:.2f} | Ask ${market_data['xyz_ask']:.2f} | Mid ${market_data['xyz_mid']:.2f} | Spread ${market_data['xyz_ask'] - market_data['xyz_bid']:.2f}")
        
        # 价差分析
        print(f"\n{Fore.YELLOW}【价差分析】{Style.RESET_ALL}")
        flx_to_xyz_spread = market_data['xyz_bid'] - market_data['flx_ask']
        xyz_to_flx_spread = market_data['flx_bid'] - market_data['xyz_ask']
        
        print(f"  FLX买→XYZ卖: ${flx_to_xyz_spread:.4f}", end='')
        if flx_to_xyz_spread > 0:
            print(f" {Fore.GREEN}(正价差){Style.RESET_ALL}")
        else:
            print(f" {Fore.RED}(负价差){Style.RESET_ALL}")
        
        print(f"  XYZ买→FLX卖: ${xyz_to_flx_spread:.4f}", end='')
        if xyz_to_flx_spread > 0:
            print(f" {Fore.GREEN}(正价差){Style.RESET_ALL}")
        else:
            print(f" {Fore.RED}(负价差){Style.RESET_ALL}")
        
        # 计算扣费后的净利润
        avg_price = (market_data['flx_mid'] + market_data['xyz_mid']) / 2
        open_fee = self.calculator.calculate_open_fee(avg_price)
        net_profit_ftx = flx_to_xyz_spread - open_fee
        net_profit_xtf = xyz_to_flx_spread - open_fee
        
        print(f"\n  扣除开仓费(${open_fee:.4f})后:")
        print(f"  FLX→XYZ净利润: {utils.color_text(f'${net_profit_ftx:.4f}', net_profit_ftx > 0)}")
        print(f"  XYZ→FLX净利润: {utils.color_text(f'${net_profit_xtf:.4f}', net_profit_xtf > 0)}")
        
        # 套利机会状态
        print(f"\n{Fore.YELLOW}【套利机会】{Style.RESET_ALL}")
        if opportunity:
            print(f"  {Fore.GREEN}✓ 发现套利机会{Style.RESET_ALL}")
            print(f"  方向: {Fore.GREEN}{opportunity['direction']}{Style.RESET_ALL}")
            print(f"  可执行价差: ${opportunity['spread']:.4f}")
            profit_text = f"${opportunity['net_profit']:.4f}"
            print(f"  预期净利润: {utils.color_text(profit_text, True)}")
            print(f"  开仓手续费: ${opportunity['open_fee']:.4f}")
        else:
            print(f"  {Fore.CYAN}⏳ 等待满足条件的机会{Style.RESET_ALL}")
            
            # 显示距离阈值的差距
            max_net_profit = max(net_profit_ftx, net_profit_xtf)
            gap = arbitrage_config.MIN_NET_PROFIT - max_net_profit
            
            if gap > 0:
                print(f"  当前最佳净利润: ${max_net_profit:.4f}")
                print(f"  距离开仓阈值(${arbitrage_config.MIN_NET_PROFIT:.2f}): 还差 ${gap:.4f}")
            else:
                print(f"  价差满足但等待稳定性确认...")
        
        # 持仓摘要
        summary = self.position_manager.get_positions_summary()
        if summary['count'] > 0:
            print(f"\n{Fore.YELLOW}【当前持仓】{Style.RESET_ALL}")
            print(f"  持仓数量: {summary['count']} | 总仓位: ${summary['total_size']:.2f}")
            total_pnl_text = f"${summary['total_unrealized_pnl']:.4f}"
            print(f"  总浮盈: {utils.color_text(total_pnl_text, summary['total_unrealized_pnl'] > 0)}")
            
            for pos_info in summary['positions']:
                color = Fore.GREEN if pos_info['unrealized_pnl'] > 0 else Fore.RED
                print(f"  • {pos_info['direction']}: ${pos_info['size']:.2f} | "
                      f"持仓{pos_info['holding_seconds'] / 60:.0f}分钟 | "
                      f"浮盈 {color}${pos_info['unrealized_pnl']:.4f}{Style.RESET_ALL}")
            
            # 显示平仓条件差距
            print(f"\n{Fore.YELLOW}【平仓条件】{Style.RESET_ALL}")
            for position in self.position_manager.positions:
                if position.direction == 'FLX_TO_XYZ':
                    # 需要XYZ→FLX方向反转
                    reversal_spread = xyz_to_flx_spread
                    threshold = getattr(arbitrage_config, 'REVERSAL_MIN_SPREAD_FLX_TO_XYZ', 
                                        arbitrage_config.REVERSAL_MIN_SPREAD)
                    reversal_dir = 'XYZ→FLX'
                else:
                    # 需要FLX→XYZ方向反转
                    reversal_spread = flx_to_xyz_spread
                    threshold = getattr(arbitrage_config, 'REVERSAL_MIN_SPREAD_XYZ_TO_FLX',
                                        arbitrage_config.REVERSAL_MIN_SPREAD)
                    reversal_dir = 'FLX→XYZ'
                
                gap_reversal = threshold - reversal_spread
                if gap_reversal > 0:
                    print(f"  {position.direction}: 需{reversal_dir}反转 > ${threshold:.2f}")
                    print(f"    当前{reversal_dir}价差: ${reversal_spread:.4f}")
                    print(f"    距离平仓阈值: {Fore.RED}还差 ${gap_reversal:.4f}{Style.RESET_ALL}")
                else:
                    print(f"  {position.direction}: {Fore.GREEN}✓ 反转条件已满足！{Style.RESET_ALL}")
                    print(f"    当前{reversal_dir}价差: ${reversal_spread:.4f} > ${threshold:.2f}")
                
                # 止盈条件
                if position.unrealized_pnl > 0:
                    tp_gap = arbitrage_config.TAKE_PROFIT_TARGET - position.unrealized_pnl
                    if tp_gap > 0:
                        print(f"    距离止盈(${arbitrage_config.TAKE_PROFIT_TARGET:.2f}): 还差 ${tp_gap:.4f}")
                    else:
                        print(f"    {Fore.GREEN}✓ 已达止盈目标！{Style.RESET_ALL}")
                
                # 超时条件
                holding_minutes = position.get_holding_duration() / 60
                timeout_remain = arbitrage_config.POSITION_TIMEOUT_HOURS * 60 - holding_minutes
                if timeout_remain > 0:
                    print(f"    距离超时兜底: {timeout_remain:.0f}分钟")
                else:
                    print(f"    {Fore.YELLOW}⚠ 已超时，将强制平仓{Style.RESET_ALL}")
        
        # 交易统计
        stats = self.position_manager.get_statistics()
        if stats['total_trades'] > 0:
            print(f"\n{Fore.YELLOW}【交易统计】{Style.RESET_ALL}")
            print(f"  总交易: {stats['total_trades']} 笔 | "
                  f"盈利: {stats.get('profitable_trades', 0)} | "
                  f"亏损: {stats.get('losing_trades', 0)} | "
                  f"胜率: {stats['win_rate']:.1f}%")
            realized_pnl_text = f"${stats['total_realized_pnl']:.4f}"
            print(f"  总盈亏: {utils.color_text(realized_pnl_text, stats['total_realized_pnl'] > 0)} | "
                  f"平均: ${stats['avg_pnl']:.4f} | "
                  f"平均持仓: {stats['avg_holding_time'] / 60:.1f}分钟")
        
        # 系统信息
        print(f"\n{Fore.CYAN}{'─' * 80}{Style.RESET_ALL}")
        mode_text = 'DRY-RUN' if self.dry_run else 'LIVE'
        mode_color = Fore.YELLOW if self.dry_run else Fore.RED
        print(f"模式: {mode_color}{mode_text}{Style.RESET_ALL} | "
              f"扫描间隔: {arbitrage_config.MONITOR_INTERVAL}秒 | "
              f"最佳价差记录: ${self.best_spread_seen:.4f}")
        print(f"{Fore.CYAN}{'─' * 80}{Style.RESET_ALL}")
    
    def run(self):
        """运行套利引擎"""
        print(f"{Fore.GREEN}开始监控...{Style.RESET_ALL}\n")
        
        try:
            while True:
                # 获取市场数据
                market_data = self.get_market_data()
                if not market_data:
                    time.sleep(arbitrage_config.MONITOR_INTERVAL)
                    continue
                
                # 记录价差净利润（每次循环都记录）
                self.profit_monitor.log_spread_profit(market_data, self.calculator)
                
                # 监控现有持仓
                self.monitor_positions(market_data)
                
                # 寻找新的套利机会
                opportunity = self.find_arbitrage_opportunity(market_data)
                
                # 显示状态
                self.display_status(market_data, opportunity)
                
                # 如果有套利机会，执行开仓
                if opportunity:
                    self.execute_open(opportunity, market_data)
                
                # 等待下一次循环
                time.sleep(arbitrage_config.MONITOR_INTERVAL)
        
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}{'=' * 80}")
            print("用户终止程序")
            print(f"{'=' * 80}{Style.RESET_ALL}\n")
            
            # 显示最终统计
            stats = self.position_manager.get_statistics()
            if stats['total_trades'] > 0:
                self.logger.print_statistics(stats)
            
            # 显示未平仓位
            if self.position_manager.positions:
                print(f"{Fore.YELLOW}警告: 仍有 {len(self.position_manager.positions)} 个未平仓位{Style.RESET_ALL}\n")
                for pos in self.position_manager.positions:
                    print(f"  - {pos}")
            
            print(f"\n程序已退出\n")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='TSLA FLX vs XYZ 套利交易引擎')
    parser.add_argument('--live', action='store_true', help='实盘模式（默认为模拟模式）')
    args = parser.parse_args()
    
    # 创建交易引擎
    trader = ArbitrageTrader(dry_run=not args.live)
    
    # 运行
    trader.run()


if __name__ == "__main__":
    main()
