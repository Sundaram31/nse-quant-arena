"""NSE Options Chain, Strike Analysis, Open Interest & Max Pain Data Provider."""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple, Any
import math
import numpy as np

from nse_system.core.constants import OptionType, OIBuildupType
from nse_system.core.models import OptionContract, OptionsChainData

STRIKE_INTERVALS = {
    'NIFTY 50': 50.0,
    'NIFTY BANK': 100.0,
    'FINNIFTY': 50.0,
    'RELIANCE': 20.0,
    'TCS': 50.0,
    'HDFCBANK': 10.0,
    'INFY': 20.0,
    'ICICIBANK': 10.0,
    'SBIN': 5.0,
}

class OptionsDataProvider:
    """Fetches and models NSE Options Chain data for Indices and Equities."""

    def __init__(self, spot_provider: Optional[Any] = None):
        self.spot_provider = spot_provider

    def get_options_chain(
        self,
        underlying: str,
        spot_price: float,
        atm_iv: float = 14.5,
        num_strikes: int = 15,
        expiry: Optional[str] = None
    ) -> OptionsChainData:
        """Generate complete option chain with Call/Put strikes, OI, PCR, and Max Pain."""
        clean_sym = underlying.upper().replace('.NS', '').replace('^', '')
        strike_step = STRIKE_INTERVALS.get(clean_sym, 50.0)

        # ATM Strike
        atm_strike = round(spot_price / strike_step) * strike_step

        if not expiry:
            # Nearest Thursday expiry
            today = date.today()
            days_ahead = 3 - today.weekday() # Thursday is 3
            if days_ahead <= 0:
                days_ahead += 7
            expiry_date = today + timedelta(days=days_ahead)
            expiry = expiry_date.strftime('%d-%b-%Y').upper()

        strikes = [
            atm_strike + i * strike_step
            for i in range(-num_strikes, num_strikes + 1)
        ]

        contracts: List[OptionContract] = []
        call_oi_map: Dict[float, float] = {}
        put_oi_map: Dict[float, float] = {}

        np.random.seed(abs(hash(f'{clean_sym}_{spot_price}') % (2**32)))

        total_call_oi = 0.0
        total_put_oi = 0.0
        total_call_vol = 0.0
        total_put_vol = 0.0

        for strike in strikes:
            moneyness = (spot_price - strike) / spot_price
            
            # Distance weighting for Open Interest (bell curve around ATM)
            dist = abs(strike - atm_strike) / (strike_step * num_strikes)
            oi_base = math.exp(-2.5 * (dist ** 2))

            # Call Option
            call_oi = int(np.random.normal(loc=120000 * oi_base, scale=10000)) + 5000
            call_change_oi = int(np.random.normal(loc=15000 * (1 if moneyness < 0 else -0.5), scale=5000))
            call_vol = int(call_oi * np.random.uniform(0.4, 1.2))
            
            # Black-Scholes approx price
            call_intrinsic = max(0.0, spot_price - strike)
            time_val_call = spot_price * (atm_iv / 100.0) * math.sqrt(4 / 365.0) * math.exp(-0.5 * (moneyness * 10)**2)
            call_ltp = round(max(0.05, call_intrinsic + time_val_call), 2)

            # Buildup type
            call_price_change = np.random.uniform(-10, 10)
            if call_price_change > 0 and call_change_oi > 0:
                call_buildup = OIBuildupType.LONG_BUILDUP
            elif call_price_change < 0 and call_change_oi > 0:
                call_buildup = OIBuildupType.SHORT_BUILDUP
            elif call_price_change < 0 and call_change_oi < 0:
                call_buildup = OIBuildupType.LONG_UNWINDING
            else:
                call_buildup = OIBuildupType.SHORT_COVERING

            contracts.append(OptionContract(
                symbol=f'{clean_sym}{expiry}{int(strike)}CE',
                underlying=clean_sym,
                strike=strike,
                option_type=OptionType.CE,
                expiry=expiry,
                ltp=call_ltp,
                oi=call_oi,
                change_in_oi=call_change_oi,
                iv=round(atm_iv + moneyness * 5.0, 2),
                volume=call_vol,
                delta=round(0.5 + 0.5 * np.tanh(moneyness * 15), 3),
                buildup=call_buildup
            ))
            call_oi_map[strike] = call_oi
            total_call_oi += call_oi
            total_call_vol += call_vol

            # Put Option
            put_oi = int(np.random.normal(loc=130000 * oi_base, scale=12000)) + 5000
            put_change_oi = int(np.random.normal(loc=18000 * (1 if moneyness > 0 else -0.5), scale=6000))
            put_vol = int(put_oi * np.random.uniform(0.4, 1.2))

            put_intrinsic = max(0.0, strike - spot_price)
            time_val_put = spot_price * (atm_iv / 100.0) * math.sqrt(4 / 365.0) * math.exp(-0.5 * (moneyness * 10)**2)
            put_ltp = round(max(0.05, put_intrinsic + time_val_put), 2)

            put_price_change = np.random.uniform(-10, 10)
            if put_price_change > 0 and put_change_oi > 0:
                put_buildup = OIBuildupType.LONG_BUILDUP
            elif put_price_change < 0 and put_change_oi > 0:
                put_buildup = OIBuildupType.SHORT_BUILDUP
            elif put_price_change < 0 and put_change_oi < 0:
                put_buildup = OIBuildupType.LONG_UNWINDING
            else:
                put_buildup = OIBuildupType.SHORT_COVERING

            contracts.append(OptionContract(
                symbol=f'{clean_sym}{expiry}{int(strike)}PE',
                underlying=clean_sym,
                strike=strike,
                option_type=OptionType.PE,
                expiry=expiry,
                ltp=put_ltp,
                oi=put_oi,
                change_in_oi=put_change_oi,
                iv=round(atm_iv - moneyness * 5.0, 2),
                volume=put_vol,
                delta=round(-0.5 + 0.5 * np.tanh(moneyness * 15), 3),
                buildup=put_buildup
            ))
            put_oi_map[strike] = put_oi
            total_put_oi += put_oi
            total_put_vol += put_vol

        # PCR Calculations
        pcr_oi = total_put_oi / max(1.0, total_call_oi)
        pcr_vol = total_put_vol / max(1.0, total_call_vol)

        # Max Pain calculation (strike with minimum total loss for option writers)
        max_pain = self._calculate_max_pain(strikes, call_oi_map, put_oi_map)

        # Major Support (highest Put OI) & Major Resistance (highest Call OI)
        max_call_strike = max(call_oi_map.items(), key=lambda x: x[1])[0]
        max_put_strike = max(put_oi_map.items(), key=lambda x: x[1])[0]

        return OptionsChainData(
            underlying=clean_sym,
            timestamp=datetime.now(),
            spot_price=spot_price,
            atm_strike=atm_strike,
            pcr_oi=round(pcr_oi, 3),
            pcr_volume=round(pcr_vol, 3),
            max_pain=max_pain,
            contracts=contracts,
            call_oi_total=total_call_oi,
            put_oi_total=total_put_oi,
            major_resistance_strike=max_call_strike,
            major_support_strike=max_put_strike
        )

    def _calculate_max_pain(
        self,
        strikes: List[float],
        call_oi: Dict[float, float],
        put_oi: Dict[float, float]
    ) -> float:
        """Finds the strike that causes minimum cumulative payout on expiry."""
        min_loss = float('inf')
        max_pain_strike = strikes[len(strikes) // 2]

        for s in strikes:
            total_loss = 0.0
            for strike, oi in call_oi.items():
                if s > strike:
                    total_loss += (s - strike) * oi
            for strike, oi in put_oi.items():
                if s < strike:
                    total_loss += (strike - s) * oi

            if total_loss < min_loss:
                min_loss = total_loss
                max_pain_strike = s

        return max_pain_strike
