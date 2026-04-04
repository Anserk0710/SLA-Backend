import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.init_db import init_db

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.PROJECT_NAME, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.on_event("startup")
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

@app.get("/")
def root():
    return {"message": "Selamat datang di API SLA!"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
