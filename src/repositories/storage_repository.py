import uuid
from fastapi import HTTPException, status
from supabase import Client
from src.config.database import get_supabase_client
from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# How long a signed URL stays valid (in seconds).
# 24 hours is generous enough that a user won't hit an expired
# image mid-session, but short enough to limit exposure.
SIGNED_URL_EXPIRY_SECONDS = 60 * 60 * 24  # 24 hours


class StorageRepository:
    def __init__(self, db: Client = None):
        self.db = db or get_supabase_client()

    def upload_photo(self, event_id: str, image_bytes: bytes, original_filename: str) -> str:
        """
        Upload compressed photo to Supabase Storage.
        Returns the storage PATH (not a URL) so we can generate
        fresh signed URLs on demand rather than storing an expiring URL.
        """
        file_id = uuid.uuid4().hex
        path = f"{event_id}/{file_id}.jpg"
        self.db.storage.from_(settings.STORAGE_BUCKET_PHOTOS).upload(
            path=path,
            file=image_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "false"},
        )
        # Return the path, not the URL — we sign on read
        return path

    def upload_qr_code(self, event_id: str, qr_bytes: bytes) -> str:
        """
        Upload QR code PNG to Supabase Storage.
        Returns a long-lived signed URL since QR codes are not sensitive.
        """
        path = f"{event_id}/qr_code.png"
        self.db.storage.from_(settings.STORAGE_BUCKET_QR).upload(
            path=path,
            file=qr_bytes,
            file_options={"content-type": "image/png", "upsert": "true"},
        )
        # QR codes can have a 1-year expiry
        try:
            signed = self.db.storage.from_(settings.STORAGE_BUCKET_QR).create_signed_url(
                path=path,
                expires_in=60 * 60 * 24 * 365,
            )
            logger.info("Supabase create_signed_url response: %s", signed)
            return signed["signedURL"]
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate QR code URL. Please try again.",
            )

    def get_signed_url(self, path: str) -> str:
        """
        Generate a fresh signed URL for a single photo path.
        Call this every time you need to serve a photo to the frontend.
        """
        try:
            signed = self.db.storage.from_(settings.STORAGE_BUCKET_PHOTOS).create_signed_url(
                path=path,
                expires_in=SIGNED_URL_EXPIRY_SECONDS,
            )
            logger.info("Supabase create_signed_url (photo) response: %s", signed)
            return signed["signedURL"]
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate access URL for image. Please try again.",
            )

    def get_signed_urls_bulk(self, paths: list[str]) -> dict[str, str]:
        """
        Generate signed URLs for multiple paths in one Supabase call.
        Returns a dict of { path: signed_url }.
        Skips any paths that are already full URLs (legacy photos stored
        before the signed URL migration).
        """
        if not paths:
            return {}

        # Separate legacy full URLs from storage paths
        storage_paths = [p for p in paths if not p.startswith("http")]
        legacy_urls = {p: p for p in paths if p.startswith("http")}

        if not storage_paths:
            return legacy_urls

        try:
            results = self.db.storage.from_(settings.STORAGE_BUCKET_PHOTOS).create_signed_urls(
                paths=storage_paths,
                expires_in=SIGNED_URL_EXPIRY_SECONDS,
            )
            logger.info("Supabase create_signed_urls (bulk) response: %s", results)
            signed = {
                item["path"]: item["signedURL"]
                for item in results
                if item and item.get("signedURL")
            }
            # Merge signed URLs with legacy full URLs
            return {**signed, **legacy_urls}
        except Exception as exc:
            logger.error("Failed to generate bulk signed URLs: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate image URLs. Please refresh and try again.",
            )