from typing import Optional
import bcrypt
from supabase import Client
from src.config.database import get_supabase_client
from src.utils.logging import get_logger

logger = get_logger(__name__)


class OrganizerRepository:
    def __init__(self, db: Client = None):
        self.db = db or get_supabase_client()

    def hash_password(self, plain: str) -> str:
        """Hash a plaintext password using bcrypt."""
        password_bytes = plain.encode("utf-8")
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    def verify_password(self, plain: str, hashed: str) -> bool:
        """Verify a plaintext password against a bcrypt hash."""
        try:
            return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

    def create_organizer(self, email: str, password: str) -> dict:
        password_hash = self.hash_password(password)
        result = (
            self.db.table("organizers")
            .insert({"email": email, "password_hash": password_hash})
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to create organizer")
        return result.data[0]

    def get_by_email(self, email: str) -> Optional[dict]:
        result = (
            self.db.table("organizers")
            .select("*")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_by_id(self, organizer_id: str) -> Optional[dict]:
        result = (
            self.db.table("organizers")
            .select("id, email, created_at")
            .eq("id", organizer_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
