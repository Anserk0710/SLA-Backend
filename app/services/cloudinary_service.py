import cloudinary
import cloudinary.uploader

from app.core.config import settings


def ensure_cloudinary_configured() -> None:
    if not settings.CLOUDINARY_CLOUD_NAME or not settings.CLOUDINARY_API_KEY or not settings.CLOUDINARY_API_SECRET:
        raise ValueError("Konfigurasi Cloudinary belum lengkap.")


def configure_cloudinary() -> None:
    ensure_cloudinary_configured()
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_checkin_photo(file_obj, filename: str | None = None) -> dict:
    configure_cloudinary()
    return cloudinary.uploader.upload(
        file_obj,
        folder=f"{settings.CLOUDINARY_FOLDER}/checkins",
        resource_type="image",
        use_filename=True,
        unique_filename=True,
        overwrite=False,
        filename_override=filename,
    )


def upload_resolution_video(file_obj, filename: str | None = None) -> dict:
    configure_cloudinary()
    return cloudinary.uploader.upload(
        file_obj,
        folder=f"{settings.CLOUDINARY_FOLDER}/resolutions",
        resource_type="video",
        use_filename=True,
        unique_filename=True,
        overwrite=False,
        filename_override=filename,
    )