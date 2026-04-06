import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.init_db import init_db

logger = logging.getLogger(__name__)

fastapi_app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

fastapi_app.include_router(api_router, prefix=settings.API_V1_STR)

@fastapi_app.on_event("startup")
def on_startup() -> None:
    try:
        summary = init_db()
        logger.info(
            "Startup init_db completed",
            extra={
                "created_roles": summary.created_roles,
                "created_users": summary.created_users,
                "updated_users": summary.updated_users,
            },
        )
    except Exception:
        logger.exception("Startup init_db failed")
        raise

@fastapi_app.get("/")
def root():
    return {"message": "Selamat datang di API SLA!"}

@fastapi_app.get("/health")
def health_check():
    return {"status": "ok"}

# Wrap the whole app so CORS headers are still present on error responses.
app = CORSMiddleware(
    app=fastapi_app,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
