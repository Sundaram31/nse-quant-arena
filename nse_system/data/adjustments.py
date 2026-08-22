"""
Corporate Action & Split / Bonus Adjustment Engine for NSE Equities.
Applies backward price and volume adjustments to remove split and bonus discontinuities
from raw NSE Bhavcopy data, ensuring smooth EMAs, ATR, RSI, and accurate P&L calculations.
"""
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd

# Standard NSE Split & Bonus Multiplier Thresholds
STANDARD_RATIOS = [
    (0.10, 0.10, "1:10 Split"),
    (0.20, 0.20, "1:5 Split"),
    (0.25, 0.25, "1:4 Split"),
    (0.3333, 0.3333, "1:2 Bonus / 1:3 Split"),
    (0.50, 0.50, "1:1 Bonus / 1:2 Split"),
    (0.6667, 0.6667, "1:2 Bonus / 2:3 Ratio"),
]

class CorporateActionAdjuster:
    """Detects and applies backward split/bonus adjustments on OHLCV DataFrames."""

    @staticmethod
    def detect_corporate_actions(
        df: pd.DataFrame,
        tolerance: float = 0.08
    ) -> List[Dict[str, Any]]:
        """Scans a price series for split and bonus discontinuities."""
        if df.empty or len(df) < 5:
            return []

        events = []
        close = df['close']
        prev_close = close.shift(1)
        overnight_ratios = close / prev_close

        for i in range(1, len(df)):
            ratio = float(overnight_ratios.iloc[i])
            if np.isnan(ratio):
                continue

            # Check if ratio is <= 0.68 (representing a >= 32% overnight drop)
            if ratio <= 0.68:
                matched_factor = None
                matched_label = None
                
                for expected_ratio, factor, label in STANDARD_RATIOS:
                    if abs(ratio - expected_ratio) <= tolerance:
                        matched_factor = expected_ratio
                        matched_label = label
                        break

                if matched_factor is not None:
                    events.append({
                        'date': df.index[i],
                        'index_pos': i,
                        'observed_ratio': ratio,
                        'adjustment_factor': matched_factor,
                        'description': matched_label,
                        'prev_close': float(prev_close.iloc[i]),
                        'new_close': float(close.iloc[i])
                    })

        return events

    @classmethod
    def adjust_dataframe(
        cls,
        df: pd.DataFrame,
        events: Optional[List[Dict[str, Any]]] = None
    ) -> pd.DataFrame:
        """
        Applies backward adjustment to Open, High, Low, Close, VWAP, and Volume.
        Past prices are multiplied by adjustment factor, past volume is divided by factor.
        """
        if df.empty or len(df) < 5:
            return df

        df_adj = df.copy()
        if events is None:
            events = cls.detect_corporate_actions(df)

        if not events:
            return df_adj

        # Calculate cumulative backward adjustment factors
        # Start with factor 1.0 for the latest data, and multiply backwards at each ex-date
        adj_multipliers = np.ones(len(df_adj))
        
        # Sort events descending by date
        sorted_events = sorted(events, key=lambda x: x['date'], reverse=True)
        cumulative_factor = 1.0

        for ev in sorted_events:
            pos = ev['index_pos']
            factor = ev['adjustment_factor']
            cumulative_factor *= factor
            # Apply cumulative factor to all bars prior to this corporate action date
            adj_multipliers[:pos] *= factor

        # Apply adjustments
        for col in ['open', 'high', 'low', 'close', 'vwap']:
            if col in df_adj.columns:
                df_adj[col] = (df_adj[col] * adj_multipliers).round(2)

        if 'volume' in df_adj.columns:
            df_adj['volume'] = (df_adj['volume'] / adj_multipliers).round(0)

        return df_adj
