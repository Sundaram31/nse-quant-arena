"""Interactive Visualization Components using Altair and Streamlit."""
from typing import Dict, List, Any
import pandas as pd
import numpy as np
import altair as alt
import streamlit as st

from nse_system.analytics.rrg import RRGPoint
from nse_system.core.models import OptionsChainData, Trade

def plot_rrg_chart(rrg_data: Dict[str, RRGPoint]) -> alt.Chart:
    """Generates Julius de Kempenaer (JdK) 4-Quadrant Relative Rotation Graph."""
    records = []
    for sym, pt in rrg_data.items():
        records.append({
            'Symbol': pt.name,
            'RS_Ratio': pt.rs_ratio,
            'RS_Momentum': pt.rs_momentum,
            'Quadrant': pt.quadrant.value,
            'Distance': pt.distance_from_center
        })

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

def plot_options_oi(chain: OptionsChainData) -> alt.Chart:
    """Generates strike-wise Call vs Put Open Interest bar chart."""
    records = []
    for c in chain.contracts:
        records.append({
            'Strike': str(int(c.strike)),
            'Strike_Num': c.strike,
            'Option_Type': 'Call OI (Resistance)' if c.option_type.value == 'CE' else 'Put OI (Support)',
            'Open_Interest': c.oi
        })

    df = pd.DataFrame(records)
    # Filter 10 strikes around ATM
    atm = chain.atm_strike
    df = df[(df['Strike_Num'] >= atm - 300) & (df['Strike_Num'] <= atm + 300)]

    chart = alt.Chart(df).mark_bar().encode(
        x=alt.X('Strike:O', sort=alt.SortField('Strike_Num', order='ascending'), title='Strike Price'),
        y=alt.Y('Open_Interest:Q', title='Open Interest (Contracts)'),
        color=alt.Color('Option_Type:N', scale=alt.Scale(
            domain=['Call OI (Resistance)', 'Put OI (Support)'],
            range=['#EF4444', '#10B981']
        )),
        xOffset='Option_Type:N',
        tooltip=['Strike', 'Option_Type', 'Open_Interest']
    ).properties(
        width=700,
        height=350,
        title=f'{chain.underlying} Open Interest Distribution | PCR: {chain.pcr_oi:.2f} | Max Pain: {chain.max_pain}'
    )
    return chart

def plot_equity_curve(equity_history: List[Dict[str, Any]]) -> alt.Chart:
    """Plots portfolio equity growth over time."""
    if not equity_history:
        return alt.Chart(pd.DataFrame({'x': [], 'y': []})).mark_line()

    df = pd.DataFrame(equity_history)
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
        tooltip=['timestamp:T', 'equity:Q', 'close:Q']
    ).properties(
        width=700,
        height=320,
        title='Portfolio Net Equity Curve (After All Indian Taxes & Brokerage)'
    )
    return chart
