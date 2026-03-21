from fastapi import HTTPException, status
from src.repositories.organizer_repository import OrganizerRepository
from src.utils.jwt import create_access_token
from src.models.schemas import AuthResponse
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    def __init__(self):
        self.repo = OrganizerRepository()

    def register(self, email: str, password: str) -> AuthResponse:
        existing = self.repo.get_by_email(email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists.",
            )
        organizer = self.repo.create_organizer(email, password)
        token = create_access_token(str(organizer["id"]))
        return AuthResponse(organizer_id=str(organizer["id"]), token=token)

    def login(self, email: str, password: str) -> AuthResponse:
        organizer = self.repo.get_by_email(email)
        if not organizer or not self.repo.verify_password(password, organizer["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )
        token = create_access_token(str(organizer["id"]))
        return AuthResponse(organizer_id=str(organizer["id"]), token=token)
