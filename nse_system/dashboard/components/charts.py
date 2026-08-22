"""Interactive Visualization Components using Altair and Streamlit."""
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import altair as alt
import streamlit as st

from nse_system.analytics.rrg import RRGPoint
from nse_system.core.models import OptionsChainData, Trade

def plot_rrg_chart(rrg_data: Optional[Dict[str, RRGPoint]]) -> Optional[alt.Chart]:
    """Generates Julius de Kempenaer (JdK) 4-Quadrant Relative Rotation Graph."""
    if not rrg_data:
        empty_df = pd.DataFrame({'x': [100.0], 'y': [100.0], 'Message': ['RRG calculation requires active price data for benchmark and symbols']})
        return alt.Chart(empty_df).mark_text(size=14, color='#64748B').encode(
            x=alt.X('x:Q', scale=alt.Scale(domain=[90, 110])),
            y=alt.Y('y:Q', scale=alt.Scale(domain=[90, 110])),
            text='Message:N'
        ).properties(
            width=700,
            height=450,
            title='Relative Rotation Graph (RRG) - Awaiting Data'
        )

    records = []
    for sym, pt in rrg_data.items():
        if pt is not None and hasattr(pt, 'rs_ratio') and hasattr(pt, 'rs_momentum'):
            records.append({
                'Symbol': str(pt.name),
                'RS_Ratio': float(pt.rs_ratio),
                'RS_Momentum': float(pt.rs_momentum),
                'Quadrant': str(pt.quadrant.value) if hasattr(pt.quadrant, 'value') else str(pt.quadrant),
                'Distance': float(pt.distance_from_center)
            })

    if not records:
        empty_df = pd.DataFrame({'x': [100.0], 'y': [100.0], 'Message': ['RRG calculation requires active price data for benchmark and symbols']})
        return alt.Chart(empty_df).mark_text(size=14, color='#64748B').encode(
            x=alt.X('x:Q', scale=alt.Scale(domain=[90, 110])),
            y=alt.Y('y:Q', scale=alt.Scale(domain=[90, 110])),
            text='Message:N'
        ).properties(
            width=700,
            height=450,
            title='Relative Rotation Graph (RRG) - Awaiting Data'
        )

    df = pd.DataFrame(records)

    # Dynamic zoom domain centered on 100
    r_min = min(float(df['RS_Ratio'].min()), float(df['RS_Momentum'].min()), 98.0) - 1.5
    r_max = max(float(df['RS_Ratio'].max()), float(df['RS_Momentum'].max()), 102.0) + 1.5

    scatter = alt.Chart(df).mark_circle(size=300).encode(
        x=alt.X('RS_Ratio:Q', scale=alt.Scale(domain=[r_min, r_max], zero=False), title='JdK RS-Ratio (Relative Strength vs Benchmark)'),
        y=alt.Y('RS_Momentum:Q', scale=alt.Scale(domain=[r_min, r_max], zero=False), title='JdK RS-Momentum (Momentum RoC)'),
        color=alt.Color('Quadrant:N', scale=alt.Scale(
            domain=['LEADING', 'WEAKENING', 'LAGGING', 'IMPROVING'],
            range=['#10B981', '#F59E0B', '#EF4444', '#3B82F6']
        )),
        tooltip=['Symbol', 'Quadrant', alt.Tooltip('RS_Ratio:Q', format='.2f'), alt.Tooltip('RS_Momentum:Q', format='.2f')]
    )

    text = scatter.mark_text(align='left', baseline='middle', dx=12, fontSize=11, fontWeight='bold').encode(
        text='Symbol:N'
    )

    # Reference lines at (100, 100)
    rule_x = alt.Chart(pd.DataFrame({'x': [100.0]})).mark_rule(strokeDash=[4, 4], color='#94A3B8', size=1.5).encode(x='x:Q')
    rule_y = alt.Chart(pd.DataFrame({'y': [100.0]})).mark_rule(strokeDash=[4, 4], color='#94A3B8', size=1.5).encode(y='y:Q')

    chart = (rule_x + rule_y + scatter + text).properties(
        width=700,
        height=450,
        title='Relative Rotation Graph (RRG) - Momentum & Strength Quadrants'
    ).interactive()
    return chart

