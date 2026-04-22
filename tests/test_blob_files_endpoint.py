from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1.endpoints import blob_files as blob_files_endpoint
from app.core.config import settings


def test_blob_file_endpoint_returns_404_when_backend_not_vercel_blob(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        blob_files_endpoint,
        "settings",
        SimpleNamespace(STORAGE_BACKEND="local"),
    )

    response = client.get(f"{settings.API_V1_PREFIX}/files/blob/checkins/2026/04/22/proof.jpg")

    assert response.status_code == 404
    assert response.json()["detail"] == "File tidak ditemukan"


def test_blob_file_endpoint_returns_blob_content(
    client: TestClient,
    monkeypatch,
) -> None:
    async def fake_get_blob_content(_blob_path: str) -> dict[str, str | bytes]:
        return {
            "content": b"blob-bytes",
            "content_type": "image/jpeg",
            "cache_control": "public, max-age=3600",
            "etag": "etag-value",
        }

    monkeypatch.setattr(
        blob_files_endpoint,
        "settings",
        SimpleNamespace(STORAGE_BACKEND="vercel_blob"),
    )
    monkeypatch.setattr(
        blob_files_endpoint,
        "get_vercel_blob_content",
        fake_get_blob_content,
    )

    response = client.get(f"{settings.API_V1_PREFIX}/files/blob/checkins/2026/04/22/proof.jpg")

    assert response.status_code == 200
    assert response.content == b"blob-bytes"
    assert response.headers["content-type"] == "image/jpeg"
    assert response.headers["cache-control"] == "public, max-age=3600"
    assert response.headers["etag"] == "etag-value"

