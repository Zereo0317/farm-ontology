import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.planet_scene_pixel import PLANET_SCENE_PIXEL_URL, record_scene_pixel

ROOT = Path(__file__).resolve().parents[1]
URL = PLANET_SCENE_PIXEL_URL


class PlanetScenePixelTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_stores_one_scene_pixel(self):
        saved = record_scene_pixel(self.folder, citation_url=URL)
        header = saved["header"]
        self.assertEqual(header["item_id"], "20261105_162410_82_24d8")
        self.assertEqual(header["datetime"], "2026-11-05T16:24:10.823737Z")
        self.assertEqual(header["citation_url"], URL)
        self.assertEqual(header["column"], 6260)
        self.assertEqual(header["row"], 4454)
        self.assertEqual(header["band_values"], [109, 130, 113, 255])
        self.assertEqual(
            header["sample_order"],
            ["red", "green", "blue", "unassociated_alpha"],
        )
        self.assertEqual(
            list(zip(header["sample_order"], header["band_values"])),
            [
                ("red", 109),
                ("green", 130),
                ("blue", 113),
                ("unassociated_alpha", 255),
            ],
        )
        self.assertEqual(header["licence"], "CC-BY-NC-4.0")
        self.assertFalse(header["permits_financial_use"])
        self.assertEqual(header["class_c_policy"], "closed")
        self.assertEqual(
            set(header),
            {
                "item_id",
                "datetime",
                "citation_url",
                "column",
                "row",
                "band_values",
                "sample_order",
                "licence",
                "permits_financial_use",
                "class_c_policy",
            },
        )
        text = (self.folder / saved["file"]).read_text(encoding="utf-8")
        for word in (
            "2026:11:05 16:24:10",
            "content_length",
            "Biratori",
            "yield",
            "price",
            "trade",
            "42.7018152",
            "license",
        ):
            self.assertNotIn(word, text, word)
        source = (ROOT / "farm_ontology" / "planet_scene_pixel.py").read_text(encoding="utf-8")
        flat = source.replace("\n", " ")
        self.assertIn("The tiff datetime is not the stored datetime.", flat)
        self.assertIn("https://data.source.coop/ is not the citation.", flat)
        self.assertIn("https://www.planet.com/account/ is not the citation.", flat)
        self.assertIn("A trailing slash is not the citation.", flat)
        self.assertIn("CC-BY-NC-4.0 does not set financial use to true.", flat)
        self.assertIn("permits_financial_use stays false.", flat)
        self.assertIn("Class C stays closed.", flat)
        self.assertIn("It is not the Biratori field.", flat)
        self.assertIn("It is not a yield.", flat)
        self.assertIn("It is not a price.", flat)
        self.assertIn("It is not a trade.", flat)
        self.assertIn("content_length is not stored.", flat)
        self.assertNotIn("164604031", source)
        self.assertEqual(len(list(self.folder.iterdir())), 1)

    def test_missing_citation_writes_nothing(self):
        for citation in (None, "", "   "):
            with self.assertRaises(ValueError):
                record_scene_pixel(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_other_citation_writes_nothing(self):
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
                record_scene_pixel(self.folder, citation_url=citation)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_yield_label_writes_nothing(self):
        for label in ("yield", "Yield", "YIELD", "price", "Price"):
            with self.assertRaises(ValueError):
                record_scene_pixel(self.folder, citation_url=URL, label=label)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_trade_label_writes_nothing(self):
        for label in ("trade", "Trade", "TRADE", "completed harvest", "biratori"):
            with self.assertRaises(ValueError):
                record_scene_pixel(self.folder, citation_url=URL, label=label)
        with self.assertRaises(ValueError):
            record_scene_pixel(self.folder, citation_url=URL, permits_financial_use=True)
        with self.assertRaises(ValueError):
            record_scene_pixel(self.folder, citation_url=URL, class_c_policy="open")
        with self.assertRaises(ValueError):
            record_scene_pixel(self.folder, citation_url=URL, column=1, row=1, band_values=[0])
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_field_save_does_not_ingest_planet_scene_pixel(self):
        for name in ("record.py", "page_io.py", "mcp_stdio.py"):
            text = (ROOT / "farm_ontology" / name).read_text(encoding="utf-8")
            self.assertNotIn("planet_scene_pixel", text)
            self.assertNotIn("20261105_162410_82_24d8", text)
            self.assertNotIn("data.source.coop", text)


if __name__ == "__main__":
    unittest.main()
