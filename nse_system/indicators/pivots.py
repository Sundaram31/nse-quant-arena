"""Central Pivot Range (CPR) and Classical / Camarilla Pivot Points Engine."""
from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

@dataclass
class CPRLevels:
    """CPR and classical pivot resistance/support levels."""
    pivot: float
    tc: float          # Top Central Pivot
    bc: float          # Bottom Central Pivot
    cpr_width_pct: float
    cpr_type: str      # 'NARROW' (Trending expected), 'AVERAGE', 'WIDE' (Rangebound expected)
    r1: float
    r2: float
    r3: float
    r4: float
    s1: float
    s2: float
    s3: float
    s4: float

@dataclass
class CamarillaLevels:
    """Camarilla pivot levels."""
    h1: float
    h2: float
    h3: float  # Key Reversal Sell Zone
    h4: float  # Key Breakout Buy Zone
    l1: float
    l2: float
    l3: float  # Key Reversal Buy Zone
    l4: float  # Key Breakdown Sell Zone

class PivotEngine:
    """Calculates Central Pivot Range and Pivot Points for Indian intraday trading."""

    @staticmethod
    def calculate_daily_cpr(high: float, low: float, close: float) -> CPRLevels:
        """Compute CPR and Pivot levels based on previous day High, Low, Close."""
        pivot = (high + low + close) / 3.0
        bc = (high + low) / 2.0
        tc = (pivot - bc) + pivot  # 2 * pivot - bc
        
        # Ensure TC is the higher value if inverted
        top = max(tc, bc)
        bottom = min(tc, bc)

        cpr_width = abs(top - bottom)
        cpr_width_pct = (cpr_width / pivot) * 100.0 if pivot > 0 else 0.0

        if cpr_width_pct < 0.25:
            cpr_type = 'NARROW'
        elif cpr_width_pct > 0.55:
            cpr_type = 'WIDE'
        else:
            cpr_type = 'AVERAGE'

        # Classical Floor Pivots
        r1 = 2.0 * pivot - low
        s1 = 2.0 * pivot - high
        
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        
        r3 = high + 2.0 * (pivot - low)
        s3 = low - 2.0 * (high - pivot)

        r4 = high + 3.0 * (pivot - low)
        s4 = low - 3.0 * (high - pivot)

        return CPRLevels(
            pivot=round(pivot, 2),
            tc=round(top, 2),
            bc=round(bottom, 2),
            cpr_width_pct=round(cpr_width_pct, 3),
            cpr_type=cpr_type,
            r1=round(r1, 2),
            r2=round(r2, 2),
            r3=round(r3, 2),
            r4=round(r4, 2),
            s1=round(s1, 2),
            s2=round(s2, 2),
            s3=round(s3, 2),
            s4=round(s4, 2)
        )

    @staticmethod
    def calculate_camarilla(high: float, low: float, close: float) -> CamarillaLevels:
        """Compute Camarilla intraday pivot points."""
        range_hl = high - low
        h4 = close + (range_hl * 1.1 / 2.0)
        h3 = close + (range_hl * 1.1 / 4.0)
        h2 = close + (range_hl * 1.1 / 6.0)
        h1 = close + (range_hl * 1.1 / 12.0)

        l1 = close - (range_hl * 1.1 / 12.0)
        l2 = close - (range_hl * 1.1 / 6.0)
        l3 = close - (range_hl * 1.1 / 4.0)
        l4 = close - (range_hl * 1.1 / 2.0)

        return CamarillaLevels(
            h1=round(h1, 2), h2=round(h2, 2), h3=round(h3, 2), h4=round(h4, 2),
            l1=round(l1, 2), l2=round(l2, 2), l3=round(l3, 2), l4=round(l4, 2)
        )
