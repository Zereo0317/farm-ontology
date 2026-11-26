# -*- coding: utf-8 -*-
"""Hermetic UA-invariants: landing glyph rounds, photo-policy, pitch
proof-cell count. Source-parsing only; CI-cheap, no HTTP."""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
LANDING_COPY = ROOT / "landing" / "src" / "lib" / "copy"
PITCH_COPY = ROOT / "web" / "lib" / "pitch-copy.ts"

LOCALES = ("zh-TW", "zh-CN", "en", "ja", "th")

GLYPH_PROBES = {
    "zh-TW": ["農", "報", "帳", "傳統"],
    "zh-CN": ["农", "报", "账", "台账"],
    "ja": ["の", "圃場", "ほ場", "サイン"],
    "th": ["แปลง", "ข้อมูล", "ฟาร์ม", "สรุป"],
    "en": [" the ", " and "],
}

BANNED_MARKETING_WORDS = (
    "AI 生成",
    "AI-generated",
    "illustrative",
    "示意圖",
    "generated image",
    "生成写真",
)


class LandingGlyphRounds(unittest.TestCase):
    def test_every_locale_carries_its_own_script(self):
        for locale in LOCALES:
            text = (LANDING_COPY / f"{locale}.ts").read_text(encoding="utf-8")
            hits = [needle for needle in GLYPH_PROBES[locale] if needle in text]
            self.assertGreaterEqual(
                len(hits), 2, f"{locale}: too few native glyphs ({hits})"
            )

    def test_no_locale_bleeds_foreign_script_into_body_keys(self):
        cn_marks = ["简", "记", "帐"]
        tw_text = (LANDING_COPY / "zh-TW.ts").read_text(encoding="utf-8")
        leaked = [mark for mark in cn_marks if mark in tw_text]
        self.assertEqual(leaked, [], f"zh-TW leaked simplified glyphs: {leaked}")


class PhotoPolicyInvariants(unittest.TestCase):
    def test_landing_source_references_no_uncertified_photos(self):
        page = (
            ROOT / "landing" / "src" / "components" / "landing-page.tsx"
        ).read_text(encoding="utf-8")
        self.assertNotIn(
            "/photos/",
            page,
            "landing must not serve uncertified photography",
        )

    def test_marketing_copy_free_of_ai_image_words(self):
        for locale in LOCALES:
            text = (LANDING_COPY / f"{locale}.ts").read_text(encoding="utf-8")
            for word in BANNED_MARKETING_WORDS:
                self.assertNotIn(word, text, f"{locale}: banned phrase {word!r}")


class ProofCellContract(unittest.TestCase):
    def test_pitch_reliable_carries_six_proof_cells_per_locale(self):
        t = PITCH_COPY.read_text(encoding="utf-8")
        blocks = re.findall(r"proofs: \[(.*?)\n      \],", t, re.DOTALL)
        self.assertEqual(len(blocks), 5, "expected one proofs array per locale")
        for block in blocks:
            cells = block.count("{\n          num:") + block.count("{ num:")
            self.assertGreaterEqual(
                cells, 6, "sixth proof cell (market evidence) missing"
            )


if __name__ == "__main__":
    unittest.main()
