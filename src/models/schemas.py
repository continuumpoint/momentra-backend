from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class PhotoStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ─── Auth ─────────────────────────────────────────────────────────────────────

class OrganizerRegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class OrganizerLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    organizer_id: str
    token: str


# ─── Events ───────────────────────────────────────────────────────────────────

class EventCreateRequest(BaseModel):
    event_name: str
    event_start_time: datetime
    event_end_time: datetime

    @field_validator("event_end_time")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        start = info.data.get("event_start_time")
        if start and v <= start:
            raise ValueError("event_end_time must be after event_start_time")
        return v


class EventResponse(BaseModel):
    event_id: str
    event_name: str
    event_start_time: datetime
    event_end_time: datetime
    upload_deadline: datetime
    upload_link: str
    gallery_link: str
    qr_code_url: Optional[str] = None


class EventDetailResponse(BaseModel):
    event_id: str
    event_name: str
    event_start_time: datetime
    event_end_time: datetime
    upload_deadline: datetime
    upload_link: str
    gallery_link: str
    qr_code_url: Optional[str] = None
    created_at: datetime


class EventsListResponse(BaseModel):
    events: List[EventResponse]


# ─── Guest ────────────────────────────────────────────────────────────────────

class GuestAccessResponse(BaseModel):
    event_name: str
    event_start_time: datetime
    event_end_time: datetime
    upload_deadline: datetime
    can_upload: bool


class GuestRegisterRequest(BaseModel):
    guest_name: str
    device_fingerprint: str

    @field_validator("guest_name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("guest_name cannot be empty")
        return v

    @field_validator("device_fingerprint")
    @classmethod
    def fingerprint_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("device_fingerprint cannot be empty")
        return v


class GuestRegisterResponse(BaseModel):
    session_id: str
    remaining_uploads: int


class GuestSessionResponse(BaseModel):
    remaining_uploads: int
    uploaded_photos_count: int


# ─── Photos ───────────────────────────────────────────────────────────────────

class PhotoRecord(BaseModel):
    id: str
    guest_name: str
    file_url: str
    status: PhotoStatus
    uploaded_at: datetime


class PhotoUploadResponse(BaseModel):
    uploaded_count: int
    remaining_uploads: int
    photo_ids: List[str]


class BulkPhotoUpdateRequest(BaseModel):
    photo_ids: List[str]
    action: str

    @field_validator("action")
    @classmethod
    def valid_action(cls, v: str) -> str:
        if v not in ("approve", "reject"):
            raise ValueError("action must be 'approve' or 'reject'")
        return v

    @field_validator("photo_ids")
    @classmethod
    def ids_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("photo_ids cannot be empty")
        return v


class BulkPhotoUpdateResponse(BaseModel):
    updated_count: int
    gallery_link: str


class PhotosListResponse(BaseModel):
    photos: List[PhotoRecord]


# ─── Gallery ──────────────────────────────────────────────────────────────────

class GalleryPhoto(BaseModel):
    id: str
    file_url: str
    guest_name: str
    uploaded_at: datetime


class GalleryResponse(BaseModel):
    event_name: str
    photos: List[GalleryPhoto]


# ─── QR Code ──────────────────────────────────────────────────────────────────

class QRCodeResponse(BaseModel):
    qr_code_url: str


# ─── Error ────────────────────────────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str