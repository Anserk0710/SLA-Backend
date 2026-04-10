from app.services import location_service


def test_format_reverse_geocoded_address_uses_name_when_missing_from_formatted() -> None:
    result = {
        "name": "Menara Palma",
        "formatted": "Jl. H. R. Rasuna Said Kav. 6, Jakarta Selatan 12950, Indonesia",
        "postcode": "12950",
    }

    formatted_address = location_service._format_reverse_geocoded_address(result)

    assert formatted_address == (
        "Menara Palma, Jl. H. R. Rasuna Said Kav. 6, Jakarta Selatan 12950, Indonesia"
    )


def test_reverse_geocode_location_reads_geoapify_result(monkeypatch) -> None:
    location_service._reverse_geocode_cache.clear()
    captured_request: dict[str, object] = {}

    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "results": [
                    {
                        "formatted": "Jl. H. R. Rasuna Said Kav. 6, Jakarta Selatan 12950, Indonesia",
                        "address_line1": "Jl. H. R. Rasuna Said Kav. 6",
                        "address_line2": "Jakarta Selatan 12950, Indonesia",
                        "postcode": "12950",
                    }
                ]
            }

    class DummyClient:
        def __init__(self, **kwargs) -> None:
            captured_request["client_kwargs"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def get(self, url: str, params: dict[str, str]) -> DummyResponse:
            captured_request["url"] = url
            captured_request["params"] = params
            return DummyResponse()

    monkeypatch.setattr(location_service.httpx, "Client", DummyClient)
    monkeypatch.setattr(location_service.settings, "GEOAPIFY_API_KEY", "test-key")
    monkeypatch.setattr(
        location_service.settings,
        "GEOAPIFY_REVERSE_GEOCODE_URL",
        "https://api.geoapify.com/v1/geocode/reverse",
    )
    monkeypatch.setattr(location_service.settings, "GEOAPIFY_LANG", "id")

    result = location_service.reverse_geocode_location(-6.21462, 106.84513)

    assert result == {
        "latitude": -6.21462,
        "longitude": 106.84513,
        "full_address": "Jl. H. R. Rasuna Said Kav. 6, Jakarta Selatan 12950, Indonesia",
    }
    assert captured_request["url"] == "https://api.geoapify.com/v1/geocode/reverse"
    assert captured_request["params"] == {
        "lat": "-6.21462",
        "lon": "106.84513",
        "format": "json",
        "limit": "1",
        "lang": "id",
        "apiKey": "test-key",
    }
    assert captured_request["client_kwargs"] == {
        "timeout": 15.0,
        "follow_redirects": True,
        "headers": {"Accept": "application/json"},
    }
