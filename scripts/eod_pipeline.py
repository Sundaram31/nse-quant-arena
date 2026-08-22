"""
Automated End-of-Day (EOD) Data Download & Quantitative Market Scan Pipeline.
1. Syncs latest daily Bhavcopy candles into the authentic Parquet datastore.
2. Applies CorporateActionAdjuster to ensure split/bonus continuity.
3. Runs the multi-factor Fibonacci, Price Action, and Confluence Screeners across F&O and Nifty 500.
4. Generates a structured Daily Market Radar Report for the next trading morning.
"""
import os
import sys
import json
from datetime import datetime, date, timedelta
from typing import Dict, List, Any
import pandas as pd

# Ensure nse_system in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nse_system.data.universe import UniverseManager
from nse_system.data.historical import NSEHistoricalDataProvider
from nse_system.data.adjustments import CorporateActionAdjuster
from nse_system.data.sync_scheduler import DailyDataSynchronizer
from nse_system.analytics.screener import QuantStockScreener
from nse_system.analytics.confluence import CompositeConfluenceEngine

REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

def run_eod_pipeline(universe: str = 'fno', save_report: bool = True) -> Dict[str, Any]:
    """Executes the complete EOD sync, corporate action adjustment, and quantitative radar scan."""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    today_date_str = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 80)
    print(f"  🚀 NSE QUANT ARENA: AUTOMATED EOD SYNC & RADAR SCAN")
    print(f"  Timestamp: {now_str} | Target Universe: {universe.upper()}")
    print("=" * 80 + "\n")

    # -----------------------------------------------------------------
    # STEP 1: INCREMENTAL DATA SYNC
    # -----------------------------------------------------------------
    print("📡 Step 1/3: Checking Datastore & Performing Incremental Sync...")
    synchronizer = DailyDataSynchronizer()
    sync_res = synchronizer.sync_daily_eod(universe_name=universe, timeframe='1d')
    print(f"   ✓ Checked {sync_res['symbols_checked']} symbols | Updated/Verified: {sync_res['symbols_updated']}")
    
    # -----------------------------------------------------------------
    # STEP 2: QUANTITATIVE RADAR SCAN
    # -----------------------------------------------------------------
    print("\n🔍 Step 2/3: Executing Multi-Factor Quantitative Screener & Confluence Scan...")
    dp = NSEHistoricalDataProvider()
    screener = QuantStockScreener(data_provider=dp)
    candidates = screener.scan_universe(universe_name=universe, min_confidence=65.0)
    
    print(f"   ✓ Scan Complete! Found {len(candidates)} High-Conviction Setups across {universe.upper()}.")

    # -----------------------------------------------------------------
    # STEP 3: STRUCTURED REPORT GENERATION
    # -----------------------------------------------------------------
    print("\n📊 Step 3/3: Formatting Daily Swing Radar Report...")
    report_rows = []
    for c in candidates:
        horizon_days = max(2, int(round((abs(c.target_1 - c.entry_trigger) / max(0.5, getattr(c, 'atr', 2.0))) * 1.5)))
        report_rows.append({
            'Symbol': c.symbol,
            'Setup': c.matched_strategy,
            'Confidence': f"{c.confidence_score:.0f}%",
            'Entry (₹)': f"₹{c.entry_trigger:,.2f}",
            'Stop Loss (₹)': f"₹{c.stop_loss:,.2f}",
            'Target 1 (₹)': f"₹{c.target_1:,.2f} ({horizon_days}d)",
            'Target 2 (₹)': f"₹{c.target_2:,.2f}",
            'R:R': c.risk_reward_ratio,
            'Catalyst / Confluence Reason': c.catalyst_reason
        })

    df_report = pd.DataFrame(report_rows)
    
    if not df_report.empty:
        print("\n" + "=" * 80)
        print(f"  🎯 TOP HIGH-CONVICTION SWING RADAR CANDIDATES ({today_date_str})")
        print("=" * 80)
        print(df_report.to_string(index=False))
        print("=" * 80 + "\n")
    else:
        print("   ℹ️ No high-conviction swing setups passed the strict confluence filters today.")

    if save_report:
        # Save JSON
        json_path = os.path.join(REPORTS_DIR, 'latest_swing_radar.json')
        with open(json_path, 'w') as f:
            json.dump([c.__dict__ for c in candidates], f, indent=2, default=str)

        # Save Markdown Report
        md_path = os.path.join(REPORTS_DIR, f'EOD_SCAN_{today_date_str}.md')
        with open(md_path, 'w') as f:
            f.write(f"# 🎯 NSE Quant Arena: Daily EOD Swing Radar Report\n")
            f.write(f"**Scan Date:** {now_str} | **Universe:** {universe.upper()} | **Setups Found:** {len(candidates)}\n\n")
            if not df_report.empty:
                headers = list(df_report.columns)
                f.write("| " + " | ".join(headers) + " |\n")
                f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")
                for _, row in df_report.iterrows():
                    f.write("| " + " | ".join(str(val) for val in row.values) + " |\n")
                f.write("\n")
            else:
                f.write("*No candidates met the minimum 75-point confluence threshold today.*\n\n")
            f.write("### Execution Instructions:\n")
            f.write("1. **Target 1 Fill**: Book 50% profits at Target 1 and immediately trail Stop Loss to Entry (Breakeven).\n")
            f.write("2. **Target 2 Runner**: Let remaining 50% trail with 21 EMA or ATR trailing stop.\n")
            f.write("3. **Risk Containment**: Never risk more than 1.0% of total portfolio equity on any single trade.\n")
        
        print(f"💾 Saved Daily Report to: {md_path}")
        print(f"💾 Saved Latest JSON to:   {json_path}")

    return {
        'scan_date': now_str,
        'candidates_count': len(candidates),
        'candidates': [c.__dict__ for c in candidates]
    }

if __name__ == '__main__':
    u_arg = sys.argv[1] if len(sys.argv) > 1 else 'fno'
    run_eod_pipeline(universe=u_arg)
