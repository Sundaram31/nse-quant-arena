"""Simulated Paper Broker with live margins and order management."""
from typing import Dict, List, Optional
from datetime import datetime
from nse_system.broker.base import BaseBroker
from nse_system.core.models import Order, Position, OrderStatus

class PaperBroker(BaseBroker):
    """In-memory paper trading broker."""

    def __init__(self, initial_capital: float = 100000.0):
        self.capital = initial_capital
        self.used_margin = 0.0
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self._connected = False

    def connect(self) -> bool:
        self._connected = True
        return True

    def get_margins(self) -> Dict[str, float]:
        return {
            'available_cash': self.capital - self.used_margin,
            'used_margin': self.used_margin,
            'total_collateral': self.capital
        }

    def place_order(self, order: Order) -> Order:
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.updated_at = datetime.now()
        self.orders[order.order_id] = order
        return order

    def cancel_order(self, order_id: str) -> bool:
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            return True
        return False

    def get_positions(self) -> List[Position]:
        return list(self.positions.values())

    def get_orders(self) -> List[Order]:
        return list(self.orders.values())
