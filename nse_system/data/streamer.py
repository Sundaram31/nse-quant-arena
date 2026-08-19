"""Market Data Streamer and Replay Engine for Paper Trading & Live Simulation."""
from datetime import datetime, timedelta
import time
import threading
from typing import List, Callable, Optional, Dict
from nse_system.core.models import Candle, Tick

class MarketDataStreamer:
    """Streams tick and candle events to registered subscriber callbacks."""

    def __init__(self):
        self._candle_subscribers: List[Callable[[Candle], None]] = []
        self._tick_subscribers: List[Callable[[Tick], None]] = []
        self._is_running = False
        self._thread: Optional[threading.Thread] = None

    def subscribe_candle(self, callback: Callable[[Candle], None]):
        self._candle_subscribers.append(callback)

    def subscribe_tick(self, callback: Callable[[Tick], None]):
        self._tick_subscribers.append(callback)

    def emit_candle(self, candle: Candle):
        for cb in self._candle_subscribers:
            try:
                cb(candle)
            except Exception as e:
                print(f'Error in candle subscriber: {e}')

    def emit_tick(self, tick: Tick):
        for cb in self._tick_subscribers:
            try:
                cb(tick)
            except Exception as e:
                print(f'Error in tick subscriber: {e}')

    def replay_candles(self, candles: List[Candle], speed_multiplier: float = 10.0, delay_sec: float = 0.05):
        """Replays historical candle series in a background thread."""
        def _replay():
            self._is_running = True
            for candle in candles:
                if not self._is_running:
                    break
                self.emit_candle(candle)
                # Generate synthetic intermediate tick
                tick = Tick(
                    timestamp=candle.timestamp,
                    symbol='MARKET',
                    ltp=candle.close,
                    volume=candle.volume,
                    bid=round(candle.close - 0.05, 2),
                    ask=round(candle.close + 0.05, 2),
                    oi=candle.oi
                )
                self.emit_tick(tick)
                time.sleep(max(0.001, delay_sec / speed_multiplier))
            self._is_running = False

        self._thread = threading.Thread(target=_replay, daemon=True)
        self._thread.start()

    def stop(self):
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
