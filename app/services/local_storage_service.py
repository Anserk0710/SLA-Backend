from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


def _safe_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _normalize_folder(folder: str) -> Path:
    normalized = folder.strip().strip("/\\")
    if not normalized:
        raise ValueError("Folder upload tidak boleh kosong.")

    folder_path = Path(normalized)
    if folder_path.is_absolute() or ".." in folder_path.parts:
        raise ValueError("Folder upload tidak valid.")

    return folder_path


def _build_public_url(relative_path: str) -> str:
    base_url = settings.APP_BASE_URL.rstrip("/")
    return f"{base_url}/{relative_path.lstrip('/')}"


async def save_uploaded_file(
    file: UploadFile,
    folder: str,
    *,
    resource_type: str | None = None,
) -> dict[str, Any]:
    """
    Simpan file ke:
    <UPLOAD_DIR>/<folder>/YYYY/MM/DD/

    Return value sengaja kompatibel dengan struktur upload_result lama
    agar service teknisi tetap bisa memakai key ala Cloudinary.
    """
    extension = _safe_extension(file.filename or "")
    today = datetime.now()

    target_dir = (
        settings.upload_dir_path
        / _normalize_folder(folder)
        / str(today.year)
        / f"{today.month:02d}"
        / f"{today.day:02d}"
    )
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{uuid4().hex}{extension}"
    target_file = target_dir / filename

    bytes_written = 0

    with target_file.open("wb") as output:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break

            output.write(chunk)
            bytes_written += len(chunk)

    await file.seek(0)

    public_root = settings.public_root_dir_path
    try:
        relative_path = target_file.relative_to(public_root).as_posix()
    except ValueError as exc:
        raise ValueError("UPLOAD_DIR harus berada di dalam PUBLIC_ROOT_DIR.") from exc

    derived_resource_type = resource_type or (file.content_type or "").split("/", 1)[0] or "raw"
    file_format = extension.removeprefix(".") or None
    public_url = _build_public_url(relative_path)

    return {
        "public_id": relative_path,
        "secure_url": public_url,
        "resource_type": derived_resource_type,
        "format": file_format,
        "bytes": bytes_written,
        "width": None,
        "height": None,
        "duration": None,
        "disk_path": str(target_file),
        "relative_path": relative_path,
        "public_url": public_url,
        "filename": filename,
        "original_filename": file.filename,
        "content_type": file.content_type,
    }


def delete_uploaded_file(upload_result: dict[str, Any] | None) -> None:
    if not upload_result:
        return

    disk_path = upload_result.get("disk_path")
    if not disk_path:
        return

    file_path = Path(disk_path)
    try:
        file_path.unlink(missing_ok=True)
    except OSError:
        return

    upload_root = settings.upload_dir_path.resolve()
    current_dir = file_path.parent

    while current_dir != upload_root and current_dir.exists():
        try:
            current_dir.rmdir()
        except OSError:
            break
        current_dir = current_dir.parent


async def upload_checkin_photo(file: UploadFile) -> dict[str, Any]:
    return await save_uploaded_file(
        file=file,
        folder="checkins",
        resource_type="image",
    )


async def upload_resolution_video(file: UploadFile) -> dict[str, Any]:
    return await save_uploaded_file(
        file=file,
        folder="resolutions",
        resource_type="video",
    )
