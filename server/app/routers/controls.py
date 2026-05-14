"""Remote control router — send commands to the device."""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, Device, ParentalRule
from ..schemas import RemoteCommand, ParentalControlsUpdate
from ..auth import get_current_user

router = APIRouter(prefix="/api/controls", tags=["controls"])

# In-memory device connection registry (simple prototype approach)
# In production, use Redis pub/sub or a message queue
_device_commands: dict[str, list[dict]] = {}


@router.post("/send")
async def send_command(
    cmd: RemoteCommand,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a remote command to the MikaBox device."""
    result = await db.execute(select(Device).where(Device.user_id == user.id))
    device = result.scalars().first()
    if not device:
        raise HTTPException(status_code=404, detail="No device found.")

    # Queue command for device to pick up
    if device.device_id not in _device_commands:
        _device_commands[device.device_id] = []

    _device_commands[device.device_id].append({
        "command": cmd.command,
        "payload": cmd.payload,
    })

    return {"status": "sent", "command": cmd.command}


@router.get("/pending/{device_id}")
async def get_pending_commands(device_id: str):
    """Device polls for pending commands (fallback if WebSocket is unavailable)."""
    commands = _device_commands.pop(device_id, [])
    return {"commands": commands}


@router.get("/rules")
async def get_parental_rules(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get active parental control rules for the user's profiles."""
    result = await db.execute(
        select(ParentalRule)
        .join(ParentalRule.profile)
        .where(ParentalRule.profile.has(user_id=user.id))
        .where(ParentalRule.is_active == True)
    )
    rules = result.scalars().all()

    # Flatten into a rules dict
    rules_dict = {}
    for rule in rules:
        try:
            rules_dict[rule.rule_type] = json.loads(rule.value)
        except json.JSONDecodeError:
            rules_dict[rule.rule_type] = rule.value

    return rules_dict


@router.put("/rules")
async def update_parental_controls(
    update: ParentalControlsUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update parental control settings."""
    # For prototype, update rules for the first profile
    from ..models import ChildProfile
    result = await db.execute(
        select(ChildProfile).where(ChildProfile.user_id == user.id)
    )
    profile = result.scalars().first()
    if not profile:
        raise HTTPException(status_code=404, detail="No child profile found.")

    # Upsert rules
    for rule_type, value in update.model_dump(exclude_none=True).items():
        result = await db.execute(
            select(ParentalRule).where(
                ParentalRule.profile_id == profile.id,
                ParentalRule.rule_type == rule_type,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = json.dumps(value)
        else:
            db.add(ParentalRule(
                profile_id=profile.id,
                rule_type=rule_type,
                value=json.dumps(value),
            ))

    # Queue rules update to device
    device_result = await db.execute(select(Device).where(Device.user_id == user.id))
    device = device_result.scalars().first()
    if device and device.device_id:
        if device.device_id not in _device_commands:
            _device_commands[device.device_id] = []
        _device_commands[device.device_id].append({
            "command": "update_rules",
            "payload": update.model_dump(exclude_none=True),
        })

    return {"status": "updated"}
