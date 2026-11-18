"""Sprint-J2 guard: the pitch pages' copy (web/lib/pitch-copy.ts).

Mirrors test_i18n_schema.ReportCopyGuardTests: five first-class locales,
matching top-level key sets, per-array cardinality parity across locales,
native-script checks (traditional zh-TW / simplified zh-CN / Thai glyphs),
tone anchors per page (investor on P2/P4, farmer on P3), and page files that
carry no hardcoded prose.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
REQUIRED_PITCH_LOCALES = ["zh-TW", "zh-CN", "en", "ja", "th"]


class PitchCopyGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (WEB / "lib" / "pitch-copy.ts").read_text(encoding="utf-8")
        # Template placeholders never contain nested braces here; strip them
        # so brace balancing sees structure, not interpolations.
        cls.clean = re.sub(r"\$\{[^{}]*\}", "EXPR", raw)

    def _balanced(self, text: str, open_pos: int, open_ch: str, close_ch: str):
        depth = 0
        for j in range(open_pos, len(text)):
            if text[j] == open_ch:
                depth += 1
            elif text[j] == close_ch:
                depth -= 1
                if depth == 0:
                    return open_pos + 1, j
        raise AssertionError(f"unbalanced {open_ch}{close_ch} at {open_pos}")

    def _locale_slice(self, locale: str) -> str:
        token = f'"{locale}": {{' if "-" in locale else f"{locale}: {{"
        block = self.clean[self.clean.find("export const pitchCopy"):]
        lm = block.find(token)
        self.assertGreaterEqual(lm, 0, f"{locale} dict missing from pitchCopy")
        start, end = self._balanced(block, block.index("{", lm), "{", "}")
        return block[start:end]

    def _sub_object(self, locale_slice: str, key: str) -> str:
        km = re.search(rf"\n\s+{key}: \{{", locale_slice)
        self.assertIsNotNone(km, f"{key} object missing")
        start, end = self._balanced(locale_slice, km.end() - 1, "{", "}")
        return locale_slice[start:end]

    # ---- presence & parity -------------------------------------------------

    def test_all_five_locales_present_with_full_structure(self):
        sections = ("p1", "p2", "p3", "p4")
        mins = {"p1": 18, "p2": 11, "p3": 14, "p4": 16}
        baselines: dict[str, set[str]] = {}
        for locale in REQUIRED_PITCH_LOCALES:
            keys = set(re.findall(r"^\s{4}(p[1-4]):", self._locale_slice(locale), re.M))
            self.assertEqual(keys, {"p1", "p2", "p3", "p4"}, f"{locale} missing pitch sections")
            for section in sections:
                block = self._sub_object(self._locale_slice(locale), section)
                got = set(re.findall(r"^\s{6}([a-zA-Z][a-zA-Z0-9]*):", block, re.M))
                self.assertGreaterEqual(
                    len(got), mins[section], f"{locale}.{section} shrank: {sorted(got)}"
                )
                if locale == "zh-TW":
                    baselines[section] = got
                else:
                    self.assertEqual(
                        got,
                        baselines[section],
                        f"{locale}.{section} diverges from zh-TW shape",
                    )

    def test_key_arrays_have_identical_cardinality_across_locales(self):
        cases = {
            "loop": "p1",
            "families": "p1",
            "ladder": "p1",
            "walk": "p1",
            "algos": "p1",
            "notYet": "p1",
            "glossary": "p1",
            "have": "p2",
            "missing": "p2",
            "bring": "p3",
            "checklist": "p3",
            "rules": "p3",
            "proofs": "p4",
            "perf": "p4",
            "risks": "p4",
        }
        for array_name, section in cases.items():
            counts = {}
            for locale in REQUIRED_PITCH_LOCALES:
                block = self._sub_object(self._locale_slice(locale), section)
                am = re.search(rf"\n\s+{array_name}: \[", block)
                self.assertIsNotNone(am, f"{section}.{array_name} missing in {locale}")
                start, end = self._balanced(block, am.end() - 1, "[", "]")
                body = block[start:end]
                counts[locale] = len(re.findall(r"\n\s+(?:\{|glyph:|name:|term:|label:|num:|id:|\")", body))
            self.assertEqual(len(set(counts.values())), 1, f"{section}.{array_name} parity broken: {counts}")

    # ---- locale authenticity ----------------------------------------------

    def test_scripts_look_native(self):
        zh_tw = self._locale_slice("zh-TW")
        zh_cn = self._locale_slice("zh-CN")
        # simplified-only chars must NOT appear in zh-TW; vice versa on the anchors
        for ch in ("电", "汉", "说", "记"):
            self.assertNotIn(ch, zh_tw, f"zh-TW leaked simplified '{ch}'")
        for ch in ("電", "帳", "說", "記"):
            self.assertIn(ch, zh_tw)
            self.assertNotIn(ch, zh_cn, f"zh-CN leaked traditional '{ch}'")
        th = self._locale_slice("th")
        self.assertRegex(th, r"[ก-๛]{4,}")

    def test_en_is_real_prose_not_ts_template_leak(self):
        en = self._locale_slice("en")
        for token in (" tư ", " 支持", "レ", "の", "が"):
            self.assertNotIn(token, en)

    # ---- tone anchors (card mandate) ---------------------------------------

    def test_framer_tone_on_fieldday_and_engineer_honesty_marks(self):
        th = self._locale_slice("th")
        self.assertIn("วันลงของจริง", th)  # farmer-warm page title in Thai
        en = self._locale_slice("en")
        self.assertIn("your field", en)  # farmer-direct phrasing
        # Engineer-honest marks across every locale's P1 "not yet" section.
        for locale in REQUIRED_PITCH_LOCALES:
            p1 = self._sub_object(self._locale_slice(locale), "p1")
            nm = re.search(r"\n\s+notYetTitle: \"([^\"]+)\"", p1)
            self.assertIsNotNone(nm, f"{locale} missing notYetTitle")

    def test_investor_tone_markers_on_p2_p4(self):
        for locale in REQUIRED_PITCH_LOCALES:
            p2 = self._sub_object(self._locale_slice(locale), "p2")
            p4 = self._sub_object(self._locale_slice(locale), "p4")
            for section, needle in ((p2, "$/bu"), (p4, "1,686")):
                self.assertIn(needle, section, f"{locale} lost an investor anchor")

    def test_breached_is_cited_in_every_locale(self):
        for locale in REQUIRED_PITCH_LOCALES:
            p4 = self._sub_object(self._locale_slice(locale), "p4")
            bm = re.search(r"breachedTitle: \"([^\"]+)\"", p4)
            self.assertIsNotNone(bm, f"{locale} missing breachedTitle")
            self.assertIn("BREACHED", bm.group(1), f"{locale} lost the honest verdict")

    # ---- pages ship no hardcoded prose --------------------------------------

    def test_pitch_pages_import_copy_not_literals(self):
        pitch_dir = WEB / "app" / "pitch"
        for page in ("architecture", "data", "fieldday", "reliable"):
            text = (pitch_dir / page / "page.tsx").read_text(encoding="utf-8")
            self.assertIn("pitchCopy", text)
            self.assertNotRegex(text, r"h1>\s*[\u4e00-\u9fff]")
        chrome = (pitch_dir / "chrome.tsx").read_text(encoding="utf-8")
        self.assertIn("pitchCopy", chrome)

    def test_report_and_livez_cross_links_exist(self):
        chrome = (WEB / "app" / "pitch" / "chrome.tsx").read_text(encoding="utf-8")
        self.assertIn("/report/biratori-1119", chrome)
        self.assertIn("/livez", chrome)


if __name__ == "__main__":
    unittest.main()
