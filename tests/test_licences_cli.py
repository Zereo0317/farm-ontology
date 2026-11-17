"""CLI contract for `python -m farm_ontology.licences.cli`."""

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology.licences import cli  # noqa: E402

NOW = "2026-11-17T08:00:00+00:00"


def _run(*argv) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class CliTests(unittest.TestCase):
    def test_list_reports_specimens_and_alarm_lines(self):
        code, out, err = _run("list", "--at", NOW)
        self.assertEqual(code, 0)
        rows = [json.loads(line) for line in out.splitlines()]
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["status"] == "SPECIMEN" for row in rows))
        by_id = {row["grant_id"]: row for row in rows}
        self.assertIn("planet-trial-specimen", by_id)
        self.assertIn(
            "2026-12-17T14:59:59+00:00", by_id["planet-trial-specimen"]["expiry_utc"]
        )
        for row in rows:
            self.assertEqual(len(row["fingerprint"]), 64)
        # specimen rows never appear as live alarms
        self.assertNotIn("alarm live", err)

    def test_evaluate_denies_a_specimen_with_exit_code_one(self):
        code, out, _ = _run(
            "evaluate", "--feed", "planet.psscene", "--use", "settlement", "--at", NOW
        )
        self.assertEqual(code, 1)
        verdict = json.loads(out)
        self.assertEqual(
            (verdict["allowed"], verdict["reason"], verdict["grant"]),
            (False, "specimen", "planet-trial-specimen"),
        )

    def test_evaluate_denies_an_unknown_feed_cleanly(self):
        code, out, _ = _run(
            "evaluate", "--feed", "does.not.exist", "--use", "screening", "--at", NOW
        )
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["reason"], "unknown_feed")

    def test_state_writes_machine_readable_json_next_to_the_grants(self):
        import shutil
        import tempfile

        tmp = Path(tempfile.mkdtemp())
        try:
            for name in (
                "planet-trial.json",
                "ee-commercial-specimen.json",
                "open-meteo-q9-specimen.json",
            ):
                shutil.copy(
                    Path(cli.DEFAULT_GRANTS_DIR) / name, tmp / name
                )
            target = tmp / "state.json"
            code, out, _ = _run(
                "--dir", str(tmp), "state", "--out", str(target), "--at", NOW
            )
            self.assertEqual(code, 0)
            doc = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(doc["schema"], "farm-ontology.grants.state/1")
            self.assertTrue(doc["fail_closed"])
            self.assertFalse(
                any(row["permits_financial_use"] for row in doc["feeds"].values())
            )
        finally:
            shutil.rmtree(tmp)

    def test_dangerous_defaults_require_both_flags(self):
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                cli.main(["evaluate", "--feed", "planet.psscene"])


if __name__ == "__main__":
    unittest.main()
