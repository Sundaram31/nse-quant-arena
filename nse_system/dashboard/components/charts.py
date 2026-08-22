"""Interactive Visualization Components using Plotly with Dark/Light Theme Support & Mobile Zoom/Pan."""
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from nse_system.analytics.rrg import RRGPoint
from nse_system.core.models import OptionsChainData, Trade


def _get_theme_colors(theme: str = "dark") -> Dict[str, str]:
    """Returns color palette for chart components based on selected theme."""
    is_dark = str(theme).lower() == "dark"
    if is_dark:
        return {
            "bg": "#0B0F19",
            "paper_bg": "#0F172A",
            "grid": "#1E293B",
            "text": "#E2E8F0",
            "subtext": "#94A3B8",
            "up_color": "#10B981",
            "down_color": "#EF4444",
            "ema9": "#F59E0B",
            "ema21": "#3B82F6",
            "ema50": "#A855F7",
            "entry_color": "#38BDF8",
            "sl_color": "#F87171",
            "target1_color": "#34D399",
            "target2_color": "#10B981",
            "cpr_color": "rgba(148, 163, 184, 0.6)",
            "call_bar": "#F87171",
            "put_bar": "#34D399",
            "border": "#334155"
        }
    else:
        return {
            "bg": "#FFFFFF",
            "paper_bg": "#F8FAFC",
            "grid": "#E2E8F0",
            "text": "#0F172A",
            "subtext": "#64748B",
            "up_color": "#059669",
            "down_color": "#DC2626",
            "ema9": "#D97706",
            "ema21": "#2563EB",
            "ema50": "#7C3AED",
            "entry_color": "#0284C7",
            "sl_color": "#DC2626",
            "target1_color": "#16A34A",
            "target2_color": "#059669",
            "cpr_color": "rgba(100, 116, 139, 0.5)",
            "call_bar": "#EF4444",
            "put_bar": "#10B981",
            "border": "#CBD5E1"
        }


