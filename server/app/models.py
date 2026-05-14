"""
MikaBox Database Models
=======================
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    """Parent / admin account."""
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), default="Parent")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    profiles: Mapped[list["ChildProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    devices: Mapped[list["Device"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    consent_records: Mapped[list["ConsentRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class ChildProfile(Base):
    """Per-child profile with age and preferences."""
    __tablename__ = "child_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    avatar: Mapped[str] = mapped_column(String(50), default="🐻")  # Emoji avatar
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profiles")
    parental_rules: Mapped[list["ParentalRule"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    usage_logs: Mapped[list["UsageLog"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    memory_facts: Mapped[list["MemoryFact"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class Device(Base):
    """A paired MikaBox device."""
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    device_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), default="MikaBox")
    pairing_token: Mapped[str] = mapped_column(String(255), nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship(back_populates="devices")
    nfc_mappings: Mapped[list["NFCMapping"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class Content(Base):
    """Audio content metadata."""
    __tablename__ = "content"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    author: Mapped[str] = mapped_column(String(255), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="audiobook")  # audiobook, music, story, educational
    age_min: Mapped[int] = mapped_column(Integer, default=0)
    age_max: Mapped[int] = mapped_column(Integer, default=12)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    cover_image: Mapped[str] = mapped_column(String(255), default="")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    is_free: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class NFCMapping(Base):
    """Maps NFC tag UIDs to content."""
    __tablename__ = "nfc_mappings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"), nullable=False)
    tag_uid: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    content_id: Mapped[str] = mapped_column(ForeignKey("content.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    device: Mapped["Device"] = relationship(back_populates="nfc_mappings")
    content: Mapped["Content"] = relationship()


class UsageLog(Base):
    """Listening history for usage monitoring."""
    __tablename__ = "usage_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("child_profiles.id"), nullable=False)
    content_id: Mapped[Optional[str]] = mapped_column(ForeignKey("content.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # play_start, play_end, voice_command
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    profile: Mapped["ChildProfile"] = relationship(back_populates="usage_logs")


class MemoryFact(Base):
    """Personal facts Mika has learned about the child."""
    __tablename__ = "memory_facts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("child_profiles.id"), nullable=False)
    fact: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    profile: Mapped["ChildProfile"] = relationship(back_populates="memory_facts")


class ParentalRule(Base):
    """Parental control rules per profile."""
    __tablename__ = "parental_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    profile_id: Mapped[str] = mapped_column(ForeignKey("child_profiles.id"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)  # daily_limit, bedtime, volume_cap, blocked_content
    value: Mapped[str] = mapped_column(Text, nullable=False)  # JSON-encoded value
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    profile: Mapped["ChildProfile"] = relationship(back_populates="parental_rules")


class ConsentRecord(Base):
    """COPPA compliance — tracks parental consent."""
    __tablename__ = "consent_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(100), nullable=False)  # data_collection, voice_recording, etc.
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ip_address: Mapped[str] = mapped_column(String(45), default="")

    # Relationships
    user: Mapped["User"] = relationship(back_populates="consent_records")
