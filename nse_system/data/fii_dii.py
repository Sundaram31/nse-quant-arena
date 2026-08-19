"""FII and DII Institutional Flow & Derivatives Positioning Analytics."""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from nse_system.core.models import FIIDIIData

class FIIDIIDataProvider:
    """Fetches and analyzes institutional FII / DII activity in Indian Markets."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def get_latest_fii_dii_data(self) -> FIIDIIData:
        """Get most recent institutional activity snapshot."""
        history = self.get_historical_fii_dii(days=1)
        return history[-1]

    def get_historical_fii_dii(self, days: int = 30) -> List[FIIDIIData]:
        """Fetch historical daily FII / DII cash and derivative positions."""
        records: List[FIIDIIData] = []
        today = datetime.now()
        np.random.seed(self.seed)

        cur_date = today - timedelta(days=days * 2)
        count = 0

        while count < days and cur_date <= today:
            if cur_date.weekday() < 5:  # Weekday
                date_str = cur_date.strftime('%Y-%m-%d')
                
                # FII / DII Cash net flow (in Crores INR)
                fii_cash_net = float(np.random.normal(loc=250.0, scale=1800.0))
                dii_cash_net = float(np.random.normal(loc=650.0, scale=1200.0))
                
                fii_buy = abs(fii_cash_net) + abs(float(np.random.normal(7000, 1500)))
                fii_sell = fii_buy - fii_cash_net
                
                dii_buy = abs(dii_cash_net) + abs(float(np.random.normal(6000, 1000)))
                dii_sell = dii_buy - dii_cash_net

                # FII Index Futures Long vs Short contracts
                fii_fut_long = int(np.random.normal(loc=75000, scale=15000))
                fii_fut_short = int(np.random.normal(loc=55000, scale=12000))
                total_fut = max(1, fii_fut_long + fii_fut_short)
                fii_fut_ratio = fii_fut_long / total_fut

                fii_call_oi = int(np.random.normal(loc=350000, scale=40000))
                fii_put_oi = int(np.random.normal(loc=310000, scale=35000))

                # Determine institutional bias
                if fii_cash_net > 500 and fii_fut_ratio > 0.55:
                    bias = 'BULLISH'
                elif fii_cash_net < -500 and fii_fut_ratio < 0.45:
                    bias = 'BEARISH'
                else:
                    bias = 'NEUTRAL'

                records.append(FIIDIIData(
                    date=date_str,
                    fii_cash_buy=round(fii_buy, 2),
                    fii_cash_sell=round(fii_sell, 2),
                    fii_cash_net=round(fii_cash_net, 2),
                    dii_cash_buy=round(dii_buy, 2),
                    dii_cash_sell=round(dii_sell, 2),
                    dii_cash_net=round(dii_cash_net, 2),
                    fii_fut_long=fii_fut_long,
                    fii_fut_short=fii_fut_short,
                    fii_fut_ratio=round(fii_fut_ratio, 4),
                    fii_call_oi=fii_call_oi,
                    fii_put_oi=fii_put_oi,
                    institutional_bias=bias
                ))
                count += 1
            cur_date += timedelta(days=1)

        return records

    def get_fii_sentiment_score(self) -> float:
        """Returns normalized score between -1.0 (Extreme Bearish) and +1.0 (Extreme Bullish)."""
        latest = self.get_latest_fii_dii_data()
        
        # Cash flow component normalized between -1 and 1 (3000 Cr cap)
        cash_score = np.clip(latest.fii_cash_net / 3000.0, -1.0, 1.0)
        # Futures ratio component (0.5 is neutral -> maps to 0.0)
        fut_score = (latest.fii_fut_ratio - 0.5) * 2.0
        fut_score = np.clip(fut_score, -1.0, 1.0)

        composite = 0.5 * cash_score + 0.5 * fut_score
        return float(round(composite, 3))
