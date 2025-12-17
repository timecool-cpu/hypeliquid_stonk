"""
风控管理模块
负责余额查询、开仓检查、清算风险监控和紧急平仓
"""
import os
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum
from colorama import Fore, Style

from hyperliquid.info import Info
from dotenv import load_dotenv
from eth_account import Account

from src.config import arbitrage_config

load_dotenv()


class RiskLevel(Enum):
    """风险等级"""
    SAFE = "safe"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class BalanceInfo:
    """余额信息"""
    xyz_available: float
    flx_available: float
    xyz_dex_value: float
    flx_dex_value: float
    total_value: float


@dataclass
class LiquidationInfo:
    """清算信息"""
    dex: str
    coin: str
    side: str
    entry_price: float
    current_price: float
    liquidation_price: float
    distance_pct: float
    risk_level: RiskLevel
    margin_used: float
    unrealized_pnl: float


class RiskManager:
    """风控管理器"""
    
    LEVERAGE = getattr(arbitrage_config, 'LEVERAGE', 10)
    MARGIN_BUFFER = getattr(arbitrage_config, 'MARGIN_BUFFER', 1.2)
    WARNING_THRESHOLD = getattr(arbitrage_config, 'LIQUIDATION_WARNING_THRESHOLD', 10.0)
    EMERGENCY_THRESHOLD = getattr(arbitrage_config, 'LIQUIDATION_EMERGENCY_THRESHOLD', 3.0)
    
    def __init__(self, info: Info = None, wallet_address: str = None):
        if info is None:
            self.info = Info(skip_ws=True)
        else:
            self.info = info
            
        if wallet_address is None:
            private_key = os.getenv('HYPERLIQUID_PRIVATE_KEY')
            if private_key:
                account = Account.from_key(private_key)
                self.wallet_address = account.address
            else:
                raise ValueError("需要wallet_address或HYPERLIQUID_PRIVATE_KEY")
        else:
            self.wallet_address = wallet_address
    
    def get_balance_info(self, max_retries: int = 3) -> BalanceInfo:
        """获取所有账户余额信息，带重试机制"""
        import time
        
        for attempt in range(max_retries):
            try:
                xyz_available = 0.0
                main_state = self.info.user_state(self.wallet_address)
                if main_state:
                    xyz_available = float(main_state.get('withdrawable', 0))
                
                flx_available = 0.0
                spot_state = self.info.spot_user_state(self.wallet_address)
                if spot_state and 'balances' in spot_state:
                    for balance in spot_state['balances']:
                        if balance.get('coin') == 'USDH':
                            total = float(balance.get('total', 0))
                            hold = float(balance.get('hold', 0))
                            flx_available = total - hold
                            break
                
                xyz_dex_value = 0.0
                xyz_state = self.info.user_state(self.wallet_address, 'xyz')
                if xyz_state:
                    ms = xyz_state.get('marginSummary', {})
                    xyz_dex_value = float(ms.get('accountValue', 0))
                
                flx_dex_value = 0.0
                flx_state = self.info.user_state(self.wallet_address, 'flx')
                if flx_state:
                    ms = flx_state.get('marginSummary', {})
                    flx_dex_value = float(ms.get('accountValue', 0))
                
                total_value = xyz_available + flx_available + xyz_dex_value + flx_dex_value
                
                return BalanceInfo(
                    xyz_available=xyz_available,
                    flx_available=flx_available,
                    xyz_dex_value=xyz_dex_value,
                    flx_dex_value=flx_dex_value,
                    total_value=total_value
                )
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(1)  # 等待1秒后重试
                    continue
                # 最后一次尝试失败，返回空余额信息
                print(f"{Fore.YELLOW}获取余额失败: {e}{Style.RESET_ALL}")
                return BalanceInfo(
                    xyz_available=0.0,
                    flx_available=0.0,
                    xyz_dex_value=0.0,
                    flx_dex_value=0.0,
                    total_value=0.0
                )
    
    def can_open_position(self, position_size_usd: float) -> Tuple[bool, str]:
        """检查是否可以开仓"""
        balance = self.get_balance_info()
        required_margin = position_size_usd / self.LEVERAGE
        required_with_buffer = required_margin * self.MARGIN_BUFFER
        
        if balance.xyz_available < required_with_buffer:
            return False, f"XYZ保证金不足: 需要${required_with_buffer:.2f}, 可用${balance.xyz_available:.2f}"
        
        if balance.flx_available < required_with_buffer:
            return False, f"FLX保证金不足: 需要{required_with_buffer:.2f}USDH, 可用{balance.flx_available:.2f}USDH"
        
        return True, f"余额充足: XYZ ${balance.xyz_available:.2f}, FLX {balance.flx_available:.2f} USDH"
    
    def get_liquidation_info(self) -> List[LiquidationInfo]:
        """获取所有持仓的清算信息"""
        result = []
        
        for dex_name in ['flx', 'xyz']:
            try:
                state = self.info.user_state(self.wallet_address, dex_name)
                if not state:
                    continue
            except Exception as e:
                print(f"{Fore.YELLOW}获取{dex_name}状态失败: {e}{Style.RESET_ALL}")
                continue
            
            positions = state.get('assetPositions', [])
            for pos in positions:
                details = pos.get('position', {})
                szi = float(details.get('szi', 0))
                if szi == 0:
                    continue
                
                coin = details.get('coin', '')
                entry_px = float(details.get('entryPx', 0))
                liquidation_px = details.get('liquidationPx')
                unrealized_pnl = float(details.get('unrealizedPnl', 0))
                margin_used = float(details.get('marginUsed', 0))
                
                if not liquidation_px:
                    continue
                
                liquidation_px = float(liquidation_px)
                side = 'LONG' if szi > 0 else 'SHORT'
                
                current_price = entry_px
                try:
                    book = self.info.post("/info", {"type": "l2Book", "coin": coin})
                    if book and 'levels' in book:
                        bids = book['levels'][0]
                        asks = book['levels'][1]
                        if bids and asks:
                            best_bid = float(bids[0]['px'])
                            best_ask = float(asks[0]['px'])
                            current_price = (best_bid + best_ask) / 2
                except:
                    pass
                
                if side == 'LONG':
                    distance_pct = (current_price - liquidation_px) / current_price * 100
                else:
                    distance_pct = (liquidation_px - current_price) / current_price * 100
                
                if distance_pct < self.EMERGENCY_THRESHOLD:
                    risk_level = RiskLevel.CRITICAL
                elif distance_pct < self.WARNING_THRESHOLD:
                    risk_level = RiskLevel.WARNING
                else:
                    risk_level = RiskLevel.SAFE
                
                result.append(LiquidationInfo(
                    dex=dex_name.upper(),
                    coin=coin,
                    side=side,
                    entry_price=entry_px,
                    current_price=current_price,
                    liquidation_price=liquidation_px,
                    distance_pct=distance_pct,
                    risk_level=risk_level,
                    margin_used=margin_used,
                    unrealized_pnl=unrealized_pnl
                ))
        
        return result
    
    def check_liquidation_risk(self) -> Tuple[bool, bool, List[LiquidationInfo]]:
        """检查清算风险，返回(有预警, 需要紧急平仓, 清算信息列表)"""
        liq_infos = self.get_liquidation_info()
        has_warning = False
        need_emergency = False
        
        for info in liq_infos:
            if info.risk_level == RiskLevel.WARNING:
                has_warning = True
            elif info.risk_level == RiskLevel.CRITICAL:
                need_emergency = True
        
        return has_warning, need_emergency, liq_infos
    
    def print_risk_status(self):
        """打印风险状态"""
        print(f"\n{Fore.CYAN}{'=' * 60}")
        print(f"风控状态检查")
        print(f"{'=' * 60}{Style.RESET_ALL}")
        
        balance = self.get_balance_info()
        print(f"\n{Fore.YELLOW}【可用余额】{Style.RESET_ALL}")
        print(f"  XYZ可用 (USDC Perps): ${balance.xyz_available:.2f}")
        print(f"  FLX可用 (USDH Spot):  {balance.flx_available:.2f} USDH")
        print(f"  XYZ DEX账户价值:      ${balance.xyz_dex_value:.2f}")
        print(f"  FLX DEX账户价值:      ${balance.flx_dex_value:.2f}")
        print(f"  总价值:               ${balance.total_value:.2f}")
        
        has_warning, need_emergency, liq_infos = self.check_liquidation_risk()
        
        print(f"\n{Fore.YELLOW}【清算风险】{Style.RESET_ALL}")
        if not liq_infos:
            print(f"  {Fore.GREEN}✓ 无持仓{Style.RESET_ALL}")
        else:
            for info in liq_infos:
                if info.risk_level == RiskLevel.CRITICAL:
                    color = Fore.RED
                    icon = "🚨"
                elif info.risk_level == RiskLevel.WARNING:
                    color = Fore.YELLOW
                    icon = "⚠️"
                else:
                    color = Fore.GREEN
                    icon = "✅"
                
                print(f"\n  {info.dex} {info.coin} ({info.side})")
                print(f"    开仓价: ${info.entry_price:.2f}")
                print(f"    当前价: ${info.current_price:.2f}")
                print(f"    清算价: ${info.liquidation_price:.2f}")
                print(f"    距离清算: {color}{info.distance_pct:.1f}% {icon}{Style.RESET_ALL}")
                print(f"    占用保证金: ${info.margin_used:.2f}")
                print(f"    未实现盈亏: ${info.unrealized_pnl:.4f}")
        
        print(f"\n{Fore.YELLOW}【风险总结】{Style.RESET_ALL}")
        if need_emergency:
            print(f"  {Fore.RED}🚨 紧急: 有持仓接近清算，建议立即平仓！{Style.RESET_ALL}")
        elif has_warning:
            print(f"  {Fore.YELLOW}⚠️ 预警: 有持仓风险较高，请关注{Style.RESET_ALL}")
        else:
            print(f"  {Fore.GREEN}✅ 安全: 所有持仓风险可控{Style.RESET_ALL}")
        
        print(f"\n{Fore.CYAN}{'=' * 60}{Style.RESET_ALL}\n")
        return has_warning, need_emergency


if __name__ == "__main__":
    rm = RiskManager()
    rm.print_risk_status()
    
    print("\n测试开仓检查:")
    can_open, reason = rm.can_open_position(100)
    print(f"  开仓$100: {can_open}, {reason}")
