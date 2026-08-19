"""Data models for the NSE Quantitative Strategy Platform."""
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, List, Optional, Any
from nse_system.core.constants import (
    OrderSide, OrderType, OrderStatus, ProductType,
    MarketRegimeType, OptionType, OIBuildupType, RRGQuadrant
)

@dataclass
class Candle:
    """OHLCV+OI Candle representation."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    oi: float = 0.0
    vwap: Optional[float] = None

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def range(self) -> float:
        return self.high - self.low

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

@dataclass
class Tick:
    """Market tick data representation."""
    timestamp: datetime
    symbol: str
    ltp: float
    volume: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    oi: float = 0.0

@dataclass
class Signal:
    """Strategy generated trading signal."""
    timestamp: datetime
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'EXIT_LONG', 'EXIT_SHORT', 'HOLD'
    price: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    trailing_sl: Optional[float] = None
    reason: str = ''
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Order:
    """Order record representing broker orders."""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    product_type: ProductType = ProductType.MIS
    quantity: int = 1
    price: float = 0.0
    trigger_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    avg_price: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    tag: str = ''
    reject_reason: Optional[str] = None

@dataclass
class Trade:
    """Completed trade record with PnL and tax breakdown."""
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    product_type: ProductType
    quantity: int
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    gross_pnl: float
    net_pnl: float
    taxes: float
    return_pct: float
    holding_duration_mins: float
    exit_reason: str = 'TARGET'
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Position:
    """Open market position."""
    symbol: str
    product_type: ProductType
    quantity: int = 0  # positive for long, negative for short
    avg_price: float = 0.0
    ltp: float = 0.0
    realized_pnl: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.quantity != 0

    @property
    def unrealized_pnl(self) -> float:
        if self.quantity == 0:
            return 0.0
        return (self.ltp - self.avg_price) * self.quantity

    @property
    def market_value(self) -> float:
        return abs(self.quantity) * self.ltp

@dataclass
class Portfolio:
    """Portfolio tracking capital, positions, and NAV."""
    initial_capital: float
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    closed_trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_portfolio_value(self) -> float:
        unrealized = sum(pos.unrealized_pnl for pos in self.positions.values())
        return self.cash + unrealized

@dataclass
class OptionContract:
    """Option strike data."""
    symbol: str
    underlying: str
    strike: float
    option_type: OptionType
    expiry: str
    ltp: float
    oi: float
    change_in_oi: float
    iv: float
    volume: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    buildup: OIBuildupType = OIBuildupType.NEUTRAL

@dataclass
class OptionsChainData:
    """Snapshot of full options chain for an underlying."""
    underlying: str
    timestamp: datetime
    spot_price: float
    atm_strike: float
    pcr_oi: float
    pcr_volume: float
    max_pain: float
    contracts: List[OptionContract] = field(default_factory=list)
    call_oi_total: float = 0.0
    put_oi_total: float = 0.0
    major_resistance_strike: float = 0.0
    major_support_strike: float = 0.0

@dataclass
class FIIDIIData:
    """FII and DII institutional flow record."""
    date: str
    fii_cash_buy: float
    fii_cash_sell: float
    fii_cash_net: float
    dii_cash_buy: float
    dii_cash_sell: float
    dii_cash_net: float
    fii_fut_long: int
    fii_fut_short: int
    fii_fut_ratio: float  # Long / (Long + Short)
    fii_call_oi: int = 0
    fii_put_oi: int = 0
    institutional_bias: str = 'NEUTRAL'  # 'BULLISH', 'BEARISH', 'NEUTRAL'

@dataclass
class RegimeState:
    """Market Regime snapshot."""
    timestamp: datetime
    regime_type: MarketRegimeType
    trend_score: float         # -1.0 to 1.0
    vix_level: float
    vix_regime: str            # 'LOW', 'NORMAL', 'HIGH', 'EXTREME'
    fii_sentiment: str         # 'BULLISH', 'BEARISH', 'NEUTRAL'
    pcr_level: float
    pcr_sentiment: str         # 'OVERSOLD_BULLISH', 'OVERBOUGHT_BEARISH', 'NEUTRAL'
    leading_sectors: List[str] = field(default_factory=list)
    confidence: float = 0.8
    summary: str = ''
    recommended_strategies: List[str] = field(default_factory=list)

@dataclass
class StrategyPerformance:
    """Quantitative evaluation metrics for a strategy."""
    strategy_name: str
    symbol: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    gross_pnl: float
    total_taxes: float
    net_pnl: float
    roi_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown_pct: float
    max_drawdown_duration_days: float
    calmar_ratio: float
    expectancy: float
    alpha_score: float  # Composite winning score for current regime
    trades: List[Trade] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
