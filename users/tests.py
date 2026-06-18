import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from .factories import AdminFactory, ReviewerFactory, UserFactory

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user():
    return UserFactory()


@pytest.fixture
def auth_client(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ── Registration ─────────────────────────────────────────────


@pytest.mark.django_db
class TestRegister:
    def test_register_success(self, api_client):
        resp = api_client.post("/api/users/register/", {
            "username": "newuser",
            "email": "new@example.com",
            "password": "StrongP@ss123",
        })
        assert resp.status_code == 201
        assert resp.data["username"] == "newuser"
        assert "password" not in resp.data

    def test_register_duplicate_username(self, api_client, user):
        resp = api_client.post("/api/users/register/", {
            "username": user.username,
            "email": "other@example.com",
            "password": "StrongP@ss123",
        })
        assert resp.status_code == 400

    def test_register_weak_password(self, api_client):
        resp = api_client.post("/api/users/register/", {
            "username": "weak",
            "email": "weak@example.com",
            "password": "123",
        })
        assert resp.status_code == 400


# ── Token obtain ─────────────────────────────────────────────


@pytest.mark.django_db
class TestTokenObtain:
    def test_obtain_tokens(self, api_client, user):
        resp = api_client.post("/api/token/", {
            "username": user.username,
            "password": "testpass123",
        })
        assert resp.status_code == 200
        assert "access" in resp.data
        assert "refresh" in resp.data

    def test_bad_credentials(self, api_client, user):
        resp = api_client.post("/api/token/", {
            "username": user.username,
            "password": "wrongpass",
        })
        assert resp.status_code == 401


# ── Logout (token blacklist) ─────────────────────────────────


@pytest.mark.django_db
class TestLogout:
    def test_logout_blacklists_token(self, user):
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

        resp = client.post("/api/users/logout/", {"refresh": str(refresh)})
        assert resp.status_code == 205

        resp = client.post("/api/token/refresh/", {"refresh": str(refresh)})
        assert resp.status_code == 401

    def test_logout_without_token(self, auth_client):
        resp = auth_client.post("/api/users/logout/", {})
        assert resp.status_code == 400


# ── Me endpoint ──────────────────────────────────────────────


@pytest.mark.django_db
class TestMe:
    def test_get_me(self, auth_client, user):
        resp = auth_client.get("/api/users/me/")
        assert resp.status_code == 200
        assert resp.data["username"] == user.username
        assert resp.data["role"] == "author"

    def test_update_me(self, auth_client):
        resp = auth_client.patch("/api/users/me/", {"bio": "Hello"})
        assert resp.status_code == 200
        assert resp.data["bio"] == "Hello"

    def test_unauthenticated(self, api_client):
        resp = api_client.get("/api/users/me/")
        assert resp.status_code == 401


# ── RBAC ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestRBAC:
    def test_user_roles(self):
        author = UserFactory()
        reviewer = ReviewerFactory()
        admin = AdminFactory()
        assert author.role == "author"
        assert reviewer.role == "reviewer"
        assert admin.role == "admin"