def plot_options_oi(chain: Optional[OptionsChainData]) -> alt.Chart:
    """Generates strike-wise Call vs Put Open Interest bar chart."""
    if not chain or not chain.contracts:
        empty_df = pd.DataFrame({'x': [0], 'y': [0], 'Message': ['No options chain data available']})
        return alt.Chart(empty_df).mark_text(size=14, color='#64748B').encode(text='Message:N').properties(
            width=700, height=350, title='Options Open Interest - Awaiting Data'
        )

    records = []
    for c in chain.contracts:
        records.append({
            'Strike': str(int(c.strike)),
            'Strike_Num': float(c.strike),
            'Option_Type': 'Call OI (Resistance)' if getattr(c.option_type, 'value', str(c.option_type)) == 'CE' else 'Put OI (Support)',
            'Open_Interest': float(c.oi)
        })

    df = pd.DataFrame(records)
    if df.empty:
        empty_df = pd.DataFrame({'x': [0], 'y': [0], 'Message': ['No options chain contracts available']})
        return alt.Chart(empty_df).mark_text(size=14, color='#64748B').encode(text='Message:N').properties(width=700, height=350)

    # Dynamic 16 strikes closest to ATM (works for any index or stock price)
    atm = float(chain.atm_strike)
    df['dist'] = (df['Strike_Num'] - atm).abs()
    df = df.sort_values('dist').head(24).sort_values('Strike_Num').drop(columns=['dist'])

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Strike:O', sort=alt.SortField('Strike_Num', order='ascending'), title='Strike Price'),
        y=alt.Y('Open_Interest:Q', title='Open Interest (Contracts)'),
        color=alt.Color('Option_Type:N', scale=alt.Scale(
            domain=['Call OI (Resistance)', 'Put OI (Support)'],
            range=['#EF4444', '#10B981']
        )),
        xOffset='Option_Type:N',
        tooltip=['Strike', 'Option_Type', alt.Tooltip('Open_Interest:Q', format=',.0f')]
    ).properties(
        width=700,
        height=350,
        title=f'{chain.underlying} Open Interest Distribution | PCR: {chain.pcr_oi:.2f} | Max Pain: ₹{chain.max_pain:,.0f}'
    )
    return chart

def plot_equity_curve(equity_history: List[Dict[str, Any]]) -> alt.Chart:
    """Plots portfolio equity growth over time."""
    if not equity_history:
        empty_df = pd.DataFrame({'x': [0], 'y': [0], 'Message': ['No equity curve history generated yet']})
        return alt.Chart(empty_df).mark_text(size=14, color='#64748B').encode(text='Message:N').properties(
            width=700, height=320, title='Portfolio Net Equity Curve'
        )

    df = pd.DataFrame(equity_history)
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    chart = alt.Chart(df).mark_area(
        line={'color': '#10B981', 'width': 2},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='#10B981', offset=0),
                   alt.GradientStop(color='rgba(16, 185, 129, 0.05)', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X('timestamp:T', title='Date & Time'),
        y=alt.Y('equity:Q', title='Portfolio Equity (INR)', scale=alt.Scale(zero=False)),
        tooltip=['timestamp:T', alt.Tooltip('equity:Q', format=',.2f')]
    ).properties(
        width=700,
        height=320,
        title='Portfolio Net Equity Curve (After All Indian Taxes & Brokerage)'
    )
    return chart

