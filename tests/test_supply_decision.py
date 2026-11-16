import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.bmkg_prakiraan import BMKG_PRAKIRAAN_URL
from farm_ontology.bmkg_prakiraan import record_series_header as record_bmkg
from farm_ontology.csd_industrial import CSD_INDUSTRIAL_URL
from farm_ontology.csd_industrial import record_series_header as record_csd
from farm_ontology.eia_steo import EIA_STEO_URL
from farm_ontology.eia_steo import record_series_header as record_steo
from farm_ontology.fao_food_price_index import FAO_FOOD_PRICE_INDEX_URL
from farm_ontology.fao_food_price_index import record_series_header as record_fao
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
        steo = record_steo(self.headers, citation_url=EIA_STEO_URL)["header"]
        iea = record_iea(self.headers, citation_url=IEA_OIL_URL)["header"]
        opec = record_opec(self.headers, citation_url=OPEC_ASB_URL)["header"]
        csd = record_csd(self.headers, citation_url=CSD_INDUSTRIAL_URL)["header"]
        return [
            {"subject": "food supply", "header": fao},
            {"subject": "food supply", "header": wasde},
            {"subject": "food supply", "header": bmkg},
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
            if record["header"]["kind"] == "Prakiraan Cuaca":
                self.assertEqual(keys, stored_fields - {"period", "unit"})
                self.assertNotIn("the field was not opened", parsed_decision)
            else:
                self.assertEqual(keys, stored_fields)
            self.assertFalse(record["header"]["permits_financial_use"])

    def test_refused_asks_write_nothing(self):
        records = self._records()
        self.assertIn(
            "Prakiraan Cuaca",
            [record["header"]["kind"] for record in records],
        )
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
