import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from farm_ontology import REASONER
from farm_ontology.manifest import load_manifest, manifest_ok, manifest_violations

ROOT = Path(__file__).resolve().parents[1]


class ManifestTests(unittest.TestCase):
    def test_manifest_pins_references_and_rejects_forbidden_imports(self):
        document = load_manifest()
        self.assertEqual(manifest_violations(document), [])
        self.assertTrue(manifest_ok(document))
        self.assertEqual(document["class_c_policy"], "closed")
        self.assertEqual(document["reasoner"], "none")
        self.assertEqual(document["imports"], [])
        self.assertEqual(len(document["open_questions"]), 21)
        self.assertFalse(document["envo"]["imported"])
        self.assertEqual(
            document["iri_base"],
            "https://github.com/Zereo0317/farm-ontology/ns/",
        )
        self.assertEqual(document["iri_base_status"], "provisional-not-a-final-domain")
        turtle = (ROOT / "ontology" / "fd-decision.ttl").read_bytes()
        digest = hashlib.sha256(turtle).hexdigest()
        self.assertEqual(document["local_module"]["sha256"], digest)
        self.assertFalse(document["local_module"]["vendored_upstream"])
        text = turtle.decode("utf-8")
        self.assertIn("skos:exactMatch", text)
        self.assertIn("c_12332", text)
        self.assertNotIn("owl:imports", text)
        self.assertNotIn("owl:sameAs", text)
        self.assertNotIn("owl:equivalentClass", text)
        self.assertNotIn("glosis", text.lower())
        bad = dict(document)
        bad["imports"] = ["https://github.com/glosis-ld/glosis"]
        self.assertFalse(manifest_ok(bad))
        build = (ROOT / "ontology" / "BUILD.txt").read_text(encoding="utf-8")
        self.assertIn("reasoner: none", build)
        self.assertEqual(REASONER, "none")
        package = "\n".join(
            path.read_text(encoding="utf-8") for path in (ROOT / "farm_ontology").rglob("*.py")
        )
        self.assertNotIn("owlready2", package)
        self.assertNotIn("owlrl", package)


if __name__ == "__main__":
    unittest.main()
