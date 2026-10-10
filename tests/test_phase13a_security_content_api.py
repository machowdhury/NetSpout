from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_security_content_catalog_endpoints():
    summary = client.get("/api/security-content/summary")
    assert summary.status_code == 200
    assert summary.json()["detections"] == 2181
    assert summary.json()["metadata_only"] is True

    listing = client.get(
        "/api/security-content/detections",
        params={
            "q": "React Server Components",
            "technique": "T1190",
            "compatibility": "REQUIRES_TRANSFORMATION",
        },
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    detection = listing.json()["items"][0]

    detail = client.get(
        f"/api/security-content/detections/{detection['catalog_key']}"
    )
    assert detail.status_code == 200
    assert detail.json()["dependencies"]["sourcetypes"] == [
        "cisco:sfw:estreamer"
    ]


def test_security_content_relationship_endpoints():
    assert client.get("/api/security-content/stories?limit=1").status_code == 200
    assert client.get("/api/security-content/datasets?limit=1").status_code == 200
    mitre = client.get("/api/security-content/mitre")
    assert mitre.status_code == 200
    t1190 = next(row for row in mitre.json() if row["technique"] == "T1190")
    assert t1190["name"] == "Exploit Public-Facing Application"
    assert "initial-access" in t1190["tactics"]


def test_security_content_execution_requires_authorized_connection():
    replay = client.post(
        "/api/security-content/replays",
        json={
            "local_id": "0" * 64,
            "dataset_path": "/datasets/example.log",
            "index": "main",
            "timestamp_mode": "PRESERVE",
        },
    )
    assert replay.status_code in {403, 409}
