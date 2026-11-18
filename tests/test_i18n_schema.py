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


class ReportCopyGuardTests(unittest.TestCase):
    """Report (biratori-1119) copy must be structurally complete in ALL FIVE
    locales (Sprint-B raised zh-TW+ja to the full house roster).

    Every locale dict must carry the same top-level keys and the same array
    cardinalities — a translated-but-shorter array would push another
    language's strings at readers otherwise. The scanner is template-aware:
    `${...}` expressions inside template literals are stripped before any
    brace counting, and each array's element count comes from its own
    balanced `[...]` slice, not a shared window.
    """

    REQUIRED_REPORT_LOCALES = ["zh-TW", "zh-CN", "en", "ja", "th"]
    ARRAYS = {
        # key -> regex matching the first line of each ELEMENT
        "playbook": r"glyph:",
        "invTranches": r"share:",
        "invCalendar": r'^\s+"',
        "invAssumptions": r'^\s+"',
        "invSpine": r"num:",
        "invLinks": r"label:",
        "invRefs": r"label:",
    }
    # The investor tab is the ONLY place a licensing caveat may appear; each
    # locale phrases it natively (registered here so a "translated" footer
    # that lost its teeth fails loud).
    FOOTER_EXPECTATION = {
        "zh-TW": ["非投資要約", "金融用途授權現為否"],
        "zh-CN": ["不是投资邀约", "金融用途授权现为否"],
        "en": ["not an investment solicitation", "licensing is currently OFF"],
        "ja": ["投資勧誘ではありません", "金融用途のライセンスは現状オフ"],
        "th": ["ไม่ใช่การชักชวนลงทุน", "การอนุญาตใช้เพื่อการเงินยังปิดอยู่"],
    }

    @classmethod
    def setUpClass(cls):
        # Template placeholders never contain nested braces in this module.
        cls.clean = re.sub(r"\$\{[^{}]*\}", "EXPR", (WEB / "lib" / "report-copy.ts").read_text(encoding="utf-8"))

    def _balanced(self, text: str, open_pos: int, open_ch: str, close_ch: str) -> tuple[int, int]:
        """Return (content_start, content_end) inside open/close at open_pos."""
        depth = 0
        for j in range(open_pos, len(text)):
            if text[j] == open_ch:
                depth += 1
            elif text[j] == close_ch:
                depth -= 1
                if depth == 0:
                    return open_pos + 1, j
        raise AssertionError(f"unbalanced {open_ch}{close_ch} at {open_pos}")

    def _locale_slice(self, clean: str, locale: str) -> str:
        token = f'"{locale}": {{' if "-" in locale else f"{locale}: {{"
        block = clean[clean.find("export const reportCopy"):]
        lm = block.find(token)
        self.assertGreaterEqual(lm, 0, f"{locale} dict missing from reportCopy")
        start, end = self._balanced(block, block.index("{", lm), "{", "}")
        return block[start:end]

    def _array_elements(self, locale_slice: str, key: str) -> list[str]:
        am = re.search(rf"\n\s+{key}: \[", locale_slice)
        self.assertIsNotNone(am, f"{key} array missing")
        start, end = self._balanced(locale_slice, am.end() - 1, "[", "]")
        body = locale_slice[start:end]
        sign = self.ARRAYS[key]
        if sign.startswith("^"):
            return re.findall(sign + r"[^\n]*", body, re.M)
        return re.findall(sign, body)

    def test_all_five_locales_present_with_matching_key_sets(self):
        baseline: set[str] | None = None
        for locale in self.REQUIRED_REPORT_LOCALES:
            current = set(re.findall(r"^\s{4}([a-zA-Z][a-zA-Z0-9]*):", self._locale_slice(self.clean, locale), re.M))
            self.assertTrue(current, f"{locale} dict empty")
            if baseline is None:
                baseline = current
            else:
                self.assertEqual(current, baseline, f"{locale} diverges from zh-TW")
        anchors = {"docTitle", "h1", "tabFarmer", "tabInvestor", "sceneTitle", "invRoiTitle", "invFooter"}
        self.assertTrue(anchors.issubset(baseline or set()), f"missing anchors: {sorted(anchors - (baseline or set()))}")

    def test_array_cardinality_matches_across_all_five_locales(self):
        for key in self.ARRAYS:
            counts = {}
            for locale in self.REQUIRED_REPORT_LOCALES:
                counts[locale] = len(self._array_elements(self._locale_slice(self.clean, locale), key))
            self.assertGreater(min(counts.values()), 0, f"{key} must not be emptied")
            self.assertEqual(len(set(counts.values())), 1, f"{key} arrays differ between locales: {counts}")

    def test_farmer_voice_avoids_internal_jargon(self):
        # Founder: kill internal-compliance vocabulary from the farmer tabs.
        text = self.clean
        for phrase in ("許可", "治理", "授權牆", "コンプライアンス", "情治", "compliance layer"):
            self.assertNotIn(phrase, text)

    def test_investor_tab_stamps_the_single_compliance_line(self):
        for locale in self.REQUIRED_REPORT_LOCALES:
            slice_text = self._locale_slice(self.clean, locale)
            fm = re.search(r"invFooter: \"(.+)\"", slice_text)
            self.assertIsNotNone(fm, f"{locale} missing invFooter")
            for needle in self.FOOTER_EXPECTATION[locale]:
                self.assertIn(needle, fm.group(1), f"{locale} footer lost '{needle}'")

    def test_scripts_look_native_not_machine_swapped(self):
        # zh-CN must be Simplified (no traditional-only drift-ins), th must be
        # Thai script, en must keep the business register on its columns.
        zh_cn = self._locale_slice(self.clean, "zh-CN")
        for trad in ("風", "後", "資", "點", "區", "現為否"):
            self.assertNotIn(trad, zh_cn, f"zh-CN carries traditional/remnant '{trad}'")
        self.assertIn("格点", zh_cn)
        th = self._locale_slice(self.clean, "th")
        self.assertRegex(th, r"[ก-๛]")
        en = self._locale_slice(self.clean, "en")
        self.assertIn("tranche", en.lower())
        self.assertIn("$/bu", en)

    def test_pages_never_hardcode_report_strings(self):
        page = (WEB / "app" / "report" / "biratori-1119" / "page.tsx").read_text(encoding="utf-8")
        # Numeric + structural literals only; prose arrives from reportCopy.
        self.assertIn("reportCopy", page)
        self.assertNotIn("農夫版", page)
        self.assertNotIn("生産者版", page)
        self.assertNotIn("ลงทุน", page)


if __name__ == "__main__":
    unittest.main()
