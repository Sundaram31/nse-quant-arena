"""Rich Command Line Interface for NSE Quantitative Strategy Platform."""
import argparse
import sys
import os
import subprocess
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from nse_system.data.symbols import NSE_INDICES, NSE_EQUITIES, get_all_sector_indices
from nse_system.data.universe import UniverseManager
from nse_system.data.historical import NSEHistoricalDataProvider
from nse_system.data.historical_collector import HistoricalDataCollector
from nse_system.data.sync_scheduler import DailyDataSynchronizer
from nse_system.data.fii_dii import FIIDIIDataProvider
from nse_system.data.options_data import OptionsDataProvider
from nse_system.analytics.rrg import RRGAnalyzer
from nse_system.analytics.volatility import VolatilityEngine
from nse_system.analytics.screener import QuantStockScreener
from nse_system.engine.arena import StrategyBattleArena
from nse_system.engine.backtest import BacktestEngine
from nse_system.strategies import STRATEGY_REGISTRY, get_strategy, list_available_strategies

console = Console(force_terminal=True)

def run_arena_command(args):
    info_text = f"[bold green]⚔️ Running Strategy Battle Arena for {args.symbol}[/bold green]\nPeriod: {args.days} days | Timeframe: {args.timeframe} | VIX: {args.vix}"
    console.print(Panel(info_text, title="NSE Quant Arena"))
    
    arena = StrategyBattleArena()
    tournament = arena.run_tournament(
        symbol=args.symbol,
        timeframe=args.timeframe,
        days=args.days,
        initial_capital=args.capital,
        vix_level=args.vix
    )

    reg = tournament.regime_state
    console.print(f"[bold cyan]Market Regime:[/] {reg.regime_type.value} | [bold cyan]VIX:[/] {reg.vix_level:.2f} ({reg.vix_regime}) | [bold cyan]FII Bias:[/] {reg.fii_sentiment} | [bold cyan]PCR:[/] {reg.pcr_level:.2f}")
    console.print(f"[italic yellow]{reg.summary}[/italic yellow]\n")

    # Leaderboard Table
    table = Table(title=f"🏆 Strategy Tournament Leaderboard - {args.symbol}", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="bold")
    table.add_column("Strategy")
    table.add_column("Alpha Score", justify="right")
    table.add_column("Win Rate %", justify="right")
    table.add_column("Profit Factor", justify="right")
    table.add_column("Net PnL (INR)", justify="right")
    table.add_column("Sharpe", justify="right")
    table.add_column("Max DD %", justify="right")
    table.add_column("Status", justify="center")

    for rank, p in enumerate(tournament.leaderboard, 1):
        status = "[green]✅ WINNER[/green]" if rank == 1 else ("[cyan]ACTIVE[/cyan]" if p.strategy_name in tournament.recommended_active_strategies else "[red]AVOID[/red]")
        pnl_style = "green" if p.net_pnl >= 0 else "red"
        table.add_row(
            f"#{rank}",
            p.strategy_name,
            f"{p.alpha_score:.1f}",
            f"{p.win_rate:.1f}%",
            f"{p.profit_factor:.2f}",
            f"[{pnl_style}]₹{p.net_pnl:+,.2f}[/{pnl_style}]",
            f"{p.sharpe_ratio:.2f}",
            f"{p.max_drawdown_pct:.2f}%",
            status
        )

    console.print(table)
    console.print(f"\n[bold green]Decision:[/] {tournament.executive_summary}\n")

def run_scan_command(args):
    info_text = f"[bold green]🎯 Scanning Universe: {args.universe.upper()} for High-Probability Setups[/bold green]"
    console.print(Panel(info_text, title="NSE Quant Trade Radar"))
    
    screener = QuantStockScreener()
    candidates = screener.scan_universe(universe_name=args.universe, min_confidence=args.confidence)

    if args.type == "swing_long":
        candidates = [c for c in candidates if c.trading_type.value == "SWING_LONG"]
    elif args.type == "swing_short":
        candidates = [c for c in candidates if c.trading_type.value == "SWING_SHORT"]
    elif args.type == "intraday":
        candidates = [c for c in candidates if "INTRADAY" in c.trading_type.value]

    if not candidates:
        console.print("[yellow]No candidates found matching the criteria.[/yellow]")
        return

    table = Table(title=f"📋 Top Ranked Stock Candidates ({len(candidates)} Found)", show_header=True, header_style="bold green")
    table.add_column("Symbol", style="bold")
    table.add_column("Setup Type", justify="center")
    table.add_column("Conf %", justify="right")
    table.add_column("Trigger (INR)", justify="right")
    table.add_column("SL (INR)", justify="right")
    table.add_column("Target 1 (INR)", justify="right")
    table.add_column("RRG Quadrant", justify="center")
    table.add_column("Reason")

    for c in candidates[:20]:
        badge = "[green]SWING LONG[/green]" if c.trading_type.value == "SWING_LONG" else ("[red]SWING SHORT[/red]" if c.trading_type.value == "SWING_SHORT" else "[yellow]INTRADAY[/yellow]")
        table.add_row(
            c.symbol,
            badge,
            f"{c.confidence_score:.0f}%",
            f"₹{c.entry_trigger:,.2f}",
            f"₹{c.stop_loss:,.2f}",
            f"₹{c.target_1:,.2f}",
            c.rrg_quadrant,
            c.catalyst_reason[:65] + "..." if len(c.catalyst_reason) > 65 else c.catalyst_reason
        )

    console.print(table)

