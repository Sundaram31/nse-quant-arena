"""DhanHQ Broker Adapter Template."""
from typing import Dict, List, Optional
from nse_system.broker.base import BaseBroker
from nse_system.core.models import Order, Position

class DhanAdapter(BaseBroker):
    """Ready-to-plug Adapter for DhanHQ API."""

    def __init__(self, client_id: str = '', access_token: str = ''):
        self.client_id = client_id
        self.access_token = access_token

    def connect(self) -> bool:
        return True if self.access_token else False

    def get_margins(self) -> Dict[str, float]:
        return {'available_cash': 100000.0, 'used_margin': 0.0, 'total_collateral': 100000.0}

    def place_order(self, order: Order) -> Order:
        return order

    def cancel_order(self, order_id: str) -> bool:
        return True

    def get_positions(self) -> List[Position]:
        return []

    def get_orders(self) -> List[Order]:
        return []
