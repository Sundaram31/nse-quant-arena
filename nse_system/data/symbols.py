"""NSE Universe, Indices, Sectoral mapping, and Lot Sizes."""
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class SymbolInfo:
    symbol: str
    name: str
    sector: str
    lot_size: int = 1
    tick_size: float = 0.05
    is_index: bool = False
    yahoo_ticker: str = ''

NSE_INDICES = {
    'NIFTY 50': SymbolInfo('NIFTY 50', 'Nifty 50 Index', 'Benchmark', 50, 0.05, True, '^NSEI'),
    'NIFTY BANK': SymbolInfo('NIFTY BANK', 'Nifty Bank Index', 'Banking', 15, 0.05, True, '^NSEBANK'),
    'FINNIFTY': SymbolInfo('FINNIFTY', 'Nifty Financial Services', 'Financials', 40, 0.05, True, 'NIFTY_FIN_SERVICE.NS'),
    'NIFTY IT': SymbolInfo('NIFTY IT', 'Nifty IT Index', 'Information Technology', 25, 0.05, True, '^CNXIT'),
    'NIFTY AUTO': SymbolInfo('NIFTY AUTO', 'Nifty Auto Index', 'Automobile', 25, 0.05, True, '^CNXAUTO'),
    'NIFTY PHARMA': SymbolInfo('NIFTY PHARMA', 'Nifty Pharma Index', 'Healthcare', 25, 0.05, True, '^CNXPHARMA'),
    'NIFTY METAL': SymbolInfo('NIFTY METAL', 'Nifty Metal Index', 'Metals & Mining', 25, 0.05, True, '^CNXMETAL'),
    'NIFTY FMCG': SymbolInfo('NIFTY FMCG', 'Nifty FMCG Index', 'Consumer Goods', 25, 0.05, True, '^CNXFMCG'),
    'NIFTY REALTY': SymbolInfo('NIFTY REALTY', 'Nifty Realty Index', 'Real Estate', 25, 0.05, True, '^CNXREALTY'),
    'NIFTY ENERGY': SymbolInfo('NIFTY ENERGY', 'Nifty Energy Index', 'Energy & Power', 25, 0.05, True, '^CNXENERGY'),
    'INDIA VIX': SymbolInfo('INDIA VIX', 'India Volatility Index', 'Volatility', 1, 0.01, True, '^INDIAVIX'),
}

NSE_EQUITIES = {
    'RELIANCE': SymbolInfo('RELIANCE', 'Reliance Industries Ltd.', 'Energy & Oil', 250, 0.05, False, 'RELIANCE.NS'),
    'TCS': SymbolInfo('TCS', 'Tata Consultancy Services Ltd.', 'Information Technology', 175, 0.05, False, 'TCS.NS'),
    'HDFCBANK': SymbolInfo('HDFCBANK', 'HDFC Bank Ltd.', 'Banking', 550, 0.05, False, 'HDFCBANK.NS'),
    'INFY': SymbolInfo('INFY', 'Infosys Ltd.', 'Information Technology', 400, 0.05, False, 'INFY.NS'),
    'ICICIBANK': SymbolInfo('ICICIBANK', 'ICICI Bank Ltd.', 'Banking', 700, 0.05, False, 'ICICIBANK.NS'),
    'BHARTIARTL': SymbolInfo('BHARTIARTL', 'Bharti Airtel Ltd.', 'Telecom', 475, 0.05, False, 'BHARTIARTL.NS'),
    'SBIN': SymbolInfo('SBIN', 'State Bank of India', 'Banking', 750, 0.05, False, 'SBIN.NS'),
    'ITC': SymbolInfo('ITC', 'ITC Ltd.', 'Consumer Goods', 1600, 0.05, False, 'ITC.NS'),
    'LT': SymbolInfo('LT', 'Larsen & Toubro Ltd.', 'Infrastructure', 175, 0.05, False, 'LT.NS'),
    'TATAMOTORS': SymbolInfo('TATAMOTORS', 'Tata Motors Ltd.', 'Automobile', 700, 0.05, False, 'TATAMOTORS.NS'),
    'KOTAKBANK': SymbolInfo('KOTAKBANK', 'Kotak Mahindra Bank Ltd.', 'Banking', 400, 0.05, False, 'KOTAKBANK.NS'),
    'AXISBANK': SymbolInfo('AXISBANK', 'Axis Bank Ltd.', 'Banking', 625, 0.05, False, 'AXISBANK.NS'),
    'HINDUNILVR': SymbolInfo('HINDUNILVR', 'Hindustan Unilever Ltd.', 'Consumer Goods', 300, 0.05, False, 'HINDUNILVR.NS'),
    'BAJFINANCE': SymbolInfo('BAJFINANCE', 'Bajaj Finance Ltd.', 'Financials', 125, 0.05, False, 'BAJFINANCE.NS'),
    'MARUTI': SymbolInfo('MARUTI', 'Maruti Suzuki India Ltd.', 'Automobile', 50, 0.05, False, 'MARUTI.NS'),
    'SUNPHARMA': SymbolInfo('SUNPHARMA', 'Sun Pharmaceutical Ind. Ltd.', 'Healthcare', 350, 0.05, False, 'SUNPHARMA.NS'),
    'TITAN': SymbolInfo('TITAN', 'Titan Company Ltd.', 'Consumer Discretionary', 175, 0.05, False, 'TITAN.NS'),
    'TATASTEEL': SymbolInfo('TATASTEEL', 'Tata Steel Ltd.', 'Metals & Mining', 5500, 0.05, False, 'TATASTEEL.NS'),
    'WIPRO': SymbolInfo('WIPRO', 'Wipro Ltd.', 'Information Technology', 1500, 0.05, False, 'WIPRO.NS'),
    'NTPC': SymbolInfo('NTPC', 'NTPC Ltd.', 'Energy & Power', 1500, 0.05, False, 'NTPC.NS'),
}

ALIAS_MAP = {
    'BAJAJAUTO': 'BAJAJ-AUTO',
    'BAJAJ_AUTO': 'BAJAJ-AUTO',
    'MM': 'M&M',
    'MNM': 'M&M',
    'NIFTY': 'NIFTY 50',
    'BANKNIFTY': 'NIFTY BANK',
    'NIFTYBANK': 'NIFTY BANK',
    'FIN_NIFTY': 'FINNIFTY',
    'TATAPOWER': 'TATAPOWER',
    'LTTD': 'LT',
    'ADANI': 'ADANIENT'
}

def get_symbol_info(symbol: str) -> SymbolInfo:
    sym = symbol.upper().replace('.NS', '').replace('^', '').strip()
    sym = ALIAS_MAP.get(sym, sym)
    if sym in NSE_INDICES:
        return NSE_INDICES[sym]
    if sym in NSE_EQUITIES:
        return NSE_EQUITIES[sym]
    # Default fallback
    return SymbolInfo(
        symbol=sym,
        name=sym,
        sector='General',
        lot_size=1,
        tick_size=0.05,
        is_index=False,
        yahoo_ticker=f'{sym}.NS'
    )

def get_all_sector_indices() -> List[str]:
    return [
        'NIFTY BANK', 'NIFTY IT', 'NIFTY AUTO', 'NIFTY PHARMA',
        'NIFTY METAL', 'NIFTY FMCG', 'NIFTY REALTY', 'NIFTY ENERGY'
    ]

def get_fno_universe() -> List[str]:
    return list(NSE_EQUITIES.keys())
