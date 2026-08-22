#!/bin/bash
cd "$(dirname "$0")"
echo "================================================================="
echo "  🚀 Starting NSE Quant Arena: Automated EOD Sync & Radar Scan  "
echo "================================================================="
python3 scripts/eod_pipeline.py fno
echo ""
echo "Scan complete! Reports saved in 'reports/' directory."
read -p "Press [Enter] to exit..."
