from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_dependencies():
    with patch("src.main.ConversationHandler"):
        yield


@pytest.fixture(scope="module")
def app():
    # Import inside the fixture to ensure any module-level mocks are applied
    # and to avoid side effects during test collection
    from src.main import app
    return app


@pytest.fixture(scope="module")
def client(app):
    return TestClient(app)


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the AWS-FCJ-Backend API"}


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_me_requires_bearer_token(client):
    response = client.get("/user-info")
    assert response.status_code in (401, 403)


def test_me_returns_user_profile(client):
    from src.auth.jwt_handler import create_access_token

    token = create_access_token(data={"sub": "me@example.com"})

    with patch(
        "src.routers.auth.login.users_collection.find_one", new_callable=AsyncMock
    ) as mock_find_one:
        mock_find_one.return_value = {
            "_id": "user-id-1",
            "email": "me@example.com",
            "is_verified": True,
            "name": "Me",
            "role": "admin",
        }

        response = client.get(
            "/user-info", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me@example.com"
        assert data["id"] == "user-id-1"
        assert data["name"] == "Me"
        assert data["role"] == "admin"


def test_me_404_when_user_missing(client):
    from src.auth.jwt_handler import create_access_token

    token = create_access_token(data={"sub": "missing@example.com"})

    with patch(
        "src.routers.auth.login.users_collection.find_one", new_callable=AsyncMock
    ) as mock_find_one:
        mock_find_one.return_value = None

        response = client.get(
            "/user-info", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404