def run_backtest_command(args):
    info_text = f"[bold blue]📊 Running Backtest: {args.strategy} on {args.symbol}[/bold blue]\nPeriod: {args.days} days | Timeframe: {args.timeframe}"
    console.print(Panel(info_text, title="NSE Backtest Engine"))
    
    dp = NSEHistoricalDataProvider()
    candles = dp.get_historical_candles(args.symbol, datetime.now() - timedelta(days=args.days), datetime.now(), args.timeframe)
    
    strat = get_strategy(args.strategy, symbol=args.symbol, timeframe=args.timeframe)
    bt = BacktestEngine(strategy=strat, initial_capital=args.capital)
    perf = bt.run(candles)

    console.print(f"[bold]Total Trades:[/] {perf.total_trades} | [bold]Winning:[/] {perf.winning_trades} | [bold]Losing:[/] {perf.losing_trades}")
    console.print(f"[bold]Win Rate:[/] {perf.win_rate:.1f}% | [bold]Profit Factor:[/] {perf.profit_factor:.2f}")
    console.print(f"[bold]Gross PnL:[/] ₹{perf.gross_pnl:+,.2f} | [bold]Taxes & Charges:[/] ₹{perf.total_taxes:,.2f} | [bold green]Net Realized PnL:[/] [bold]₹{perf.net_pnl:+,.2f}[/]")
    console.print(f"[bold]Sharpe Ratio:[/] {perf.sharpe_ratio:.2f} | [bold]Max Drawdown:[/] {perf.max_drawdown_pct:.2f}%\n")

def run_download_history_command(args):
    info_text = f"[bold green]📥 Downloading Historical Data for Universe: {args.universe.upper()}[/bold green]\nTimeframe: {args.timeframe} | Lookback: {args.days} days"
    console.print(Panel(info_text, title="NSE Data Ingestion"))
    
    collector = HistoricalDataCollector()
    symbols = UniverseManager.get_universe(args.universe)
    console.print(f"Fetching [bold cyan]{len(symbols)}[/bold cyan] symbols...")

    def _progress(done, total, sym, count):
        if done % 10 == 0 or done == total:
            console.print(f"  [{done}/{total}] {sym:<15} -> [green]{count} bars saved[/green]")

    results = collector.download_universe(
        universe_name=args.universe,
        timeframe=args.timeframe,
        start_date=datetime.now() - timedelta(days=args.days),
        end_date=datetime.now(),
        progress_callback=_progress
    )
    console.print(f"\n[bold green]✅ Download Completed![/bold green] Total symbols processed: {len(results)}")

def run_update_daily_command(args):
    console.print(Panel(f"[bold cyan]🔄 Running Incremental EOD Sync for {args.universe.upper()}[/bold cyan]", title="NSE Daily Updater"))
    sync = DailyDataSynchronizer()
    results = sync.sync_daily_eod(universe_name=args.universe, timeframe=args.timeframe)
    console.print(f"[bold green]✅ Incremental Sync Done![/bold green] Updated {len(results)} symbols.")

def run_data_status_command(args):
    collector = HistoricalDataCollector()
    df_status = collector.get_datastore_status()
    if df_status.empty:
        console.print("[yellow]No historical datasets found in local storage. Run `python -m nse_system download-history` first.[/yellow]")
        return

    table = Table(title=f"📁 Local Parquet Datastore ({len(df_status)} files)", show_header=True, header_style="bold cyan")
    table.add_column("Symbol", style="bold")
    table.add_column("TF", justify="center")
    table.add_column("Total Bars", justify="right")
    table.add_column("Start Date")
    table.add_column("End Date")
    table.add_column("Size (KB)", justify="right")
    table.add_column("Last Close (INR)", justify="right")

    for row in df_status.head(25).itertuples():
        table.add_row(
            str(row.Symbol), str(row.Timeframe), str(row._3),
            str(row._4), str(row._5), f"{row._6:.1f}", f"₹{row._7:,.2f}"
        )
    console.print(table)
    if len(df_status) > 25:
        console.print(f"[italic]... and {len(df_status) - 25} more symbols.[/italic]")

