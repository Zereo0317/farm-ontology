"""An agent can read a stored header and receive its stored kind."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.bps_manufacturing_index import BPS_MANUFACTURING_INDEX_URL
from farm_ontology.bps_manufacturing_index import record_series_header as record_bps
from farm_ontology.ecmwf_open_data import ECMWF_OPEN_DATA_URL
from farm_ontology.ecmwf_open_data import record_series_header as record_ecmwf
from farm_ontology.gfs_forecast import GFS_FORECAST_URL
from farm_ontology.gfs_forecast import record_series_header as record_gfs
from farm_ontology.header_schema import (
    FORECAST_SENTENCE,
    INDEX_SENTENCE,
    STORED_HEADER_SCHEMA,
    STORED_KIND_SCHEMA,
    read_stored_header,
)
from farm_ontology.mcp_stdio import TOOLS, call_tool
from farm_ontology.page_io import dispatch

ROOT = Path(__file__).resolve().parents[1]


def _load(folder, saved):
    return json.loads((folder / saved["file"]).read_text(encoding="utf-8"))


class HeaderSchemaTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _stored(self, header):
        result = read_stored_header(header)
        self.assertEqual(set(result), {"kind", "permits_financial_use", "statement"})
        self.assertFalse(result["permits_financial_use"])
        self.assertEqual(
            result["statement"],
            f"{header['kind']}. {FORECAST_SENTENCE} {INDEX_SENTENCE}",
        )
        for key in ("yield", "price", "trade"):
            self.assertNotIn(key, result)
        return result

    def test_stored_headers_return_their_kinds(self):
        ecmwf = _load(self.folder, record_ecmwf(self.folder, citation_url=ECMWF_OPEN_DATA_URL))
        gfs = _load(self.folder, record_gfs(self.folder, citation_url=GFS_FORECAST_URL))
        bps = _load(self.folder, record_bps(self.folder, citation_url=BPS_MANUFACTURING_INDEX_URL))
        self.assertEqual(self._stored(ecmwf)["kind"], "Open data")
        self.assertEqual(self._stored(gfs)["kind"], "Global Forecast System")
        self.assertEqual(self._stored(bps)["kind"], "index")
        self.assertIn("copyright_notice", bps)
        self.assertNotIn("copyright_notice", self._stored(bps))
        forecast = dict(ecmwf)
        forecast["kind"] = "forecast"
        self.assertEqual(self._stored(forecast)["kind"], "forecast")
        self.assertIn(FORECAST_SENTENCE, self._stored(forecast)["statement"])
        self.assertIn(INDEX_SENTENCE, self._stored(bps)["statement"])

    def test_mcp_and_page_return_the_same_kind(self):
        header = _load(self.folder, record_gfs(self.folder, citation_url=GFS_FORECAST_URL))
        tool = call_tool("read_stored_header", header)
        self.assertFalse(tool["isError"])
        body = json.loads(tool["content"][0]["text"])
        page = dispatch({"op": "read_header", "header": header})
        self.assertEqual(body, page)
        self.assertEqual(body["kind"], "Global Forecast System")
        self.assertFalse(body["permits_financial_use"])
        schema = dispatch({"op": "schema"})
        self.assertEqual(schema["stored_header"], STORED_HEADER_SCHEMA)
        self.assertEqual(schema["stored_kind"], STORED_KIND_SCHEMA)
        self.assertIs(schema["stored_kind"]["properties"]["permits_financial_use"]["const"], False)
        self.assertIn(FORECAST_SENTENCE, schema["read_header"]["description"])
        self.assertIn(INDEX_SENTENCE, schema["read_header"]["description"])
        listed = {tool["name"]: tool for tool in TOOLS}
        exposed = listed["read_stored_header"]
        self.assertEqual(exposed["inputSchema"], STORED_HEADER_SCHEMA)
        self.assertEqual(exposed["outputSchema"], STORED_KIND_SCHEMA)
        for key in ("yield", "price", "trade"):
            self.assertNotIn(key, exposed["inputSchema"]["properties"])
            self.assertNotIn(key, exposed["outputSchema"]["properties"])

    def test_refused_keys_and_financial_use_add_nothing(self):
        header = _load(self.folder, record_ecmwf(self.folder, citation_url=ECMWF_OPEN_DATA_URL))
        before = sorted(path.name for path in self.folder.iterdir())
        for key, value in (
            ("yield", 1),
            ("price", 1),
            ("trade", 1),
            ("permits_financial_use", True),
        ):
            attempt = dict(header)
            attempt[key] = value
            with self.assertRaises(ValueError):
                read_stored_header(attempt)
            with self.assertRaises(ValueError):
                dispatch({"op": "read_header", "header": attempt})
            refused = call_tool("read_stored_header", attempt)
            self.assertTrue(refused["isError"])
        self.assertEqual(sorted(path.name for path in self.folder.iterdir()), before)
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("ecmwf_open_data", text)
            self.assertNotIn("gfs_forecast", text)
            self.assertNotIn("bps_manufacturing_index", text)
            self.assertNotIn("supply_decision", text)


if __name__ == "__main__":
    unittest.main()
