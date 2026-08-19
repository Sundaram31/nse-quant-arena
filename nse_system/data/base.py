"""Abstract Data Provider interface."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
import pandas as pd
from nse_system.core.models import Candle, Tick

class BaseDataProvider(ABC):
    """Abstract interface for fetching historical and real-time market data."""

    @abstractmethod
    def get_historical_candles(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '5m'
    ) -> List[Candle]:
        """Fetch historical candles for a symbol."""
        pass

    @abstractmethod
    def get_historical_dataframe(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '5m'
    ) -> pd.DataFrame:
        """Fetch historical candles as a pandas DataFrame with OHLCV columns."""
        pass
