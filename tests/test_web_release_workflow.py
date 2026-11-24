import unittest
from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github" / "workflows" / "web-image.yml"


class WebReleaseWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_push_builds_a_no_traffic_candidate_without_promotion(self):
        candidate = self.text.split("  candidate-web:", 1)[1].split("  deploy-web:", 1)[0]
        self.assertIn("--tag auth-candidate --no-traffic", candidate)
        self.assertIn("FARM_WEB_DEPLOYER_READY == 'true'", candidate)
        self.assertIn("farm-web-deployer@seges-ai.iam.gserviceaccount.com", candidate)
        deploy = self.text.split("  deploy-web:", 1)[1].split("  pin-rollback:", 1)[0]
        self.assertIn("github.event_name == 'workflow_dispatch'", deploy)
        self.assertIn("inputs.accepted_image_digest == inputs.promotion_image_ref", deploy)
        self.assertIn("FARM_WEB_ACCEPTANCE_DIGEST", deploy)
        self.assertIn("verify_promotion_acceptance", deploy)

    def test_promotion_checks_runtime_and_tagged_login_before_traffic(self):
        deploy = self.text.split("  deploy-web:", 1)[1].split("  pin-rollback:", 1)[0]
        self.assertIn("environment: web-production", deploy)
        self.assertIn("verify_web_promotion_config.py", deploy)
        self.assertIn("record-folder-iam.json", deploy)
        self.assertIn("record-bucket-iam.json", deploy)
        self.assertIn("FARM_WEB_MEMBERSHIP_ADMINISTRATOR", deploy)
        self.assertIn("FARM_WEB_MEMBERSHIP_ADMINISTRATOR", deploy)
        self.assertIn('value(spec.serviceAccountName)', deploy)
        self.assertIn("versions list", deploy)
        self.assertIn("/api/auth/login", deploy)
        self.assertIn("/api/boundaries", deploy)
        self.assertLess(deploy.index("/api/auth/login"), deploy.index("update-traffic farm-seges-ai-web"))
        candidate = self.text.split("  candidate-web:", 1)[1].split("  deploy-web:", 1)[0]
        self.assertIn('value(spec.serviceAccountName)', candidate)

    def test_rollback_requires_matching_accepted_digest(self):
        rollback = self.text.split("  pin-rollback:", 1)[1]
        self.assertIn("inputs.accepted_image_digest != ''", rollback)
        self.assertIn('test "$INPUT_ACCEPTED_IMAGE_DIGEST" = "$EXPECTED"', rollback)
        self.assertIn("serving_revision(json.load(open(sys.argv[1])))", rollback)


if __name__ == "__main__":
    unittest.main()
