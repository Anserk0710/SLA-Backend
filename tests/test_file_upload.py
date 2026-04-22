from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from app.utils import file_upload as file_upload_module


def _build_upload_file(
    filename: str,
    content: bytes,
    content_type: str,
) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


@pytest.mark.anyio
async def test_validate_image_upload_returns_metadata_and_resets_pointer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        file_upload_module,
        "settings",
        SimpleNamespace(MAX_IMAGE_UPLOAD_MB=5, MAX_VIDEO_UPLOAD_MB=25),
    )
    file = _build_upload_file("arrival.JPG", b"image-bytes", "image/jpeg")

    metadata = await file_upload_module.validate_image_upload(file)

    assert metadata == {
        "filename": "arrival.JPG",
        "extension": ".jpg",
        "content_type": "image/jpeg",
        "size_bytes": len(b"image-bytes"),
        "size_mb": 0.0,
    }
    assert await file.read() == b"image-bytes"


@pytest.mark.anyio
async def test_validate_image_upload_rejects_invalid_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        file_upload_module,
        "settings",
        SimpleNamespace(MAX_IMAGE_UPLOAD_MB=5, MAX_VIDEO_UPLOAD_MB=25),
    )
    file = _build_upload_file("arrival.gif", b"image-bytes", "image/gif")

    with pytest.raises(HTTPException, match="Ekstensi file foto tidak didukung."):
        await file_upload_module.validate_image_upload(file)


@pytest.mark.anyio
async def test_validate_video_upload_rejects_invalid_content_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        file_upload_module,
        "settings",
        SimpleNamespace(MAX_IMAGE_UPLOAD_MB=5, MAX_VIDEO_UPLOAD_MB=25),
    )
    file = _build_upload_file("resolution.mp4", b"video-bytes", "application/octet-stream")

    with pytest.raises(HTTPException, match="Tipe file video tidak didukung."):
        await file_upload_module.validate_video_upload(file)


@pytest.mark.anyio
async def test_validate_video_upload_rejects_file_larger_than_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        file_upload_module,
        "settings",
        SimpleNamespace(MAX_IMAGE_UPLOAD_MB=5, MAX_VIDEO_UPLOAD_MB=1),
    )
    file = _build_upload_file(
        "resolution.mp4",
        b"x" * ((1024 * 1024) + 1),
        "video/mp4",
    )

    with pytest.raises(HTTPException, match="Ukuran video melebihi 1MB."):
        await file_upload_module.validate_video_upload(file)

    assert await file.read(4) == b"xxxx"


@pytest.mark.anyio
async def test_validate_image_upload_rejects_empty_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        file_upload_module,
        "settings",
        SimpleNamespace(MAX_IMAGE_UPLOAD_MB=5, MAX_VIDEO_UPLOAD_MB=25),
    )
    file = _build_upload_file("arrival.jpg", b"", "image/jpeg")

    with pytest.raises(HTTPException, match="File foto kosong."):
        await file_upload_module.validate_image_upload(file)
