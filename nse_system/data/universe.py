"""NSE Universe Management - NIFTY 500, F&O Stocks, and Sectoral Baskets."""
import os
from typing import List, Dict, Optional
import requests
import pandas as pd

# Comprehensive NIFTY 500 and Liquid F&O Stocks Master List
FNO_STOCKS = [
    'AARTIIND', 'ABB', 'ABBOTINDIA', 'ABCAPITAL', 'ABFRL', 'ACC', 'ADANIENT', 'ADANIPORTS',
    'ALKEM', 'AMBUJACEM', 'APOLLOHOSP', 'APOLLOTYRE', 'ASHOKLEY', 'ASIANPAINT', 'ASTRAL',
    'ATUL', 'AUBANK', 'AUROPHARMA', 'AXISBANK', 'BAJAJ-AUTO', 'BAJAJFINSV', 'BAJFINANCE',
    'BALKRISIND', 'BALRAMCHIN', 'BANDHANBNK', 'BANKBARODA', 'BATAINDIA', 'BEL', 'BERGEPAINT',
    'BHARATFORG', 'BHARTIARTL', 'BHEL', 'BIOCON', 'BOSCHLTD', 'BPCL', 'BRITANNIA',
    'BSOFT', 'CANBK', 'CANFINHOME', 'CHAMBLFERT', 'CHOLAFIN', 'CIPLA', 'COALINDIA',
    'COFORGE', 'COLPAL', 'CONCOR', 'COROMANDEL', 'CROMPTON', 'CUMMINSIND', 'DABUR',
    'DALBHARAT', 'DEEPAKNTR', 'DELHIVERY', 'DIVISLAB', 'DIXON', 'DLF', 'DRREDDY',
    'EICHERMOT', 'ESCORTS', 'EXIDEIND', 'FEDERALBNK', 'GAIL', 'GLENMARK', 'GMRINFRA',
    'GNFC', 'GODREJCP', 'GODREJPROP', 'GRANULES', 'GRASIM', 'GUJGASLTD', 'HAL',
    'HAVELLS', 'HCLTECH', 'HDFCAMC', 'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO',
    'HINDCOPPER', 'HINDPETRO', 'HINDUNILVR', 'ICICIBANK', 'ICICIGI', 'ICICIPRULI', 'IDEA',
    'IDFC', 'IDFCFIRSTB', 'IEX', 'IGL', 'INDHOTEL', 'INDIACEM', 'INDIAMART', 'INDIGO',
    'INDUSINDBK', 'INDUSTOWER', 'INFY', 'IOC', 'IPCALAB', 'IRCTC', 'ITC', 'JINDALSTEL',
    'JKCEMENT', 'JSWSTEEL', 'JUBLFOOD', 'KALYANKJIL', 'KOTAKBANK', 'LALPATHLAB', 'LAURUSLABS',
    'LICHSGFIN', 'LICI', 'LT', 'LTF', 'LTIM', 'LTTS', 'LUPIN', 'M&M', 'M&MFIN',
    'MANAPPURAM', 'MARICO', 'MARUTI', 'MAXHEALTH', 'MCX', 'METROPOLIS', 'MFSL', 'MGL',
    'MOTHERSON', 'MPHASIS', 'MRF', 'MUTHOOTFIN', 'NATIONALUM', 'NAUKRI', 'NAVINFLUOR',
    'NESTLEIND', 'NMDC', 'NTPC', 'OBEROIRLTY', 'OFSS', 'ONGC', 'PAGEIND', 'PEL',
    'PERSISTENT', 'PETRONET', 'PFC', 'PHOENIXLTD', 'PIDILITIND', 'PIIND', 'PNB',
    'POLYCAB', 'POONAWALLA', 'POWERGRID', 'PRESTIGE', 'PVRINOX', 'RAMCOCEM', 'RBLBANK',
    'RECLTD', 'RELIANCE', 'SAIL', 'SBICARD', 'SBILIFE', 'SBIN', 'SHREECEM', 'SHRIRAMFIN',
    'SIEMENS', 'SRF', 'SUNPHARMA', 'SUNTV', 'SYNGENE', 'TATACHEM', 'TATACOMM', 'TATACONSUM',
    'TATAMOTORS', 'TATAPOWER', 'TATASTEEL', 'TCS', 'TECHM', 'TITAN', 'TORNTPHARM',
    'TORNTPOWER', 'TRENT', 'TVSMOTOR', 'UBL', 'ULTRACEMCO', 'UNIONBANK', 'UPL', 'VBL',
    'VEDL', 'VOLTAS', 'WIPRO', 'YESBANK', 'ZYDUSLIFE'
]

