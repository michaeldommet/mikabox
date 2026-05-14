"""Privacy service — COPPA compliance, data review, and deletion."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import User, ConsentRecord, UsageLog, ChildProfile

logger = logging.getLogger("mikabox.service.privacy")


async def grant_consent(
    user_id: str,
    consent_type: str,
    ip_address: str,
    db: AsyncSession,
) -> ConsentRecord:
    """Record parental consent for a specific data use."""
    record = ConsentRecord(
        user_id=user_id,
        consent_type=consent_type,
        granted=True,
        granted_at=datetime.now(timezone.utc),
        ip_address=ip_address,
    )
    db.add(record)
    await db.flush()
    logger.info("Consent granted: user=%s type=%s", user_id, consent_type)
    return record


async def revoke_consent(
    user_id: str,
    consent_type: str,
    db: AsyncSession,
) -> bool:
    """Revoke a previously granted consent."""
    result = await db.execute(
        select(ConsentRecord).where(
            ConsentRecord.user_id == user_id,
            ConsentRecord.consent_type == consent_type,
            ConsentRecord.granted == True,
        )
    )
    record = result.scalar_one_or_none()
    if record:
        record.granted = False
        record.revoked_at = datetime.now(timezone.utc)
        logger.info("Consent revoked: user=%s type=%s", user_id, consent_type)
        return True
    return False


async def get_user_data_export(user_id: str, db: AsyncSession) -> dict:
    """
    Export all data associated with a user (COPPA: right to review).
    Returns a structured dict of all stored data.
    """
    # Profiles
    profiles_result = await db.execute(
        select(ChildProfile).where(ChildProfile.user_id == user_id)
    )
    profiles = profiles_result.scalars().all()

    # Usage logs
    profile_ids = [p.id for p in profiles]
    usage_result = await db.execute(
        select(UsageLog).where(UsageLog.profile_id.in_(profile_ids))
    ) if profile_ids else None
    usage_logs = usage_result.scalars().all() if usage_result else []

    # Consent records
    consent_result = await db.execute(
        select(ConsentRecord).where(ConsentRecord.user_id == user_id)
    )
    consents = consent_result.scalars().all()

    return {
        "profiles": [
            {"name": p.name, "age": p.age, "created_at": str(p.created_at)}
            for p in profiles
        ],
        "usage_logs": [
            {
                "event": l.event_type,
                "duration_seconds": l.duration_seconds,
                "created_at": str(l.created_at),
            }
            for l in usage_logs
        ],
        "consent_records": [
            {
                "type": c.consent_type,
                "granted": c.granted,
                "granted_at": str(c.granted_at) if c.granted_at else None,
                "revoked_at": str(c.revoked_at) if c.revoked_at else None,
            }
            for c in consents
        ],
    }


async def delete_user_data(user_id: str, db: AsyncSession) -> dict:
    """
    Delete all data associated with a user (COPPA: right to delete).
    Returns a summary of what was deleted.
    """
    # Get profile IDs
    profiles_result = await db.execute(
        select(ChildProfile.id).where(ChildProfile.user_id == user_id)
    )
    profile_ids = list(profiles_result.scalars().all())

    deleted = {"usage_logs": 0, "profiles": 0, "consents": 0}

    # Delete usage logs
    if profile_ids:
        result = await db.execute(
            delete(UsageLog).where(UsageLog.profile_id.in_(profile_ids))
        )
        deleted["usage_logs"] = result.rowcount

    # Delete consent records
    result = await db.execute(
        delete(ConsentRecord).where(ConsentRecord.user_id == user_id)
    )
    deleted["consents"] = result.rowcount

    # Delete profiles
    result = await db.execute(
        delete(ChildProfile).where(ChildProfile.user_id == user_id)
    )
    deleted["profiles"] = result.rowcount

    logger.info("User data deleted: user=%s summary=%s", user_id, deleted)
    return deleted
