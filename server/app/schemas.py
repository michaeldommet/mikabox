"""
MikaBox API Schemas
===================

Pydantic models for request/response validation.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    display_name: str = Field(default="Parent", max_length=100)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Child Profiles ────────────────────────────────────────────────────

class ProfileCreate(BaseModel):
    name: str = Field(max_length=100)
    age: int = Field(ge=0, le=18)
    avatar: str = Field(default="🐻", max_length=50)


class ProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    age: Optional[int] = Field(None, ge=0, le=18)
    avatar: Optional[str] = Field(None, max_length=50)


class ProfileResponse(BaseModel):
    id: str
    name: str
    age: int
    avatar: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Devices ───────────────────────────────────────────────────────────

class DevicePair(BaseModel):
    device_id: str = Field(max_length=100)
    name: str = Field(default="MikaBox", max_length=100)


class DeviceResponse(BaseModel):
    id: str
    device_id: str
    name: str
    is_online: bool
    last_seen: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceState(BaseModel):
    device_id: str
    state: str
    server_connected: bool
    current_track: Optional[dict] = None
    volume: int
    nfc_tag: Optional[str] = None
    profile_id: str
    usage_today_minutes: float
    remaining_minutes: float


# ── Content ───────────────────────────────────────────────────────────

class ContentResponse(BaseModel):
    id: str
    title: str
    author: str
    description: str
    category: str
    age_min: int
    age_max: int
    duration_seconds: int
    cover_image: str
    is_free: bool

    model_config = {"from_attributes": True}


class ContentUpload(BaseModel):
    title: str = Field(max_length=255)
    author: str = Field(default="", max_length=255)
    description: str = Field(default="", max_length=2000)
    category: str = Field(default="audiobook")
    age_min: int = Field(default=0, ge=0)
    age_max: int = Field(default=12, le=18)


# ── Parental Controls ────────────────────────────────────────────────

class ParentalRuleCreate(BaseModel):
    rule_type: str  # daily_limit, bedtime, volume_cap, blocked_content
    value: str      # JSON-encoded value


class ParentalRuleResponse(BaseModel):
    id: str
    rule_type: str
    value: str
    is_active: bool

    model_config = {"from_attributes": True}


class ParentalControlsUpdate(BaseModel):
    daily_limit_minutes: Optional[int] = Field(None, ge=15, le=480)
    bedtime_start: Optional[str] = None   # "HH:MM"
    bedtime_end: Optional[str] = None     # "HH:MM"
    volume_cap: Optional[int] = Field(None, ge=0, le=100)
    blocked_content_ids: Optional[list[str]] = None


# ── Memory ────────────────────────────────────────────────────────────

class MemoryFactResponse(BaseModel):
    id: str
    fact: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Usage ─────────────────────────────────────────────────────────────

class UsageLogCreate(BaseModel):
    event: str
    content_id: Optional[str] = None
    trigger: str = ""
    tag_uid: str = ""
    profile_id: str = "default"
    duration_seconds: float = 0.0


class UsageLogResponse(BaseModel):
    id: str
    event_type: str
    duration_seconds: float
    created_at: datetime

    model_config = {"from_attributes": True}


class UsageSummary(BaseModel):
    today_minutes: float
    week_minutes: float
    month_minutes: float
    top_content: list[dict]
    daily_breakdown: list[dict]


# ── Remote Control ────────────────────────────────────────────────────

class RemoteCommand(BaseModel):
    command: str  # play, pause, resume, stop, skip_forward, skip_back, set_volume
    payload: dict = Field(default_factory=dict)


# ── NFC Mapping ───────────────────────────────────────────────────────

class NFCMappingCreate(BaseModel):
    tag_uid: str
    content_id: str
    label: str = ""


class NFCMappingResponse(BaseModel):
    id: str
    tag_uid: str
    content_id: str
    label: str

    model_config = {"from_attributes": True}
