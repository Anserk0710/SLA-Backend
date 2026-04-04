from fastapi.testclient import TestClient

from app.core.config import settings


def test_login_success(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={
            "username": settings.FIRST_SUPERUSER_EMAIL,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == settings.FIRST_SUPERUSER_EMAIL
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


def test_login_invalid_password_returns_401(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={
            "username": settings.FIRST_SUPERUSER_EMAIL,
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Email atau password salah"


def test_login_email_is_trimmed_and_case_insensitive(client: TestClient) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        data={
            "username": f"  {settings.FIRST_SUPERUSER_EMAIL.upper()}  ",
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )

    assert response.status_code == 200
