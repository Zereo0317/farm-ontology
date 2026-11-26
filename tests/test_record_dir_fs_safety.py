import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import record


class RecordDirFileSystemSafety(unittest.TestCase):
    def test_gcs_backend_does_not_mkdir_in_read_only_root(self):
        """GCS mode: record_dir() must not touch the filesystem (a read-only
        container used to die on mkdir BEFORE the backend was consulted)."""
        with tempfile.TemporaryDirectory() as tmp:
            readonly_root = Path(tmp) / "ro"
            readonly_root.mkdir()
            readonly_root.chmod(0o555)
            env = {"FARM_RECORD_BACKEND": "gcs", "FARM_RECORD_DIR": ""}
            with mock.patch.object(record, "ROOT", readonly_root), mock.patch.dict(os.environ, env, clear=False):
                try:
                    out = record.record_dir()
                    self.assertEqual(out, readonly_root / "field-notes")
                finally:
                    readonly_root.chmod(0o755)

    def test_local_backend_still_creates_the_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {"FARM_RECORD_BACKEND": "local", "FARM_RECORD_DIR": ""}
            with mock.patch.object(record, "ROOT", root), mock.patch.dict(os.environ, env, clear=False):
                out = record.record_dir()
                self.assertTrue((out / "notes").is_dir())


if __name__ == "__main__":
    unittest.main()
