import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D, localcontext
from farm_ontology.markets.paper_ledger import FillUnit, PaperFill, PaperLedger, Side

T = datetime(2026, 11, 22, tzinfo=timezone.utc)
def fill(fill_id='f1', **kwargs):
    values = dict(fill_id=fill_id, instrument='soy-cash', side=Side.BUY,
                  quantity_bushels=D('10'), price=D('12.5'),
                  price_unit=FillUnit.USD_PER_BUSHEL, fee_usd=D('1'), filled_at=T)
    values.update(kwargs)
    return PaperFill(**values)

class PaperLedgerTests(unittest.TestCase):
    def test_cash_inventory_fees_and_reconciliation(self):
        ledger = PaperLedger(D('1000'))
        self.assertEqual(ledger.record_fill(fill()).cash_usd, D('874'))
        snap = ledger.record_fill(fill('f2', side=Side.SELL, quantity_bushels=D('4'),
                                       price=D('13'), fee_usd=D('0.5'), filled_at=T+timedelta(seconds=1)))
        self.assertEqual(snap.cash_usd, D('925.5'))
        self.assertEqual(snap.positions_bushels, (('soy-cash', D('6')),))
        self.assertTrue(ledger.reconcile(cash_usd=D('925.5'), positions_bushels={'soy-cash':D('6')}).matches)
        bad = ledger.reconcile(cash_usd=D('924.5'), positions_bushels={'soy-cash':D('5'), 'other':D('2')})
        self.assertEqual(bad.cash_difference_usd, D('-1'))
        self.assertEqual(bad.position_differences_bushels, (('other', D('2')), ('soy-cash', D('-1'))))
        self.assertFalse(bad.matches)

    def test_duplicate_out_of_order_and_failed_fills_are_atomic(self):
        ledger = PaperLedger(D('1000'))
        before = ledger.record_fill(fill())
        for bad in (fill(), fill('f2', filled_at=T-timedelta(seconds=1)),
                    fill('f3', quantity_bushels=D('1000')),
                    fill('f4', side=Side.SELL, quantity_bushels=D('11'))):
            with self.subTest(fill_id=bad.fill_id), self.assertRaises(ValueError):
                ledger.record_fill(bad)
            self.assertEqual(ledger.snapshot(), before)
        self.assertEqual(ledger.record_fill(fill('f3')).fill_count, 2)

    def test_types_units_finite_and_timezone_are_required(self):
        variants = [dict(price=12.5), dict(price=D('NaN')), dict(price=D('0')),
                    dict(quantity_bushels=D('-1')), dict(fee_usd=D('-1')),
                    dict(price_unit='USD/bu'), dict(side='buy'),
                    dict(filled_at=datetime(2026,11,22))]
        for kwargs in variants:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                fill(**kwargs)

    def test_decimal_context_does_not_round_cash_or_quantity(self):
        ledger = PaperLedger(D('1000'))
        with localcontext() as ctx:
            ctx.prec = 5
            result = ledger.record_fill(fill(quantity_bushels=D('0.123456'), price=D('1.234567'), fee_usd=D('0')))
        self.assertEqual(result.cash_usd, D('999.847585296448'))
        self.assertTrue(ledger.reconcile(cash_usd=result.cash_usd, positions_bushels={'soy-cash':D('0.123456')}).matches)

    def test_zero_position_removed_and_no_implicit_execution_interface(self):
        ledger = PaperLedger(D('1000'))
        ledger.record_fill(fill())
        snap = ledger.record_fill(fill('f2', side=Side.SELL))
        self.assertEqual(snap.positions_bushels, ())
        self.assertFalse(hasattr(ledger, 'submit_order'))

if __name__ == '__main__':
    unittest.main()
