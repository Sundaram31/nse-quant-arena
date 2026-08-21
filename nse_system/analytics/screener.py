"""Multi-Factor Quantitative Stock Screener & Live Intraday Radar Engine (Price + Volume + Sentiment)."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from enum import Enum
import pandas as pd
import numpy as np

from nse_system.data.universe import UniverseManager
from nse_system.data.symbols import get_symbol_info
from nse_system.data.historical import NSEHistoricalDataProvider
from nse_system.data.options_data import OptionsDataProvider
from nse_system.data.news_sentiment import NewsSentimentEngine, StockSentimentReport
from nse_system.indicators.technical import ema, sma, rsi, atr, vwap
from nse_system.indicators.pivots import PivotEngine, CPRLevels
from nse_system.analytics.rrg import RRGAnalyzer, RRGQuadrant
from nse_system.strategies import get_strategy

class TradingType(Enum):
    SWING_LONG = 'SWING_LONG'
    SWING_SHORT = 'SWING_SHORT'
    INTRADAY_LONG = 'INTRADAY_LONG'
    INTRADAY_SHORT = 'INTRADAY_SHORT'
    NEUTRAL = 'NEUTRAL'

@dataclass
class ScreenerCandidate:
    symbol: str
    trading_type: TradingType
    matched_strategy: str
    confidence_score: float     # 0 to 100
    current_price: float
    entry_trigger: float
    stop_loss: float
    target_1: float            # 1:2 Risk-Reward (Partial Profit & SL to Breakeven)
    target_2: float            # 1:3 Risk-Reward (Full Runner Target)
    risk_reward_ratio: str
    rrg_quadrant: str
    oi_buildup: str
    catalyst_reason: str
    sentiment: str = '🟢 POSITIVE'
    timestamp: datetime = field(default_factory=datetime.now)

class QuantStockScreener:
    """Scans NSE universe across the 3 Pillars: Price Structure, Volume Action, and Sentiment."""

    def __init__(self, data_provider: Optional[NSEHistoricalDataProvider] = None):
        self.data_provider = data_provider or NSEHistoricalDataProvider()
        self.options_provider = OptionsDataProvider()
        self.rrg_analyzer = RRGAnalyzer()
        self.news_engine = NewsSentimentEngine()

    def scan_live_intraday_radar(
        self,
        universe_name: str = 'fno',
        timeframe: str = '5m'
    ) -> List[ScreenerCandidate]:
        """Scans short-timeframe (5m/15m) intraday candles to pop up today's live actionable trades."""
        symbols = UniverseManager.get_universe(universe_name)[:50]
        radar_picks: List[ScreenerCandidate] = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=5)

        for sym in symbols:
            try:
                candles = self.data_provider.get_historical_candles(sym, start_date, end_date, timeframe)
                if len(candles) < 30:
                    continue

                curr_c = candles[-1]
                curr_price = curr_c.close

                # Evaluate Helega Milega on small timeframe
                strat_hm = get_strategy('Helega_Milega', symbol=sym, timeframe=timeframe)
                sig_hm = strat_hm.on_candle(curr_c, candles)
                if sig_hm:
                    risk = max(1.0, abs(curr_price - sig_hm.stop_loss))
                    t1 = round(curr_price + 2.0 * risk if sig_hm.signal_type.value == 'BUY' else curr_price - 2.0 * risk, 2)
                    t2 = round(curr_price + 3.0 * risk if sig_hm.signal_type.value == 'BUY' else curr_price - 3.0 * risk, 2)
                    radar_picks.append(ScreenerCandidate(
                        symbol=sym,
                        trading_type=TradingType.INTRADAY_LONG if sig_hm.signal_type.value == 'BUY' else TradingType.INTRADAY_SHORT,
                        matched_strategy='🔥 Helega Milega (RSI Smoothed + VWAP)',
                        confidence_score=94.0,
                        current_price=curr_price,
                        entry_trigger=curr_price,
                        stop_loss=sig_hm.stop_loss,
                        target_1=t1,
                        target_2=t2,
                        risk_reward_ratio='1:2.0 (Target 1) | 1:3.0 (Target 2)',
                        rrg_quadrant='Intraday Momentum',
                        oi_buildup='Volume Surge',
                        catalyst_reason=sig_hm.metadata.get('reason', 'Helega Milega Intraday Crossover')
                    ))
                    continue

                # Evaluate Price Volume Action
                strat_pva = get_strategy('Price_Volume_Action', symbol=sym, timeframe=timeframe)
                sig_pva = strat_pva.on_candle(curr_c, candles)
                if sig_pva:
                    risk = max(1.0, abs(curr_price - sig_pva.stop_loss))
                    t1 = round(curr_price + 2.0 * risk if sig_pva.signal_type.value == 'BUY' else curr_price - 2.0 * risk, 2)
                    t2 = round(curr_price + 3.0 * risk if sig_pva.signal_type.value == 'BUY' else curr_price - 3.0 * risk, 2)
                    radar_picks.append(ScreenerCandidate(
                        symbol=sym,
                        trading_type=TradingType.INTRADAY_LONG if sig_pva.signal_type.value == 'BUY' else TradingType.INTRADAY_SHORT,
                        matched_strategy='⚡ Price-Volume Action (PVA 20-Bar Breakout)',
                        confidence_score=92.0,
                        current_price=curr_price,
                        entry_trigger=curr_price,
                        stop_loss=sig_pva.stop_loss,
                        target_1=t1,
                        target_2=t2,
                        risk_reward_ratio='1:2.0 (Target 1) | 1:3.0 (Target 2)',
                        rrg_quadrant='Institutional Footprint',
                        oi_buildup='Ultra-High Volume Breakout',
                        catalyst_reason=sig_pva.metadata.get('reason', 'PVA Breakout')
                    ))
                    continue

                # Evaluate VWAP SuperTrend
                strat_vwap = get_strategy('VWAP_SuperTrend', symbol=sym, timeframe=timeframe)
                sig_vwap = strat_vwap.on_candle(curr_c, candles)
                if sig_vwap:
                    risk = max(1.0, abs(curr_price - sig_vwap.stop_loss))
                    t1 = round(curr_price + 2.0 * risk if sig_vwap.signal_type.value == 'BUY' else curr_price - 2.0 * risk, 2)
                    t2 = round(curr_price + 3.0 * risk if sig_vwap.signal_type.value == 'BUY' else curr_price - 3.0 * risk, 2)
                    radar_picks.append(ScreenerCandidate(
                        symbol=sym,
                        trading_type=TradingType.INTRADAY_LONG if sig_vwap.signal_type.value == 'BUY' else TradingType.INTRADAY_SHORT,
                        matched_strategy='VWAP + SuperTrend Directional',
                        confidence_score=88.0,
                        current_price=curr_price,
                        entry_trigger=curr_price,
                        stop_loss=sig_vwap.stop_loss,
                        target_1=t1,
                        target_2=t2,
                        risk_reward_ratio='1:2.0 (Target 1) | 1:3.0 (Target 2)',
                        rrg_quadrant='Trend Following',
                        oi_buildup='Trend Aligned',
                        catalyst_reason='VWAP & SuperTrend aligned with momentum'
                    ))

            except Exception:
                continue

        radar_picks.sort(key=lambda x: x.confidence_score, reverse=True)
        return radar_picks

    def scan_universe(
        self,
        universe_name: str = 'fno',
        min_confidence: float = 60.0
    ) -> List[ScreenerCandidate]:
        """Runs comprehensive multi-factor scan across the stock universe."""
        symbols = UniverseManager.get_universe(universe_name)
        return self.scan_custom_symbols(symbols[:60], min_confidence=min_confidence)

    def scan_custom_symbols(
        self,
        symbols: List[str],
        min_confidence: float = 50.0
    ) -> List[ScreenerCandidate]:
        """Runs scan on a user-provided list of favourite stocks/symbols."""
        candidates: List[ScreenerCandidate] = []
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)

        # Compute RRG Relative Strength vs NIFTY 50 Benchmark
        benchmark_df = self.data_provider.get_historical_dataframe('NIFTY 50', start_date, end_date, '1d')
        basket_data = {}
        stock_dfs = {}

        for sym in symbols:
            clean_sym = sym.strip().upper()
            if not clean_sym:
                continue
            try:
                df_daily = self.data_provider.get_historical_dataframe(clean_sym, start_date, end_date, '1d')
                if len(df_daily) >= 15:
                    basket_data[clean_sym] = df_daily['close']
                    stock_dfs[clean_sym] = df_daily
            except Exception:
                continue

        rrg_map = self.rrg_analyzer.calculate_rrg(basket_data, benchmark_df['close']) if basket_data else {}

        # Evaluate Multi-Factor Quant Setup for Each Stock
        for sym, df_daily in stock_dfs.items():
            try:
                cand = self._evaluate_stock(sym, df_daily, rrg_map.get(sym))
                if cand and cand.confidence_score >= min_confidence:
                    candidates.append(cand)
            except Exception:
                continue

        candidates.sort(key=lambda x: x.confidence_score, reverse=True)
        return candidates

    def diagnose_single_stock(self, symbol: str) -> Dict[str, Any]:
        """Generates a comprehensive 360-degree quant diagnostic health card for any favourite stock."""
        clean_sym = symbol.strip().upper()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)

        df_daily = self.data_provider.get_historical_dataframe(clean_sym, start_date, end_date, '1d')
        benchmark_df = self.data_provider.get_historical_dataframe('NIFTY 50', start_date, end_date, '1d')

        closes = df_daily['close']
        highs = df_daily['high']
        lows = df_daily['low']
        volumes = df_daily['volume']

        curr_price = float(closes.iloc[-1])
        prev_close = float(closes.iloc[-2]) if len(closes) > 1 else curr_price
        chg_pct = (curr_price - prev_close) / prev_close * 100.0

        # Technical Indicators
        ema9_val = float(ema(closes, 9).iloc[-1])
        ema21_val = float(ema(closes, 21).iloc[-1])
        ema50_val = float(ema(closes, 50).iloc[-1]) if len(closes) >= 50 else ema21_val
        rsi_val = float(rsi(closes, 14).iloc[-1])
        atr_val = float(atr(df_daily, 14).iloc[-1])
        vol_avg = float(volumes.iloc[-20:].mean()) if len(volumes) >= 20 else float(volumes.mean())
        rel_vol = float(volumes.iloc[-1] / max(1.0, vol_avg))

        # Pivots
        prev_high = float(highs.iloc[-2]) if len(highs) > 1 else float(highs.iloc[-1])
        prev_low = float(lows.iloc[-2]) if len(lows) > 1 else float(lows.iloc[-1])
        cpr = PivotEngine.calculate_daily_cpr(prev_high, prev_low, prev_close)

        # RRG calculation
        rrg_res = self.rrg_analyzer.calculate_rrg({clean_sym: closes}, benchmark_df['close'])
        rrg_pt = rrg_res.get(clean_sym)
        quadrant = rrg_pt.quadrant.value if rrg_pt else 'IMPROVING'
        rs_ratio = rrg_pt.rs_ratio if rrg_pt else 100.0
        rs_momentum = rrg_pt.rs_momentum if rrg_pt else 100.0

        # Options chain
        chain = self.options_provider.get_options_chain(clean_sym, curr_price, atm_iv=15.0)

        # News & Corporate Catalyst Report
        sentiment_report = self.news_engine.analyze_stock_sentiment(clean_sym)

        # Multi-factor score & verdict
        strengths = []
        risks = []
        bullish_pts = 0
        bearish_pts = 0

        # Trend test
        if curr_price > ema21_val and ema9_val > ema21_val:
            bullish_pts += 30
            strengths.append(f'Bullish 9/21 EMA Golden Cross (₹{ema9_val:.2f} > ₹{ema21_val:.2f})')
        elif curr_price < ema21_val and ema9_val < ema21_val:
            bearish_pts += 30
            risks.append(f'Bearish 9/21 EMA Death Cross (₹{ema9_val:.2f} < ₹{ema21_val:.2f})')

        if curr_price > ema50_val:
            bullish_pts += 15
            strengths.append(f'Price trading comfortably above 50-period moving average (₹{ema50_val:.2f})')
        else:
            bearish_pts += 15
            risks.append(f'Price trading below 50-period moving average (₹{ema50_val:.2f})')

        # RSI test
        if 55.0 <= rsi_val <= 70.0:
            bullish_pts += 20
            strengths.append(f'Strong bullish momentum with healthy RSI ({rsi_val:.1f})')
        elif rsi_val > 70.0:
            bullish_pts += 10
            risks.append(f'RSI is in Overbought zone ({rsi_val:.1f}) - watch for mean reversion pullback')
        elif rsi_val < 45.0:
            bearish_pts += 20
            risks.append(f'Weak momentum with low RSI ({rsi_val:.1f})')

        # RRG test
        if quadrant in ('LEADING', 'IMPROVING'):
            bullish_pts += 25
            strengths.append(f'Relative Strength is strong vs NIFTY 50 ({quadrant} Quadrant | RS-Ratio: {rs_ratio:.2f})')
        else:
            bearish_pts += 25
            risks.append(f'Underperforming the broader market ({quadrant} Quadrant | RS-Ratio: {rs_ratio:.2f})')

        # Volume test
        if rel_vol > 1.2:
            strengths.append(f'Institutional volume participation ({rel_vol:.1f}x of 20-day average)')

        # News & Earnings Catalyst
        if sentiment_report.overall_sentiment == '🟢 POSITIVE':
            bullish_pts += 10
            strengths.append(f'Positive Financial Media Sentiment ({sentiment_report.sentiment_score:+.0f}/100)')
        elif sentiment_report.overall_sentiment == '🔴 NEGATIVE':
            bearish_pts += 10
            risks.append(f'Negative Financial Media Sentiment ({sentiment_report.sentiment_score:+.0f}/100)')

        if sentiment_report.is_earnings_imminent:
            risks.append(f'⚠️ Imminent Quarterly Results ({sentiment_report.upcoming_earnings_date}) - Event Gap Risk!')

        # CPR test
        if cpr.cpr_type == 'NARROW':
            strengths.append(f'Narrow CPR ({cpr.cpr_width_pct:.2f}%) indicates imminent explosive breakout move')

        # Final Verdict
        if bullish_pts >= 60 and bullish_pts > bearish_pts:
            verdict = '🟢 STRONGLY BULLISH'
            rec_setup = 'SWING LONG'
            sl = round(min(curr_price - (1.5 * atr_val), cpr.bc), 2)
            risk = max(1.0, curr_price - sl)
            t1 = round(curr_price + (2.0 * risk), 2)
            t2 = round(curr_price + (3.0 * risk), 2)
            confidence = min(96.0, 50.0 + bullish_pts / 2.0)
        elif bearish_pts >= 60 and bearish_pts > bullish_pts:
            verdict = '🔴 STRONGLY BEARISH'
            rec_setup = 'SWING SHORT'
            sl = round(max(curr_price + (1.5 * atr_val), cpr.tc), 2)
            risk = max(1.0, sl - curr_price)
            t1 = round(curr_price - (2.0 * risk), 2)
            t2 = round(curr_price - (3.0 * risk), 2)
            confidence = min(96.0, 50.0 + bearish_pts / 2.0)
        elif cpr.cpr_type == 'NARROW' or rel_vol > 1.5:
            is_bull = curr_price >= prev_close
            verdict = '⚡ HIGH VOLATILITY / BREAKOUT'
            rec_setup = 'INTRADAY LONG BREAKOUT' if is_bull else 'INTRADAY SHORT BREAKDOWN'
            if is_bull:
                sl = round(curr_price - (1.0 * atr_val), 2)
                risk = max(1.0, curr_price - sl)
                t1 = round(curr_price + (2.0 * risk), 2)
                t2 = round(curr_price + (3.0 * risk), 2)
            else:
                sl = round(curr_price + (1.0 * atr_val), 2)
                risk = max(1.0, sl - curr_price)
                t1 = round(curr_price - (2.0 * risk), 2)
                t2 = round(curr_price - (3.0 * risk), 2)
            confidence = 75.0
        else:
            verdict = '⚪ CONSOLIDATION / RANGEBOUND'
            if curr_price <= cpr.pivot:
                rec_setup = 'CPR MEAN REVERSION (BUY DIP AT SUPPORT)'
                sl = round(min(curr_price - (1.0 * atr_val), cpr.s1), 2)
                risk = max(1.0, curr_price - sl)
                t1 = round(curr_price + (1.5 * risk), 2)
                t2 = round(curr_price + (2.5 * risk), 2)
            else:
                rec_setup = 'CPR MEAN REVERSION (SELL POP AT RESISTANCE)'
                sl = round(max(curr_price + (1.0 * atr_val), cpr.r1), 2)
                risk = max(1.0, sl - curr_price)
                t1 = round(curr_price - (1.5 * risk), 2)
                t2 = round(curr_price - (2.5 * risk), 2)
            confidence = 58.0

        return {
            'symbol': clean_sym,
            'current_price': curr_price,
            'change_pct': chg_pct,
            'verdict': verdict,
            'recommended_setup': rec_setup,
            'confidence_score': confidence,
            'entry_trigger': curr_price,
            'stop_loss': sl,
            'target_1': t1,
            'target_2': t2,
            'risk_reward': '1:2.0 (Target 1) | 1:3.0 (Target 2)',
            'rrg_quadrant': quadrant,
            'rs_ratio': rs_ratio,
            'rs_momentum': rs_momentum,
            'ema9': ema9_val,
            'ema21': ema21_val,
            'ema50': ema50_val,
            'rsi': rsi_val,
            'atr': atr_val,
            'rel_volume': rel_vol,
            'cpr': cpr,
            'options_chain': chain,
            'sentiment_report': sentiment_report,
            'strengths': strengths,
            'risks': risks
        }

    def _evaluate_stock(
        self,
        symbol: str,
        df_daily: pd.DataFrame,
        rrg_pt: Optional[Any]
    ) -> Optional[ScreenerCandidate]:
        """Evaluates technicals, pivots, options buildup, and RRG quadrant for a stock."""
        if len(df_daily) < 15:
            return None

        closes = df_daily['close']
        highs = df_daily['high']
        lows = df_daily['low']
        volumes = df_daily['volume']

        curr_price = float(closes.iloc[-1])
        prev_close = float(closes.iloc[-2]) if len(closes) > 1 else curr_price
        prev_high = float(highs.iloc[-2]) if len(highs) > 1 else float(highs.iloc[-1])
        prev_low = float(lows.iloc[-2]) if len(lows) > 1 else float(lows.iloc[-1])

        # Technical Indicators
        ema9_val = float(ema(closes, 9).iloc[-1])
        ema21_val = float(ema(closes, 21).iloc[-1])
        ema50_val = float(ema(closes, 50).iloc[-1]) if len(closes) >= 50 else ema21_val
        rsi_val = float(rsi(closes, 14).iloc[-1])
        atr_val = float(atr(df_daily, 14).iloc[-1])
        vol_avg = float(volumes.iloc[-20:].mean()) if len(volumes) >= 20 else float(volumes.mean())
        rel_vol = float(volumes.iloc[-1] / max(1.0, vol_avg))

        # CPR Analysis
        cpr = PivotEngine.calculate_daily_cpr(prev_high, prev_low, prev_close)
        is_narrow_cpr = cpr.cpr_type == 'NARROW'

        # RRG Quadrant
        quadrant_str = rrg_pt.quadrant.value if rrg_pt else 'IMPROVING'
        rs_ratio = rrg_pt.rs_ratio if rrg_pt else 100.0

        # Simulated Derivatives OI Buildup
        chain = self.options_provider.get_options_chain(symbol, curr_price, atm_iv=15.0)
        pcr = chain.pcr_oi

        # -------------------------------------------------------------
        # SETUP 1: SWING LONG (Momentum + Leadership + Bullish Alignment)
        # -------------------------------------------------------------
        if curr_price > ema21_val and ema9_val > ema21_val and rsi_val > 54.0 and quadrant_str in ('LEADING', 'IMPROVING'):
            confidence = 65.0
            if curr_price > ema50_val: confidence += 10.0
            if quadrant_str == 'LEADING': confidence += 10.0
            if 60.0 < rsi_val < 72.0: confidence += 5.0
            if rel_vol > 1.2: confidence += 5.0
            if pcr > 1.10: confidence += 5.0

            sl = round(min(curr_price - (1.5 * atr_val), cpr.bc), 2)
            risk = max(1.0, curr_price - sl)
            t1 = round(curr_price + (2.0 * risk), 2)
            t2 = round(curr_price + (3.0 * risk), 2)

            return ScreenerCandidate(
                symbol=symbol,
                trading_type=TradingType.SWING_LONG,
                matched_strategy='RRG Leadership + EMA Trend Alignment',
                confidence_score=min(95.0, confidence),
                current_price=curr_price,
                entry_trigger=round(curr_price, 2),
                stop_loss=sl,
                target_1=t1,
                target_2=t2,
                risk_reward_ratio='1:2.0 (Target 1) | 1:3.0 (Target 2)',
                rrg_quadrant=f'🟢 {quadrant_str}',
                oi_buildup='Long Buildup (PCR > 1.1)' if pcr > 1.0 else 'Neutral',
                catalyst_reason=f'Trading in {quadrant_str} quadrant with 9/21 EMA Golden Cross (RSI: {rsi_val:.1f}, RelVol: {rel_vol:.1f}x)'
            )

        # -------------------------------------------------------------
        # SETUP 2: SWING SHORT (Breakdown + Underperformance + Bearish Trend)
        # -------------------------------------------------------------
        if curr_price < ema21_val and ema9_val < ema21_val and rsi_val < 46.0 and quadrant_str in ('LAGGING', 'WEAKENING'):
            confidence = 65.0
            if curr_price < ema50_val: confidence += 10.0
            if quadrant_str == 'LAGGING': confidence += 10.0
            if 25.0 < rsi_val < 40.0: confidence += 5.0
            if rel_vol > 1.2: confidence += 5.0
            if pcr < 0.85: confidence += 5.0

            sl = round(max(curr_price + (1.5 * atr_val), cpr.tc), 2)
            risk = max(1.0, sl - curr_price)
            t1 = round(curr_price - (2.0 * risk), 2)
            t2 = round(curr_price - (3.0 * risk), 2)

            return ScreenerCandidate(
                symbol=symbol,
                trading_type=TradingType.SWING_SHORT,
                matched_strategy='RRG Laggard Breakdown + Death Cross',
                confidence_score=min(95.0, confidence),
                current_price=curr_price,
                entry_trigger=round(curr_price, 2),
                stop_loss=sl,
                target_1=t1,
                target_2=t2,
                risk_reward_ratio='1:2.0 (Target 1) | 1:3.0 (Target 2)',
                rrg_quadrant=f'🔴 {quadrant_str}',
                oi_buildup='Short Buildup (Call Heavy)' if pcr < 0.9 else 'Unwinding',
                catalyst_reason=f'Underperforming in {quadrant_str} quadrant with 9/21 EMA Death Cross (RSI: {rsi_val:.1f}, RelVol: {rel_vol:.1f}x)'
            )

        # -------------------------------------------------------------
        # SETUP 3: INTRADAY LONG / SHORT (Narrow CPR Breakout / High ATR)
        # -------------------------------------------------------------
        if is_narrow_cpr or rel_vol >= 1.5 or (rsi_val > 58.0 and curr_price > prev_high):
            is_bullish = curr_price >= prev_close
            t_type = TradingType.INTRADAY_LONG if is_bullish else TradingType.INTRADAY_SHORT
            confidence = 70.0 + (10.0 if is_narrow_cpr else 0.0) + (5.0 if rel_vol > 1.8 else 0.0)

            if is_bullish:
                sl = round(curr_price - (1.0 * atr_val), 2)
                risk = max(0.5, curr_price - sl)
                t1 = round(curr_price + (2.0 * risk), 2)
                t2 = round(curr_price + (3.0 * risk), 2)
                reason = f'Narrow CPR ({cpr.cpr_width_pct:.2f}%) high-momentum breakout with {rel_vol:.1f}x volume spike'
            else:
                sl = round(curr_price + (1.0 * atr_val), 2)
                risk = max(0.5, sl - curr_price)
                t1 = round(curr_price - (2.0 * risk), 2)
                t2 = round(curr_price - (3.0 * risk), 2)
                reason = f'Narrow CPR breakdown below session low with high ATR volatility expansion'

            return ScreenerCandidate(
                symbol=symbol,
                trading_type=t_type,
                matched_strategy='Opening Range / Narrow CPR Breakout (15m)',
                confidence_score=min(92.0, confidence),
                current_price=curr_price,
                entry_trigger=round(curr_price, 2),
                stop_loss=sl,
                target_1=t1,
                target_2=t2,
                risk_reward_ratio='1:2.0 (Target 1) | 1:3.0 (Target 2)',
                rrg_quadrant=f'{quadrant_str}',
                oi_buildup='High Volume Breakout',
                catalyst_reason=reason
            )

        return None
