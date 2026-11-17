"""Punch-list discipline: data of record, doctrine clause, md render parity."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PUNCHLIST = ROOT / "grants" / "punchlist.yaml"
RENDER = ROOT / "docs" / "legal" / "commercial-punchlist.md"

EXPECTED_ITEMS = {
    "PL-PLANET-COMMERCIAL",
    "PL-EE-COMMERCIAL-REGISTRATION",
    "PL-OPENMETEO-Q9",
    "PL-JMA-REDISTRIBUTION",
    "PL-ACTUATION-COMPLIANCE",
    "PL-CORPORATE-STATUS",
}

VERIFICATION_DATE = "2026-11-17"

# docs/alpha-fairness-doctrine.md §4 rail 1, VERBATIM (dash for dash).
DOCTRINE_CLAUSE_4_1 = (
    "The Company maintains proprietary positions in agricultural commodities. "
    "When its data indicates materially adverse or favourable conditions for "
    "Your fields, the Company shall disclose the existence — never the size — "
    "of related positions in its periodic decision-support report, before the "
    "affected transaction dates."
)


def _yaml_lines() -> list[str]:
    return PUNCHLIST.read_text(encoding="utf-8").splitlines()


def _items_in_yaml() -> list[tuple[str, list[str]]]:
    """Very small scanner: `  - id: NAME` starts an item chunk."""
    items: list[tuple[str, list[str]]] = []
    current: tuple[str, list[str]] | None = None
    for line in _yaml_lines():
        match = re.match(r"^  - id: ([\w-]+)$", line)
        if match:
            if current:
                items.append(current)
            current = (match.group(1), [])
        elif current is not None and line.startswith("    "):
            current[1].append(line)
    if current:
        items.append(current)
    return items


def _clause_from_yaml() -> str:
    lines = _yaml_lines()
    start = None
    for index, line in enumerate(lines):
        if line == "    text: >-":
            start = index + 1
            break
    assert start is not None, "the contract pack clause text block vanished"
    folded: list[str] = []
    for line in lines[start:]:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent <= 4:
            break
        folded.append(line.strip())
    text = " ".join(folded)
    assert text.startswith('"') and text.endswith('"'), "clause must stay quoted"
    return text.strip('"')


class PunchlistDataTests(unittest.TestCase):
    def test_all_six_items_exist_with_correct_statuses(self):
        items = _items_in_yaml()
        self.assertEqual({name for name, _ in items}, EXPECTED_ITEMS)
        for name, chunk in items:
            statuses = [line for line in chunk if line.strip().startswith("status:")]
            self.assertEqual(len(statuses), 1, name)
            self.assertIn("NOT-YET-EXECUTED", statuses[0], name)

    def test_every_item_has_owner_actions_evidence_and_dated_sources(self):
        for name, chunk in _items_in_yaml():
            body = "\n".join(chunk)
            for needle in ("owner:", "next_action:", "evidence_to_attach:", "expected_unlock:"):
                self.assertIn(needle, body, f"{name} lacks {needle}")
            self.assertIn(f'verified: "{VERIFICATION_DATE}"', body, name)
            self.assertRegex(body, r"- url: https?://", msg=name)

    def test_verification_date_stamp_is_current(self):
        self.assertIn(f"verification_date: \"{VERIFICATION_DATE}\"", "\n".join(_yaml_lines()))

    def test_planet_item_names_checkpoint_deadline_and_credit_model(self):
        body = "\n".join(dict(_items_in_yaml())["PL-PLANET-COMMERCIAL"])
        for needle in ("2026-12-17", "2026-11-30", "3,000", "SEATS", "CREDIT MODEL"):
            self.assertIn(needle, body)

    def test_openmeteo_item_names_the_adapter_file(self):
        body = "\n".join(dict(_items_in_yaml())["PL-OPENMETEO-Q9"])
        self.assertIn("farm_ontology/adapters/open_meteo.py", body)

    def test_actuation_item_covers_three_legislation_families(self):
        body = "\n".join(dict(_items_in_yaml())["PL-ACTUATION-COMPLIANCE"])
        for needle in ("航空法", "農薬適用基準", "ISO11783"):
            self.assertIn(needle, body)

    def test_corporate_item_blocks_signing_until_the_register_issues(self):
        body = "\n".join(dict(_items_in_yaml())["PL-CORPORATE-STATUS"])
        self.assertIn("登記事項証明書", body)
        self.assertIn("法人番号", body)

    def test_punchlist_references_the_three_specimen_grants(self):
        text = "\n".join(_yaml_lines())
        for name in (
            "grants/planet-trial.json",
            "grants/ee-commercial-specimen.json",
            "grants/open-meteo-q9-specimen.json",
        ):
            self.assertIn(name, text)

    def test_specimens_beside_the_punchlist_carry_the_flag(self):
        import json

        for name in (
            "planet-trial.json",
            "ee-commercial-specimen.json",
            "open-meteo-q9-specimen.json",
        ):
            doc = json.loads((ROOT / "grants" / name).read_text(encoding="utf-8"))
            self.assertIs(doc.get("specimen"), True, name)
            self.assertTrue(doc.get("specimen_note"), name)


class ContractPackTests(unittest.TestCase):
    def test_clause_4_1_is_verbatim_including_the_long_dashes(self):
        self.assertEqual(_clause_from_yaml(), DOCTRINE_CLAUSE_4_1)

    def test_contract_pack_marks_itself_ready_to_sign_pending_company(self):
        text = "\n".join(_yaml_lines())
        self.assertIn("READY-TO-SIGN", text)
        self.assertIn("PENDING-PL-CORPORATE-STATUS", text)

    def test_markdown_render_carries_the_clause_and_all_items(self):
        md = RENDER.read_text(encoding="utf-8")
        for needle in (
            "**Concurrent-position disclosure (doctrine §4.1, verbatim, mandatory):**",
            "> \"The Company maintains proprietary positions",
        ):
            self.assertIn(needle, md)
        # the block-quoted render folds lines; strip "> " prefixes, flatten,
        # and compare whitespace-insensitively
        cleaned = " ".join(
            line.lstrip().lstrip(">").strip() for line in md.splitlines()
        )
        self.assertIn(" ".join(DOCTRINE_CLAUSE_4_1.split()), cleaned)
        self.assertEqual(set(re.findall(r"^## (PL-[A-Z0-9-]+) ", md, re.M)), EXPECTED_ITEMS)
        self.assertEqual(len(re.findall(r"^## PL-.*NOT-YET-EXECUTED", md, re.M)), 6)


class LedgerStaysFresh(unittest.TestCase):
    def test_state_generator_sees_the_specimen_dir(self):
        from farm_ontology.licences.grants import build_state, load_grants
        from tests.support import NOW

        state = build_state(load_grants(ROOT / "grants"), NOW)
        self.assertFalse(any(row["permits_financial_use"] for row in state["feeds"].values()))


if __name__ == "__main__":
    unittest.main()
