from typing import Any

import httpx

from app.core.config import settings

_reverse_geocode_cache: dict[tuple[float, float], str] = {}


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").split())


def _includes_text(source: str, value: str) -> bool:
    return value.lower() in source.lower()


def _push_unique_segment(segments: list[str], value: str | None) -> None:
    normalized = _normalize_text(value)
    if not normalized:
        return

    already_exists = any(_includes_text(segment, normalized) for segment in segments)
    if not already_exists:
        segments.append(normalized)


def _join_segments(values: list[str | None], separator: str = ", ") -> str:
    return separator.join(filter(None, (_normalize_text(value) for value in values)))


def _extract_first_result(payload: dict[str, Any]) -> dict[str, Any]:
    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise ValueError("Alamat lengkap tidak ditemukan untuk koordinat saat ini.")

    result = results[0]
    if not isinstance(result, dict):
        raise ValueError("Format data alamat dari layanan peta tidak valid.")

    return result


def _build_fallback_address(result: dict[str, Any]) -> str:
    return _join_segments(
        [
            result.get("address_line1"),
            result.get("address_line2"),
            result.get("postcode"),
            result.get("country"),
        ]
    )


def _format_reverse_geocoded_address(result: dict[str, Any]) -> str:
    segments: list[str] = []
    display_name = _normalize_text(result.get("formatted"))
    location_label = _normalize_text(result.get("name"))
    postcode = _normalize_text(result.get("postcode"))

    if location_label and display_name and not _includes_text(display_name, location_label):
        _push_unique_segment(segments, location_label)

    if display_name:
        _push_unique_segment(segments, display_name)
    else:
        _push_unique_segment(segments, _build_fallback_address(result))

    if postcode and not _includes_text(", ".join(segments), postcode):
        _push_unique_segment(segments, postcode)

    return ", ".join(segments)


def reverse_geocode_location(latitude: float, longitude: float) -> dict[str, Any]:
    if not settings.GEOAPIFY_API_KEY.strip():
        raise ValueError("Geoapify API key belum dikonfigurasi di backend.")

    cache_key = (round(latitude, 6), round(longitude, 6))
    cached_address = _reverse_geocode_cache.get(cache_key)
    if cached_address:
        return {
            "latitude": latitude,
            "longitude": longitude,
            "full_address": cached_address,
        }

    params = {
        "lat": str(latitude),
        "lon": str(longitude),
        "format": "json",
        "limit": "1",
        "lang": settings.GEOAPIFY_LANG,
        "apiKey": settings.GEOAPIFY_API_KEY,
    }

    headers = {
        "Accept": "application/json",
    }

    try:
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers) as client:
            response = client.get(settings.GEOAPIFY_REVERSE_GEOCODE_URL, params=params)
            response.raise_for_status()

        payload = response.json()
    except httpx.HTTPError as exc:
        raise ValueError("Gagal mengambil alamat lengkap dari layanan peta.") from exc

    error_message = _normalize_text(payload.get("message") or payload.get("error"))
    if error_message:
        raise ValueError(error_message)

    full_address = _format_reverse_geocoded_address(_extract_first_result(payload))
    if not full_address:
        raise ValueError("Alamat lengkap tidak ditemukan untuk koordinat saat ini.")

    _reverse_geocode_cache[cache_key] = full_address

    return {
        "latitude": latitude,
        "longitude": longitude,
        "full_address": full_address,
    }
