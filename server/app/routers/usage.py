"""Usage analytics router — listening reports and history."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, UsageLog, ChildProfile
from ..schemas import UsageLogCreate, UsageSummary
from ..auth import get_current_user

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.post("/log")
async def log_usage_event(event: UsageLogCreate, db: AsyncSession = Depends(get_db)):
    """Log a usage event from the device."""
    log = UsageLog(
        profile_id=event.profile_id,
        content_id=event.content_id,
        event_type=event.event,
        duration_seconds=event.duration_seconds,
        metadata_json=f'{{"trigger": "{event.trigger}", "tag_uid": "{event.tag_uid}"}}',
    )
    db.add(log)
    return {"status": "logged"}


@router.get("/summary", response_model=UsageSummary)
async def get_usage_summary(
    profile_id: str = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get usage summary for a child profile."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    month_start = today_start.replace(day=1)

    # Get profile IDs for this user
    if profile_id:
        profile_ids = [profile_id]
    else:
        result = await db.execute(
            select(ChildProfile.id).where(ChildProfile.user_id == user.id)
        )
        profile_ids = [r for r in result.scalars().all()]

    if not profile_ids:
        return UsageSummary(
            today_minutes=0, week_minutes=0, month_minutes=0,
            top_content=[], daily_breakdown=[],
        )

    # Today's usage
    today_result = await db.execute(
        select(func.coalesce(func.sum(UsageLog.duration_seconds), 0))
        .where(and_(
            UsageLog.profile_id.in_(profile_ids),
            UsageLog.created_at >= today_start,
        ))
    )
    today_seconds = today_result.scalar() or 0

    # Week's usage
    week_result = await db.execute(
        select(func.coalesce(func.sum(UsageLog.duration_seconds), 0))
        .where(and_(
            UsageLog.profile_id.in_(profile_ids),
            UsageLog.created_at >= week_start,
        ))
    )
    week_seconds = week_result.scalar() or 0

    # Month's usage
    month_result = await db.execute(
        select(func.coalesce(func.sum(UsageLog.duration_seconds), 0))
        .where(and_(
            UsageLog.profile_id.in_(profile_ids),
            UsageLog.created_at >= month_start,
        ))
    )
    month_seconds = month_result.scalar() or 0

    return UsageSummary(
        today_minutes=round(today_seconds / 60, 1),
        week_minutes=round(week_seconds / 60, 1),
        month_minutes=round(month_seconds / 60, 1),
        top_content=[],      # TODO: aggregate top content
        daily_breakdown=[],  # TODO: daily breakdown chart data
    )


@router.get("/history")
async def get_usage_history(
    profile_id: str = Query(None),
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent usage history."""
    query = select(UsageLog).order_by(UsageLog.created_at.desc()).limit(limit)

    if profile_id:
        query = query.where(UsageLog.profile_id == profile_id)
    else:
        result = await db.execute(
            select(ChildProfile.id).where(ChildProfile.user_id == user.id)
        )
        profile_ids = list(result.scalars().all())
        if profile_ids:
            query = query.where(UsageLog.profile_id.in_(profile_ids))

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "event_type": log.event_type,
            "duration_seconds": log.duration_seconds,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]

@router.get("/searches")
async def get_search_history(
    profile_id: str = Query(None),
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent web search history."""
    import json
    query = select(UsageLog).where(UsageLog.event_type == "web_search").order_by(UsageLog.created_at.desc()).limit(limit)

    if profile_id:
        query = query.where(UsageLog.profile_id == profile_id)
    else:
        result = await db.execute(
            select(ChildProfile.id).where(ChildProfile.user_id == user.id)
        )
        profile_ids = list(result.scalars().all())
        if profile_ids:
            query = query.where(UsageLog.profile_id.in_(profile_ids))

    result = await db.execute(query)
    logs = result.scalars().all()

    searches = []
    for log in logs:
        try:
            meta = json.loads(log.metadata_json)
            search_query = meta.get("query", "Unknown query")
        except json.JSONDecodeError:
            search_query = "Unknown query"

        searches.append({
            "id": log.id,
            "query": search_query,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })

    return searches

@router.delete("/searches")
async def clear_search_history(
    profile_id: str = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear web search history."""
    from sqlalchemy import delete
    
    query = delete(UsageLog).where(UsageLog.event_type == "web_search")
    
    if profile_id:
        query = query.where(UsageLog.profile_id == profile_id)
    else:
        result = await db.execute(
            select(ChildProfile.id).where(ChildProfile.user_id == user.id)
        )
        profile_ids = list(result.scalars().all())
        if profile_ids:
            query = query.where(UsageLog.profile_id.in_(profile_ids))
            
    await db.execute(query)
    await db.commit()
    
    return {"status": "cleared"}
