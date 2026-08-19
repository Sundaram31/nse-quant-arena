"""Position Sizing Algorithms (Fixed Fractional, ATR Volatility, Fixed Quantity)."""
import math
from typing import Optional
from nse_system.data.symbols import get_symbol_info

class PositionSizer:
    """Calculates optimal order quantity considering NSE lot sizes and portfolio risk parameters."""

    @staticmethod
    def calculate_quantity(
        capital: float,
        price: float,
        stop_loss: Optional[float] = None,
        risk_per_trade_pct: float = 0.01,  # 1% risk per trade
        symbol: str = '',
        atr: Optional[float] = None,
        method: str = 'RISK_BASED'         # 'RISK_BASED', 'CAPITAL_PCT', 'FIXED'
    ) -> int:
        """Compute lot-adjusted position quantity."""
        sym_info = get_symbol_info(symbol)
        lot_size = sym_info.lot_size if sym_info.lot_size > 0 else 1

        if price <= 0:
            return lot_size

        if method == 'RISK_BASED' and stop_loss is not None and stop_loss > 0:
            risk_per_share = abs(price - stop_loss)
            if risk_per_share <= 0:
                risk_per_share = price * 0.01
            risk_amount = capital * risk_per_trade_pct
            raw_qty = int(risk_amount / risk_per_share)
        elif method == 'ATR' and atr is not None and atr > 0:
            risk_amount = capital * risk_per_trade_pct
            raw_qty = int(risk_amount / (1.5 * atr))
        else:
            # Simple capital percentage allocation (e.g. 10% capital per trade with 5x MIS leverage)
            allocation = capital * 0.20 * 5.0
            raw_qty = int(allocation / price)

        # For cash equities, lot size is 1. Only enforce lot size multiple for Indices / F&O
        if sym_info.is_index:
            raw_qty = max(lot_size, (raw_qty // lot_size) * lot_size)
        else:
            raw_qty = max(1, raw_qty)
        return max(1, raw_qty)
