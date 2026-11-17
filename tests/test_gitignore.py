import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

IGNORED = (
    ".env",
    "deploy/.env",
    ".env.local",
    "web/.env.production",
    "certs/server.pem",
    "vendor/prod-credentials-backup.json",
    "keys/my-service-account-prod.json",
    "planet-api-key",
    "secrets/planet-api-key.txt",
    ".planet-api-key",
    "api-key.txt",
    "config/api-key.txt",
)
KEPT = (
    "farm_ontology/policy.py",
    "README.md",
    "tests/test_gitignore.py",
)


class GitignoreKeyFileTests(unittest.TestCase):
    def test_key_file_names_are_ignored(self) -> None:
        rules = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("!", rules)
        completed = subprocess.run(
            ["git", "check-ignore", "-v", "--no-index", "--", *IGNORED, *KEPT],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        ignored = set()
        for line in completed.stdout.splitlines():
            path = line.split("\t", 1)[-1].replace("\\", "/")
            ignored.add(path)
        for name in IGNORED:
            self.assertIn(name, ignored)
        for name in KEPT:
            self.assertNotIn(name, ignored)
        for name in IGNORED:
            self.assertFalse((ROOT / name).exists())


if __name__ == "__main__":
    unittest.main()
