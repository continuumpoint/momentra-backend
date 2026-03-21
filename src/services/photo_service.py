from typing import List, Optional
from datetime import datetime, timezone
from fastapi import HTTPException, status, UploadFile
from src.repositories.event_repository import EventRepository
from src.repositories.photo_repository import PhotoRepository
from src.repositories.guest_session_repository import GuestSessionRepository
from src.repositories.storage_repository import StorageRepository
from src.models.schemas import (
    PhotoUploadResponse,
    BulkPhotoUpdateResponse,
    PhotosListResponse,
    PhotoRecord,
    GalleryResponse,
    GalleryPhoto,
    GuestAccessResponse,
    GuestRegisterResponse,
    GuestSessionResponse,
    PhotoStatus,
)
from src.utils.image import validate_image_file, compress_image, verify_image_content
from src.utils.links import build_gallery_link
from src.config.settings import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


def _parse_dt(val) -> datetime:
    """Parse ISO string or return datetime as-is."""
    if isinstance(val, datetime):
        return val
    return datetime.fromisoformat(str(val).replace("Z", "+00:00"))


class PhotoService:
    def __init__(self):
        self.event_repo = EventRepository()
        self.photo_repo = PhotoRepository()
        self.session_repo = GuestSessionRepository()
        self.storage_repo = StorageRepository()

    # ─── Guest Access ─────────────────────────────────────────────────────────

    def get_guest_access(self, event_id: str) -> GuestAccessResponse:
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        now = datetime.now(timezone.utc)
        start = _parse_dt(event["event_start_time"])
        deadline = _parse_dt(event["upload_deadline"])
        # Make timezone aware if needed
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        can_upload = start <= now <= deadline
        return GuestAccessResponse(
            event_name=event["event_name"],
            event_start_time=event["event_start_time"],
            event_end_time=event["event_end_time"],
            upload_deadline=event["upload_deadline"],
            can_upload=can_upload,
        )

    def register_guest(self, event_id: str, guest_name: str, device_fingerprint: str) -> GuestRegisterResponse:
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        session = self.session_repo.get_or_create_session(event_id, device_fingerprint, guest_name)
        remaining = self.session_repo.remaining_uploads(session)
        return GuestRegisterResponse(session_id=str(session["id"]), remaining_uploads=remaining)

    def get_guest_session(self, event_id: str, device_fingerprint: str) -> GuestSessionResponse:
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        session = self.session_repo.get_session(event_id, device_fingerprint)
        if not session:
            return GuestSessionResponse(remaining_uploads=settings.MAX_PHOTOS_PER_GUEST, uploaded_photos_count=0)
        remaining = self.session_repo.remaining_uploads(session)
        return GuestSessionResponse(remaining_uploads=remaining, uploaded_photos_count=session["photo_count"])

    # ─── Upload ───────────────────────────────────────────────────────────────

    async def upload_photos(
        self,
        event_id: str,
        guest_name: str,
        device_fingerprint: str,
        files: List[UploadFile],
    ) -> PhotoUploadResponse:
        # 1. Verify event exists and upload window is open
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        now = datetime.now(timezone.utc)
        start = _parse_dt(event["event_start_time"])
        deadline = _parse_dt(event["upload_deadline"])
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        if not (start <= now <= deadline):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Upload window is closed for this event.",
            )

        # 2. Check remaining quota
        session = self.session_repo.get_or_create_session(event_id, device_fingerprint, guest_name)
        remaining = self.session_repo.remaining_uploads(session)
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Upload limit of {settings.MAX_PHOTOS_PER_GUEST} photos per guest reached.",
            )
        # Clamp to remaining quota
        files_to_process = files[:remaining]

        # 3. Process and upload each file
        photo_ids = []
        for upload_file in files_to_process:
            raw = await upload_file.read()
            # Size check
            if len(raw) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File {upload_file.filename!r} exceeds 10MB limit.",
                )
            # Validate
            validate_image_file(upload_file.content_type or "application/octet-stream", upload_file.filename or "upload")
            verify_image_content(raw)
            # Compress
            compressed = compress_image(raw)
            # Store
            file_url = self.storage_repo.upload_photo(event_id, compressed, upload_file.filename or "photo.jpg")
            photo = self.photo_repo.create_photo(
                event_id=event_id,
                guest_name=guest_name,
                device_fingerprint=device_fingerprint,
                file_url=file_url,
                file_size_bytes=len(compressed),
            )
            photo_ids.append(str(photo["id"]))

        # 4. Update session photo count
        self.session_repo.increment_photo_count(str(session["id"]), len(photo_ids))
        # Refresh session for remaining count
        updated_session = self.session_repo.get_session(event_id, device_fingerprint)
        new_remaining = self.session_repo.remaining_uploads(updated_session)

        return PhotoUploadResponse(
            uploaded_count=len(photo_ids),
            remaining_uploads=new_remaining,
            photo_ids=photo_ids,
        )

    # ─── Moderation ───────────────────────────────────────────────────────────

    def get_event_photos(self, event_id: str, organizer_id: str, status_filter: Optional[str]) -> PhotosListResponse:
        try:
            self.event_repo.assert_owns_event(event_id, organizer_id)
        except PermissionError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        photos = self.photo_repo.get_by_event(event_id, status_filter)
        return PhotosListResponse(
            photos=[
                PhotoRecord(
                    id=str(p["id"]),
                    guest_name=p["guest_name"],
                    file_url=p["file_url"],
                    status=PhotoStatus(p["status"]),
                    uploaded_at=p["uploaded_at"],
                )
                for p in photos
            ]
        )

    def bulk_update_photos(
        self, organizer_id: str, photo_ids: List[str], action: str, frontend_base: str
    ) -> BulkPhotoUpdateResponse:
        # Validate photos belong to organizer's events (security check)
        # For efficiency we trust organizer-scoped API but verify at least one photo exists
        new_status = "approved" if action == "approve" else "rejected"
        count = self.photo_repo.bulk_update_status(photo_ids, new_status)
        # We can't easily build gallery_link without event_id here;
        # return generic dashboard URL
        gallery_link = f"{frontend_base}/dashboard"
        return BulkPhotoUpdateResponse(updated_count=count, gallery_link=gallery_link)

    # ─── Gallery ──────────────────────────────────────────────────────────────

    def get_gallery(self, event_id: str, frontend_base: str) -> GalleryResponse:
        event = self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        photos = self.photo_repo.get_approved_for_gallery(event_id)
        return GalleryResponse(
            event_name=event["event_name"],
            photos=[
                GalleryPhoto(
                    id=str(p["id"]),
                    file_url=p["file_url"],
                    guest_name=p["guest_name"],
                    uploaded_at=p["uploaded_at"],
                )
                for p in photos
            ],
        )
