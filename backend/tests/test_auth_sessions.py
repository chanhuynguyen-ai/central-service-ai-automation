from fastapi.testclient import TestClient

from app.db.session import get_db
from app.models.models import AuthSession, User


def _login(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "employee@centralops.demo",
            "password": "Employee123!",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_login_returns_access_and_refresh_tokens(client: TestClient) -> None:
    body = _login(client)

    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "employee@centralops.demo"


def test_refresh_token_is_stored_only_as_hash(client: TestClient) -> None:
    body = _login(client)

    db_provider = client.app.dependency_overrides[get_db]
    db_generator = db_provider()
    db = next(db_generator)
    try:
        session = db.query(AuthSession).order_by(AuthSession.id.desc()).first()
        assert session is not None
        assert session.refresh_token_hash != body["refresh_token"]
        assert len(session.refresh_token_hash) == 64
    finally:
        db_generator.close()


def test_refresh_rotates_token_and_rejects_reuse(client: TestClient) -> None:
    login_body = _login(client)
    first_refresh = login_body["refresh_token"]

    rotated = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert rotated.status_code == 200
    second_refresh = rotated.json()["refresh_token"]
    assert second_refresh != first_refresh
    assert rotated.json()["access_token"]

    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh},
    )
    assert reused.status_code == 401

    second_rotation = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": second_refresh},
    )
    assert second_rotation.status_code == 200


def test_logout_revokes_refresh_session(client: TestClient) -> None:
    body = _login(client)
    refresh_token = body["refresh_token"]

    logout = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout.status_code == 204

    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh.status_code == 401


def test_refresh_rejects_deactivated_user(client: TestClient) -> None:
    body = _login(client)

    db_provider = client.app.dependency_overrides[get_db]
    db_generator = db_provider()
    db = next(db_generator)
    try:
        user = db.query(User).filter(User.email == "employee@centralops.demo").first()
        assert user is not None
        user.is_active = False
        db.commit()
    finally:
        db_generator.close()

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": body["refresh_token"]},
    )
    assert response.status_code == 401


def test_auth_me_returns_current_user(client: TestClient) -> None:
    body = _login(client)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "employee@centralops.demo"
