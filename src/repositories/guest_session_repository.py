from typing import Optional
from supabase import Client
from src.config.database import get_supabase_client
from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class GuestSessionRepository:
    def __init__(self, db: Client = None):
        self.db = db or get_supabase_client()

    def get_session(self, event_id: str, device_fingerprint: str) -> Optional[dict]:
        result = (
            self.db.table("guest_sessions")
            .select("*")
            .eq("event_id", event_id)
            .eq("device_fingerprint", device_fingerprint)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def create_session(self, event_id: str, device_fingerprint: str, guest_name: str) -> dict:
        result = (
            self.db.table("guest_sessions")
            .insert({
                "event_id": event_id,
                "device_fingerprint": device_fingerprint,
                "guest_name": guest_name,
                "photo_count": 0,
            })
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to create guest session")
        return result.data[0]

    def get_or_create_session(self, event_id: str, device_fingerprint: str, guest_name: str) -> dict:
        existing = self.get_session(event_id, device_fingerprint)
        if existing:
            return existing
        return self.create_session(event_id, device_fingerprint, guest_name)

    def increment_photo_count(self, session_id: str, increment: int) -> dict:
        # Use RPC to atomically increment; fallback: fetch-then-update
        session = (
            self.db.table("guest_sessions")
            .select("photo_count")
            .eq("id", session_id)
            .limit(1)
            .execute()
        )
        if not session.data:
            raise ValueError("Session not found")
        new_count = session.data[0]["photo_count"] + increment
        result = (
            self.db.table("guest_sessions")
            .update({"photo_count": new_count})
            .eq("id", session_id)
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to update photo count")
        return result.data[0]

    def remaining_uploads(self, session: dict) -> int:
        return max(0, settings.MAX_PHOTOS_PER_GUEST - session["photo_count"])
