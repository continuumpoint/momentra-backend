"""
Integration-style tests using FastAPI TestClient with mocked Supabase.
Run with: pytest tests/ -v
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Patch settings before app import so env vars aren't required
with patch.dict("os.environ", {
    "JWT_SECRET": "test_secret_key_32_chars_minimum!!",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_KEY": "test_key",
    "ALLOWED_ORIGINS": '["http://localhost:3000"]',
    "FRONTEND_URL": "http://localhost:3000",
}):
    from src.main import app

client = TestClient(app)

# ─── Fixtures ────────────────────────────────────────────────────────────────

MOCK_ORGANIZER = {
    "id": "aaaaaaaa-0000-0000-0000-000000000001",
    "email": "test@example.com",
    "password_hash": "$2b$12$KIX/4iBcm5xDPpBXm8mEpOlWBPzE7jV4eN5oLw/VmTAEqyeKHmMuG",
    "created_at": "2025-01-01T00:00:00Z",
}

MOCK_EVENT = {
    "id": "bbbbbbbb-0000-0000-0000-000000000001",
    "organizer_id": MOCK_ORGANIZER["id"],
    "event_name": "Test Wedding",
    "event_start_time": "2025-06-01T14:00:00Z",
    "event_end_time": "2025-06-01T22:00:00Z",
    "upload_deadline": "2025-06-03T10:00:00Z",
    "qr_code_url": None,
    "created_at": "2025-05-01T00:00:00Z",
    "updated_at": "2025-05-01T00:00:00Z",
}


# ─── Health Check ─────────────────────────────────────────────────────────────

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# ─── Auth ─────────────────────────────────────────────────────────────────────

class TestAuthRegister:
    @patch("src.repositories.organizer_repository.OrganizerRepository.get_by_email", return_value=None)
    @patch("src.repositories.organizer_repository.OrganizerRepository.create_organizer", return_value=MOCK_ORGANIZER)
    def test_register_success(self, mock_create, mock_get):
        response = client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "securepass123",
        })
        assert response.status_code == 201
        data = response.json()
        assert "token" in data
        assert "organizer_id" in data

    @patch("src.repositories.organizer_repository.OrganizerRepository.get_by_email", return_value=MOCK_ORGANIZER)
    def test_register_duplicate_email(self, mock_get):
        response = client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "securepass123",
        })
        assert response.status_code == 409

    def test_register_weak_password(self):
        response = client.post("/api/v1/auth/register", json={
            "email": "new@example.com",
            "password": "short",
        })
        assert response.status_code == 422

    def test_register_invalid_email(self):
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "password": "securepass123",
        })
        assert response.status_code == 422


class TestAuthLogin:
    @patch("src.repositories.organizer_repository.OrganizerRepository.get_by_email", return_value=MOCK_ORGANIZER)
    @patch("src.repositories.organizer_repository.OrganizerRepository.verify_password", return_value=True)
    def test_login_success(self, mock_verify, mock_get):
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "password123",
        })
        assert response.status_code == 200
        assert "token" in response.json()

    @patch("src.repositories.organizer_repository.OrganizerRepository.get_by_email", return_value=None)
    def test_login_wrong_email(self, mock_get):
        response = client.post("/api/v1/auth/login", json={
            "email": "nobody@example.com",
            "password": "password123",
        })
        assert response.status_code == 401

    @patch("src.repositories.organizer_repository.OrganizerRepository.get_by_email", return_value=MOCK_ORGANIZER)
    @patch("src.repositories.organizer_repository.OrganizerRepository.verify_password", return_value=False)
    def test_login_wrong_password(self, mock_verify, mock_get):
        response = client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword",
        })
        assert response.status_code == 401


# ─── Events ───────────────────────────────────────────────────────────────────

def _get_token():
    """Get a valid JWT for the mock organizer."""
    from src.utils.jwt import create_access_token
    return create_access_token(MOCK_ORGANIZER["id"])


class TestEvents:
    @patch("src.repositories.event_repository.EventRepository.create_event", return_value=MOCK_EVENT)
    def test_create_event_success(self, mock_create):
        token = _get_token()
        response = client.post(
            "/api/v1/events",
            json={
                "event_name": "Test Wedding",
                "event_start_time": "2025-06-01T14:00:00Z",
                "event_end_time": "2025-06-01T22:00:00Z",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["event_name"] == "Test Wedding"
        assert "upload_link" in data
        assert "gallery_link" in data

    def test_create_event_no_auth(self):
        response = client.post("/api/v1/events", json={
            "event_name": "Test",
            "event_start_time": "2025-06-01T14:00:00Z",
            "event_end_time": "2025-06-01T22:00:00Z",
        })
        assert response.status_code == 403

    def test_create_event_end_before_start(self):
        token = _get_token()
        response = client.post(
            "/api/v1/events",
            json={
                "event_name": "Bad Event",
                "event_start_time": "2025-06-01T22:00:00Z",
                "event_end_time": "2025-06-01T14:00:00Z",
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    @patch("src.repositories.event_repository.EventRepository.get_by_id", return_value=MOCK_EVENT)
    def test_get_event_success(self, mock_get):
        token = _get_token()
        event_id = MOCK_EVENT["id"]
        response = client.get(
            f"/api/v1/events/{event_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["event_name"] == "Test Wedding"

    @patch("src.repositories.event_repository.EventRepository.get_by_id", return_value=None)
    def test_get_event_not_found(self, mock_get):
        token = _get_token()
        response = client.get(
            "/api/v1/events/nonexistent-id",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 404


# ─── Guest Access ─────────────────────────────────────────────────────────────

class TestGuestAccess:
    @patch("src.repositories.event_repository.EventRepository.get_by_id", return_value=MOCK_EVENT)
    def test_guest_access_returns_event_info(self, mock_get):
        response = client.get(f"/api/v1/events/{MOCK_EVENT['id']}/guest-access")
        assert response.status_code == 200
        data = response.json()
        assert "event_name" in data
        assert "can_upload" in data

    @patch("src.repositories.event_repository.EventRepository.get_by_id", return_value=None)
    def test_guest_access_not_found(self, mock_get):
        response = client.get("/api/v1/events/nonexistent/guest-access")
        assert response.status_code == 404


# ─── Image Validation ─────────────────────────────────────────────────────────

class TestImageValidation:
    def test_invalid_mime_type_rejected(self):
        from src.utils.image import validate_image_file
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            validate_image_file("application/pdf", "document.pdf")
        assert exc_info.value.status_code == 422

    def test_valid_jpeg_accepted(self):
        from src.utils.image import validate_image_file
        # Should not raise
        validate_image_file("image/jpeg", "photo.jpg")

    def test_valid_png_accepted(self):
        from src.utils.image import validate_image_file
        validate_image_file("image/png", "photo.png")
