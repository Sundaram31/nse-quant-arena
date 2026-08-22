# User Profile & NSE Quant Arena Operating Guidelines

## 👤 User Profile & Communication Principles
- **Background**: The user is a **Mechanical Engineer** with a **no-code background** and zero computer science/programming training.
- **Communication Style**:
  - Keep all explanations intuitive, proactive, structured, and free of unnecessary programming jargon (treat explanations like a mechanical machine/vehicle owner's manual).
  - Proactively advise on system requirements (RAM, disk space, internet, battery, maintenance intervals) rather than waiting to be asked.
  - Never require the user to write terminal commands for daily operations; always provide or maintain 1-click desktop launchers (`.command` files) and cloud-ready links.

---

## ⚙️ System Specifications & Hardware Profile
- **Storage Profile**:
  - Full Datastore: `nse_system/data/datastore/` (~104 MB, 3,223 stocks in high-speed Parquet format).
  - Manifest & Index: `nse_system/data/datastore_manifest.json` (instant <5ms lookups).
  - Monthly Archive: `backups/` (~65 MB per `.tar.gz` compressed snapshot).
- **Runtime Profile**:
  - Local RAM: Light footprint (~350 MB active usage).
  - Compute: 100% vector-accelerated NumPy/Pandas and Plotly interactive rendering.
  - Internet Requirement: Only 10–15 seconds at 4:00 PM IST on trading days to download Bhavcopy; all backtests, screeners, and indicators run 100% offline.

---

## 🚗 Core Operational Workflows (No-Code)

### 1. Daily EOD Scan Workflow (4:00 PM IST Weekdays)
- User executes `Start_Automated_EOD_Scan.command` by double-clicking it on macOS.
- Downloads daily exchange data, detects/applies corporate action split/bonus adjustments backward, and runs quantitative multi-factor filters (Fibonacci Golden Pockets, Sweet-Spot Momentum, Narrow CPR).
- Generates `reports/EOD_SCAN_{DATE}.md` and updates the active candidate pool.

### 2. Live Mobile & Web Dashboard (24/7 Zero Mac Needed)
- Hosted on Streamlit Community Cloud (`Sundaram31/nse-quant-arena` on branch `main`).
- Auto-syncs on every git push to `main`.
- Features: Touch pinch-to-zoom/pan Plotly candlestick charts, 1-click timeframe selectors (`1M`, `3M`, `6M`, `ALL`), Options OI distributions, and seamless Light/Dark mode switching.

### 3. Safety & Backup Routine (Monthly)
- User double-clicks `Backup_Database.command` on macOS.
- Compresses datastore into `backups/nse_datastore_backup_{TIMESTAMP}.tar.gz` with SHA-256 integrity verification.
- Restore is available anytime via `python3 scripts/restore_datastore.py`.

---

## 🛡️ Core System Directives
- **Zero Simulation Mandate**: Never mock or simulate fake prices or assume arbitrary random signals. All indicators, prices, and volumes must come 100% from genuine exchange parquet files.
- **Corporate Action Integrity**: Always ensure historical data is adjusted backward for stock splits/bonuses (e.g. Tata Steel 10:1 split, Reliance 1:1 bonus) to protect ATR and stop loss calculations.
