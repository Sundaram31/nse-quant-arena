"""Strategy registry and exports."""
from typing import Dict, Type
from nse_system.strategies.base import BaseStrategy
from nse_system.strategies.orb import ORBStrategy
from nse_system.strategies.vwap_supertrend import VWAPSuperTrendStrategy
from nse_system.strategies.cpr_reversion import CPRReversionStrategy
from nse_system.strategies.ema_crossover import MultiEMACrossoverStrategy
from nse_system.strategies.bollinger_rsi import BollingerRSIStrategy
from nse_system.strategies.oi_momentum import OIMomentumStrategy
from nse_system.strategies.rrg_sector_momentum import RRGSectorMomentumStrategy
from nse_system.strategies.helega_milega import HelegaMilegaStrategy
from nse_system.strategies.price_volume_action import PriceVolumeActionStrategy

STRATEGY_REGISTRY: Dict[str, Type[BaseStrategy]] = {
    'ORB': ORBStrategy,
    'VWAP_SuperTrend': VWAPSuperTrendStrategy,
    'Helega_Milega': HelegaMilegaStrategy,
    'Price_Volume_Action': PriceVolumeActionStrategy,
    'CPR_Reversion': CPRReversionStrategy,
    'EMA_Crossover': MultiEMACrossoverStrategy,
    'Bollinger_RSI': BollingerRSIStrategy,
    'OI_Momentum': OIMomentumStrategy,
    'RRG_Sector_Momentum': RRGSectorMomentumStrategy
}

def get_strategy(name: str, symbol: str, timeframe: str = '5m', params: dict = None) -> BaseStrategy:
    """Factory to instantiate strategy by name."""
    strat_cls = STRATEGY_REGISTRY.get(name, VWAPSuperTrendStrategy)
    return strat_cls(symbol=symbol, timeframe=timeframe, params=params)

def list_available_strategies() -> list:
    return list(STRATEGY_REGISTRY.keys())

__all__ = [
    'BaseStrategy', 'ORBStrategy', 'VWAPSuperTrendStrategy', 'CPRReversionStrategy',
    'MultiEMACrossoverStrategy', 'BollingerRSIStrategy', 'OIMomentumStrategy',
    'RRGSectorMomentumStrategy', 'HelegaMilegaStrategy', 'PriceVolumeActionStrategy',
    'STRATEGY_REGISTRY', 'get_strategy', 'list_available_strategies'
]
