"""Diary data models."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Date, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class DiaryEntry(Base):
    """Daily diary entry."""

    __tablename__ = "diary_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    diary_date: Mapped[Optional[date]] = mapped_column(Date)  # None means "未知"
    diary_date_unknown: Mapped[bool] = mapped_column(default=False)

    # Insight (header)
    insight_type: Mapped[str] = mapped_column(String(20))  # highlight / observation / summary
    insight_text: Mapped[str] = mapped_column(Text)
    insight_media_type: Mapped[Optional[str]] = mapped_column(String(20))  # keyframe / video_clip / null
    insight_media_url: Mapped[Optional[str]] = mapped_column(String(500))  # processed media URL
    insight_media_thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Emotion overview
    happy_minutes: Mapped[float] = mapped_column(Float, default=0)
    angry_minutes: Mapped[float] = mapped_column(Float, default=0)
    calm_minutes: Mapped[float] = mapped_column(Float, default=0)

    # Meta
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    source_video_count: Mapped[int] = mapped_column(Integer, default=0)
    total_source_duration_seconds: Mapped[float] = mapped_column(Float, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    key_events: Mapped[list["DiaryKeyEvent"]] = relationship(
        back_populates="diary", cascade="all, delete-orphan", order_by="DiaryKeyEvent.start_time"
    )


class DiaryKeyEvent(Base):
    """Key event within a diary entry."""

    __tablename__ = "diary_key_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    diary_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("diary_entries.id"))

    start_time: Mapped[Optional[str]] = mapped_column(String(10))  # HH:MM
    end_time: Mapped[Optional[str]] = mapped_column(String(10))  # HH:MM
    title: Mapped[str] = mapped_column(String(200))
    narrative: Mapped[str] = mapped_column(Text)  # Rich text, 2nd person
    importance_type: Mapped[str] = mapped_column(String(20))  # objective / personalized / duration_based
    emotion_tag: Mapped[Optional[str]] = mapped_column(String(10))  # happy / angry / null
    emotion_note: Mapped[Optional[str]] = mapped_column(Text)
    tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    related_person_ids: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # Relationships
    diary: Mapped["DiaryEntry"] = relationship(back_populates="key_events")
    media: Mapped[list["EventMedia"]] = relationship(back_populates="event", cascade="all, delete-orphan")


class EventMedia(Base):
    """Media attached to a diary key event."""

    __tablename__ = "event_media"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("diary_key_events.id"))

    media_type: Mapped[str] = mapped_column(String(20))  # keyframe / video_clip
    url: Mapped[str] = mapped_column(String(500))  # Processed media URL (ready to display)
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Source tracking (for debug panel only, not shown to app user)
    source_video_id: Mapped[Optional[str]] = mapped_column(String(100))
    source_timestamp: Mapped[Optional[float]] = mapped_column(Float)
    clip_start: Mapped[Optional[float]] = mapped_column(Float)
    clip_end: Mapped[Optional[float]] = mapped_column(Float)

    event: Mapped["DiaryKeyEvent"] = relationship(back_populates="media")
