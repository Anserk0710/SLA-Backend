import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _normalize_path(path: str) -> str:
    normalized = path.rstrip("/")
    return normalized or "/"


def _get_client_ip(request: Request) -> str:
    # Vercel dan reverse proxy umumnya meneruskan IP client lewat header ini.
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",")[0].strip()
        if first_ip:
            return first_ip

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        normalized = real_ip.strip()
        if normalized:
            return normalized

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id

        started_at = time.perf_counter()
        response = await call_next(request)

        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        logger.info(
            "request_completed | request_id=%s | method=%s | path=%s | status=%s | duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )

        return response


class InMemoryRateLimiter:
    """
    Cocok untuk single backend instance.
    Jika nanti multi-instance, pindahkan storage ke Redis/shared store.
    """

    def __init__(self) -> None:
        self._storage: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow_request(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()

        with self._lock:
            bucket = self._storage[key]

            while bucket and (now - bucket[0]) >= window_seconds:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return False, retry_after

            bucket.append(now)
            return True, 0


rate_limiter = InMemoryRateLimiter()


class PublicFormRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        target_path = f"{settings.API_V1_PREFIX}/public/tickets"
        is_target_path = _normalize_path(request.url.path) == target_path
        is_target_method = request.method.upper() == "POST"

        if is_target_path and is_target_method:
            client_ip = _get_client_ip(request)
            rate_key = f"public-form:{client_ip}"

            is_allowed, retry_after = rate_limiter.allow_request(
                key=rate_key,
                limit=settings.PUBLIC_FORM_RATE_LIMIT,
                window_seconds=settings.PUBLIC_FORM_RATE_WINDOW_SECONDS,
            )

            if not is_allowed:
                logger.warning(
                    "rate_limited | request_id=%s | client_ip=%s | path=%s | retry_after=%s",
                    getattr(request.state, "request_id", "unknown"),
                    client_ip,
                    request.url.path,
                    retry_after,
                )
                return JSONResponse(
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                    content={
                        "detail": "Terlalu banyak percobaan. Silakan coba lagi beberapa saat.",
                        "retry_after_seconds": retry_after,
                    },
                )

        return await call_next(request)
