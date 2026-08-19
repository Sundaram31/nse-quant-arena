"""Cross-Platform Auto Daily Sync Worker."""
from datetime import datetime
from nse_system.data.sync_scheduler import DailyDataSynchronizer

def run_auto_sync():
    print(f'Starting automated daily EOD sync at {datetime.now()}...')
    sync = DailyDataSynchronizer()
    res = sync.sync_daily_eod(universe_name='all', timeframe='1d')
    print(f'Sync finished successfully! Updated {len(res)} symbols.')

if __name__ == '__main__':
    run_auto_sync()