def run_dashboard_command(args):
    console.print("[bold green]🚀 Launching Streamlit Dashboard...[/bold green]")
    app_path = os.path.join(os.path.dirname(__file__), "..", "dashboard", "app.py")
    subprocess.run(["streamlit", "run", app_path, "--server.port", str(args.port)])

def main():
    parser = argparse.ArgumentParser(description="NSE Quantitative Strategy Platform CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Scan subparser
    scan_parser = subparsers.add_parser("scan", help="Scan universe for high-probability trade setups")
    scan_parser.add_argument("--universe", default="fno", choices=["fno", "nifty500", "nifty50"], help="Universe")
    scan_parser.add_argument("--type", default="all", choices=["all", "swing_long", "swing_short", "intraday"], help="Trade type")
    scan_parser.add_argument("--confidence", type=float, default=65.0, help="Min confidence score")

    # Arena subparser
    arena_parser = subparsers.add_parser("arena", help="Run multi-strategy tournament & find best strategy")
    arena_parser.add_argument("--symbol", default="NIFTY 50", help="NSE Symbol or Index")
    arena_parser.add_argument("--timeframe", default="5m", help="Candle timeframe")
    arena_parser.add_argument("--days", type=int, default=30, help="Lookback period")
    arena_parser.add_argument("--capital", type=float, default=100000.0, help="Capital in INR")
    arena_parser.add_argument("--vix", type=float, default=14.5, help="India VIX level")

    # Backtest subparser
    bt_parser = subparsers.add_parser("backtest", help="Run single strategy backtest")
    bt_parser.add_argument("--strategy", default="VWAP_SuperTrend", help="Strategy name")
    bt_parser.add_argument("--symbol", default="RELIANCE", help="NSE Symbol")
    bt_parser.add_argument("--timeframe", default="5m", help="Candle timeframe")
    bt_parser.add_argument("--days", type=int, default=30, help="Lookback period")
    bt_parser.add_argument("--capital", type=float, default=100000.0, help="Capital in INR")

    # Data download subparser
    dl_parser = subparsers.add_parser("download-history", help="Download historical data for universe")
    dl_parser.add_argument("--universe", default="fno", choices=["fno", "nifty500", "nifty50", "indices", "all"], help="Universe")
    dl_parser.add_argument("--timeframe", default="1d", help="Timeframe (1d, 1h, 15m, 5m)")
    dl_parser.add_argument("--days", type=int, default=1825, help="Lookback days (default 5 years for 1d)")

    # Data update subparser
    up_parser = subparsers.add_parser("update-daily", help="Incremental EOD sync for universe")
    up_parser.add_argument("--universe", default="fno", help="Universe")
    up_parser.add_argument("--timeframe", default="1d", help="Timeframe")

    # Data status subparser
    subparsers.add_parser("data-status", help="Inspect local Parquet datastore status")

    # Dashboard subparser
    dash_parser = subparsers.add_parser("dashboard", help="Launch Streamlit web dashboard")
    dash_parser.add_argument("--port", type=int, default=8501, help="Port to run Streamlit on")

    # List strategies
    subparsers.add_parser("list-strategies", help="List all available strategies")

    args = parser.parse_args()

    if args.command == "scan":
        run_scan_command(args)
    elif args.command == "arena":
        run_arena_command(args)
    elif args.command == "backtest":
        run_backtest_command(args)
    elif args.command == "download-history":
        run_download_history_command(args)
    elif args.command == "update-daily":
        run_update_daily_command(args)
    elif args.command == "data-status":
        run_data_status_command(args)
    elif args.command == "dashboard":
        run_dashboard_command(args)
    elif args.command == "list-strategies":
        console.print("[bold magenta]Available Strategies:[/bold magenta]")
        for s in list_available_strategies():
            console.print(f"  • {s}")
    else:
        class DefaultArgs:
            symbol = "NIFTY 50"
            timeframe = "5m"
            days = 30
            capital = 100000.0
            vix = 14.5
        run_arena_command(DefaultArgs())

if __name__ == "__main__":
    main()
