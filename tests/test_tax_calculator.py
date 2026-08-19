"""Unit tests for NSE Tax and Brokerage Calculator."""
import unittest
from nse_system.core.tax_calculator import NSETaxCalculator
from nse_system.core.constants import ProductType, InstrumentType

class TestNSETaxCalculator(unittest.TestCase):

    def test_intraday_mis_charges(self):
        # 100 shares of RELIANCE bought at 3000 and sold at 3050
        breakdown = NSETaxCalculator.calculate_trade_costs(
            buy_price=3000.0,
            sell_price=3050.0,
            quantity=100,
            product_type=ProductType.MIS,
            instrument_type=InstrumentType.EQUITY
        )
        self.assertEqual(breakdown.buy_turnover, 300000.0)
        self.assertEqual(breakdown.sell_turnover, 305000.0)
        self.assertEqual(breakdown.turnover, 605000.0)
        # Brokerage max flat 20 each side = 40
        self.assertEqual(breakdown.brokerage, 40.0)
        # STT 0.025% on sell (305000 * 0.00025 = 76.25)
        self.assertAlmostEqual(breakdown.stt, 76.25, places=2)
        # Total charges should be positive
        self.assertGreater(breakdown.total_charges, 120.0)

    def test_delivery_cnc_charges(self):
        breakdown = NSETaxCalculator.calculate_trade_costs(
            buy_price=1000.0,
            sell_price=1100.0,
            quantity=50,
            product_type=ProductType.CNC,
            instrument_type=InstrumentType.EQUITY
        )
        self.assertEqual(breakdown.brokerage, 0.0)
        self.assertGreater(breakdown.dp_charges, 0.0)
        self.assertGreater(breakdown.stt, 0.0)

if __name__ == '__main__':
    unittest.main()
