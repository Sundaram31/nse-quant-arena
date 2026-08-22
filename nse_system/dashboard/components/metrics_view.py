"""Metrics cards, trade logs, and tax summary tables."""
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional
from nse_system.core.models import StrategyPerformance, RegimeState, Trade

def render_kpi_cards(perf: Optional[StrategyPerformance]):
    """Displays key quantitative performance metrics."""
    if not perf:
        st.info('No quantitative performance metrics available.')
        return

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

def render_regime_banner(regime: Optional[RegimeState]):
    """Renders current market regime alert banner."""
    if not regime:
        st.info('No market regime snapshot available.')
        return

    regime_name = getattr(regime.regime_type, 'value', str(regime.regime_type))
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info(f"**Market Regime**\n\n### {regime_name}")
    with col2:
        st.info(f"**India VIX & Regime**\n\n### {regime.vix_level:.2f} ({regime.vix_regime})")
    with col3:
        st.info(f"**FII Bias**\n\n### {regime.fii_sentiment}")
    with col4:
        st.info(f"**Options PCR**\n\n### {regime.pcr_level:.2f} ({regime.pcr_sentiment})")

    st.success(f"💡 **Regime Insight**: {regime.summary}")

def render_trade_log_table(trades: Optional[List[Trade]]):
    """Displays interactive table of completed trades."""
    if not trades:
        st.write('No trades generated in this period.')
        return

    records = []
    for t in trades:
        side_str = getattr(t.side, 'value', str(t.side))
        entry_str = t.entry_time.strftime('%Y-%m-%d %H:%M') if hasattr(t.entry_time, 'strftime') else str(t.entry_time)
        exit_str = t.exit_time.strftime('%Y-%m-%d %H:%M') if hasattr(t.exit_time, 'strftime') else str(t.exit_time)
        records.append({
            'Trade ID': t.trade_id,
            'Symbol': t.symbol,
            'Side': side_str,
            'Qty': t.quantity,
            'Entry Price': f'₹{t.entry_price:.2f}',
            'Exit Price': f'₹{t.exit_price:.2f}',
            'Entry Time': entry_str,
            'Exit Time': exit_str,
            'Gross PnL': f'₹{t.gross_pnl:+,.2f}',
            'Taxes & Charges': f'₹{t.taxes:,.2f}',
            'Net Realized PnL': f'₹{t.net_pnl:+,.2f}',
            'Exit Reason': t.exit_reason
        })

    df = pd.DataFrame(records)
    st.dataframe(df, use_container_width=True)

