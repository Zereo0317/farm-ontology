import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.fieldtest.sites import SITES, SiteSpec, get_site

EXPECTED_IDS = (
    "biratori-hidaka",
    "obihiro-tokachi",
    "nakafurano-kamikawa",
    "nemuro-hanasaki",
    "tsuruoka-shonai",
)


class SitesRegistryTests(unittest.TestCase):
    def test_five_sites_with_exact_ids(self):
        self.assertEqual([site.site_id for site in SITES], list(EXPECTED_IDS))

    def test_biratori_is_the_campaign_anchor(self):
        site = get_site("biratori-hidaka")
        self.assertEqual((site.latitude, site.longitude), (42.7018, 142.4071))
        self.assertFalse(site.is_control)

    def test_tsuruoka_is_the_only_control(self):
        controls = [site for site in SITES if site.is_control]
        self.assertEqual([site.site_id for site in controls], ["tsuruoka-shonai"])

    def test_coordinates_in_japan_bounds(self):
        for site in SITES:
            self.assertTrue(30 <= site.latitude <= 46, site.site_id)
            self.assertTrue(128 <= site.longitude <= 146, site.site_id)

    def test_sow_window_is_midmay_earlyjune_and_tagged(self):
        for site in SITES:
            self.assertLessEqual(
                "05-10", site.sow_window_start_md, site.site_id
            )
            self.assertGreaterEqual(
                "06-10", site.sow_window_end_md, site.site_id
            )
            self.assertTrue(
                any("SOW-HOKKAIDO" in tag for tag in site.verify_tags),
                site.site_id,
            )
            start, end = site.sow_window_2027
            self.assertTrue(start.startswith("2027-05-"), (site.site_id, start))
            self.assertTrue(end.startswith("2027-06-"), (site.site_id, end))

    def test_gdd_bands_ordered_and_tagged(self):
        for site in SITES:
            self.assertLess(
                site.season_gdd_band_low, site.season_gdd_band_high, site.site_id
            )
            self.assertGreater(site.season_gdd_band_low, 0.0, site.site_id)
            self.assertGreater(site.season_gdd_band_high, 2100.0 * 0.99, site.site_id)
            self.assertTrue(
                any("GDD-SANITY-BAND" in tag for tag in site.verify_tags),
                site.site_id,
            )

    def test_hokkaido_gdd_ceiling_below_control_floor_variance(self):
        """Nemuro's cool band must not swallow the Shonai control's floor."""
        nemuro = get_site("nemuro-hanasaki")
        control = get_site("tsuruoka-shonai")
        self.assertLess(
            nemuro.season_gdd_band_high,
            control.season_gdd_band_high,
        )

    def test_jma_blocks_resolved_or_explicit_gap(self):
        for site in SITES:
            if site.jma_block is None:
                self.assertIn(
                    "verify", site.jma_block_note.lower(), site.site_id
                )
            else:
                self.assertRegex(site.jma_block, r"\A[0-9]{4}\Z", site.site_id)

    def test_2026_sowing_defaults_inside_each_window(self):
        for site in SITES:
            month_day = site.sow_default_2026[5:10]
            self.assertTrue(
                site.sow_window_start_md <= month_day <= site.sow_window_end_md,
                (site.site_id, month_day),
            )

    def test_get_site_unknown_raises_and_spec_frozen(self):
        with self.assertRaises(KeyError):
            get_site("atlantis")
        spec = get_site("obihiro-tokachi")
        with self.assertRaises(AttributeError):
            spec.latitude = 0.0  # type: ignore[misc]

    def test_specs_do_not_leak_changed_fields(self):
        import dataclasses

        for site in SITES:
            fields = {item.name for item in dataclasses.fields(site)}
            self.assertLessEqual(
                {
                    "site_id",
                    "label",
                    "latitude",
                    "longitude",
                    "is_control",
                    "sow_window_start_md",
                    "sow_window_end_md",
                    "season_gdd_band_low",
                    "season_gdd_band_high",
                    "jma_block",
                    "sow_default_2026",
                    "verify_tags",
                },
                fields,
            )


if __name__ == "__main__":
    unittest.main()
