#!/bin/bash
# Automated Daily NSE EOD Ingestion Script (Runs Mon-Fri @ 16:00 IST)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=== Starting Daily Incremental Sync: $(date) ===" >> ~/.cache/nse_system/sync.log
python3 -m nse_system update-daily --universe all --timeframe 1d >> ~/.cache/nse_system/sync.log 2>&1
echo "=== Sync Completed: $(date) ===" >> ~/.cache/nse_system/sync.log
