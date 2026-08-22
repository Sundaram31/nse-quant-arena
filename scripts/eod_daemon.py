"""
Automated EOD Background Scheduler Daemon.
Monitors system clock and automatically executes the EOD Data Download & Market Scan
at 16:00 (4:00 PM IST) every trading day (Monday through Friday).
"""
import os
import sys
import time
from datetime import datetime, time as dtime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.eod_pipeline import run_eod_pipeline

TARGET_HOUR = 16   # 4:00 PM
TARGET_MINUTE = 0  # 00 mins

def start_daemon(universe: str = 'fno', run_immediately: bool = False):
    print("=" * 80)
    print(f"  ⏰ NSE QUANT ARENA: AUTOMATED EOD SCHEDULER DAEMON STARTED")
    print(f"  Scheduled Run Time: 16:00:00 IST (Mon-Fri) | Universe: {universe.upper()}")
    print("=" * 80 + "\n")

    if run_immediately:
        print("⚡ Executing immediate on-demand EOD scan...")
        run_eod_pipeline(universe=universe)

    last_run_date = datetime.now().date() if run_immediately else None

    while True:
        try:
            now = datetime.now()
            today = now.date()
            weekday = now.weekday() # 0 = Mon, 4 = Fri, 5 = Sat, 6 = Sun

            # Check if it's a weekday and time is >= 16:00 and hasn't run today
            if weekday < 5 and (now.hour > TARGET_HOUR or (now.hour == TARGET_HOUR and now.minute >= TARGET_MINUTE)):
                if last_run_date != today:
                    print(f"\n⏰ Triggering scheduled 4:00 PM IST EOD Pipeline for {today}...")
                    run_eod_pipeline(universe=universe)
                    last_run_date = today

            # Sleep for 60 seconds between checks
            time.sleep(60)
        except KeyboardInterrupt:
            print("\n🛑 EOD Scheduler Daemon stopped by user.")
            break
        except Exception as e:
            print(f"⚠️ Scheduler Error: {e}. Retrying in 60s...")
            time.sleep(60)

if __name__ == '__main__':
    run_now = '--now' in sys.argv
    u = 'fno'
    for arg in sys.argv[1:]:
        if arg not in ('--now', '-n'):
            u = arg
            break
    start_daemon(universe=u, run_immediately=run_now)
