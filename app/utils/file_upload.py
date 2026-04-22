from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}

ALLOWED_VIDEO_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
}

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}


async def _validate_upload(
    file: UploadFile,
    *,
    allowed_content_types: set[str],
    allowed_extensions: set[str],
    max_size_mb: int,
    field_label: str,
) -> dict[str, str | int | float]:
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_label} wajib diisi.",
        )

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nama file {field_label} tidak valid.",
        )

    extension = Path(file.filename).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ekstensi file {field_label} tidak didukung.",
        )

    content_type = (file.content_type or "").lower()
    if content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipe file {field_label} tidak didukung.",
        )

    max_bytes = max_size_mb * 1024 * 1024
    size_bytes = 0

    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break

        size_bytes += len(chunk)

        if size_bytes > max_bytes:
            await file.seek(0)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ukuran {field_label} melebihi {max_size_mb}MB.",
            )

    await file.seek(0)

    if size_bytes == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File {field_label} kosong.",
        )

    return {
        "filename": file.filename,
        "extension": extension,
        "content_type": content_type,
        "size_bytes": size_bytes,
        "size_mb": round(size_bytes / (1024 * 1024), 2),
    }


async def validate_image_upload(file: UploadFile) -> dict[str, str | int | float]:
    return await _validate_upload(
        file=file,
        allowed_content_types=ALLOWED_IMAGE_CONTENT_TYPES,
        allowed_extensions=ALLOWED_IMAGE_EXTENSIONS,
        max_size_mb=settings.MAX_IMAGE_UPLOAD_MB,
        field_label="foto",
    )


async def validate_video_upload(file: UploadFile) -> dict[str, str | int | float]:
    return await _validate_upload(
        file=file,
        allowed_content_types=ALLOWED_VIDEO_CONTENT_TYPES,
        allowed_extensions=ALLOWED_VIDEO_EXTENSIONS,
        max_size_mb=settings.MAX_VIDEO_UPLOAD_MB,
        field_label="video",
    )
