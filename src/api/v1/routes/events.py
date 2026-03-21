from fastapi import APIRouter, Depends, Request
from src.models.schemas import (
    EventCreateRequest,
    EventResponse,
    EventDetailResponse,
    QRCodeResponse,
)
from src.services.event_service import EventService
from src.middleware.auth import get_current_organizer

router = APIRouter(prefix="/events", tags=["events"])
_service = EventService()


@router.post("", response_model=EventResponse, status_code=201)
def create_event(
    body: EventCreateRequest,
    request: Request,
    organizer_id: str = Depends(get_current_organizer),
):
    return _service.create_event(
        organizer_id=organizer_id,
        event_name=body.event_name,
        event_start_time=body.event_start_time,
        event_end_time=body.event_end_time,
        request=request,
    )


@router.get("/{event_id}", response_model=EventDetailResponse)
def get_event(
    event_id: str,
    request: Request,
    organizer_id: str = Depends(get_current_organizer),
):
    return _service.get_event(event_id, organizer_id, request)


@router.post("/{event_id}/qr-code", response_model=QRCodeResponse)
def generate_qr_code(
    event_id: str,
    request: Request,
    organizer_id: str = Depends(get_current_organizer),
):
    return _service.generate_qr_code(event_id, organizer_id, request)