def plot_stock_strategy_chart(
    df: pd.DataFrame,
    symbol: str,
    entry_trigger: Optional[float] = None,
    stop_loss: Optional[float] = None,
    target_1: Optional[float] = None,
    target_2: Optional[float] = None,
    cpr: Optional[Any] = None,
    strategy_name: Optional[str] = None,
    num_bars: int = 75,
    theme: str = "dark"
) -> go.Figure:
    """Generates an interactive Plotly Candlestick + Volume + EMAs + CPR + Blueprint Levels chart.
    Features: Pinch-to-zoom, touch panning, range slider, 1-click timeframe selectors, and Dark/Light styling.
    """
    c = _get_theme_colors(theme)

    if df.empty or len(df) < 5:
        fig = go.Figure()
        fig.add_annotation(
            text=f"Insufficient historical candle data for {symbol}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=c["subtext"])
        )
        fig.update_layout(
            template="plotly_dark" if theme == "dark" else "plotly_white",
            paper_bgcolor=c["paper_bg"],
            plot_bgcolor=c["bg"],
            height=400
        )
        return fig

    plot_df = df.tail(num_bars).copy()
    plot_df.columns = [str(col).lower() for col in plot_df.columns]
    
    if "timestamp" not in plot_df.columns:
        if "date" in plot_df.columns:
            plot_df["timestamp"] = plot_df["date"]
        else:
            plot_df["timestamp"] = plot_df.index
    plot_df["timestamp"] = pd.to_datetime(plot_df["timestamp"])
    
    if "volume" not in plot_df.columns:
        plot_df["volume"] = 0.0

    # Indicators
    plot_df["ema9"] = plot_df["close"].ewm(span=9, adjust=False).mean()
    plot_df["ema21"] = plot_df["close"].ewm(span=21, adjust=False).mean()
    plot_df["ema50"] = plot_df["close"].ewm(span=50, adjust=False).mean()

    # Create 2-row Subplot: Row 1 = Price + Indicators (75%), Row 2 = Volume (25%)
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.75, 0.25]
    )

    # 1. Candlestick Trace
    fig.add_trace(
        go.Candlestick(
            x=plot_df["timestamp"],
            open=plot_df["open"],
            high=plot_df["high"],
            low=plot_df["low"],
            close=plot_df["close"],
            name="Price",
            increasing_line_color=c["up_color"],
            decreasing_line_color=c["down_color"],
            increasing_fillcolor=c["up_color"],
            decreasing_fillcolor=c["down_color"],
            line=dict(width=1)
        ),
        row=1, col=1
    )

    # 2. Moving Average Lines
    fig.add_trace(go.Scatter(x=plot_df["timestamp"], y=plot_df["ema9"], mode="lines", name="EMA 9", line=dict(color=c["ema9"], width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=plot_df["timestamp"], y=plot_df["ema21"], mode="lines", name="EMA 21", line=dict(color=c["ema21"], width=1.5)), row=1, col=1)
    fig.add_trace(go.Scatter(x=plot_df["timestamp"], y=plot_df["ema50"], mode="lines", name="EMA 50", line=dict(color=c["ema50"], width=1.5)), row=1, col=1)

    # 3. Daily CPR Levels (Dashed Horizontal Bands)
    if cpr and hasattr(cpr, "pivot") and cpr.pivot > 0:
        fig.add_hline(y=float(cpr.tc), line_dash="dash", line_color=c["cpr_color"], line_width=1.2, annotation_text="CPR TC", annotation_position="top left", row=1, col=1)
        fig.add_hline(y=float(cpr.pivot), line_dash="dot", line_color=c["cpr_color"], line_width=1.5, annotation_text="CPR Pivot", annotation_position="top left", row=1, col=1)
        fig.add_hline(y=float(cpr.bc), line_dash="dash", line_color=c["cpr_color"], line_width=1.2, annotation_text="CPR BC", annotation_position="bottom left", row=1, col=1)

    # 4. Blueprint Execution Levels (Entry, Stop Loss, Target 1, Target 2)
    if entry_trigger and entry_trigger > 0:
        fig.add_hline(y=float(entry_trigger), line_dash="dashdot", line_color=c["entry_color"], line_width=2.0, annotation_text=f"🎯 Entry ₹{entry_trigger:,.2f}", annotation_position="right", row=1, col=1)
    if stop_loss and stop_loss > 0:
        fig.add_hline(y=float(stop_loss), line_dash="solid", line_color=c["sl_color"], line_width=2.0, annotation_text=f"🛑 SL ₹{stop_loss:,.2f}", annotation_position="right", row=1, col=1)
    if target_1 and target_1 > 0:
        fig.add_hline(y=float(target_1), line_dash="dash", line_color=c["target1_color"], line_width=1.8, annotation_text=f"🏁 T1 (1:2) ₹{target_1:,.2f}", annotation_position="right", row=1, col=1)
    if target_2 and target_2 > 0:
        fig.add_hline(y=float(target_2), line_dash="dash", line_color=c["target2_color"], line_width=1.8, annotation_text=f"🚀 T2 (1:3) ₹{target_2:,.2f}", annotation_position="right", row=1, col=1)

    # 5. Volume Bar Chart
    vol_colors = [c["up_color"] if row["close"] >= row["open"] else c["down_color"] for _, row in plot_df.iterrows()]
    fig.add_trace(
        go.Bar(
            x=plot_df["timestamp"],
            y=plot_df["volume"],
            name="Volume",
            marker_color=vol_colors,
            opacity=0.75
        ),
        row=2, col=1
    )

    # Title & Formatting
    title_text = f"<b>{symbol}</b> • Daily Candlesticks + EMAs (9/21/50) + CPR"
    if strategy_name:
        title_text += f" <span style='font-size:12px; color:{c['subtext']};'>[{strategy_name}]</span>"

    fig.update_layout(
        title=dict(text=title_text, font=dict(size=14, color=c["text"])),
        template="plotly_dark" if theme == "dark" else "plotly_white",
        paper_bgcolor=c["paper_bg"],
        plot_bgcolor=c["bg"],
        font=dict(color=c["text"], family="Inter, system-ui, -apple-system"),
        height=480,
        margin=dict(l=10, r=60, t=40, b=10),
        xaxis_rangeslider_visible=False,
        showlegend=False,
        hovermode="x unified"
    )

    fig.update_xaxes(
        gridcolor=c["grid"],
        showgrid=True,
        zeroline=False,
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(step="all", label="ALL")
            ]),
            bgcolor=c["paper_bg"],
            activecolor=c["entry_color"],
            font=dict(size=11, color=c["text"]),
            x=0.0, y=1.12
        ),
        row=1, col=1
    )

    fig.update_xaxes(gridcolor=c["grid"], showgrid=True, zeroline=False, row=2, col=1)
    fig.update_yaxes(title="Price (INR)", gridcolor=c["grid"], showgrid=True, zeroline=False, row=1, col=1)
    fig.update_yaxes(title="Vol", gridcolor=c["grid"], showgrid=False, zeroline=False, row=2, col=1)

    return fig


