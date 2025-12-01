"""
辅助函数模块
"""
import config
from datetime import datetime
from colorama import Fore, Style, init

# 初始化 colorama
init(autoreset=True)


def format_price(price, decimal_places=None):
    """格式化价格显示"""
    if decimal_places is None:
        decimal_places = config.DECIMAL_PLACES
    return f"{float(price):.{decimal_places}f}"


def calculate_spread_percentage(price1, price2):
    """
    计算价差百分比
    
    Args:
        price1: 第一个价格
        price2: 第二个价格
    
    Returns:
        价差百分比（绝对值）
    """
    avg_price = (price1 + price2) / 2
    spread = abs(price1 - price2)
    return (spread / avg_price) * 100


def calculate_arbitrage_profit(buy_price, sell_price, position_size, use_maker_fee=True):
    """
    计算套利利润（扣除手续费）
    
    Args:
        buy_price: 买入价格
        sell_price: 卖出价格
        position_size: 仓位大小（USDC）
        use_maker_fee: 是否使用 maker 费率（否则使用 taker 费率）
    
    Returns:
        净利润（USDC）
    """
    fee_rate = config.MAKER_FEE if use_maker_fee else config.TAKER_FEE
    
    # 买入成本（包括手续费）
    buy_cost = position_size * (1 + fee_rate)
    
    # 卖出收入（扣除手续费）
    quantity = position_size / buy_price
    sell_revenue = quantity * sell_price * (1 - fee_rate)
    
    # 净利润
    profit = sell_revenue - buy_cost
    return profit


def estimate_total_fees(position_size, num_trades=2):
    """
    估算总手续费
    
    Args:
        position_size: 仓位大小（USDC）
        num_trades: 交易次数（开仓+平仓 = 4次）
    
    Returns:
        总手续费（USDC）
    """
    return position_size * config.TAKER_FEE * num_trades


def color_text(text, positive=True):
    """
    根据正负值给文本上色
    
    Args:
        text: 要显示的文本
        positive: True 为绿色（正值），False 为红色（负值）
    
    Returns:
        带颜色的文本
    """
    color = Fore.GREEN if positive else Fore.RED
    return f"{color}{text}{Style.RESET_ALL}"


def format_timestamp():
    """返回当前时间戳字符串"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def print_header(text):
    """打印标题"""
    print(f"\n{Fore.CYAN}{'=' * 80}")
    print(f"{text.center(80)}")
    print(f"{'=' * 80}{Style.RESET_ALL}\n")


def print_separator():
    """打印分隔线"""
    print(f"{Fore.YELLOW}{'-' * 80}{Style.RESET_ALL}")


def calculate_mid_price(orderbook_data):
    """
    从订单簿数据计算中间价
    
    Args:
        orderbook_data: L2 订单簿数据
    
    Returns:
        中间价（float）
    """
    if not orderbook_data or 'levels' not in orderbook_data:
        return None
    
    levels = orderbook_data['levels']
    if len(levels) < 2 or not levels[0] or not levels[1]:
        return None
    
    # levels[0] 是 bids（买单），levels[1] 是 asks（卖单）
    best_bid = float(levels[0][0]['px']) if levels[0] else None
    best_ask = float(levels[1][0]['px']) if levels[1] else None
    
    if best_bid and best_ask:
        return (best_bid + best_ask) / 2
    
    return None


def get_best_bid_ask(orderbook_data):
    """
    从订单簿获取最佳买卖价
    
    Args:
        orderbook_data: L2 订单簿数据
    
    Returns:
        (best_bid, best_ask) 元组
    """
    if not orderbook_data or 'levels' not in orderbook_data:
        return None, None
    
    levels = orderbook_data['levels']
    if len(levels) < 2:
        return None, None
    
    best_bid = float(levels[0][0]['px']) if levels[0] and len(levels[0]) > 0 else None
    best_ask = float(levels[1][0]['px']) if levels[1] and len(levels[1]) > 0 else None
    
    return best_bid, best_ask
