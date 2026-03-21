from fastapi import APIRouter
from src.models.schemas import OrganizerRegisterRequest, OrganizerLoginRequest, AuthResponse
from src.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
_service = AuthService()


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(body: OrganizerRegisterRequest):
    return _service.register(body.email, body.password)


@router.post("/login", response_model=AuthResponse)
def login(body: OrganizerLoginRequest):
    return _service.login(body.email, body.password)
