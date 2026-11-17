"""Live refetch of the cited Planet visual COG.

The citation is the visual cog already cited.
The refetch reads that response and stores its status, three headers,
the printed bytes, the printed tiff datetime, and the printed crs name.
It does not store a pixel, a coordinate, a yield, a price, or a trade.
permits_financial_use stays false. Class C stays closed.
"""

import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.planet_visual_cog import (
    CRS_NAME,
    PLANET_VISUAL_COG_URL,
    PRINTED,
    TIFF_DATETIME,
    record_visual_cog,
)
from farm_ontology.policy import CLASS_C_POLICY
from farm_ontology.testing import online_gate

ROOT = Path(__file__).resolve().parents[1]
URL = PLANET_VISUAL_COG_URL


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AssertionError("the refetch does not follow another page")


class PlanetVisualCogTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    @online_gate()
    def test_live_refetch_stores_the_response_header(self):
        saved = record_visual_cog(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["status"], 206)
        self.assertEqual(
            header["headers"]["Content-Type"],
            "image/tiff; application=geotiff; profile=cloud-optimized",
        )
        self.assertEqual(
            header["headers"]["ETag"],
            '"6e91cd4baa2e47346ecc6e0743910dbc-20"',
        )
        self.assertEqual(
            header["headers"]["Last-Modified"],
            "Mon, 09 Nov 2026 17:00:50 GMT",
        )
        self.assertEqual(header["printed"], PRINTED)
        self.assertEqual(header["printed"][:8], "GDAL_STR")
        self.assertTrue(header["printed"].endswith("NO\n "))
        self.assertEqual(header["tiff_datetime"], "2026:11:05 16:24:10")
        self.assertEqual(header["tiff_datetime"], TIFF_DATETIME)
        self.assertEqual(header["crs_name"], "WGS 84 / UTM zone 15S")
        self.assertEqual(header["crs_name"], CRS_NAME)
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        self.assertEqual(header["class_c_policy"], CLASS_C_POLICY)
        self.assertEqual(
            set(header),
            {
                "citation_url",
                "status",
                "headers",
                "printed",
                "tiff_datetime",
                "crs_name",
                "permits_financial_use",
                "class_c_policy",
            },
        )
        self.assertEqual(
            set(header["headers"]),
            {"Content-Type", "ETag", "Last-Modified"},
        )
        request = urllib.request.Request(
            URL,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Range": "bytes=0-4095",
                "Accept": "*/*",
            },
            method="GET",
        )
        opener = urllib.request.build_opener(_NoRedirect)
        with opener.open(request, timeout=60) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(response.geturl(), URL)
            self.assertEqual(
                response.headers.get("Content-Type"),
                header["headers"]["Content-Type"],
            )
            self.assertEqual(response.headers.get("ETag"), header["headers"]["ETag"])
            self.assertEqual(
                response.headers.get("Last-Modified"),
                header["headers"]["Last-Modified"],
            )
            content_range = response.headers.get("Content-Range")
            body = response.read()
        self.assertEqual(body[:4], b"II*\x00")
        self.assertEqual(body[8:191], PRINTED.encode("ascii"))
        self.assertIn(TIFF_DATETIME.encode("ascii"), body)
        self.assertIn(CRS_NAME.encode("ascii"), body)
        self.assertEqual(header["tiff_datetime"].encode("ascii"), TIFF_DATETIME.encode("ascii"))
        self.assertIn(header["crs_name"].encode("ascii"), body)
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        self.assertIn(TIFF_DATETIME, text)
        self.assertIn(CRS_NAME, text)
        self.assertIn(header["citation_url"], text)
        self.assertNotIn("2026-11-05T16:24:10", text)
        self.assertNotIn(str(content_range).split("/")[-1], text)
        for word in (
            "yield",
            "price",
            "trade",
            "Biratori",
            "column",
            "row",
            "band_values",
            "pixel",
            "latitude",
            "longitude",
            "easting",
            "northing",
            "content_length",
            "Content-Length",
            "Content-Range",
            "licence",
            "license",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "planet_visual_cog.py").read_text(
            encoding="utf-8"
        )
        flat = source.replace("\n", " ")
        self.assertIn("The stored tiff datetime is 2026:11:05 16:24:10.", flat)
        self.assertIn("The stored crs name is WGS 84 / UTM zone 15S.", flat)
        self.assertIn("A coordinate is not invented.", flat)
        self.assertIn("A pixel is not stored.", flat)
        self.assertIn("Content-Length is not stored.", flat)
        self.assertIn("Content-Range is not stored.", flat)
        self.assertIn("https://data.source.coop/ is not the citation.", flat)
        self.assertIn("https://www.planet.com/account/ is not the citation.", flat)
        self.assertIn("A trailing slash is not the citation.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("Class C stays closed.", flat)
        self.assertIn("This is not the Biratori field.", flat)
        self.assertIn("It is not a yield.", flat)
        self.assertIn("It is not a price.", flat)
        self.assertIn("It is not a trade.", flat)
        self.assertNotIn(str(content_range).split("/")[-1], source)
        self.assertIn("2026:11:05 16:24:10", source)
        self.assertIn("WGS 84 / UTM zone 15S", source)
        self.assertIn("2026-11-05T16:24:10 is not the printed tiff datetime.", flat)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        with patch(
            "farm_ontology.planet_visual_cog._open",
            side_effect=AssertionError("fetched"),
        ):
            for citation in (None, "", "   "):
                with self.assertRaises(ValueError):
                    record_visual_cog(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
        with patch(
            "farm_ontology.planet_visual_cog._open",
            side_effect=AssertionError("fetched"),
        ):
            for citation in (
                "https://data.source.coop/",
                "https://www.planet.com/account/",
                URL + "/",
                "http://data.source.coop/planet/disasterdata/"
                "galapagos-santa-cruz-floods-2026-10-30/post-event/"
                "planetscope-2026-11-05/items/20261105_162410_82_24d8/"
                "20261105_162410_82_24d8_visual.tif",
                "https://example.com/20261105_162410_82_24d8_visual.tif",
            ):
                with self.assertRaises(ValueError):
                    record_visual_cog(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_yield_price_or_trade_label_writes_nothing(self):
        with patch(
            "farm_ontology.planet_visual_cog._open",
            side_effect=AssertionError("fetched"),
        ):
            for label in ("yield", "Yield", "price", "trade", "biratori", "settlement"):
                with self.assertRaises(ValueError):
                    record_visual_cog(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_financial_use_class_c_and_pixel_write_nothing(self):
        with patch(
            "farm_ontology.planet_visual_cog._open",
            side_effect=AssertionError("fetched"),
        ):
            with self.assertRaises(ValueError):
                record_visual_cog(
                    self.folder, citation_url=URL, permits_financial_use=True
                )
            with self.assertRaises(ValueError):
                record_visual_cog(
                    self.folder, citation_url=URL, class_c_policy="open"
                )
            with self.assertRaises(ValueError):
                record_visual_cog(
                    self.folder,
                    citation_url=URL,
                    column=1,
                    row=1,
                    band_values=[0],
                )
            with self.assertRaises(ValueError):
                record_visual_cog(
                    self.folder,
                    citation_url=URL,
                    latitude=0,
                    longitude=0,
                )
            with self.assertRaises(ValueError):
                record_visual_cog(
                    self.folder,
                    citation_url=URL,
                    easting=1,
                    northing=1,
                )
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_unmatched_response_writes_nothing(self):
        class _Response:
            status = 401
            headers = {"Content-Type": "text/html"}

            def geturl(self):
                return URL

            def read(self):
                return b"<html>login</html>"

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

        with patch(
            "farm_ontology.planet_visual_cog._open",
            return_value=_Response(),
        ):
            with self.assertRaises(ValueError):
                record_visual_cog(self.folder, citation_url=URL)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_planet_visual_cog(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("planet_visual_cog", text)
            self.assertNotIn("20261105_162410_82_24d8", text)
            self.assertNotIn("data.source.coop", text)


if __name__ == "__main__":
    unittest.main()
