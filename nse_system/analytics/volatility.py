"""India VIX Regimes, Implied Volatility (IV Rank & Percentile), and Black-Scholes Greeks Engine."""
from dataclasses import dataclass
from typing import Dict, Any, Tuple
import math
import numpy as np

@dataclass
class VIXRegimeInfo:
    vix: float
    regime: str           # 'LOW', 'NORMAL', 'HIGH', 'EXTREME'
    iv_rank: float        # 0 to 100
    iv_percentile: float  # 0 to 100
    regime_description: str
    suitable_strategies: list

def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

class VolatilityEngine:
    """Analytics engine for VIX regimes, IV Rank, and Options Greeks."""

    @staticmethod
    def analyze_india_vix(current_vix: float, historical_vix: list = None) -> VIXRegimeInfo:
        """Evaluate India VIX and determine market volatility environment."""
        if not historical_vix:
            historical_vix = [11.2, 12.5, 13.8, 14.2, 15.1, 16.3, 17.5, 18.9, 21.0, 13.0, 14.5]

        min_vix = min(historical_vix)
        max_vix = max(historical_vix)

        # IV Rank (IVR)
        ivr = ((current_vix - min_vix) / max(0.1, max_vix - min_vix)) * 100.0
        ivr = float(np.clip(ivr, 0.0, 100.0))

        # IV Percentile (IVP)
        count_below = sum(1 for v in historical_vix if v < current_vix)
        ivp = (count_below / max(1, len(historical_vix))) * 100.0

        if current_vix < 12.0:
            regime = 'LOW'
            desc = 'Low Volatility / Market Consolidation. Options buying is cheap; breakouts are explosive.'
            strats = ['Opening Range Breakout (ORB)', 'Multi-EMA Trend Rider', 'Long Straddle']
        elif current_vix <= 16.5:
            regime = 'NORMAL'
            desc = 'Normal Volatility. Balanced market, ideal for directional trend following and swing momentum.'
            strats = ['VWAP + SuperTrend', 'Multi-EMA Crossover', 'RRG Sector Momentum']
        elif current_vix <= 22.0:
            regime = 'HIGH'
            desc = 'High Volatility / Sharp Swings. Mean reversion and wide CPR support/resistance bounces dominate.'
            strats = ['CPR Reversion', 'Bollinger Bands + RSI', 'Iron Condor / Short Strangle']
        else:
            regime = 'EXTREME'
            desc = 'Extreme Volatility / High Panic or Event Day. Wide swings, use reduced position sizing.'
            strats = ['Bollinger Reversion', 'Defined-Risk Hedged Spreads']

        return VIXRegimeInfo(
            vix=round(current_vix, 2),
            regime=regime,
            iv_rank=round(ivr, 1),
            iv_percentile=round(ivp, 1),
            regime_description=desc,
            suitable_strategies=strats
        )

    @classmethod
    def black_scholes_price(
        cls,
        spot: float,
        strike: float,
        t_years: float,
        r: float,
        iv: float,
        option_type: str = 'CE'
    ) -> float:
        """Black-Scholes option pricing model."""
        if t_years <= 0:
            return max(0.0, spot - strike) if option_type == 'CE' else max(0.0, strike - spot)
        if iv <= 0:
            iv = 0.01

        d1 = (math.log(spot / strike) + (r + 0.5 * iv * iv) * t_years) / (iv * math.sqrt(t_years))
        d2 = d1 - iv * math.sqrt(t_years)

        if option_type == 'CE':
            price = spot * _norm_cdf(d1) - strike * math.exp(-r * t_years) * _norm_cdf(d2)
        else:
            price = strike * math.exp(-r * t_years) * _norm_cdf(-d2) - spot * _norm_cdf(-d1)

        return max(0.05, price)

    @classmethod
    def calculate_greeks(
        cls,
        spot: float,
        strike: float,
        t_years: float,
        r: float,
        iv: float,
        option_type: str = 'CE'
    ) -> Dict[str, float]:
        """Calculate Black-Scholes Greeks: Delta, Gamma, Theta, Vega."""
        if t_years <= 0.0001:
            return {'delta': 1.0 if option_type == 'CE' else -1.0, 'gamma': 0.0, 'theta': 0.0, 'vega': 0.0}

        d1 = (math.log(spot / strike) + (r + 0.5 * iv * iv) * t_years) / (iv * math.sqrt(t_years))
        d2 = d1 - iv * math.sqrt(t_years)

        pdf_d1 = _norm_pdf(d1)
        gamma = pdf_d1 / (spot * iv * math.sqrt(t_years))
        vega = spot * math.sqrt(t_years) * pdf_d1 / 100.0  # per 1% IV change

        if option_type == 'CE':
            delta = _norm_cdf(d1)
            theta = (- (spot * pdf_d1 * iv) / (2.0 * math.sqrt(t_years)) - r * strike * math.exp(-r * t_years) * _norm_cdf(d2)) / 365.0
        else:
            delta = _norm_cdf(d1) - 1.0
            theta = (- (spot * pdf_d1 * iv) / (2.0 * math.sqrt(t_years)) + r * strike * math.exp(-r * t_years) * _norm_cdf(-d2)) / 365.0

        return {
            'delta': round(delta, 4),
            'gamma': round(gamma, 6),
            'theta': round(theta, 4),
            'vega': round(vega, 4)
        }
