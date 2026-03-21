from typing import Optional, List
from supabase import Client
from datetime import datetime, timezone
from src.config.database import get_supabase_client
from src.utils.logging import get_logger

logger = get_logger(__name__)


class PhotoRepository:
    def __init__(self, db: Client = None):
        self.db = db or get_supabase_client()

    def create_photo(
        self,
        event_id: str,
        guest_name: str,
        device_fingerprint: str,
        file_url: str,
        file_size_bytes: int,
    ) -> dict:
        result = (
            self.db.table("photos")
            .insert({
                "event_id": event_id,
                "guest_name": guest_name,
                "device_fingerprint": device_fingerprint,
                "file_url": file_url,
                "file_size_bytes": file_size_bytes,
                "status": "pending",
            })
            .execute()
        )
        if not result.data:
            raise ValueError("Failed to create photo record")
        return result.data[0]

    def get_by_event(self, event_id: str, status: Optional[str] = None) -> List[dict]:
        query = self.db.table("photos").select("*").eq("event_id", event_id)
        if status:
            query = query.eq("status", status)
        result = query.order("uploaded_at", desc=True).execute()
        return result.data or []

    def bulk_update_status(self, photo_ids: List[str], status: str) -> int:
        """Updates status for all given photo IDs. Returns count updated."""
        reviewed_at = datetime.now(timezone.utc).isoformat()
        result = (
            self.db.table("photos")
            .update({"status": status, "reviewed_at": reviewed_at})
            .in_("id", photo_ids)
            .execute()
        )
        return len(result.data) if result.data else 0

    def get_approved_for_gallery(self, event_id: str) -> List[dict]:
        result = (
            self.db.table("photos")
            .select("id, file_url, guest_name, uploaded_at")
            .eq("event_id", event_id)
            .eq("status", "approved")
            .order("uploaded_at", desc=True)
            .execute()
        )
        return result.data or []
