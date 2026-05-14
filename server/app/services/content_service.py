"""Content curation service — recommendations and catalog management."""

import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Content, ChildProfile

logger = logging.getLogger("mikabox.service.content")


async def get_recommendations(
    profile_id: str,
    db: AsyncSession,
    limit: int = 10,
) -> list[Content]:
    """Get age-appropriate content recommendations for a child profile."""
    result = await db.execute(
        select(ChildProfile).where(ChildProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return []

    result = await db.execute(
        select(Content)
        .where(and_(
            Content.age_min <= profile.age,
            Content.age_max >= profile.age,
        ))
        .order_by(Content.title)
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_content_summary(db: AsyncSession) -> str:
    """Get a comma-separated list of all content titles for AI context."""
    result = await db.execute(select(Content.title).order_by(Content.title))
    titles = result.scalars().all()
    return ", ".join(titles) if titles else "various audiobooks and music"
