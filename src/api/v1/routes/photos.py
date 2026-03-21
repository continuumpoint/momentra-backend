from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from src.models.schemas import (
    BulkPhotoUpdateRequest,
    BulkPhotoUpdateResponse,
    GalleryResponse,
    GuestAccessResponse,
    GuestRegisterRequest,
    GuestRegisterResponse,
    GuestSessionResponse,
    PhotoUploadResponse,
    PhotosListResponse,
)
from src.services.photo_service import PhotoService
from src.middleware.auth import get_current_organizer
import os

router = APIRouter(tags=["photos"])
_service = PhotoService()


def _frontend_base(request: Request) -> str:
    return os.getenv("FRONTEND_URL", str(request.base_url).rstrip("/"))


# ─── Guest ────────────────────────────────────────────────────────────────────

@router.get("/events/{event_id}/guest-access", response_model=GuestAccessResponse)
def guest_access(event_id: str):
    return _service.get_guest_access(event_id)


@router.post("/events/{event_id}/register-guest", response_model=GuestRegisterResponse, status_code=201)
def register_guest(event_id: str, body: GuestRegisterRequest):
    return _service.register_guest(event_id, body.guest_name, body.device_fingerprint)


@router.get("/events/{event_id}/guest-session", response_model=GuestSessionResponse)
def guest_session(event_id: str, device_fingerprint: str = Query(...)):
    return _service.get_guest_session(event_id, device_fingerprint)


@router.post("/events/{event_id}/upload", response_model=PhotoUploadResponse, status_code=201)
async def upload_photos(
    event_id: str,
    guest_name: str = Form(...),
    device_fingerprint: str = Form(...),
    files: List[UploadFile] = File(...),
):
    return await _service.upload_photos(event_id, guest_name, device_fingerprint, files)


# ─── Gallery (public) ─────────────────────────────────────────────────────────

@router.get("/events/{event_id}/gallery", response_model=GalleryResponse)
def get_gallery(event_id: str, request: Request):
    return _service.get_gallery(event_id, _frontend_base(request))


# ─── Organizer photo management ───────────────────────────────────────────────

@router.get("/events/{event_id}/photos", response_model=PhotosListResponse)
def list_photos(
    event_id: str,
    status: Optional[str] = Query(None, regex="^(pending|approved|rejected)$"),
    organizer_id: str = Depends(get_current_organizer),
):
    return _service.get_event_photos(event_id, organizer_id, status)


@router.patch("/photos/bulk-update", response_model=BulkPhotoUpdateResponse)
def bulk_update_photos(
    body: BulkPhotoUpdateRequest,
    request: Request,
    organizer_id: str = Depends(get_current_organizer),
):
    return _service.bulk_update_photos(organizer_id, body.photo_ids, body.action, _frontend_base(request))
