import uuid
from supabase import Client
from src.config.database import get_supabase_client
from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class StorageRepository:
    def __init__(self, db: Client = None):
        self.db = db or get_supabase_client()

    def upload_photo(self, event_id: str, image_bytes: bytes, original_filename: str) -> str:
        """Upload compressed photo to Supabase Storage. Returns public URL."""
        file_id = uuid.uuid4().hex
        path = f"{event_id}/{file_id}.jpg"
        self.db.storage.from_(settings.STORAGE_BUCKET_PHOTOS).upload(
            path=path,
            file=image_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "false"},
        )
        public_url = self.db.storage.from_(settings.STORAGE_BUCKET_PHOTOS).get_public_url(path)
        return public_url

    def upload_qr_code(self, event_id: str, qr_bytes: bytes) -> str:
        """Upload QR code PNG to Supabase Storage. Returns public URL."""
        path = f"{event_id}/qr_code.png"
        self.db.storage.from_(settings.STORAGE_BUCKET_QR).upload(
            path=path,
            file=qr_bytes,
            file_options={"content-type": "image/png", "upsert": "true"},
        )
        public_url = self.db.storage.from_(settings.STORAGE_BUCKET_QR).get_public_url(path)
        return public_url
