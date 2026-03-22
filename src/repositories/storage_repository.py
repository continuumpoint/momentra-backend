import uuid
from fastapi import HTTPException, status
from supabase import Client
from src.config.database import get_supabase_client
from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

SIGNED_URL_EXPIRY_SECONDS = 60 * 60 * 24  # 24 hours


class StorageRepository:
    def __init__(self, db: Client = None):
        self.db = db or get_supabase_client()

    def upload_photo(self, event_id: str, image_bytes: bytes, original_filename: str) -> str:
        """Upload compressed photo. Returns storage PATH not URL."""
        file_id = uuid.uuid4().hex
        path = f"{event_id}/{file_id}.jpg"
        self.db.storage.from_(settings.STORAGE_BUCKET_PHOTOS).upload(
            path=path,
            file=image_bytes,
            file_options={"content-type": "image/jpeg", "upsert": "false"},
        )
        return path

    def _extract_signed_url(self, signed: dict) -> str:
        """Extract signed URL from Supabase response regardless of key name."""
        logger.info("Supabase signed URL response: %s", signed)
        url = (
            signed.get("signedURL")
            or signed.get("signed_url")
            or signed.get("signedUrl")
            or ""
        )
        return url

    def upload_qr_code(self, event_id: str, qr_bytes: bytes) -> str:
        """Upload QR code PNG. Returns a long-lived signed URL."""
        path = f"{event_id}/qr_code.png"
        self.db.storage.from_(settings.STORAGE_BUCKET_QR).upload(
            path=path,
            file=qr_bytes,
            file_options={"content-type": "image/png", "upsert": "true"},
        )
        try:
            signed = self.db.storage.from_(settings.STORAGE_BUCKET_QR).create_signed_url(
                path=path,
                expires_in=60 * 60 * 24 * 365,
            )
            return self._extract_signed_url(signed)
        except Exception as exc:
            logger.error("Failed to generate signed URL for QR code %s: %s", path, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate QR code URL. Please try again.",
            )

    def get_signed_url(self, path: str) -> str:
        """Generate a fresh signed URL for a single photo path."""
        try:
            signed = self.db.storage.from_(settings.STORAGE_BUCKET_PHOTOS).create_signed_url(
                path=path,
                expires_in=SIGNED_URL_EXPIRY_SECONDS,
            )
            return self._extract_signed_url(signed)
        except Exception as exc:
            logger.error("Failed to generate signed URL for path %s: %s", path, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate access URL for image. Please try again.",
            )

    def get_signed_urls_bulk(self, paths: list[str]) -> dict[str, str]:
        """Generate signed URLs for multiple paths in one Supabase call."""
        if not paths:
            return {}

        storage_paths = [p for p in paths if not p.startswith("http")]
        legacy_urls = {p: p for p in paths if p.startswith("http")}

        if not storage_paths:
            return legacy_urls

        try:
            results = self.db.storage.from_(settings.STORAGE_BUCKET_PHOTOS).create_signed_urls(
                paths=storage_paths,
                expires_in=SIGNED_URL_EXPIRY_SECONDS,
            )
            logger.info("Supabase bulk signed URLs response: %s", results)
            signed = {}
            for item in results:
                if not item:
                    continue
                url = (
                    item.get("signedURL")
                    or item.get("signed_url")
                    or item.get("signedUrl")
                )
                path = item.get("path")
                if path and url:
                    signed[path] = url
            return {**signed, **legacy_urls}
        except Exception as exc:
            logger.error("Failed to generate bulk signed URLs: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate image URLs. Please refresh and try again.",
            )

    def delete_photo(self, path: str) -> bool:
        """Delete a photo from Supabase Storage by its path."""
        try:
            self.db.storage.from_(settings.STORAGE_BUCKET_PHOTOS).remove([path])
            return True
        except Exception as exc:
            logger.error("Failed to delete photo from storage %s: %s", path, exc)
            return False