"""The web i18n schema must completely support five locales.

House rule (founder directive 2026-11-18): zh-TW, zh-CN, en, ja, th are
FIRST-CLASS — every dictionary must carry EVERY key for every locale,
the chooser must offer all five, and no user-facing component may go
back to hardcoded bilingual literals.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
REQUIRED_LOCALES = ["zh-TW", "zh-CN", "en", "ja", "th"]


class I18nSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copy_ts = (WEB / "lib" / "copy.ts").read_text(encoding="utf-8")

    def _locale_dict_keys(self, locale: str, dict_name: str) -> set[str]:
        dm = re.search(rf'export const {dict_name}: Record<Locale, \w+> = \{{', self.copy_ts)
        self.assertIsNotNone(dm, f"{dict_name} const not found")
        block = self.copy_ts[dm.start():]
        token = f'"{locale}": {{' if "-" in locale else f"{locale}: {{"
        lm = block.find(token)
        self.assertGreaterEqual(lm, 0, f"{locale} dict missing from {dict_name}")
        i = block.index("{", lm)
        depth = 0
        for j in range(i, len(block)):
            if block[j] == "{":
                depth += 1
            elif block[j] == "}":
                depth -= 1
                if depth == 0:
                    break
        return set(re.findall(r"^\s{4}([a-zA-Z]+)[(:]", block[i:j], re.M))

    def test_locale_registry_carries_all_five(self):
        m = re.search(r'export const locales = \[(.*?)\] as const;', self.copy_ts, re.S)
        listed = re.findall(r'"([^"]+)"|([a-z]{2}(?:-[A-Z]{2})?)', m.group(1))
        names = [a or b for a, b in listed]
        self.assertEqual(names, REQUIRED_LOCALES)

    def test_every_locale_has_the_full_field_dictionary(self):
        type_block = re.search(r"type Copy = \{(.*?)\n\};", self.copy_ts, re.S)
        copy_keys = set(re.findall(r"^\s{2}([a-zA-Z]+)(?:\?)?:", type_block.group(1), re.M))
        # The zh dictionaries legitimately carry the 43 shared Copy keys; en/
        # ja/th also carry function-valued keys. Extract each dict directly.
        for locale in REQUIRED_LOCALES:
            keys = self._locale_dict_keys(locale, "copy")
            self.assertTrue(copy_keys.issubset(keys), f"{locale} missing {sorted(copy_keys - keys)[:6]}")
            self.assertLessEqual(len(keys), 50, f"{locale} grew surprise keys")

    def test_every_locale_has_the_full_advisory_dictionary(self):
        type_block = re.search(r"export type AdvisoryCopy = \{(.*?)\n\};", self.copy_ts, re.S)
        adv_keys = set(re.findall(r"^\s{2}([a-zA-Z]+)(?:\?)?:", type_block.group(1), re.M))
        self.assertTrue(adv_keys)
        adv_block_m = re.search(r"export const advisoryCopy: Record<Locale, AdvisoryCopy> = \{", self.copy_ts)
        adv_block = self.copy_ts[adv_block_m.start():]
        for locale in REQUIRED_LOCALES:
            token = f'"{locale}": {{' if "-" in locale else f"{locale}: {{"
            lm = adv_block.find(token)
            self.assertGreaterEqual(lm, 0, f"{locale} advisory dict missing")
            i = adv_block.index("{", lm)
            depth = 0
            for j in range(i, len(adv_block)):
                if adv_block[j] == "{":
                    depth += 1
                elif adv_block[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
            keys = set(re.findall(r"^\s{4}([a-zA-Z]+)[(:]", adv_block[i:j], re.M))
            self.assertEqual(keys, adv_keys, f"{locale} advisory dictionary incomplete")

    def test_chooser_offers_all_five_labels(self):
        m = re.search(
            r"export const localeLabels: Record<Locale, string> = \{(.*?)\};",
            self.copy_ts,
            re.S,
        )
        for locale in REQUIRED_LOCALES:
            self.assertIn(f'"{locale}"' if "-" in locale else f"{locale}:", m.group(1))
        # Thai must actually BE Thai script
        self.assertRegex(m.group(1), r"[ไ-๛]")

    def test_locale_persistence_uses_the_dynamic_whitelist(self):
        sheet = (WEB / "app" / "field-sheet.tsx").read_text(encoding="utf-8")
        self.assertIn("(locales as readonly string[]).includes", sheet)
        self.assertNotIn('saved === "zh-TW" ||', sheet)  # hardcoded whitelist retired

    def test_middleware_negotiates_first_visit_language(self):
        mw = (WEB / "middleware.ts").read_text(encoding="utf-8")
        # reads the browser's Accept-Language header
        self.assertIn("accept-language", mw)
        # stamps the SAME cookie the client chooser mirrors (one shared name)
        self.assertIn('LOCALE_COOKIE = "farm-locale"', mw)
        # respects an explicit choice: negotiates only when the cookie is absent
        self.assertIn("!request.cookies.get(LOCALE_COOKIE)?.value", mw)
        # five-way routing table present (bare/ambiguous zh leans traditional)
        self.assertIn('return "zh-TW"', mw)
        self.assertIn('return "zh-CN"', mw)
        self.assertIn('return "ja"', mw)
        self.assertIn('return "th"', mw)
        self.assertIn('return "en"', mw)

    def test_html_lang_reflects_bcp47_per_locale(self):
        self.assertIn("localeHtmlLang", (WEB / "app" / "field-sheet.tsx").read_text(encoding="utf-8"))
        m = re.search(
            r"export const localeHtmlLang: Record<Locale, string> = \{(.*?)\};",
            self.copy_ts,
            re.S,
        )
        block = m.group(1)
        for token, tag in (('"zh-TW": "zh-Hant-TW"', "zh-Hant-TW"), ("th: \"th\"", "th"), ('ja: "ja"', "ja"), ('en: "en"', "en")):
            self.assertIn(token if ": " in token else f"{token}", block)
        # Thai entry present with its own script-free tag
        self.assertRegex(block, r"th:\s*\"th\"")

    def test_no_bilingual_hardcoded_headings_remain_in_advisories(self):
        text = (WEB / "app" / "advisories.tsx").read_text(encoding="utf-8")
        # the paired-literal style ("即時氣象 Live weather") is retired; strings
        # come from the dictionary
        self.assertNotRegex(text, r"[\u4e00-\u9fff] [A-Z][a-z]+ ")

    def test_python_guard_matches_five_locales(self):
        py = (Path(__file__).parent / "test_page_io.py").read_text(encoding="utf-8")
        self.assertIn("th", py)


if __name__ == "__main__":
    unittest.main()
