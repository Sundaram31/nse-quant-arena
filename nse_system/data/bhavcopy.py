"""NSE Official Bhavcopy Ingestion Engine (Equities & Derivatives EOD)."""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import os
import io
import zipfile
import requests
import pandas as pd

class NSEBhavcopyFetcher:
    """Fetches and parses official daily NSE Bhavcopy files."""

    def __init__(self, download_dir: Optional[str] = None):
        self.download_dir = download_dir or os.path.expanduser('~/.cache/nse_system/bhavcopy')
        os.makedirs(self.download_dir, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        })

    def fetch_equity_bhavcopy(self, trade_date: date) -> Optional[pd.DataFrame]:
        """Fetches Cash Market Bhavcopy with delivery data for a specific date."""
        if trade_date.weekday() >= 5:  # Weekend
            return None

        d_str = trade_date.strftime('%d%m%Y')
        dd = trade_date.strftime('%d')
        mmm = trade_date.strftime('%b').upper()
        yyyy = trade_date.strftime('%Y')

        # Local cache check
        cached_file = os.path.join(self.download_dir, f'cm_bhav_{d_str}.parquet')
        if os.path.exists(cached_file):
            try:
                return pd.read_parquet(cached_file)
            except Exception:
                pass

        # Try official NSE endpoints
        urls = [
            f'https://archives.nseindia.com/products/content/sec_bhavdata_full_{d_str}.csv',
            f'https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{d_str}.csv',
            f'https://archives.nseindia.com/content/historical/EQUITIES/{yyyy}/{mmm}/cm{dd}{mmm}{yyyy}bhav.csv.zip'
        ]

        for url in urls:
            try:
                resp = self.session.get(url, timeout=6)
                if resp.status_code == 200:
                    if url.endswith('.zip'):
                        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
                            csv_name = z.namelist()[0]
                            with z.open(csv_name) as f:
                                df = pd.read_csv(f)
                    else:
                        df = pd.read_csv(io.StringIO(resp.text))

                    # Standardize column names
                    df.columns = [c.strip().upper() for c in df.columns]
                    # Filter Series EQ
                    if 'SERIES' in df.columns:
                        df = df[df['SERIES'].isin(['EQ', 'BE', 'BZ'])]

                    # Save to cache
                    df.to_parquet(cached_file)
                    return df
            except Exception:
                continue

        # If unreached or failed, return None explicitly (Zero-Mock Policy)
        return None
