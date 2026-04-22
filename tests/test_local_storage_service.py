from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest
from starlette.datastructures import Headers, UploadFile

from app.services import local_storage_service


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
async def test_save_uploaded_file_persists_file_and_returns_compatible_payload(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "public_html"
    upload_dir = public_root / "uploads"
    monkeypatch.setattr(
        local_storage_service,
        "settings",
        SimpleNamespace(
            APP_BASE_URL="https://ptcahyaintanmedika.co.id",
            PUBLIC_ROOT_DIR=str(public_root),
            UPLOAD_DIR=str(upload_dir),
            public_root_dir_path=public_root,
            upload_dir_path=upload_dir,
        ),
    )

    file = _build_upload_file("arrival.JPG", b"image-bytes", "image/jpeg")

    result = await local_storage_service.save_uploaded_file(
        file=file,
        folder="checkins",
        resource_type="image",
    )

    saved_file = Path(result["disk_path"])

    assert saved_file.exists()
    assert saved_file.read_bytes() == b"image-bytes"
    assert result["public_id"] == result["relative_path"]
    assert result["secure_url"] == result["public_url"]
    assert result["resource_type"] == "image"
    assert result["format"] == "jpg"
    assert result["bytes"] == len(b"image-bytes")
    assert result["original_filename"] == "arrival.JPG"
    assert result["content_type"] == "image/jpeg"
    assert result["relative_path"].startswith("uploads/checkins/")
    assert result["public_url"].startswith("https://ptcahyaintanmedika.co.id/uploads/checkins/")
    assert await file.read() == b"image-bytes"


@pytest.mark.anyio
async def test_upload_resolution_video_uses_resolution_folder(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "public_html"
    upload_dir = public_root / "uploads"
    monkeypatch.setattr(
        local_storage_service,
        "settings",
        SimpleNamespace(
            APP_BASE_URL="https://ptcahyaintanmedika.co.id",
            PUBLIC_ROOT_DIR=str(public_root),
            UPLOAD_DIR=str(upload_dir),
            public_root_dir_path=public_root,
            upload_dir_path=upload_dir,
        ),
    )

    file = _build_upload_file("resolution.mp4", b"video-bytes", "video/mp4")

    result = await local_storage_service.upload_resolution_video(file)

    assert result["resource_type"] == "video"
    assert result["format"] == "mp4"
    assert result["relative_path"].startswith("uploads/resolutions/")


@pytest.mark.anyio
async def test_save_uploaded_file_rejects_invalid_folder(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "public_html"
    upload_dir = public_root / "uploads"
    monkeypatch.setattr(
        local_storage_service,
        "settings",
        SimpleNamespace(
            APP_BASE_URL="https://ptcahyaintanmedika.co.id",
            PUBLIC_ROOT_DIR=str(public_root),
            UPLOAD_DIR=str(upload_dir),
            public_root_dir_path=public_root,
            upload_dir_path=upload_dir,
        ),
    )

    file = _build_upload_file("arrival.jpg", b"image-bytes", "image/jpeg")

    with pytest.raises(ValueError, match="Folder upload tidak valid."):
        await local_storage_service.save_uploaded_file(file=file, folder="../outside")


def test_delete_uploaded_file_removes_saved_file_and_empty_parent_dirs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    public_root = tmp_path / "public_html"
    upload_dir = public_root / "uploads"
    target_dir = upload_dir / "checkins" / "2026" / "04" / "17"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "proof.jpg"
    target_file.write_bytes(b"image-bytes")

    monkeypatch.setattr(
        local_storage_service,
        "settings",
        SimpleNamespace(
            APP_BASE_URL="https://ptcahyaintanmedika.co.id",
            PUBLIC_ROOT_DIR=str(public_root),
            UPLOAD_DIR=str(upload_dir),
            public_root_dir_path=public_root,
            upload_dir_path=upload_dir,
        ),
    )

    local_storage_service.delete_uploaded_file({"disk_path": str(target_file)})

    assert not target_file.exists()
    assert not target_dir.exists()
    assert upload_dir.exists()
