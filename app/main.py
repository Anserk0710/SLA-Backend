from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import PublicFormRateLimitMiddleware, RequestLoggingMiddleware
from app.db.init_db import init_db

setup_logging()

logger = get_logger(__name__)


def _mount_local_uploads(app: FastAPI) -> None:
    uses_local_storage = bool(getattr(settings, "uses_local_storage", False))
    if not uses_local_storage:
        return

    upload_dir_path = getattr(settings, "upload_dir_path", None)
    upload_url_prefix = getattr(settings, "UPLOAD_URL_PREFIX", "/uploads")
    if upload_dir_path is None:
        return

    app.mount(
        upload_url_prefix,
        StaticFiles(directory=str(upload_dir_path), check_dir=False),
        name="uploads",
    )


def _build_error_response(
    request: Request,
    *,
    status_code: int,
    content: dict,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    response = JSONResponse(
        status_code=status_code,
        content={
            **content,
            "request_id": request_id,
        },
    )
    if request_id:
        response.headers["X-Request-ID"] = request_id
    return response


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        debug=settings.DEBUG,
    )

    # Tambahkan rate limit lebih dulu agar request logging membungkus semua response,
    # termasuk 429 dari limiter.
    app.add_middleware(PublicFormRateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    if settings.allowed_hosts:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.allowed_hosts,
        )

    if settings.ENVIRONMENT == "production":
        app.add_middleware(HTTPSRedirectMiddleware)

    _mount_local_uploads(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

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
                    "patched_ticket_schema": getattr(summary, "patched_ticket_schema", False),
                },
            )
        except Exception:
            logger.exception("Startup init_db failed")
            raise

    @app.get("/")
    def root() -> dict[str, str]:
        return {"message": "Selamat datang di API SLA!"}

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "environment": settings.ENVIRONMENT,
        }

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return _build_error_response(
            request,
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _build_error_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validasi request gagal.",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled exception",
            extra={
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
                "method": request.method,
            },
        )
        return _build_error_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "Terjadi kesalahan internal pada server.",
            },
        )

    return app


fastapi_app = create_app()

# Wrap the whole app so CORS headers are still present on error responses.
app = CORSMiddleware(
    app=fastapi_app,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
