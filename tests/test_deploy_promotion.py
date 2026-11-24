"""Release checks operate on recorded metadata, without calling GCP or GitHub."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("verify_promotion", Path(__file__).resolve().parents[1] / "deploy" / "verify-promotion.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class PromotionTests(unittest.TestCase):
    def setUp(self):
        self.sha = "a" * 40
        self.image = "asia-east1-docker.pkg.dev/seges-ai/farm/image@sha256:" + "b" * 64
        self.service = {"status": {"traffic": [{"percent": 100, "revisionName": "stage-1"}]}}
        self.revision = {"metadata": {"name": "stage-1"}, "spec": {"containers": [{"env": [{"name": "FARM_RELEASE_COMMIT", "value": self.sha}]}]}, "status": {"imageDigest": self.image, "conditions": [{"type": "Ready", "status": "True"}]}}
        self.runs = {"workflow_runs": [{"head_sha": self.sha, "event": "push", "head_branch": "main", "status": "completed", "conclusion": "success"}]}
    def check(self):
        return module.verified_image(self.service, self.revision, self.runs, self.sha)
    def test_valid_exact_digest(self):
        self.assertEqual(self.check(), self.image)
    def test_fails_closed(self):
        for change in ("traffic", "commit", "digest", "ci", "ready"):
            self.setUp()
            if change == "traffic": self.service["status"]["traffic"][0]["percent"] = 99
            if change == "commit": self.revision["spec"]["containers"][0]["env"][0]["value"] = "wrong"
            if change == "digest": self.revision["status"]["imageDigest"] = "mutable:tag"
            if change == "ci": self.runs["workflow_runs"][0]["conclusion"] = "failure"
            if change == "ready": self.revision["status"]["conditions"][0]["status"] = "False"
            with self.subTest(change=change), self.assertRaises(ValueError): self.check()

    def test_workflow_queries_completed_runs_then_checks_success_conclusion(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github" / "workflows" / "deploy-prod-tag.yml").read_text(encoding="utf-8")
        self.assertIn("actions/workflows/test.yml/runs?head_sha=${SHA}&event=push&status=completed&per_page=100", workflow)
        self.assertNotIn("&status=success&", workflow)

class ProductionConfigTests(unittest.TestCase):
    def test_required_secrets_and_storage_must_be_present(self):
        env = [{"name": k, "value": v} for k, v in {"GCP_PROJECT": "seges-ai", "EE_PROJECT": "seges-ai", "FARM_RECORD_BACKEND": "gcs", "FARM_RECORD_BUCKET": "farm-seges-ai-records"}.items()]
        env.extend({"name": k, "valueFrom": {"secretKeyRef": {"name": v}}} for k, v in {"PLANET_API_KEY": "Planet-labs", "WEB_ACCESS_TOKEN": "web-access-token"}.items())
        service = {"spec": {"template": {"spec": {"containers": [{"env": env}]}}}}
        module.verify_production_config(service)
        env.pop()
        with self.assertRaises(ValueError): module.verify_production_config(service)
