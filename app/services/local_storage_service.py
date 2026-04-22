import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings
from app.services import cloudinary_service


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


def _build_blob_proxy_url(blob_path: str) -> str:
    prefix = settings.API_V1_PREFIX.rstrip("/")
    proxy_path = f"{prefix}/files/blob/{blob_path.lstrip('/')}"
    return _build_public_url(proxy_path)


def _get_storage_backend() -> str:
    return getattr(settings, "STORAGE_BACKEND", "local").strip().lower()


def _ensure_vercel_blob_configured() -> str:
    token = getattr(settings, "blob_read_write_token", None)
    if not token:
        raise ValueError("BLOB_READ_WRITE_TOKEN wajib diisi saat STORAGE_BACKEND=vercel_blob.")
    return token


def _get_blob_access() -> str:
    access = getattr(settings, "BLOB_ACCESS", "public").strip().lower()
    if access not in {"public", "private"}:
        raise ValueError("BLOB_ACCESS tidak valid. Gunakan public atau private.")
    return access


def _build_blob_path(folder: str, filename: str | None) -> tuple[str, str | None]:
    extension = _safe_extension(filename or "")
    file_format = extension.removeprefix(".") or None
    today = datetime.now()
    unique_name = f"{uuid4().hex}{extension}"
    path = f"{folder.strip('/').strip()}/{today.year}/{today.month:02d}/{today.day:02d}/{unique_name}"
    return path, file_format


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


async def _save_uploaded_file_to_cloudinary(
    file: UploadFile,
    *,
    folder: str,
    resource_type: str | None = None,
) -> dict[str, Any]:
    await file.seek(0)

    if folder.strip("/").strip() == "checkins":
        upload_result = cloudinary_service.upload_checkin_photo(file.file, filename=file.filename)
    else:
        upload_result = cloudinary_service.upload_resolution_video(file.file, filename=file.filename)

    await file.seek(0)

    if resource_type and not upload_result.get("resource_type"):
        upload_result["resource_type"] = resource_type

    extension = _safe_extension(file.filename or "")
    upload_result.setdefault("format", extension.removeprefix(".") or None)
    upload_result.setdefault("bytes", 0)
    upload_result.setdefault("original_filename", file.filename)
    upload_result.setdefault("content_type", file.content_type)

    return upload_result


async def _save_uploaded_file_to_vercel_blob(
    file: UploadFile,
    *,
    folder: str,
    resource_type: str | None = None,
) -> dict[str, Any]:
    # Import lazily agar backend local/cloudinary tidak bergantung pada package ini saat startup.
    from vercel.blob import AsyncBlobClient

    token = _ensure_vercel_blob_configured()
    blob_access = _get_blob_access()
    blob_path, file_format = _build_blob_path(folder, file.filename)
    await file.seek(0)
    file_bytes = await file.read()

    client = AsyncBlobClient(token=token)
    try:
        put_result = await client.put(
            blob_path,
            file_bytes,
            access=blob_access,
            content_type=file.content_type or None,
            add_random_suffix=False,
            overwrite=False,
        )
    finally:
        await client.aclose()

    await file.seek(0)

    derived_resource_type = resource_type or (file.content_type or "").split("/", 1)[0] or "raw"
    blob_public_url = (
        _build_blob_proxy_url(put_result.pathname)
        if blob_access == "private"
        else put_result.url
    )

    return {
        "public_id": put_result.pathname,
        "secure_url": blob_public_url,
        "resource_type": derived_resource_type,
        "format": file_format,
        "bytes": len(file_bytes),
        "width": None,
        "height": None,
        "duration": None,
        "disk_path": None,
        "relative_path": put_result.pathname,
        "public_url": blob_public_url,
        "filename": Path(put_result.pathname).name,
        "original_filename": file.filename,
        "content_type": put_result.content_type or file.content_type,
        "blob_access": blob_access,
        "blob_url": put_result.url,
        "blob_download_url": put_result.download_url,
    }


async def get_vercel_blob_content(blob_path: str) -> dict[str, Any]:
    from vercel.blob import AsyncBlobClient

    token = _ensure_vercel_blob_configured()
    blob_access = _get_blob_access()
    normalized_path = blob_path.strip().lstrip("/")
    if not normalized_path:
        raise ValueError("Path blob tidak valid.")

    client = AsyncBlobClient(token=token)
    try:
        blob_result = await client.get(
            normalized_path,
            access=blob_access,
            timeout=30,
            use_cache=True,
        )
    finally:
        await client.aclose()

    return {
        "content": blob_result.content,
        "content_type": blob_result.content_type or "application/octet-stream",
        "cache_control": blob_result.cache_control,
        "etag": blob_result.etag,
    }


async def _upload_by_active_backend(
    file: UploadFile,
    folder: str,
    *,
    resource_type: str | None = None,
) -> dict[str, Any]:
    storage_backend = _get_storage_backend()
    if storage_backend == "local":
        return await save_uploaded_file(file=file, folder=folder, resource_type=resource_type)
    if storage_backend == "cloudinary":
        return await _save_uploaded_file_to_cloudinary(
            file=file,
            folder=folder,
            resource_type=resource_type,
        )
    if storage_backend == "vercel_blob":
        return await _save_uploaded_file_to_vercel_blob(
            file=file,
            folder=folder,
            resource_type=resource_type,
        )

    raise ValueError("STORAGE_BACKEND tidak didukung.")


async def _delete_uploaded_file_from_vercel_blob(upload_result: dict[str, Any]) -> None:
    from vercel.blob import AsyncBlobClient

    token = _ensure_vercel_blob_configured()
    blob_ref = (
        upload_result.get("public_id")
        or upload_result.get("relative_path")
        or upload_result.get("blob_url")
        or upload_result.get("secure_url")
        or upload_result.get("public_url")
    )
    if not blob_ref:
        return

    client = AsyncBlobClient(token=token)
    try:
        await client.delete(blob_ref)
    finally:
        await client.aclose()


def delete_uploaded_file(upload_result: dict[str, Any] | None) -> None:
    if not upload_result:
        return

    storage_backend = _get_storage_backend()
    if storage_backend == "vercel_blob":
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_delete_uploaded_file_from_vercel_blob(upload_result))
        else:
            loop.create_task(_delete_uploaded_file_from_vercel_blob(upload_result))
        return

    if storage_backend != "local":
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
    return await _upload_by_active_backend(
        file=file,
        folder="checkins",
        resource_type="image",
    )


async def upload_resolution_video(file: UploadFile) -> dict[str, Any]:
    return await _upload_by_active_backend(
        file=file,
        folder="resolutions",
        resource_type="video",
    )
