"""Exact Indian NSE Regulatory & Brokerage Tax Calculator."""
from dataclasses import dataclass
from typing import Dict, Any
from nse_system.core.constants import ProductType, InstrumentType

@dataclass
class TradeCostBreakdown:
    """Detailed breakdown of all charges for a trade."""
    turnover: float
    buy_turnover: float
    sell_turnover: float
    brokerage: float
    stt: float
    exchange_charges: float
    gst: float
    sebi_charges: float
    stamp_duty: float
    dp_charges: float
    total_charges: float

    def to_dict(self) -> Dict[str, float]:
        return {
            'Turnover': round(self.turnover, 2),
            'Brokerage': round(self.brokerage, 2),
            'STT': round(self.stt, 2),
            'Exchange Txn Charges': round(self.exchange_charges, 2),
            'GST (18%)': round(self.gst, 2),
            'SEBI Charges': round(self.sebi_charges, 2),
            'Stamp Duty': round(self.stamp_duty, 2),
            'DP Charges': round(self.dp_charges, 2),
            'Total Taxes & Charges': round(self.total_charges, 2)
        }

class NSETaxCalculator:
    """Calculates statutory taxes and broker commissions as per SEBI / NSE rules."""

    BROKERAGE_FLAT = 20.0          # Max ₹20 per order
    BROKERAGE_PCT_INTRADAY = 0.0003 # 0.03%
    BROKERAGE_PCT_DELIVERY = 0.0000 # Zero brokerage for delivery (standard discount broker)

    # Statutory tax rates
    STT_INTRADAY_SELL = 0.00025    # 0.025% on sell side
    STT_DELIVERY_BUY_SELL = 0.001  # 0.1% on buy and sell
    STT_FUTURES_SELL = 0.0002      # 0.02% on sell
    STT_OPTIONS_SELL = 0.001       # 0.1% on sell premium

    EXCHANGE_TURNOVER_EQUITY = 0.0000345 # 0.00345%
    EXCHANGE_TURNOVER_FUT = 0.00002      # 0.002%
    EXCHANGE_TURNOVER_OPT = 0.00053      # 0.053%

    GST_RATE = 0.18  # 18% on Brokerage + Exchange + SEBI
    SEBI_RATE = 0.000001 # ₹10 per Crore (0.0001%)

    STAMP_DUTY_INTRADAY_BUY = 0.00003  # 0.003% on buy
    STAMP_DUTY_DELIVERY_BUY = 0.00015  # 0.015% on buy
    STAMP_DUTY_FUTURES_BUY = 0.00002   # 0.002% on buy
    STAMP_DUTY_OPTIONS_BUY = 0.00003   # 0.003% on buy premium

    DP_CHARGE_DELIVERY_SELL = 15.93    # ₹13.50 + 18% GST

    @classmethod
    def calculate_trade_costs(
        cls,
        buy_price: float,
        sell_price: float,
        quantity: int,
        product_type: ProductType = ProductType.MIS,
        instrument_type: InstrumentType = InstrumentType.EQUITY
    ) -> TradeCostBreakdown:
        """Calculate complete costs for an entry and exit pair."""
        buy_turnover = buy_price * quantity
        sell_turnover = sell_price * quantity
        total_turnover = buy_turnover + sell_turnover

        # 1. Brokerage
        if product_type == ProductType.MIS:
            buy_brok = min(cls.BROKERAGE_FLAT, buy_turnover * cls.BROKERAGE_PCT_INTRADAY)
            sell_brok = min(cls.BROKERAGE_FLAT, sell_turnover * cls.BROKERAGE_PCT_INTRADAY)
            brokerage = buy_brok + sell_brok
        elif product_type == ProductType.CNC:
            brokerage = 0.0
        elif instrument_type in (InstrumentType.OPTIONS_CE, InstrumentType.OPTIONS_PE, InstrumentType.FUTURES):
            brokerage = cls.BROKERAGE_FLAT * 2 # Buy order + Sell order
        else:
            brokerage = cls.BROKERAGE_FLAT * 2

        # 2. STT (Securities Transaction Tax)
        if product_type == ProductType.MIS:
            stt = sell_turnover * cls.STT_INTRADAY_SELL
        elif product_type == ProductType.CNC:
            stt = (buy_turnover + sell_turnover) * cls.STT_DELIVERY_BUY_SELL
        elif instrument_type == InstrumentType.FUTURES:
            stt = sell_turnover * cls.STT_FUTURES_SELL
        elif instrument_type in (InstrumentType.OPTIONS_CE, InstrumentType.OPTIONS_PE):
            stt = sell_turnover * cls.STT_OPTIONS_SELL
        else:
            stt = sell_turnover * cls.STT_INTRADAY_SELL

        # 3. Exchange Transaction Charges
        if instrument_type == InstrumentType.EQUITY:
            exchange_charges = total_turnover * cls.EXCHANGE_TURNOVER_EQUITY
        elif instrument_type == InstrumentType.FUTURES:
            exchange_charges = total_turnover * cls.EXCHANGE_TURNOVER_FUT
        else:
            exchange_charges = total_turnover * cls.EXCHANGE_TURNOVER_OPT

        # 4. SEBI Charges
        sebi_charges = total_turnover * cls.SEBI_RATE

        # 5. Stamp Duty (Only on Buy side)
        if product_type == ProductType.MIS:
            stamp_duty = buy_turnover * cls.STAMP_DUTY_INTRADAY_BUY
        elif product_type == ProductType.CNC:
            stamp_duty = buy_turnover * cls.STAMP_DUTY_DELIVERY_BUY
        elif instrument_type == InstrumentType.FUTURES:
            stamp_duty = buy_turnover * cls.STAMP_DUTY_FUTURES_BUY
        else:
            stamp_duty = buy_turnover * cls.STAMP_DUTY_OPTIONS_BUY

        # 6. DP Charges (only on Delivery sell)
        dp_charges = cls.DP_CHARGE_DELIVERY_SELL if product_type == ProductType.CNC else 0.0

        # 7. GST (18% on Brokerage + Exchange charges + SEBI charges)
        taxable_services = brokerage + exchange_charges + sebi_charges
        gst = taxable_services * cls.GST_RATE

        total_charges = (
            brokerage + stt + exchange_charges + gst + sebi_charges + stamp_duty + dp_charges
        )

        return TradeCostBreakdown(
            turnover=total_turnover,
            buy_turnover=buy_turnover,
            sell_turnover=sell_turnover,
            brokerage=brokerage,
            stt=stt,
            exchange_charges=exchange_charges,
            gst=gst,
            sebi_charges=sebi_charges,
            stamp_duty=stamp_duty,
            dp_charges=dp_charges,
            total_charges=total_charges
        )
