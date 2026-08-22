#!/bin/bash
# 📦 1-Click macOS Datastore Backup Launcher
cd "$(dirname "$0")"
echo "======================================================"
echo "📦 NSE QUANT ARENA - 1-CLICK DATASTORE BACKUP"
echo "======================================================"
python3 scripts/backup_datastore.py backups
echo ""
echo "Done! You can close this terminal window."
read -p "Press Enter to exit..."
