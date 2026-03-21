from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.utils.jwt import decode_access_token

bearer_scheme = HTTPBearer()


def get_current_organizer(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """FastAPI dependency — returns organizer_id from JWT."""
    return decode_access_token(credentials.credentials)
