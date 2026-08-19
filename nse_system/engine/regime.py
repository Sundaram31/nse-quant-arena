"""Composite Market Regime Classifier synthesizing Trend, India VIX, FII/DII, PCR & RRG."""
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from nse_system.core.constants import MarketRegimeType
from nse_system.core.models import RegimeState, FIIDIIData, OptionsChainData
from nse_system.data.fii_dii import FIIDIIDataProvider
from nse_system.data.options_data import OptionsDataProvider
from nse_system.analytics.volatility import VolatilityEngine
from nse_system.indicators.technical import ema, adx, supertrend

class MarketRegimeClassifier:
    """Determines the current market state and recommends the winning strategy profile."""

    def __init__(self):
        self.fii_provider = FIIDIIDataProvider()
        self.options_provider = OptionsDataProvider()

    def classify_market(
        self,
        symbol: str,
        df_candles: pd.DataFrame,
        current_vix: float = 14.5,
        fii_data: Optional[FIIDIIData] = None,
        options_chain: Optional[OptionsChainData] = None,
        leading_sectors: Optional[List[str]] = None
    ) -> RegimeState:
        """Classifies market regime by fusing multi-dimensional signals."""
        if df_candles.empty or len(df_candles) < 20:
            return RegimeState(
                timestamp=datetime.now(),
                regime_type=MarketRegimeType.SIDEWAYS_LOW_VOL,
                trend_score=0.0,
                vix_level=current_vix,
                vix_regime='NORMAL',
                fii_sentiment='NEUTRAL',
                pcr_level=1.0,
                pcr_sentiment='NEUTRAL',
                leading_sectors=leading_sectors or ['Banking', 'IT'],
                confidence=0.75,
                summary='Market in neutral consolidation with standard volatility.',
                recommended_strategies=['VWAP_SuperTrend', 'CPR_Reversion']
            )

        # 1. Trend Analysis
        close = df_candles['close']
        ema_20 = ema(close, 20).iloc[-1]
        ema_50 = ema(close, min(len(df_candles), 50)).iloc[-1]
        adx_df = adx(df_candles, 14)
        cur_adx = float(adx_df['adx'].iloc[-1])
        plus_di = float(adx_df['plus_di'].iloc[-1])
        minus_di = float(adx_df['minus_di'].iloc[-1])
        
        st_df = supertrend(df_candles, 10, 3.0)
        st_dir = int(st_df['supertrend_direction'].iloc[-1])

        cur_close = float(close.iloc[-1])

        # Trend Score: -1.0 (Strong Bear) to +1.0 (Strong Bull)
        trend_score = 0.0
        if cur_close > ema_20 > ema_50:
            trend_score += 0.4
        elif cur_close < ema_20 < ema_50:
            trend_score -= 0.4

        if st_dir == 1:
            trend_score += 0.3
        else:
            trend_score -= 0.3

        if cur_adx > 25:
            trend_score += 0.3 if plus_di > minus_di else -0.3

        trend_score = float(np.clip(trend_score, -1.0, 1.0))

        # 2. Volatility Analysis
        vix_info = VolatilityEngine.analyze_india_vix(current_vix)

        # 3. Institutional FII/DII Sentiment
        if not fii_data:
            fii_data = self.fii_provider.get_latest_fii_dii_data()
        fii_sentiment = fii_data.institutional_bias

        # 4. Options Chain & PCR
        if not options_chain:
            options_chain = self.options_provider.get_options_chain(symbol, cur_close, atm_iv=current_vix)
        pcr = options_chain.pcr_oi

        if pcr < 0.75:
            pcr_sentiment = 'OVERSOLD_BULLISH'
        elif pcr > 1.35:
            pcr_sentiment = 'OVERBOUGHT_BEARISH'
        else:
            pcr_sentiment = 'NEUTRAL'

        # 5. Composite Regime Determination
        if vix_info.regime == 'EXTREME' or cur_adx > 38:
            regime = MarketRegimeType.VOLATILE_EXPANSION
            summary = 'Volatile Expansion: High swings & elevated India VIX. Wide ATR expansions.'
            recommended = ['Bollinger_RSI', 'CPR_Reversion', 'ORB']
        elif trend_score >= 0.45 and (fii_sentiment in ('BULLISH', 'NEUTRAL')) and pcr >= 0.9:
            regime = MarketRegimeType.BULL_TRENDING
            summary = 'Strong Bullish Trend: Price trading above EMAs with Supertrend Green and institutional support.'
            recommended = ['VWAP_SuperTrend', 'EMA_Crossover', 'RRG_Sector_Momentum', 'ORB']
        elif trend_score <= -0.45 and (fii_sentiment in ('BEARISH', 'NEUTRAL')) and pcr <= 1.1:
            regime = MarketRegimeType.BEAR_TRENDING
            summary = 'Strong Bearish Trend: Heavy distribution below EMAs with Supertrend Red.'
            recommended = ['VWAP_SuperTrend', 'EMA_Crossover', 'OI_Momentum']
        elif vix_info.regime == 'LOW':
            regime = MarketRegimeType.SIDEWAYS_LOW_VOL
            summary = 'Sideways Low Volatility: Range compression. Breakouts from ORB / CPR are high probability.'
            recommended = ['ORB', 'CPR_Reversion', 'EMA_Crossover']
        else:
            regime = MarketRegimeType.SIDEWAYS_HIGH_VOL
            summary = 'Choppy / Rangebound: Two-way swings. Mean reversion off Bollinger Bands and CPR supports dominates.'
            recommended = ['CPR_Reversion', 'Bollinger_RSI', 'OI_Momentum']

        return RegimeState(
            timestamp=datetime.now(),
            regime_type=regime,
            trend_score=round(trend_score, 2),
            vix_level=current_vix,
            vix_regime=vix_info.regime,
            fii_sentiment=fii_sentiment,
            pcr_level=round(pcr, 2),
            pcr_sentiment=pcr_sentiment,
            leading_sectors=leading_sectors or ['Banking', 'Automobile', 'IT'],
            confidence=0.88,
            summary=summary,
            recommended_strategies=recommended
        )
