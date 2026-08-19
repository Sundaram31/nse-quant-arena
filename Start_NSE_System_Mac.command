#!/bin/bash
# One-Click Launcher for macOS
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"
echo "Starting NSE Quantitative Platform..."
open "http://localhost:8501"
python3 -m streamlit run nse_system/dashboard/app.py --server.port 8501 --server.headless false