def plot_rrg_chart(rrg_data: Optional[Dict[str, RRGPoint]], theme: str = "dark") -> go.Figure:
    """Generates an interactive Plotly 4-Quadrant Relative Rotation Graph with quadrant shading & touch zoom."""
    c = _get_theme_colors(theme)

    fig = go.Figure()

    if not rrg_data:
        fig.add_annotation(
            text="RRG calculation requires active price data for benchmark and symbols",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=c["subtext"])
        )
        fig.update_layout(
            template="plotly_dark" if theme == "dark" else "plotly_white",
            paper_bgcolor=c["paper_bg"],
            plot_bgcolor=c["bg"],
            height=420
        )
        return fig

    records = []
    for sym, pt in rrg_data.items():
        if pt is not None and hasattr(pt, "rs_ratio") and hasattr(pt, "rs_momentum"):
            records.append({
                "Symbol": str(pt.name),
                "RS_Ratio": float(pt.rs_ratio),
                "RS_Momentum": float(pt.rs_momentum),
                "Quadrant": str(pt.quadrant.value) if hasattr(pt.quadrant, "value") else str(pt.quadrant)
            })

    if not records:
        return fig

    df = pd.DataFrame(records)
    r_min = min(float(df["RS_Ratio"].min()), float(df["RS_Momentum"].min()), 98.0) - 1.5
    r_max = max(float(df["RS_Ratio"].max()), float(df["RS_Momentum"].max()), 102.0) + 1.5

    quadrant_palette = {
        "LEADING": "#10B981",
        "WEAKENING": "#F59E0B",
        "LAGGING": "#EF4444",
        "IMPROVING": "#3B82F6"
    }

    # Add quadrant points
    for q_name, q_color in quadrant_palette.items():
        q_df = df[df["Quadrant"] == q_name]
        if not q_df.empty:
            fig.add_trace(
                go.Scatter(
                    x=q_df["RS_Ratio"],
                    y=q_df["RS_Momentum"],
                    mode="markers+text",
                    name=q_name,
                    text=q_df["Symbol"],
                    textposition="top right",
                    textfont=dict(size=11, color=c["text"], family="Inter, system-ui"),
                    marker=dict(size=14, color=q_color, line=dict(width=1.5, color=c["paper_bg"])),
                    hovertemplate="<b>%{text}</b><br>RS-Ratio: %{x:.2f}<br>RS-Momentum: %{y:.2f}<br>Quadrant: " + q_name + "<extra></extra>"
                )
            )

    # Reference crosshairs at 100, 100
    fig.add_hline(y=100.0, line_dash="dash", line_color=c["border"], line_width=1.5)
    fig.add_vline(x=100.0, line_dash="dash", line_color=c["border"], line_width=1.5)

    # Quadrant corner labels
    fig.add_annotation(x=r_max - 0.5, y=r_max - 0.5, text="🟢 LEADING", showarrow=False, font=dict(color="#10B981", size=11, family="Inter"))
    fig.add_annotation(x=r_max - 0.5, y=r_min + 0.5, text="🟡 WEAKENING", showarrow=False, font=dict(color="#F59E0B", size=11, family="Inter"))
    fig.add_annotation(x=r_min + 0.5, y=r_min + 0.5, text="🔴 LAGGING", showarrow=False, font=dict(color="#EF4444", size=11, family="Inter"))
    fig.add_annotation(x=r_min + 0.5, y=r_max - 0.5, text="🔵 IMPROVING", showarrow=False, font=dict(color="#3B82F6", size=11, family="Inter"))

    fig.update_layout(
        title=dict(text="<b>Relative Rotation Graph (RRG)</b> • Sector Momentum Quadrants vs NIFTY 50", font=dict(size=14, color=c["text"])),
        template="plotly_dark" if theme == "dark" else "plotly_white",
        paper_bgcolor=c["paper_bg"],
        plot_bgcolor=c["bg"],
        font=dict(color=c["text"], family="Inter, system-ui"),
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(title="JdK RS-Ratio (Relative Strength)", range=[r_min, r_max], gridcolor=c["grid"], zeroline=False),
        yaxis=dict(title="JdK RS-Momentum (Rate of Change)", range=[r_min, r_max], gridcolor=c["grid"], zeroline=False),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def plot_options_oi(chain: Optional[OptionsChainData], theme: str = "dark") -> go.Figure:
    """Generates an interactive Plotly Call vs Put Open Interest bar chart around ATM strikes."""
    c = _get_theme_colors(theme)
    fig = go.Figure()

    if not chain or not chain.contracts:
        fig.add_annotation(
            text="No options chain data available",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=c["subtext"])
        )
        fig.update_layout(
            template="plotly_dark" if theme == "dark" else "plotly_white",
            paper_bgcolor=c["paper_bg"],
            plot_bgcolor=c["bg"],
            height=360
        )
        return fig

    records = []
    for ct in chain.contracts:
        o_type = getattr(ct.option_type, "value", str(ct.option_type))
        records.append({
            "Strike": float(ct.strike),
            "Strike_Str": str(int(ct.strike)),
            "Option_Type": "Call OI (Resistance)" if o_type == "CE" else "Put OI (Support)",
            "OI": float(ct.oi)
        })

    df = pd.DataFrame(records)
    if df.empty:
        return fig

    # Filter 20 strikes closest to ATM
    atm = float(chain.atm_strike)
    df["dist"] = (df["Strike"] - atm).abs()
    closest_strikes = df.sort_values("dist")["Strike"].drop_duplicates().head(16).tolist()
    df_filtered = df[df["Strike"].isin(closest_strikes)].sort_values("Strike")

    call_df = df_filtered[df_filtered["Option_Type"] == "Call OI (Resistance)"]
    put_df = df_filtered[df_filtered["Option_Type"] == "Put OI (Support)"]

    fig.add_trace(
        go.Bar(
            x=[str(int(s)) for s in call_df["Strike"]],
            y=call_df["OI"],
            name="Call OI (Resistance)",
            marker_color=c["call_bar"],
            opacity=0.85
        )
    )
    fig.add_trace(
        go.Bar(
            x=[str(int(s)) for s in put_df["Strike"]],
            y=put_df["OI"],
            name="Put OI (Support)",
            marker_color=c["put_bar"],
            opacity=0.85
        )
    )

    fig.update_layout(
        title=dict(text=f"<b>{chain.underlying}</b> Options Open Interest | PCR: <b>{chain.pcr_oi:.2f}</b> | Max Pain: <b>₹{chain.max_pain:,.0f}</b>", font=dict(size=13, color=c["text"])),
        template="plotly_dark" if theme == "dark" else "plotly_white",
        paper_bgcolor=c["paper_bg"],
        plot_bgcolor=c["bg"],
        font=dict(color=c["text"], family="Inter, system-ui"),
        barmode="group",
        height=380,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(title="Strike Price", gridcolor=c["grid"]),
        yaxis=dict(title="Open Interest (Contracts)", gridcolor=c["grid"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def plot_equity_curve(equity_history: List[Dict[str, Any]], theme: str = "dark") -> go.Figure:
    """Plots interactive portfolio equity curve with drawdown tracking and touch tooltips."""
    c = _get_theme_colors(theme)
    fig = go.Figure()

    if not equity_history:
        fig.add_annotation(
            text="No equity curve history generated yet",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color=c["subtext"])
        )
        fig.update_layout(
            template="plotly_dark" if theme == "dark" else "plotly_white",
            paper_bgcolor=c["paper_bg"],
            plot_bgcolor=c["bg"],
            height=340
        )
        return fig

    df = pd.DataFrame(equity_history)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    fill_color = "rgba(16, 185, 129, 0.15)" if theme == "dark" else "rgba(16, 185, 129, 0.2)"
    fig.add_trace(
        go.Scatter(
            x=df["timestamp"],
            y=df["equity"],
            mode="lines",
            name="Net Portfolio Equity",
            line=dict(color=c["up_color"], width=2.5),
            fill="tozeroy",
            fillcolor=fill_color,
            hovertemplate="Date: %{x|%Y-%m-%d}<br>Net Equity: ₹%{y:,.2f}<extra></extra>"
        )
    )

    fig.update_layout(
        title=dict(text="<b>Portfolio Net Equity Growth</b> (After All Indian Taxes & Brokerage)", font=dict(size=13, color=c["text"])),
        template="plotly_dark" if theme == "dark" else "plotly_white",
        paper_bgcolor=c["paper_bg"],
        plot_bgcolor=c["bg"],
        font=dict(color=c["text"], family="Inter, system-ui"),
        height=340,
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(title="Date & Time", gridcolor=c["grid"]),
        yaxis=dict(title="Portfolio Equity (INR)", gridcolor=c["grid"]),
        hovermode="x unified"
    )
    return fig
