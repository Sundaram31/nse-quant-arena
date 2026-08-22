---
name: nse-quant-operations
description: >-
  Operations runbook, system specifications, hardware/runtime requirements,
  no-code user profile, 1-click launchers, daily trading routines, and datastore
  backup protocols for the NSE Quant Arena platform.
---

# NSE Quant Arena - System Operations & No-Code Runbook

## 1. User & Communication Persona
- **Audience**: Mechanical Engineer with zero software programming / computer science training.
- **Rule**: Provide proactive, crystal-clear, structured engineering advice (RAM, disk space, daily maintenance, step-by-step checklists) without software jargon.
- **Interface**: Keep all workflows accessible via 1-click desktop commands (`.command` files) and mobile-responsive cloud links.

---

## 2. Hardware, Resource & Environmental Specs
- **RAM**: Minimum 4 GB, Recommended 8 GB (Local memory footprint is ~350 MB).
- **Storage**:
  - Full Datastore: `nse_system/data/datastore/` (~104 MB for 3,223 stocks).
  - Pre-indexed Manifest: `nse_system/data/datastore_manifest.json`.
  - Monthly Archive Snapshots: `backups/` (~65 MB per `.tar.gz`).
- **Internet**:
  - Only required for 10–15 seconds during EOD Bhavcopy download.
  - All indicators, strategy backtests, and charts run 100% offline.
- **Cloud Hosting**:
  - Auto-deployed on Streamlit Community Cloud from `Sundaram31/nse-quant-arena` (`main` branch).
  - Runs 24/7 with zero battery drain or compute needed on local Mac.

---

## 3. Desktop 1-Click Launchers
1. **`Start_App.command`**: Launches local Streamlit dashboard at `http://localhost:8501`.
2. **`Start_Automated_EOD_Scan.command`**: Downloads daily Bhavcopy, adjusts splits/bonuses backward, runs scans, and outputs `reports/EOD_SCAN_{DATE}.md`.
3. **`Backup_Database.command`**: Generates timestamped `.tar.gz` snapshot of datastore with SHA-256 verification in `backups/`.

---

## 4. Operational Schedule & Trader Checklist
1. **4:00 PM IST (Weekdays)**: Double-click `Start_Automated_EOD_Scan.command`.
2. **Evening / Morning**: Open dashboard on mobile or laptop to review 90%+ confidence swing setups (Entry trigger, Stop Loss, Target 1, Target 2, holding duration).
3. **1st of Every Month**: Double-click `Backup_Database.command` to save a verified backup.
