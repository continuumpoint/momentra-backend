import io
import qrcode
from datetime import datetime, timezone
from fastapi import HTTPException, status, Request
from src.repositories.event_repository import EventRepository
from src.repositories.storage_repository import StorageRepository
from src.models.schemas import EventResponse, EventDetailResponse, EventsListResponse, QRCodeResponse
from src.utils.links import build_upload_link, build_gallery_link
from src.utils.logging import get_logger

logger = get_logger(__name__)


def _get_frontend_base(request: Request) -> str:
    """Derive frontend base URL from request or env."""
    import os
    return os.getenv("FRONTEND_URL", str(request.base_url).rstrip("/"))


class EventService:
    def __init__(self):
        self.event_repo = EventRepository()
        self.storage_repo = StorageRepository()

    def _build_response(self, event: dict, base_url: str) -> dict:
        return {
            "event_id": str(event["id"]),
            "event_name": event["event_name"],
            "event_start_time": event["event_start_time"],
            "event_end_time": event["event_end_time"],
            "upload_deadline": event["upload_deadline"],
            "upload_link": build_upload_link(str(event["id"]), base_url),
            "gallery_link": build_gallery_link(str(event["id"]), base_url),
            "qr_code_url": event.get("qr_code_url"),
        }

    def create_event(
        self,
        organizer_id: str,
        event_name: str,
        event_start_time: datetime,
        event_end_time: datetime,
        request: Request,
    ) -> EventResponse:
        event = self.event_repo.create_event(
            organizer_id=organizer_id,
            event_name=event_name.strip(),
            event_start_time=event_start_time.isoformat(),
            event_end_time=event_end_time.isoformat(),
        )
        base_url = _get_frontend_base(request)
        data = self._build_response(event, base_url)
        return EventResponse(**data)

    def list_events(self, organizer_id: str, request: Request) -> EventsListResponse:
        """Returns all events belonging to the authenticated organiser."""
        events = self.event_repo.get_by_organizer(organizer_id)
        base_url = _get_frontend_base(request)
        return EventsListResponse(
            events=[
                EventResponse(**self._build_response(e, base_url))
                for e in events
            ]
        )

    def get_event(self, event_id: str, organizer_id: str, request: Request) -> EventDetailResponse:
        try:
            event = self.event_repo.assert_owns_event(event_id, organizer_id)
        except PermissionError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
        base_url = _get_frontend_base(request)
        data = self._build_response(event, base_url)
        data["created_at"] = event["created_at"]
        return EventDetailResponse(**data)

    def generate_qr_code(self, event_id: str, organizer_id: str, request: Request) -> QRCodeResponse:
        try:
            event = self.event_repo.assert_owns_event(event_id, organizer_id)
        except PermissionError:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        except ValueError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

        base_url = _get_frontend_base(request)
        upload_link = build_upload_link(event_id, base_url)

        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(upload_link)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_bytes = buf.getvalue()

        qr_url = self.storage_repo.upload_qr_code(event_id, qr_bytes)
        self.event_repo.update_qr_code_url(event_id, qr_url)
        return QRCodeResponse(qr_code_url=qr_url)
    