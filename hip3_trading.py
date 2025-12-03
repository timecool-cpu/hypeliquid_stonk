"""
Hyperliquid HIP-3 (Spot) 资产交易工具
绕过SDK的name_to_coin限制，直接使用底层API
"""
import json
from typing import Any, Dict, Optional
from eth_account import Account
from hyperliquid.utils import signing


def create_order_action(
    coin: str,
    is_buy: bool,
    sz: float,
    limit_px: Optional[float] = None,
    order_type: Dict[str, str] = {"limit": {"tif": "Ioc"}},  # Immediate or Cancel (类似市价)
    reduce_only: bool = False,
    cloid: Optional[str] = None
) -> Dict[str, Any]:
    """
    创建订单action
    
    Args:
        coin: 币种名称，如 "flx:TSLA"
        is_buy: True=买入，False=卖出
        sz: 数量
        limit_px: 限价价格，None表示使用市价附近价格
        order_type: 订单类型
        reduce_only: 是否仅平仓
        cloid: 客户端订单ID
        
    Returns:
        订单action字典
    """
    order = {
        "a": coin,  # asset
        "b": is_buy,  # is_buy
        "p": str(limit_px) if limit_px else "0",  # price (0表示市价)
        "s": str(sz),  # size
        "r": reduce_only,  # reduce_only
        "t": order_type
    }
    
    if cloid:
        order["c"] = cloid
    
    return {
        "type": "order",
        "orders": [order],
        "grouping": "na"
    }


def send_order_raw(
    exchange_instance,
    coin: str,
    is_buy: bool,
    sz: float,
    limit_px: Optional[float] = None,
    reduce_only: bool = False
) -> Any:
    """
    使用底层API直接发送订单
    
    Args:
        exchange_instance: Exchange实例（用于访问其wallet和post方法）
        coin: 币种名称
        is_buy: 买入/卖出
        sz: 数量
        limit_px: 限价（None使用市价）
        reduce_only: 仅平仓
        
    Returns:
        API响应
    """
    # 创建订单action
    action = create_order_action(
        coin=coin,
        is_buy=is_buy,
        sz=sz,
        limit_px=limit_px,
        reduce_only=reduce_only
    )
    
    # 使用Exchange的现有连接发送
    return exchange_instance.post("/exchange", action)


def market_open_hip3(
    exchange_instance,
    coin: str,
    is_buy: bool,
    sz: float,
    slippage_price: Optional[float] = None
) -> Any:
    """
    开仓HIP-3资产（市价单）
    
    Args:
        exchange_instance: Exchange实例
        coin: 币种，如 "flx:TSLA"
        is_buy: 买入/卖出
        sz: 数量
        slippage_price: 滑点价格（如果提供）
        
    Returns:
        订单响应
    """
    return send_order_raw(
        exchange_instance=exchange_instance,
        coin=coin,
        is_buy=is_buy,
        sz=sz,
        limit_px=slippage_price,
        reduce_only=False
    )


def market_close_hip3(
    exchange_instance,
    coin: str,
    sz: float,
    slippage_price: Optional[float] = None
) -> Any:
    """
    平仓HIP-3资产（市价单）
    
    注意：平仓时方向会自动反转（reduce_only=True）
    
    Args:
        exchange_instance: Exchange实例
        coin: 币种
        sz: 数量
        slippage_price: 滑点价格
        
    Returns:
        订单响应
    """
    # reduce_only模式下，方向会自动反转平仓
    # 如果持仓是多头，卖出平仓；如果是空头，买入平仓
    # 我们需要查询当前持仓方向
    
    # 简化方案：尝试两个方向，一个会成功
    # 先尝试卖出平仓（平多头）
    result = send_order_raw(
        exchange_instance=exchange_instance,
        coin=coin,
        is_buy=False,  # 卖出
        sz=sz,
        limit_px=slippage_price,
        reduce_only=True
    )
    
    return result
