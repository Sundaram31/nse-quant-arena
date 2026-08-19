"""Options Open Interest, PCR, Strike Resistance/Support, and Buildup Analytics."""
from typing import Dict, List, Tuple, Any
import pandas as pd
from nse_system.core.models import OptionsChainData, OptionContract
from nse_system.core.constants import OIBuildupType

class OptionsOIAnalyzer:
    """Analyzes Open Interest distribution, PCR sentiment, and options positioning."""

    @staticmethod
    def analyze_chain(chain: OptionsChainData) -> Dict[str, Any]:
        """Extract key quantitative insights from an options chain snapshot."""
        pcr = chain.pcr_oi
        
        # PCR Interpretation for Indian Market
        if pcr < 0.65:
            pcr_status = 'EXTREMELY_OVERSOLD'
            pcr_bias = 'BULLISH_REVERSAL_ZONE'
        elif pcr < 0.85:
            pcr_status = 'MODERATELY_OVERSOLD'
            pcr_bias = 'BULLISH_BIAS'
        elif pcr > 1.45:
            pcr_status = 'EXTREMELY_OVERBOUGHT'
            pcr_bias = 'BEARISH_REVERSAL_ZONE'
        elif pcr > 1.25:
            pcr_status = 'MODERATELY_OVERBOUGHT'
            pcr_bias = 'BEARISH_BIAS'
        else:
            pcr_status = 'NEUTRAL'
            pcr_bias = 'RANGEBOUND'

        # Find highest Call OI (Major Resistance) and highest Put OI (Major Support)
        call_strikes = [c for c in chain.contracts if c.option_type.value == 'CE']
        put_strikes = [c for c in chain.contracts if c.option_type.value == 'PE']

        sorted_calls = sorted(call_strikes, key=lambda x: x.oi, reverse=True)
        sorted_puts = sorted(put_strikes, key=lambda x: x.oi, reverse=True)

        res_1 = sorted_calls[0].strike if sorted_calls else chain.spot_price
        res_2 = sorted_calls[1].strike if len(sorted_calls) > 1 else res_1
        sup_1 = sorted_puts[0].strike if sorted_puts else chain.spot_price
        sup_2 = sorted_puts[1].strike if len(sorted_puts) > 1 else sup_1

        # Calculate Net OI Buildup Summary
        long_buildup_count = sum(1 for c in chain.contracts if c.buildup == OIBuildupType.LONG_BUILDUP)
        short_buildup_count = sum(1 for c in chain.contracts if c.buildup == OIBuildupType.SHORT_BUILDUP)
        short_covering_count = sum(1 for c in chain.contracts if c.buildup == OIBuildupType.SHORT_COVERING)
        long_unwinding_count = sum(1 for c in chain.contracts if c.buildup == OIBuildupType.LONG_UNWINDING)

        return {
            'underlying': chain.underlying,
            'spot_price': chain.spot_price,
            'atm_strike': chain.atm_strike,
            'pcr_oi': chain.pcr_oi,
            'pcr_volume': chain.pcr_volume,
            'pcr_status': pcr_status,
            'pcr_bias': pcr_bias,
            'max_pain': chain.max_pain,
            'max_pain_diff': round(chain.max_pain - chain.spot_price, 2),
            'resistance_1': res_1,
            'resistance_2': res_2,
            'support_1': sup_1,
            'support_2': sup_2,
            'call_oi_total': chain.call_oi_total,
            'put_oi_total': chain.put_oi_total,
            'buildup_summary': {
                'long_buildup': long_buildup_count,
                'short_buildup': short_buildup_count,
                'short_covering': short_covering_count,
                'long_unwinding': long_unwinding_count
            }
        }