def plot_stock_strategy_chart(
    df: pd.DataFrame,
    symbol: str,
    entry_trigger: Optional[float] = None,
    stop_loss: Optional[float] = None,
    target_1: Optional[float] = None,
    target_2: Optional[float] = None,
    cpr: Optional[Any] = None,
    strategy_name: Optional[str] = None,
    num_bars: int = 60
) -> alt.Chart:
    """Plots interactive Candlestick chart overlaid with 9/21/50 EMAs, CPR Pivots, and Trade Blueprint Execution levels."""
    if df.empty or len(df) < 5:
        empty_df = pd.DataFrame({'x': [100.0], 'y': [100.0], 'Message': [f'Insufficient historical candle data for {symbol}']})
        return alt.Chart(empty_df).mark_text(size=14, color='#64748B').encode(text='Message:N').properties(width=750, height=420)

    plot_df = df.tail(num_bars).copy()
    plot_df.columns = [str(c).lower() for c in plot_df.columns]
    if 'timestamp' not in plot_df.columns:
        if 'date' in plot_df.columns:
            plot_df['timestamp'] = plot_df['date']
        else:
            plot_df['timestamp'] = plot_df.index
    plot_df['timestamp'] = pd.to_datetime(plot_df['timestamp'])
    if 'volume' not in plot_df.columns:
        plot_df['volume'] = 0.0

    # Calculate Key Indicators
    plot_df['ema9'] = plot_df['close'].ewm(span=9, adjust=False).mean()
    plot_df['ema21'] = plot_df['close'].ewm(span=21, adjust=False).mean()
    plot_df['ema50'] = plot_df['close'].ewm(span=50, adjust=False).mean()

    # Price range for scaling
    min_p = float(plot_df['low'].min()) * 0.98
    max_p = float(plot_df['high'].max()) * 1.02
    if stop_loss and stop_loss > 0:
        min_p = min(min_p, stop_loss * 0.98)
    if target_2 and target_2 > 0:
        max_p = max(max_p, target_2 * 1.02)

    # 1. Candlestick wicks (Rule)
    rule = alt.Chart(plot_df).mark_rule().encode(
        x=alt.X('timestamp:T', title='Date', axis=alt.Axis(format='%d-%b', labelAngle=-45)),
        y=alt.Y('low:Q', scale=alt.Scale(domain=[min_p, max_p], zero=False), title='Price (INR)'),
        y2='high:Q',
        color=alt.condition('datum.open <= datum.close', alt.value('#10B981'), alt.value('#EF4444')),
        tooltip=[
            alt.Tooltip('timestamp:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('open:Q', title='Open', format=',.2f'),
            alt.Tooltip('high:Q', title='High', format=',.2f'),
            alt.Tooltip('low:Q', title='Low', format=',.2f'),
            alt.Tooltip('close:Q', title='Close', format=',.2f'),
            alt.Tooltip('volume:Q', title='Volume', format=',.0f')
        ]
    )

    # 2. Candlestick bodies (Bar)
    bar = alt.Chart(plot_df).mark_bar(size=7).encode(
        x='timestamp:T',
        y='open:Q',
        y2='close:Q',
        color=alt.condition('datum.open <= datum.close', alt.value('#10B981'), alt.value('#EF4444')),
        tooltip=[
            alt.Tooltip('timestamp:T', title='Date', format='%Y-%m-%d'),
            alt.Tooltip('open:Q', title='Open', format=',.2f'),
            alt.Tooltip('high:Q', title='High', format=',.2f'),
            alt.Tooltip('low:Q', title='Low', format=',.2f'),
            alt.Tooltip('close:Q', title='Close', format=',.2f'),
            alt.Tooltip('volume:Q', title='Volume', format=',.0f')
        ]
    )

    layers = [rule, bar]

    # 3. Overlays: EMAs
    ema9 = alt.Chart(plot_df).mark_line(color='#F59E0B', strokeWidth=1.5).encode(x='timestamp:T', y='ema9:Q')
    ema21 = alt.Chart(plot_df).mark_line(color='#3B82F6', strokeWidth=1.5).encode(x='timestamp:T', y='ema21:Q')
    ema50 = alt.Chart(plot_df).mark_line(color='#8B5CF6', strokeWidth=1.5).encode(x='timestamp:T', y='ema50:Q')
    layers.extend([ema9, ema21, ema50])

    # 4. CPR Overlay (if present)
    if cpr and hasattr(cpr, 'pivot') and cpr.pivot > 0:
        cpr_data = pd.DataFrame({
            'y': [float(cpr.tc), float(cpr.pivot), float(cpr.bc)]
        })
        cpr_rule = alt.Chart(cpr_data).mark_rule(strokeDash=[4, 4], color='#64748B', strokeWidth=1.2).encode(y='y:Q')
        layers.append(cpr_rule)

    # 5. Blueprint Levels (Entry, SL, Target 1, Target 2)
    levels_records = []
    if entry_trigger and entry_trigger > 0:
        levels_records.append({'y': float(entry_trigger), 'color': '#2563EB'})
    if stop_loss and stop_loss > 0:
        levels_records.append({'y': float(stop_loss), 'color': '#DC2626'})
    if target_1 and target_1 > 0:
        levels_records.append({'y': float(target_1), 'color': '#16A34A'})
    if target_2 and target_2 > 0:
        levels_records.append({'y': float(target_2), 'color': '#047857'})

    for lvl in levels_records:
        r_chart = alt.Chart(pd.DataFrame({'y': [lvl['y']]})).mark_rule(
            strokeDash=[6, 3],
            color=lvl['color'],
            strokeWidth=2.0
        ).encode(y='y:Q')
        layers.append(r_chart)

    title_text = f"{symbol} • Daily Candlesticks + EMAs (9/21/50) + CPR + Setup Levels"
    if strategy_name:
        title_text += f" [{strategy_name}]"

    combined = alt.layer(*layers).properties(
        width=750,
        height=440,
        title=title_text
    )
    return combined.interactive()
