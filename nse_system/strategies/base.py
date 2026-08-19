"""Base Strategy Interface and Lifecycle Management."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd

from nse_system.core.models import Candle, Tick, Signal, Order, Position
from nse_system.core.constants import ProductType, OrderSide

class BaseStrategy(ABC):
    """Abstract base class for all NSE trading strategies."""

    def __init__(
        self,
        name: str,
        symbol: str,
        timeframe: str = '5m',
        params: Optional[Dict[str, Any]] = None,
        product_type: ProductType = ProductType.MIS
    ):
        self.name = name
        self.symbol = symbol
        self.timeframe = timeframe
        self.params = params or {}
        self.product_type = product_type
        
        self.candles: List[Candle] = []
        self.current_position: int = 0  # +qty for long, -qty for short
        self.entry_price: float = 0.0
        self.stop_loss: Optional[float] = None
        self.target: Optional[float] = None
        self.is_active: bool = True

    def on_start(self):
        """Called before backtesting or live execution begins."""
        self.candles = []
        self.current_position = 0
        self.entry_price = 0.0

    @abstractmethod
    def on_candle(self, candle: Candle) -> Optional[Signal]:
        """Process each completed candle and generate trading signals."""
        pass

    def on_tick(self, tick: Tick) -> Optional[Signal]:
        """Optional hook for tick-level processing."""
        return None

    def on_order_update(self, order: Order):
        """Hook called when an order is filled or changed."""
        if order.side == OrderSide.BUY:
            self.current_position += order.filled_quantity
            self.entry_price = order.avg_price
        elif order.side == OrderSide.SELL:
            self.current_position -= order.filled_quantity
            if self.current_position == 0:
                self.entry_price = 0.0
                self.stop_loss = None
                self.target = None

    def on_stop(self):
        """Cleanup when execution ends."""
        pass

    def buy_signal(
        self,
        candle: Candle,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        reason: str = '',
        confidence: float = 1.0
    ) -> Signal:
        return Signal(
            timestamp=candle.timestamp,
            symbol=self.symbol,
            signal_type='BUY',
            price=candle.close,
            stop_loss=stop_loss,
            target=target,
            reason=reason,
            confidence=confidence
        )

    def sell_signal(
        self,
        candle: Candle,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None,
        reason: str = '',
        confidence: float = 1.0
    ) -> Signal:
        return Signal(
            timestamp=candle.timestamp,
            symbol=self.symbol,
            signal_type='SELL',
            price=candle.close,
            stop_loss=stop_loss,
            target=target,
            reason=reason,
            confidence=confidence
        )

    def exit_signal(self, candle: Candle, reason: str = 'EXIT') -> Signal:
        sig_type = 'EXIT_LONG' if self.current_position > 0 else 'EXIT_SHORT'
        return Signal(
            timestamp=candle.timestamp,
            symbol=self.symbol,
            signal_type=sig_type,
            price=candle.close,
            reason=reason
        )

    def to_dataframe(self, max_bars: int = 150) -> pd.DataFrame:
        """Convert recent accumulated candles to a pandas DataFrame."""
        if not self.candles:
            return pd.DataFrame()
        recent = self.candles[-max_bars:] if max_bars > 0 else self.candles
        records = [{
            'timestamp': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume,
            'oi': c.oi,
            'vwap': c.vwap
        } for c in recent]
        df = pd.DataFrame(records)
        df.set_index('timestamp', inplace=True)
        return df
