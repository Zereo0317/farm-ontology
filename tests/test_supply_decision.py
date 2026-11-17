import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.bmkg_ikhtisar import BMKG_IKHTISAR_URL
from farm_ontology.bmkg_ikhtisar import record_series_header as record_ikhtisar
from farm_ontology.bmkg_potensi import BMKG_POTENSI_URL
from farm_ontology.bmkg_potensi import record_series_header as record_potensi
from farm_ontology.bmkg_prakiraan import BMKG_PRAKIRAAN_URL
from farm_ontology.bmkg_prakiraan import record_series_header as record_bmkg
from farm_ontology.csd_industrial import CSD_INDUSTRIAL_URL
from farm_ontology.csd_industrial import record_series_header as record_csd
from farm_ontology.eia_steo import EIA_STEO_URL
from farm_ontology.eia_steo import record_series_header as record_steo
from farm_ontology.fao_food_price_index import FAO_FOOD_PRICE_INDEX_URL
from farm_ontology.fao_food_price_index import record_series_header as record_fao
from farm_ontology.jma_daily import JMA_DAILY_URL
from farm_ontology.jma_daily import record_series_header as record_jma_daily
from farm_ontology.jma_three_hourly import JMA_THREE_HOURLY_URL
from farm_ontology.jma_three_hourly import record_series_header as record_three_hourly
from farm_ontology.jma_torrential import JMA_TORRENTIAL_URL
from farm_ontology.jma_torrential import record_series_header as record_torrential
from farm_ontology.jma_precipitation import JMA_PRECIPITATION_URL
from farm_ontology.jma_precipitation import record_series_header as record_precipitation
from farm_ontology.jma_snow import JMA_SNOW_URL
from farm_ontology.jma_snow import record_series_header as record_snow
from farm_ontology.jma_two_week import JMA_TWO_WEEK_URL
from farm_ontology.jma_two_week import record_series_header as record_two_week
from farm_ontology.jma_seasonal import JMA_SEASONAL_URL
from farm_ontology.jma_seasonal import record_series_header as record_seasonal
from farm_ontology.jma_local import JMA_LOCAL_URL
from farm_ontology.jma_local import record_series_header as record_jma
from farm_ontology.iea_oil import IEA_OIL_URL
from farm_ontology.iea_oil import record_series_header as record_iea
from farm_ontology.opec_asb import OPEC_ASB_URL
from farm_ontology.opec_asb import record_series_header as record_opec
from farm_ontology.supply_decision import record_supply_decision
from farm_ontology.usda_wasde import USDA_WASDE_URL
from farm_ontology.usda_wasde import record_series_header as record_wasde

ROOT = Path(__file__).resolve().parents[1]

DECISION = """\
food supply: Food and Agriculture Organization of the United Nations; Food Price Index; kind index. An index is not a quantity of goods. permits_financial_use is false.
food supply: World Agricultural Outlook Board, U.S. Department of Agriculture; World Agricultural Supply and Demand Estimates; kind forecast. A forecast is not a completed harvest. permits_financial_use is false.
food supply: Badan Meteorologi, Klimatologi, dan Geofisika; Prakiraan Cuaca; kind Prakiraan Cuaca. permits_financial_use is false.
food supply: BMKG / Badan Meteorologi, Klimatologi, dan Geofisika; Ikhtisar Cuaca Harian; kind Ikhtisar Cuaca Harian. permits_financial_use is false.
food supply: BMKG / Badan Meteorologi, Klimatologi, dan Geofisika; Potensi Hujan Sepekan ke Depan; kind Potensi Hujan Sepekan ke Depan. permits_financial_use is false.
food supply: Japan Meteorological Agency; Local Information; kind Local Information. permits_financial_use is false.
food supply: Japan Meteorological Agency; Daily Forecasts; kind Daily Forecasts. permits_financial_use is false.
food supply: Japan Meteorological Agency; Distribution/Three-hourly Forecasts; kind Distribution/Three-hourly Forecasts. permits_financial_use is false.
food supply: Japan Meteorological Agency; Two-week Temperature Forecast; kind Two-week Temperature Forecast. permits_financial_use is false.
food supply: Japan Meteorological Agency; Seasonal Forecasts; kind Seasonal Forecasts. permits_financial_use is false.
food supply: Japan Meteorological Agency; Localized Torrential Rain Forecast Map; kind Forecast. A forecast is not a completed harvest. permits_financial_use is false.
food supply: Japan Meteorological Agency; Precipitation Analysis/Forecasts; kind Analysis; Forecasts. An analysis is not a quantity of goods. A forecast is not a completed harvest. permits_financial_use is false.
food supply: Japan Meteorological Agency; Snow Analysis/Forecasts; kind Analysis; Forecasts. An analysis is not a quantity of goods. A forecast is not a completed harvest. permits_financial_use is false.
oil supply: U.S. Energy Information Administration; Short-Term Energy Outlook; kind forecast. A forecast is not a completed harvest. permits_financial_use is false.
oil supply: International Energy Agency ("IEA"); Terms of Use for Non-CC Material; kind Terms. A licence, terms, disclaimer, or methodology header is not a right to trade. permits_financial_use is false.
oil supply: OPEC Secretariat; OPEC Annual Statistical Bulletin (ASB); kind Disclaimer. A licence, terms, disclaimer, or methodology header is not a right to trade. permits_financial_use is false.
manufacturing supply: Census and Statistics Department; Index of Industrial Production for Manufacturing and Waste Management Sectors; kind index. An index is not a quantity of goods. permits_financial_use is false.
farmer: World Agricultural Outlook Board, U.S. Department of Agriculture; World Agricultural Supply and Demand Estimates; kind forecast. administrative_area the published U.S. and world tables; not a farm. A forecast is not a completed harvest. permits_financial_use is false.
A forecast is not a completed harvest. An index is not a quantity of goods. A licence, terms, disclaimer, or methodology header is not a right to trade.
permits_financial_use is false.
"""


class SupplyDecisionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)
        self.headers = Path(self._tmp.name) / "headers"
        self.headers.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def _records(self):
        fao = record_fao(self.headers, citation_url=FAO_FOOD_PRICE_INDEX_URL)["header"]
        wasde = record_wasde(self.headers, citation_url=USDA_WASDE_URL)["header"]
        bmkg = record_bmkg(self.headers, citation_url=BMKG_PRAKIRAAN_URL)["header"]
        ikhtisar = record_ikhtisar(self.headers, citation_url=BMKG_IKHTISAR_URL)["header"]
        potensi = record_potensi(self.headers, citation_url=BMKG_POTENSI_URL)["header"]
        jma = record_jma(self.headers, citation_url=JMA_LOCAL_URL)["header"]
        daily = record_jma_daily(self.headers, citation_url=JMA_DAILY_URL)["header"]
        three = record_three_hourly(self.headers, citation_url=JMA_THREE_HOURLY_URL)["header"]
        two_week = record_two_week(self.headers, citation_url=JMA_TWO_WEEK_URL)["header"]
        seasonal = record_seasonal(self.headers, citation_url=JMA_SEASONAL_URL)["header"]
        torrential = record_torrential(self.headers, citation_url=JMA_TORRENTIAL_URL)["header"]
        precipitation = record_precipitation(
            self.headers, citation_url=JMA_PRECIPITATION_URL
        )["header"]
        snow = record_snow(self.headers, citation_url=JMA_SNOW_URL)["header"]
        steo = record_steo(self.headers, citation_url=EIA_STEO_URL)["header"]
        iea = record_iea(self.headers, citation_url=IEA_OIL_URL)["header"]
        opec = record_opec(self.headers, citation_url=OPEC_ASB_URL)["header"]
        csd = record_csd(self.headers, citation_url=CSD_INDUSTRIAL_URL)["header"]
        return [
            {"subject": "food supply", "header": fao},
            {"subject": "food supply", "header": wasde},
            {"subject": "food supply", "header": bmkg},
            {"subject": "food supply", "header": ikhtisar},
            {"subject": "food supply", "header": potensi},
            {"subject": "food supply", "header": jma},
            {"subject": "food supply", "header": daily},
            {"subject": "food supply", "header": three},
            {"subject": "food supply", "header": two_week},
            {"subject": "food supply", "header": seasonal},
            {"subject": "food supply", "header": torrential},
            {"subject": "food supply", "header": precipitation},
            {"subject": "food supply", "header": snow},
            {"subject": "oil supply", "header": steo},
            {"subject": "oil supply", "header": iea},
            {"subject": "oil supply", "header": opec},
            {"subject": "manufacturing supply", "header": csd},
            {"subject": "farmer", "header": wasde},
        ]

    def test_decision_repeats_stored_kinds(self):
        saved = record_supply_decision(self.folder, records=self._records())
        self.assertEqual(saved["decision"], DECISION)
        self.assertFalse(saved["permits_financial_use"])
        body = (self.folder / saved["file"]).read_text(encoding="utf-8")
        parsed_decision = saved["decision"]
        self.assertIn("kind index.", parsed_decision)
        self.assertIn("kind forecast.", parsed_decision)
        self.assertIn("kind Prakiraan Cuaca.", parsed_decision)
        self.assertIn("kind Ikhtisar Cuaca Harian.", parsed_decision)
        self.assertIn("kind Potensi Hujan Sepekan ke Depan.", parsed_decision)
        self.assertIn("kind Local Information.", parsed_decision)
        self.assertIn("kind Daily Forecasts.", parsed_decision)
        self.assertIn("kind Distribution/Three-hourly Forecasts.", parsed_decision)
        self.assertIn("kind Two-week Temperature Forecast.", parsed_decision)
        self.assertIn("kind Seasonal Forecasts.", parsed_decision)
        self.assertIn("kind Forecast.", parsed_decision)
        self.assertIn("kind Analysis; Forecasts.", parsed_decision)
        self.assertIn("Precipitation Analysis/Forecasts", parsed_decision)
        self.assertIn("kind Analysis; Forecasts.", parsed_decision)
        self.assertIn("Snow Analysis/Forecasts", parsed_decision)
        self.assertIn("An analysis is not a quantity of goods.", parsed_decision)
        self.assertIn("kind Terms.", parsed_decision)
        self.assertIn("kind Disclaimer.", parsed_decision)
        self.assertIn("A forecast is not a completed harvest.", parsed_decision)
        self.assertIn("An index is not a quantity of goods.", parsed_decision)
        self.assertIn(
            "A licence, terms, disclaimer, or methodology header is not a right to trade.",
            parsed_decision,
        )
        self.assertIn("not a farm", parsed_decision)
        self.assertNotIn("public domain", parsed_decision)
        self.assertNotIn("copyright_statement", body)
        self.assertNotIn("yield", parsed_decision)
        self.assertNotIn("hedge", parsed_decision)
        self.assertNotIn("position", parsed_decision)
        stored = __import__("json").loads(body)
        self.assertFalse(stored["permits_financial_use"])
        stored_fields = {
            "publisher",
            "product",
            "period",
            "unit",
            "administrative_area",
            "citation_url",
            "kind",
            "permits_financial_use",
        }
        for record in stored["records"]:
            keys = set(record["header"])
            if record["header"]["kind"] in {
                "Prakiraan Cuaca",
                "Local Information",
                "Ikhtisar Cuaca Harian",
            }:
                self.assertEqual(keys, stored_fields - {"period", "unit"})
                self.assertNotIn("the field was not opened", parsed_decision)
            elif record["header"]["kind"] == "Potensi Hujan Sepekan ke Depan":
                self.assertEqual(keys, stored_fields - {"unit", "administrative_area"})
                self.assertIn("untuk sepekan ke depan", record["header"]["period"])
                self.assertIn(
                    "Periode 17 \u2013 23 November 2026",
                    record["header"]["period"],
                )
                self.assertIn(
                    "Periode 27 Oktober\u20132 November 2026",
                    record["header"]["period"],
                )
                self.assertNotIn("unit", record["header"])
                self.assertNotIn("administrative_area", record["header"])
            elif record["header"]["kind"] == "Distribution/Three-hourly Forecasts":
                self.assertEqual(keys, stored_fields - {"unit", "administrative_area"})
                self.assertIn(
                    "Valid for 06-09 JST, 17 November",
                    record["header"]["period"],
                )
                self.assertIn(
                    "Updated at 05 JST, 17 November 2026",
                    record["header"]["period"],
                )
                self.assertNotIn("unit", record["header"])
                self.assertNotIn("administrative_area", record["header"])
                self.assertNotEqual(record["header"]["kind"], "Forecasts")
            elif record["header"]["kind"] == "Two-week Temperature Forecast":
                self.assertEqual(keys, stored_fields - {"unit", "administrative_area"})
                self.assertIn(
                    "The Two-week Temperature Forecast is issued at 14:30 JST every day.",
                    record["header"]["period"],
                )
                self.assertIn(
                    "five-day average temperatures from eight days ahead",
                    record["header"]["period"],
                )
                self.assertNotIn("unit", record["header"])
                self.assertNotIn("administrative_area", record["header"])
                self.assertNotEqual(record["header"]["kind"], "Forecast")
            elif record["header"]["kind"] == "Seasonal Forecasts":
                self.assertEqual(keys, stored_fields - {"unit", "administrative_area"})
                self.assertIn(
                    "Issued at 14:30 JST, 12 Nov. 2026",
                    record["header"]["period"],
                )
                self.assertIn("11/14-12/13", record["header"]["period"])
                self.assertIn("up to six months ahead", record["header"]["period"])
                self.assertNotIn("unit", record["header"])
                self.assertNotIn("administrative_area", record["header"])
                self.assertNotEqual(record["header"]["kind"], "Forecasts")
            elif record["header"]["kind"] == "Forecast":
                self.assertEqual(keys, stored_fields - {"administrative_area"})
                self.assertIn("08:50 JST, 17 November 2026", record["header"]["period"])
                self.assertIn("next 3 h", record["header"]["period"])
                self.assertIn("every 10 minutes", record["header"]["period"])
                self.assertIn("up to 6 hours ahead", record["header"]["period"])
                self.assertIn("from 7 to 15 hours ahead", record["header"]["period"])
                self.assertIn("every hour", record["header"]["period"])
                self.assertEqual(record["header"]["unit"], "300 km; 1 km; 5 km")
                self.assertNotIn("administrative_area", record["header"])
                self.assertNotEqual(
                    record["header"]["kind"],
                    record["header"]["product"],
                )
            elif record["header"]["kind"] == "Analysis; Forecasts":
                self.assertEqual(keys, stored_fields - {"administrative_area"})
                if record["header"]["product"] == "Precipitation Analysis/Forecasts":
                    self.assertIn("1-hour. precipitation", record["header"]["period"])
                    self.assertIn(
                        "09:00 JST, 17 November 2026",
                        record["header"]["period"],
                    )
                    self.assertEqual(record["header"]["unit"], "mm/h")
                elif record["header"]["product"] == "Snow Analysis/Forecasts":
                    self.assertIn("08 JST, 17 November 2026", record["header"]["period"])
                    self.assertIn(
                        "periods of 3, 6, 12, 24, 48 and 72 hours",
                        record["header"]["period"],
                    )
                    self.assertEqual(record["header"]["unit"], "cm; 300 km")
                    self.assertNotIn("snowfall", record["header"]["period"])
                else:
                    self.fail(f"unexpected product {record['header']['product']}")
                self.assertNotEqual(
                    record["header"]["product"],
                    "Localized Torrential Rain Forecast Map",
                )
                self.assertNotIn("administrative_area", record["header"])
                self.assertNotEqual(record["header"]["kind"], "Forecasts")
                self.assertNotEqual(record["header"]["kind"], "Analysis")
            elif record["header"]["kind"] == "Daily Forecasts":
                self.assertEqual(keys, stored_fields - {"unit"})
                self.assertIn(
                    "Daily weather forecasts for the week ahead in map form",
                    record["header"]["period"],
                )
                self.assertIn(
                    "Issued at 22 JST, 16 Nov. 2026",
                    record["header"]["period"],
                )
                self.assertNotIn("unit", record["header"])
                self.assertNotIn("the field was not opened", parsed_decision)
            else:
                self.assertEqual(keys, stored_fields)
            self.assertFalse(record["header"]["permits_financial_use"])

    def test_refused_asks_write_nothing(self):
        records = self._records()
        kinds = [record["header"]["kind"] for record in records]
        self.assertIn("Prakiraan Cuaca", kinds)
        self.assertIn("Ikhtisar Cuaca Harian", kinds)
        self.assertIn("Potensi Hujan Sepekan ke Depan", kinds)
        self.assertIn("Local Information", kinds)
        self.assertIn("Daily Forecasts", kinds)
        self.assertIn("Distribution/Three-hourly Forecasts", kinds)
        self.assertIn("Two-week Temperature Forecast", kinds)
        self.assertIn("Seasonal Forecasts", kinds)
        self.assertIn("Forecast", kinds)
        self.assertIn("Analysis; Forecasts", kinds)
        out = self.folder / "out"
        out.mkdir()
        for ask in (
            "yield",
            "price",
            "trade",
            "hedge",
            "position",
            "Yield",
            "PRICE",
            "Trade",
            "Hedge",
            "Position",
        ):
            with self.assertRaises(ValueError):
                record_supply_decision(out, records=records, ask=ask)
        self.assertEqual(list(out.iterdir()), [])

    def test_missing_field_or_financial_use_writes_nothing(self):
        records = self._records()
        out = self.folder / "out"
        out.mkdir()
        broken = [dict(record) for record in records]
        broken[0] = {
            "subject": "food supply",
            "header": {key: value for key, value in broken[0]["header"].items() if key != "kind"},
        }
        with self.assertRaises(ValueError):
            record_supply_decision(out, records=broken)
        granted = [dict(record) for record in records]
        granted[0] = {
            "subject": "food supply",
            "header": {**granted[0]["header"], "permits_financial_use": True},
        }
        with self.assertRaises(ValueError):
            record_supply_decision(out, records=granted)
        self.assertEqual(list(out.iterdir()), [])

    def test_field_save_does_not_ingest_supply_decision(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("supply_decision", text)
        source = (ROOT / "farm_ontology" / "supply_decision.py").read_text(encoding="utf-8")
        self.assertNotIn("urllib", source)
        self.assertNotIn("urlopen", source)
