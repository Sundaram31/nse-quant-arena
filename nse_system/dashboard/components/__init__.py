"""Dashboard components module exports."""
from nse_system.dashboard.components.charts import (
    plot_rrg_chart,
    plot_options_oi,
    plot_equity_curve,
    plot_stock_strategy_chart,
    plot_backtest_trades_chart
)
from nse_system.dashboard.components.metrics_view import (
    render_kpi_cards,
    render_regime_banner,
    render_trade_log_table
)

__all__ = [
    'plot_rrg_chart',
    'plot_options_oi',
    'plot_equity_curve',
    'plot_stock_strategy_chart',
    'plot_backtest_trades_chart',
    'render_kpi_cards',
    'render_regime_banner',
    'render_trade_log_table'
]
