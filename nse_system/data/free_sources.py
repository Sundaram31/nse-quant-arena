"""Zero-Broker Free Market Data Ingestion (NSE Official Public API & Yahoo Finance)."""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import requests
import json
import pandas as pd
import numpy as np

class FreeNSEMarketData:
    """Fetches live and historical NSE data using public web endpoints without any broker API keys."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br'
        })
        self._cookie_initialized = False

    def _init_cookies(self):
        """Initialize NSE session cookies by visiting the homepage."""
        if not self._cookie_initialized:
            try:
                self.session.get('https://www.nseindia.com', timeout=5)
                self._cookie_initialized = True
            except Exception:
                pass

    def fetch_live_option_chain_free(self, symbol: str = 'NIFTY') -> Optional[Dict[str, Any]]:
        """Fetches live options chain directly from official NSE website without API keys."""
        self._init_cookies()
        is_index = symbol.upper() in ('NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY')
        endpoint = 'option-chain-indices' if is_index else 'option-chain-equities'
        url = f'https://www.nseindia.com/api/{endpoint}?symbol={symbol.upper()}'

        try:
            resp = self.session.get(url, timeout=6)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
        return None

    def fetch_yahoo_history_free(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = '1d'
    ) -> Optional[pd.DataFrame]:
        """Fetches historical OHLCV data from Yahoo Finance via direct HTTP request (No API key needed)."""
        sym = symbol.upper().replace('^', '')
        if sym in ('NIFTY 50', 'NIFTY'):
            ticker = '^NSEI'
        elif sym in ('NIFTY BANK', 'BANKNIFTY'):
            ticker = '^NSEBANK'
        elif not sym.endswith('.NS'):
            ticker = f'{sym}.NS'
        else:
            ticker = sym

        period1 = int(start_date.timestamp())
        period2 = int(end_date.timestamp())
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={period1}&period2={period2}&interval={interval}'

        try:
            resp = self.session.get(url, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                result = data['chart']['result'][0]
                timestamps = result['timestamp']
                quote = result['indicators']['quote'][0]

                df = pd.DataFrame({
                    'open': quote['open'],
                    'high': quote['high'],
                    'low': quote['low'],
                    'close': quote['close'],
                    'volume': quote['volume']
                }, index=pd.to_datetime(timestamps, unit='s'))
                df.dropna(inplace=True)
                return df
        except Exception:
            pass
        return None
