# 🇮🇳 NSE Quantitative Strategy & Adaptive Market Arena

A quantitative research, backtesting, and algorithmic execution platform built specifically for the **National Stock Exchange of India (NSE)**.

## Quick Start
- **Streamlit Web Dashboard**: `streamlit run nse_system/dashboard/app.py`
- **CLI Strategy Arena (Tournament)**: `python3 -m nse_system arena --symbol "NIFTY 50" --days 30 --vix 14.5`
- **CLI Backtest**: `python3 -m nse_system backtest --strategy ORB --symbol RELIANCE --days 30`
- **Unit Tests**: `python3 -u -c "import unittest; unittest.main(module=None, argv=['', 'discover', '-s', 'tests', '-p', 'test_*.py'])"`
