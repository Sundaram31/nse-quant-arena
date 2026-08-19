@echo off
REM One-Click Launcher for Windows
title NSE Quantitative Strategy Platform
cd /d "%~dp0"
echo Starting NSE Quantitative Platform...
start http://localhost:8501
python -m streamlit run nse_system/dashboard/app.py --server.port 8501 --server.headless false
pause
