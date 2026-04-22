from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.core.config import settings
from app.services.local_storage_service import get_vercel_blob_content

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/blob/{blob_path:path}")
async def get_blob_file(blob_path: str):
    if settings.STORAGE_BACKEND != "vercel_blob":
        raise HTTPException(status_code=404, detail="File tidak ditemukan")

    try:
        blob_data = await get_vercel_blob_content(blob_path)
    except Exception:
        raise HTTPException(status_code=404, detail="File tidak ditemukan")

    return Response(
        content=blob_data["content"],
        media_type=blob_data["content_type"],
        headers={
            "Cache-Control": blob_data["cache_control"],
            "ETag": blob_data["etag"],
        },
    )

