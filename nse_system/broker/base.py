"""Abstract Broker Interface for Indian Stock Brokers."""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from nse_system.core.models import Order, Position

class BaseBroker(ABC):
    """Standardized API interface for Zerodha, Angel One, Dhan, and Paper Trading."""

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def get_margins(self) -> Dict[str, float]:
        pass

    @abstractmethod
    def place_order(self, order: Order) -> Order:
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        pass

    @abstractmethod
    def get_positions(self) -> List[Position]:
        pass

    @abstractmethod
    def get_orders(self) -> List[Order]:
        pass
