"""Memory router — CRUD for Mika's persistent memory facts."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, ChildProfile, MemoryFact
from ..schemas import MemoryFactResponse
from ..auth import get_current_user

router = APIRouter(prefix="/api/memory", tags=["memory"])


@router.get("/", response_model=list[MemoryFactResponse])
async def list_memory_facts(
    profile_id: str = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List memory facts. Optionally filter by profile_id."""
    stmt = select(MemoryFact).join(ChildProfile).where(ChildProfile.user_id == user.id)
    if profile_id:
        stmt = stmt.where(MemoryFact.profile_id == profile_id)
        
    stmt = stmt.order_by(MemoryFact.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.delete("/{fact_id}", status_code=204)
async def delete_memory_fact(
    fact_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific memory fact."""
    # Ensure the fact belongs to a profile owned by the user
    stmt = select(MemoryFact).join(ChildProfile).where(
        MemoryFact.id == fact_id,
        ChildProfile.user_id == user.id
    )
    result = await db.execute(stmt)
    fact = result.scalar_one_or_none()
    
    if not fact:
        raise HTTPException(status_code=404, detail="Memory fact not found.")
        
    await db.delete(fact)
    await db.commit()
