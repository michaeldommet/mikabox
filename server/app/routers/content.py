"""Content library router — browse, search, upload, download."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import User, Content
from ..schemas import ContentResponse, ContentUpload
from ..auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/api/content", tags=["content"])


@router.get("/", response_model=list[ContentResponse])
async def list_content(
    category: Optional[str] = None,
    age_min: int = Query(0, ge=0),
    age_max: int = Query(12, le=18),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Browse content library, filtered by age and category."""
    query = select(Content).where(
        and_(Content.age_min <= age_max, Content.age_max >= age_min)
    )

    if category:
        query = query.where(Content.category == category)

    if search:
        query = query.where(
            Content.title.ilike(f"%{search}%") | Content.author.ilike(f"%{search}%")
        )

    query = query.order_by(Content.title)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/catalog")
async def get_catalog(db: AsyncSession = Depends(get_db)):
    """Get full content catalog (used by device for content resolution)."""
    result = await db.execute(select(Content).order_by(Content.title))
    items = result.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "author": c.author,
            "category": c.category,
            "age_min": c.age_min,
            "age_max": c.age_max,
            "duration_seconds": c.duration_seconds,
        }
        for c in items
    ]


@router.get("/{content_id}", response_model=ContentResponse)
async def get_content(content_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")
    return content


@router.get("/{content_id}/download")
async def download_content(content_id: str, db: AsyncSession = Depends(get_db)):
    """Download audio file for offline playback on device."""
    result = await db.execute(select(Content).where(Content.id == content_id))
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found.")

    file_path = Path(content.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server.")

    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg",
        filename=file_path.name,
    )


@router.post("/upload", response_model=ContentResponse, status_code=201)
async def upload_content(
    title: str = Form(...),
    file: UploadFile = File(...),
    author: str = Form(""),
    description: str = Form(""),
    category: str = Form("audiobook"),
    age_min: int = Form(0),
    age_max: int = Form(12),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload custom audio content."""
    # Save file
    upload_dir = settings.content_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / file.filename
    with open(file_path, "wb") as f:
        data = await file.read()
        f.write(data)

    content = Content(
        title=title,
        author=author,
        description=description,
        category=category,
        age_min=age_min,
        age_max=age_max,
        file_path=str(file_path),
    )
    db.add(content)
    await db.flush()
    return content
