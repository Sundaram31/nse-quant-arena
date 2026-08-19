"""Metrics cards, trade logs, and tax summary tables."""
import streamlit as st
import pandas as pd
from typing import List, Dict, Any
from nse_system.core.models import StrategyPerformance, RegimeState, Trade

def render_kpi_cards(perf: StrategyPerformance):
    """Displays key quantitative performance metrics."""
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric('Net PnL', f'₹{perf.net_pnl:,.2f}', f'{perf.roi_pct:+.2f}%')
    with col2:
        st.metric('Win Rate', f'{perf.win_rate:.1f}%', f'{perf.winning_trades}W / {perf.losing_trades}L')
    with col3:
        st.metric('Profit Factor', f'{perf.profit_factor:.2f}')
    with col4:
        st.metric('Sharpe Ratio', f'{perf.sharpe_ratio:.2f}')
    with col5:
        st.metric('Max Drawdown', f'{perf.max_drawdown_pct:.2f}%')

def render_regime_banner(regime: RegimeState):
    """Renders current market regime alert banner."""
    color_map = {
        'BULL_TRENDING': 'green',
        'BEAR_TRENDING': 'red',
        'SIDEWAYS_LOW_VOL': 'blue',
        'SIDEWAYS_HIGH_VOL': 'orange',
        'VOLATILE_EXPANSION': 'violet'
    }
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info(f"**Market Regime**\n\n### {regime.regime_type.value}")
    with col2:
        st.info(f"**India VIX & Regime**\n\n### {regime.vix_level:.2f} ({regime.vix_regime})")
    with col3:
        st.info(f"**FII Bias**\n\n### {regime.fii_sentiment}")
    with col4:
        st.info(f"**Options PCR**\n\n### {regime.pcr_level:.2f} ({regime.pcr_sentiment})")

    st.success(f"💡 **Regime Insight**: {regime.summary}")

def render_trade_log_table(trades: List[Trade]):
    """Displays interactive table of completed trades."""
    if not trades:
        st.write('No trades generated in this period.')
        return

    records = []
    for t in trades:
        records.append({
            'Trade ID': t.trade_id,
            'Symbol': t.symbol,
            'Side': t.side.value,
            'Qty': t.quantity,
            'Entry Price': f'₹{t.entry_price:.2f}',
            'Exit Price': f'₹{t.exit_price:.2f}',
            'Entry Time': t.entry_time.strftime('%Y-%m-%d %H:%M'),
            'Exit Time': t.exit_time.strftime('%Y-%m-%d %H:%M'),
            'Gross PnL': f'₹{t.gross_pnl:+,.2f}',
            'Taxes & Charges': f'₹{t.taxes:,.2f}',
            'Net Realized PnL': f'₹{t.net_pnl:+,.2f}',
            'Exit Reason': t.exit_reason
        })

    df = pd.DataFrame(records)
    st.dataframe(df, use_container_width=True)
