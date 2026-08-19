"""Intraday 15:15 IST Auto-Squareoff Supervisor."""
from datetime import datetime, time
from typing import List
from nse_system.core.constants import MarketHours, ProductType
from nse_system.core.models import Position, Order, OrderSide, OrderType

class IntradayAutoSquareoff:
    """Enforces mandatory SEBI/broker auto square-off at 15:15 IST."""

    @staticmethod
    def is_squareoff_time(current_time: time) -> bool:
        return current_time >= MarketHours.AUTO_SQUAREOFF

    @staticmethod
    def generate_squareoff_orders(positions: List[Position]) -> List[Order]:
        orders: List[Order] = []
        for pos in positions:
            if pos.is_open and pos.product_type == ProductType.MIS:
                side = OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY
                orders.append(Order(
                    order_id=f'SQOFF_{pos.symbol}_{int(datetime.now().timestamp())}',
                    symbol=pos.symbol,
                    side=side,
                    order_type=OrderType.MARKET,
                    product_type=ProductType.MIS,
                    quantity=abs(pos.quantity),
                    tag='15:15_AUTO_SQUAREOFF'
                ))
        return orders
