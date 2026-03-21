from typing import Optional, List
from datetime import datetime, timezone, timedelta
from supabase import Client
from src.config.database import get_supabase_client
from src.utils.logging import get_logger

logger = get_logger(__name__)


class EventRepository:
    def __init__(self, db: Client = None):
        self.db = db or get_supabase_client()

    def create_event(self, organizer_id: str, event_name: str, event_start_time: str, event_end_time: str) -> dict:
        # Compute upload_deadline = event_end_time + 36 hours (app layer, not DB generated column)
        end_dt = datetime.fromisoformat(event_end_time.replace("Z", "+00:00"))
        upload_deadline = (end_dt + timedelta(hours=36)).isoformat()

        result = (
            self.db.table("events")
            .insert({
                "organizer_id": organizer_id,
                "event_name": event_name,
                "event_start_time": event_start_time,
                "event_end_time": event_end_time,
                "upload_deadline": upload_deadline,
            })
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to create event")
        return result.data[0]

    def get_by_id(self, event_id: str) -> Optional[dict]:
        result = (
            self.db.table("events")
            .select("*")
            .eq("id", event_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_by_organizer(self, organizer_id: str) -> List[dict]:
        result = (
            self.db.table("events")
            .select("*")
            .eq("organizer_id", organizer_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def update_qr_code_url(self, event_id: str, qr_code_url: str) -> dict:
        result = (
            self.db.table("events")
            .update({"qr_code_url": qr_code_url})
            .eq("id", event_id)
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to update QR code URL")
        return result.data[0]

    def assert_owns_event(self, event_id: str, organizer_id: str) -> dict:
        """Returns event if organizer owns it, else raises ValueError."""
        event = self.get_by_id(event_id)
        if not event:
            raise ValueError("Event not found")
        if event["organizer_id"] != organizer_id:
            raise PermissionError("You do not own this event")
        return event
