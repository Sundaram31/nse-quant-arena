"""
Fibonacci Retracement & Price Action Engine for NSE Equities.
Calculates Swing Pivots, Fibonacci Golden Pockets (50% - 61.8%), and Candlestick Rejection Signatures.
"""
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Any
import numpy as np
import pandas as pd

@dataclass
class FibonacciLevels:
    swing_high: float
    swing_low: float
    is_uptrend: bool
    fib_0: float        # Extreme (High in uptrend, Low in downtrend)
    fib_236: float      # 23.6% Retracement
    fib_382: float      # 38.2% Retracement
    fib_500: float      # 50.0% Equilibrium / Half-way Retracement
    fib_618: float      # 61.8% Golden Ratio Pocket
    fib_786: float      # 78.6% Deep Retracement
    fib_100: float      # Base (Low in uptrend, High in downtrend)
    fib_ext_127: float  # 127.2% Target Extension
    fib_ext_161: float  # 161.8% Target Extension

@dataclass
class PriceActionSignature:
    pattern_name: str
    is_bullish: bool
    confidence: float
    description: str

class FibonacciEngine:
    """Calculates dynamic Fibonacci Retracements and Extensions on rolling swing points."""

    @staticmethod
    def calculate_fibonacci_levels(
        df: pd.DataFrame,
        lookback_bars: int = 30
    ) -> Optional[FibonacciLevels]:
        """Calculates current Fibonacci grid from the most recent swing high and low."""
        if df.empty or len(df) < lookback_bars:
            return None

        recent_df = df.iloc[-lookback_bars:]
        high_idx = recent_df['high'].idxmax()
        low_idx = recent_df['low'].idxmin()
        
        swing_high = float(recent_df['high'].max())
        swing_low = float(recent_df['low'].min())
        price_range = swing_high - swing_low

        if price_range <= 0.01:
            return None

        # If low occurred before high, it's an uptrend (measuring pullback from high to low)
        is_uptrend = low_idx < high_idx

        if is_uptrend:
            f0 = swing_high
            f236 = round(swing_high - (0.236 * price_range), 2)
            f382 = round(swing_high - (0.382 * price_range), 2)
            f500 = round(swing_high - (0.500 * price_range), 2)
            f618 = round(swing_high - (0.618 * price_range), 2)
            f786 = round(swing_high - (0.786 * price_range), 2)
            f100 = swing_low
            ext127 = round(swing_high + (0.272 * price_range), 2)
            ext161 = round(swing_high + (0.618 * price_range), 2)
        else:
            f0 = swing_low
            f236 = round(swing_low + (0.236 * price_range), 2)
            f382 = round(swing_low + (0.382 * price_range), 2)
            f500 = round(swing_low + (0.500 * price_range), 2)
            f618 = round(swing_low + (0.618 * price_range), 2)
            f786 = round(swing_low + (0.786 * price_range), 2)
            f100 = swing_high
            ext127 = round(swing_low - (0.272 * price_range), 2)
            ext161 = round(swing_low - (0.618 * price_range), 2)

        return FibonacciLevels(
            swing_high=swing_high,
            swing_low=swing_low,
            is_uptrend=is_uptrend,
            fib_0=f0,
            fib_236=f236,
            fib_382=f382,
            fib_500=f500,
            fib_618=f618,
            fib_786=f786,
            fib_100=f100,
            fib_ext_127=ext127,
            fib_ext_161=ext161
        )

    @staticmethod
    def is_in_golden_pocket(
        price: float,
        fib: FibonacciLevels,
        tolerance_pct: float = 0.008
    ) -> Tuple[bool, str]:
        """Checks if price is currently testing the 50% to 61.8% Fibonacci Golden Pocket."""
        if not fib:
            return False, 'No Fib Data'

        if fib.is_uptrend:
            upper_zone = fib.fib_500 * (1.0 + tolerance_pct)
            lower_zone = fib.fib_618 * (1.0 - tolerance_pct)
            in_zone = lower_zone <= price <= upper_zone
            return in_zone, f'Bullish Golden Pocket (₹{fib.fib_618:.2f} - ₹{fib.fib_500:.2f})'
        else:
            lower_zone = fib.fib_500 * (1.0 - tolerance_pct)
            upper_zone = fib.fib_618 * (1.0 + tolerance_pct)
            in_zone = lower_zone <= price <= upper_zone
            return in_zone, f'Bearish Golden Resistance (₹{fib.fib_500:.2f} - ₹{fib.fib_618:.2f})'


class PriceActionDetector:
    """Detects multi-touch Support/Resistance, Pin Bars, and Engulfing Price Action signatures."""

    @staticmethod
    def detect_candle_pattern(
        open_p: float,
        high_p: float,
        low_p: float,
        close_p: float,
        prev_open: Optional[float] = None,
        prev_close: Optional[float] = None
    ) -> Optional[PriceActionSignature]:
        """Classifies the price action morphology of a candlestick."""
        candle_range = max(0.01, high_p - low_p)
        body = abs(close_p - open_p)
        body_top = max(open_p, close_p)
        body_bottom = min(open_p, close_p)

        upper_wick = high_p - body_top
        lower_wick = body_bottom - low_p

        # 1. Bullish Pin Bar / Hammer (Long lower wick >= 55% of total range)
        if lower_wick >= 0.55 * candle_range and upper_wick <= 0.20 * candle_range and close_p >= open_p:
            return PriceActionSignature(
                pattern_name='Bullish Pin Bar / Hammer',
                is_bullish=True,
                confidence=0.88,
                description=f'Strong rejection of lower prices (Lower wick: {lower_wick/candle_range*100:.0f}% of range)'
            )

        # 2. Bearish Shooting Star (Long upper wick >= 55% of total range)
        if upper_wick >= 0.55 * candle_range and lower_wick <= 0.20 * candle_range and close_p <= open_p:
            return PriceActionSignature(
                pattern_name='Bearish Shooting Star',
                is_bullish=False,
                confidence=0.88,
                description=f'Heavy selling rejection from higher prices (Upper wick: {upper_wick/candle_range*100:.0f}% of range)'
            )

        # 3. Bullish Engulfing
        if prev_open is not None and prev_close is not None:
            if prev_close < prev_open and close_p > open_p and close_p > prev_open and open_p <= prev_close:
                return PriceActionSignature(
                    pattern_name='Bullish Engulfing',
                    is_bullish=True,
                    confidence=0.85,
                    description='Green body completely engulfs previous bearish candle.'
                )

        # 4. Bearish Engulfing
        if prev_open is not None and prev_close is not None:
            if prev_close > prev_open and close_p < open_p and close_p < prev_open and open_p >= prev_close:
                return PriceActionSignature(
                    pattern_name='Bearish Engulfing',
                    is_bullish=False,
                    confidence=0.85,
                    description='Red body completely engulfs previous bullish candle.'
                )

        return None
