from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.schemas import MediaItem, ResolveResponse
from app.services.storage import storage

client = TestClient(app)


def test_health_and_web_ui():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "ytdlp_version" in data

    web_resp = client.get("/")
    assert web_resp.status_code == 200
    assert "ClipSave" in web_resp.text


def test_shortcut_version_endpoint():
    resp = client.get("/api/v1/shortcut/version")
    assert resp.status_code == 200
    assert resp.json()["version"] == settings.shortcut_version

    bundle_resp = client.get("/api/v1/shortcut/files/ClipSave-iOS-Bundle.zip")
    assert bundle_resp.status_code == 200
    assert len(bundle_resp.content) > 100

    bad_resp = client.get("/api/v1/shortcut/files/../../etc/passwd")
    assert bad_resp.status_code == 404


def test_resolve_requires_api_key_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "super-secret")
    resp = client.post("/api/v1/resolve", json={"url": "https://www.tiktok.com/@a/video/1"})
    assert resp.status_code == 401

    resp_bad = client.post(
        "/api/v1/resolve",
        headers={"X-API-Key": "wrong"},
        json={"url": "https://www.tiktok.com/@a/video/1"},
    )
    assert resp_bad.status_code == 401


def test_resolve_success_and_file_download(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "secret123")
    job_id, job_dir = storage.create_job_dir()
    sample_file = job_dir / "demo.mp4"
    sample_file.write_bytes(b"ftypmp42-fake-video-bytes")

    mock_response = ResolveResponse(
        status="ok",
        platform="tiktok",
        resolved_url="https://www.tiktok.com/@user/video/123",
        title="Demo TikTok",
        author="user",
        is_carousel=False,
        items=[
            MediaItem(
                type="video",
                download_url=f"http://testserver/api/v1/download/{job_id}/demo.mp4",
                filename="demo.mp4",
                mime_type="video/mp4",
                ext="mp4",
                size_bytes=sample_file.stat().st_size,
            )
        ],
    )

    with patch("app.routers.resolve.resolve_media", new=AsyncMock(return_value=mock_response)):
        resp = client.post(
            "/api/v1/resolve",
            headers={"X-API-Key": "secret123"},
            json={"url": "https://vt.tiktok.com/ZSYabc/", "mode": "auto", "quality": "best"},
        )
    assert resp.status_code == 200
    assert resp.json()["platform"] == "tiktok"

    dl_resp = client.get(f"/api/v1/download/{job_id}/demo.mp4")
    assert dl_resp.status_code == 200
    assert dl_resp.content == b"ftypmp42-fake-video-bytes"

    # Path traversal / invalid job id blocked
    bad_dl = client.get("/api/v1/download/invalid_id/demo.mp4")
    assert bad_dl.status_code == 404
