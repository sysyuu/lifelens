"""Diary API endpoints."""

from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.database import get_db
from server.models.diary import DiaryEntry, DiaryKeyEvent, EventMedia
from server.api.schemas import DiaryEntryOut, DiaryListItemOut, DiaryKeyEventOut, EventMediaOut

router = APIRouter(prefix="/api/diary", tags=["diary"])


@router.get("/{profile_id}/list", response_model=list[DiaryListItemOut])
async def list_diaries(
    profile_id: UUID,
    diary_date: Optional[date] = Query(None, description="Filter by specific date"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List diary entries for a user, with optional date filter."""
    query = (
        select(DiaryEntry)
        .where(DiaryEntry.profile_id == profile_id)
        .order_by(DiaryEntry.diary_date.desc().nullslast(), DiaryEntry.generated_at.desc())
        .offset(offset)
        .limit(limit)
    )

    if diary_date:
        query = query.where(DiaryEntry.diary_date == diary_date)

    result = await db.execute(
        query.options(selectinload(DiaryEntry.key_events))
    )
    diaries = result.scalars().all()

    items = []
    for d in diaries:
        items.append(DiaryListItemOut(
            id=d.id,
            diary_date=d.diary_date,
            diary_date_unknown=d.diary_date_unknown,
            insight_type=d.insight_type,
            insight_text=d.insight_text,
            insight_media_thumbnail_url=d.insight_media_thumbnail_url,
            happy_minutes=d.happy_minutes,
            angry_minutes=d.angry_minutes,
            calm_minutes=d.calm_minutes,
            event_count=len(d.key_events),
            generated_at=d.generated_at,
        ))

    return items


@router.get("/{profile_id}/dates", response_model=list[Optional[date]])
async def list_diary_dates(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all dates that have diary entries (for date picker)."""
    result = await db.execute(
        select(DiaryEntry.diary_date)
        .where(DiaryEntry.profile_id == profile_id)
        .distinct()
        .order_by(DiaryEntry.diary_date.desc().nullslast())
    )
    dates = result.scalars().all()
    return dates


@router.get("/detail/{diary_id}", response_model=DiaryEntryOut)
async def get_diary(diary_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get full diary entry with key events and media."""
    result = await db.execute(
        select(DiaryEntry)
        .options(
            selectinload(DiaryEntry.key_events).selectinload(DiaryKeyEvent.media),
        )
        .where(DiaryEntry.id == diary_id)
    )
    diary = result.scalar_one_or_none()
    if not diary:
        raise HTTPException(status_code=404, detail="Diary not found")

    return DiaryEntryOut(
        id=diary.id,
        diary_date=diary.diary_date,
        diary_date_unknown=diary.diary_date_unknown,
        insight_type=diary.insight_type,
        insight_text=diary.insight_text,
        insight_media_type=diary.insight_media_type,
        insight_media_url=diary.insight_media_url,
        insight_media_thumbnail_url=diary.insight_media_thumbnail_url,
        happy_minutes=diary.happy_minutes,
        angry_minutes=diary.angry_minutes,
        calm_minutes=diary.calm_minutes,
        source_video_count=diary.source_video_count,
        generated_at=diary.generated_at,
        key_events=[
            DiaryKeyEventOut(
                id=evt.id,
                start_time=evt.start_time,
                end_time=evt.end_time,
                title=evt.title,
                narrative=evt.narrative,
                emotion_tag=evt.emotion_tag,
                emotion_note=evt.emotion_note,
                tags=evt.tags,
                media=[EventMediaOut.model_validate(m) for m in evt.media],
            )
            for evt in diary.key_events
        ],
    )
