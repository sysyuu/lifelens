"""Video upload and processing models."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Date, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class UploadedVideo(Base):
    """A single video file uploaded by the user."""

    __tablename__ = "uploaded_videos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    filename: Mapped[str] = mapped_column(String(500))
    file_path: Mapped[str] = mapped_column(String(500))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    resolution: Mapped[Optional[str]] = mapped_column(String(20))  # e.g. "1920x1080"

    # Date extraction: from video metadata or user input
    capture_date: Mapped[Optional[date]] = mapped_column(Date)
    capture_date_unknown: Mapped[bool] = mapped_column(default=False)

    # Processing status
    status: Mapped[str] = mapped_column(String(20), default="uploaded")  # uploaded / processing / processed / failed

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class UploadBatch(Base):
    """A batch of videos uploaded together for one day's processing."""

    __tablename__ = "upload_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    target_date: Mapped[Optional[date]] = mapped_column(Date)  # The date these videos represent
    target_date_unknown: Mapped[bool] = mapped_column(default=False)
    video_ids: Mapped[list] = mapped_column(JSON, default=list)  # List of UploadedVideo UUIDs
    video_count: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_seconds: Mapped[float] = mapped_column(Float, default=0)

    # Processing
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / processing / completed / failed
    workflow_run_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
