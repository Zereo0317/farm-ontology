import hashlib
import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from farm_ontology.markets.research_capture import (
    CaptureManifest, QuoteUnit, read_capture,
)

CAPTURED = datetime(2026, 11, 20, tzinfo=timezone.utc)
DATA = (b'session_date,close,source_published_at\n'
        b'2021-10-05,1250.50,2021-10-05T21:00:00Z\n')

def manifest(data=DATA, **kwargs):
    values = dict(source_url='https://provider.example/soy.csv', instrument='ZS',
                  quote_unit=QuoteUnit.USD_CENTS_PER_BUSHEL, captured_at=CAPTURED,
                  sha256=hashlib.sha256(data).hexdigest())
    values.update(kwargs)
    return CaptureManifest(**values)

class ResearchCaptureTests(unittest.TestCase):
    def test_cents_convert_and_no_historical_lookahead(self):
        result = read_capture(manifest(), DATA)
        self.assertEqual(result.rows[0].close_usd_per_bushel, Decimal('12.505'))
        self.assertEqual(result.known_at(CAPTURED - timedelta(microseconds=1)), ())
        self.assertEqual(result.known_at(CAPTURED), result.rows)
        self.assertFalse(result.permits_financial_use)

    def test_dollar_units_do_not_convert(self):
        data = DATA.replace(b'1250.50', b'12.505')
        result = read_capture(manifest(data, quote_unit=QuoteUnit.USD_PER_BUSHEL), data)
        self.assertEqual(result.rows[0].close_usd_per_bushel, Decimal('12.505'))

    def test_unknown_units_and_hash_mismatch_refuse(self):
        with self.assertRaises(ValueError):
            manifest(quote_unit='USD/bu')
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            read_capture(manifest(), DATA.replace(b'1250.50', b'1251.50'))

    def test_naive_dates_and_late_publication_fail(self):
        with self.assertRaises(ValueError):
            manifest(captured_at=datetime(2026,11,20))
        for stamp in (b'2021-10-05T21:00:00', b'2026-11-21T00:00:00Z'):
            data = DATA.replace(b'2021-10-05T21:00:00Z', stamp)
            with self.assertRaises(ValueError):
                read_capture(manifest(data), data)
        with self.assertRaises(ValueError):
            read_capture(manifest(), DATA).known_at(datetime(2021,10,5))

    def test_malformed_nonfinite_and_duplicate_rows_refuse(self):
        samples = [DATA.replace(b'1250.50', b'NaN'),
                   DATA.replace(b'1250.50', b'Infinity'),
                   DATA + b'2021-10-05,1251,2021-10-05T21:00:00Z\n',
                   DATA.replace(b'source_published_at', b'published'),
                   DATA.replace(b'2021-10-05T21:00:00Z', b'2021-10-04T00:00:00Z')]
        for data in samples:
            with self.subTest(data=data), self.assertRaises(ValueError):
                read_capture(manifest(data), data)

if __name__ == '__main__':
    unittest.main()
