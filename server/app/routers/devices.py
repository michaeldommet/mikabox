"""Device management router — pairing, status, NFC mappings."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, Device, NFCMapping
from ..schemas import DevicePair, DeviceResponse, DeviceState, NFCMappingCreate, NFCMappingResponse
from ..auth import get_current_user
from ..services import device_service

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.post("/pair", response_model=DeviceResponse, status_code=201)
async def pair_device(
    data: DevicePair,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Pair a new MikaBox device to this account."""
    # Check if device already paired
    result = await db.execute(select(Device).where(Device.device_id == data.device_id))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Device already paired.")

    device = Device(
        user_id=user.id,
        device_id=data.device_id,
        name=data.name,
        pairing_token=str(uuid.uuid4()),
    )
    db.add(device)
    await db.flush()
    return device


@router.get("/", response_model=list[DeviceResponse])
async def list_devices(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Device).where(Device.user_id == user.id))
    return result.scalars().all()


@router.post("/state")
async def update_device_state(
    state: DeviceState,
    db: AsyncSession = Depends(get_db),
):
    """Receive state update from a device (called by device firmware)."""
    result = await db.execute(select(Device).where(Device.device_id == state.device_id))
    device = result.scalar_one_or_none()
    if device:
        device.is_online = True
        device.last_seen = datetime.now(timezone.utc)
        
    # Broadcast the new state to listening web apps
    await device_service.broadcast_device_state(state.device_id, state.model_dump())
    
    return {"status": "ok"}


@router.post("/nfc-mappings", response_model=NFCMappingResponse, status_code=201)
async def create_nfc_mapping(
    data: NFCMappingCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Map an NFC tag to content for a device."""
    # Get user's device
    result = await db.execute(select(Device).where(Device.user_id == user.id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="No device found.")

    mapping = NFCMapping(
        device_id=device.id,
        tag_uid=data.tag_uid,
        content_id=data.content_id,
        label=data.label,
    )
    db.add(mapping)
    await db.flush()
    return mapping


@router.get("/nfc-mappings", response_model=list[NFCMappingResponse])
async def list_nfc_mappings(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NFCMapping)
        .join(Device)
        .where(Device.user_id == user.id)
    )
    return result.scalars().all()