NIFTY_INDICES = [
    'NIFTY 50', 'NIFTY BANK', 'FINNIFTY', 'MIDCPNIFTY', 'NIFTY NEXT 50',
    'NIFTY IT', 'NIFTY AUTO', 'NIFTY PHARMA', 'NIFTY METAL', 'NIFTY FMCG',
    'NIFTY REALTY', 'NIFTY ENERGY', 'NIFTY PSU BANK', 'INDIA VIX'
]

class UniverseManager:
    """Manages stock universes for NIFTY 500, F&O, and Sectoral Baskets."""

    @staticmethod
    def get_fno_symbols() -> List[str]:
        """Returns the complete active NSE F&O universe (~180+ liquid stocks)."""
        return FNO_STOCKS.copy()

    @staticmethod
    def get_indices() -> List[str]:
        """Returns key NSE benchmark and sectoral indices."""
        return NIFTY_INDICES.copy()

    @classmethod
    def get_nifty_500_symbols(cls) -> List[str]:
        """Fetches official NIFTY 500 constituents from NSE or uses pre-configured master list."""
        json_path = os.path.join(os.path.dirname(__file__), 'nifty500_constituents.json')
        if os.path.exists(json_path):
            try:
                import json
                with open(json_path, 'r') as f:
                    data = json.load(f)
                if data and isinstance(data, list) and len(data) >= 100:
                    return [s.strip().upper() for s in data if s.strip()]
            except Exception:
                pass

        try:
            url = 'https://archives.nseindia.com/content/indices/ind_nifty500list.csv'
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                import io
                df = pd.read_csv(io.StringIO(resp.text))
                if 'Symbol' in df.columns:
                    return [s.strip().upper() for s in df['Symbol'].tolist() if s.strip()]
        except Exception:
            pass

        # Fallback comprehensive basket combining F&O + Top Large/Mid/Small Caps
        return sorted(list(set(FNO_STOCKS + [
            'BSE', 'CDSL', 'ZOMATO', 'PAYTM', 'POLICYBZR', 'NYKAA', 'MAPMYINDIA', 'KAYNES',
            'SUZLON', 'IRFC', 'RVNL', 'MAZDOCK', 'COCHINSHIP', 'HUDCO', 'NHPC', 'SJVN',
            'IREDA', 'JIOFIN', 'TATAELXSI', 'ANGELONE', 'KPITTECH', 'CYIENT', 'CENTRALBK',
            'IOB', 'UCOBANK', 'MAHABANK', 'FACT', 'RCF', 'GSFC', 'GNFC', 'DEEPAKFERT',
            'HAPPSTMNDS', 'LATENTVIEW', 'SONACOMS', 'CLEAN', 'MEDPLUS', 'SAPPHIRE', 'BIKAJI'
        ])))

    @classmethod
    def get_universe(cls, name: str = 'fno') -> List[str]:
        """Returns symbol list for a named universe."""
        u = name.lower()
        if u in ('fno', 'fo'):
            return cls.get_fno_symbols()
        elif u in ('nifty500', 'nifty_500', '500'):
            return cls.get_nifty_500_symbols()
        elif u in ('nifty50', 'nifty_50', '50'):
            return cls.get_fno_symbols()[:50]
        elif u in ('indices', 'index'):
            return cls.get_indices()
        elif u in ('all', 'complete'):
            return sorted(list(set(cls.get_nifty_500_symbols() + cls.get_indices())))
        else:
            return cls.get_fno_symbols()
