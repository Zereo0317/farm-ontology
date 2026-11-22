import unittest
from deploy.web_image_ref import BASE, normalize

class WebImageRefTests(unittest.TestCase):
    def test_digest_forms_resolve_once(self):
        h = "a" * 64
        expected = BASE + "@sha256:" + h
        for form in (h, "sha256:" + h, expected):
            with self.subTest(form=form): self.assertEqual(normalize(form), expected)
    def test_reject_mutable_or_other_image_refs(self):
        for value in ("latest", "sha256:bad", "other/image@sha256:" + "a" * 64, BASE + ":latest"):
            with self.subTest(value=value), self.assertRaises(ValueError): normalize(value)
