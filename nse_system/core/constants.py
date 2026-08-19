"""NSE Trading Constants and Enumerations."""
from enum import Enum
from datetime import time

class MarketHours:
    """NSE Trading session timings (IST)."""
    PRE_OPEN_START = time(9, 0, 0)
    PRE_OPEN_END = time(9, 8, 0)
    MARKET_OPEN = time(9, 15, 0)
    AUTO_SQUAREOFF = time(15, 15, 0)
    MARKET_CLOSE = time(15, 30, 0)
    POST_MARKET_END = time(16, 0, 0)
    TIMEZONE = 'Asia/Kolkata'

class ProductType(str, Enum):
    """Product types supported by Indian stock brokers."""
    MIS = 'MIS'      # Margin Intraday Square-off (Intraday)
    CNC = 'CNC'      # Cash N Carry (Delivery Equity)
    NRML = 'NRML'    # Normal (Futures & Options overnight)
    CO = 'CO'        # Cover Order
    BO = 'BO'        # Bracket Order

class SignalType(str, Enum):
    BUY = 'BUY'
    SELL = 'SELL'
    EXIT_LONG = 'EXIT_LONG'
    EXIT_SHORT = 'EXIT_SHORT'
    HOLD = 'HOLD'

class OrderType(str, Enum):
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    SL_LIMIT = 'SL'
    SL_MARKET = 'SL-M'

class OrderSide(str, Enum):
    BUY = 'BUY'
    SELL = 'SELL'

class OrderStatus(str, Enum):
    PENDING = 'PENDING'
    OPEN = 'OPEN'
    FILLED = 'FILLED'
    CANCELLED = 'CANCELLED'
    REJECTED = 'REJECTED'

class TimeFrame(str, Enum):
    MINUTE_1 = '1m'
    MINUTE_3 = '3m'
    MINUTE_5 = '5m'
    MINUTE_15 = '15m'
    MINUTE_30 = '30m'
    HOUR_1 = '1h'
    DAY_1 = '1d'

class InstrumentType(str, Enum):
    EQUITY = 'EQUITY'
    INDEX = 'INDEX'
    FUTURES = 'FUTURES'
    OPTIONS_CE = 'CE'
    OPTIONS_PE = 'PE'

class MarketRegimeType(str, Enum):
    BULL_TRENDING = 'BULL_TRENDING'
    BEAR_TRENDING = 'BEAR_TRENDING'
    SIDEWAYS_LOW_VOL = 'SIDEWAYS_LOW_VOL'
    SIDEWAYS_HIGH_VOL = 'SIDEWAYS_HIGH_VOL'
    VOLATILE_EXPANSION = 'VOLATILE_EXPANSION'

class OptionType(str, Enum):
    CE = 'CE'
    PE = 'PE'

class OIBuildupType(str, Enum):
    LONG_BUILDUP = 'LONG_BUILDUP'         # Price Up, OI Up
    SHORT_BUILDUP = 'SHORT_BUILDUP'       # Price Down, OI Up
    LONG_UNWINDING = 'LONG_UNWINDING'     # Price Down, OI Down
    SHORT_COVERING = 'SHORT_COVERING'     # Price Up, OI Down
    NEUTRAL = 'NEUTRAL'

class RRGQuadrant(str, Enum):
    LEADING = 'LEADING'       # RS > 100, Momentum > 100
    WEAKENING = 'WEAKENING'   # RS > 100, Momentum < 100
    LAGGING = 'LAGGING'       # RS < 100, Momentum < 100
    IMPROVING = 'IMPROVING'   # RS < 100, Momentum > 100

NSE_TICK_SIZE = 0.05  # Standard tick size for NSE Equities
