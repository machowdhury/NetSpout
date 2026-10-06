import os
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["NETSPOUT_STUDIO_DIR"] = tempfile.mkdtemp(prefix="netspout-studio-api-")

from app.main import app  # noqa: E402


class ScenarioStudioApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_home_and_fail_closed_sensitive_analysis(self):
        home = self.client.get("/api/studio")
        self.assertEqual(home.status_code, 200)
        self.assertEqual(len(home.json()["creation_paths"]), 3)

        synthetic_secret = "TEST_ONLY_TOKEN_" + ("X" * 24)
        response = self.client.post(
            "/api/studio/samples/analyze",
            json={
                "sample": "authorization=Bearer {}".format(synthetic_secret),
                "authorization_acknowledged": True,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["blocked"])
        self.assertNotIn(synthetic_secret, response.text)

    def test_existing_source_save_reload_delete_round_trip(self):
        draft_response = self.client.post(
            "/api/studio/drafts",
            json={
                "creation_path": "EXISTING_SOURCES",
                "source_ids": ["ietf-syslog-rfc5424"],
                "title": "API Round Trip",
            },
        )
        self.assertEqual(draft_response.status_code, 200)
        draft = draft_response.json()

        validation = self.client.post("/api/studio/packs/validate", json=draft)
        self.assertEqual(validation.status_code, 200)
        self.assertTrue(validation.json()["valid"])

        saved = self.client.post("/api/studio/packs", json=draft)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["redistribution"], "PRIVATE")

        loaded = self.client.get("/api/studio/packs/{}".format(draft["pack_id"]))
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["timeline"], draft["timeline"])

        deleted = self.client.delete(
            "/api/studio/packs/{}".format(draft["pack_id"])
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get(
                "/api/studio/packs/{}".format(draft["pack_id"])
            ).status_code,
            404,
        )


if __name__ == "__main__":
    unittest.main()
