"""Pydantic schemas for API request/response validation."""

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Profile Schemas ──

class ProfileBasicInfoCreate(BaseModel):
    nickname: Optional[str] = None
    gender: Optional[str] = None
    age_range: Optional[str] = None
    occupation: Optional[str] = None
    city: Optional[str] = None


class SocialContactOut(BaseModel):
    id: UUID
    label: Optional[str]
    relationship_type: Optional[str]
    scene_tags: Optional[list] = []
    recent_frequency: int = 0
    last_seen_date: Optional[date]

    model_config = {"from_attributes": True}


class SocialContactUpdate(BaseModel):
    label: Optional[str] = None
    relationship_type: Optional[str] = None
    scene_tags: Optional[list] = None


class InterestOut(BaseModel):
    id: UUID
    name: str
    confidence: float
    evidence_count: int
    first_detected: date
    last_detected: date

    model_config = {"from_attributes": True}


class HabitOut(BaseModel):
    weekday: Optional[dict] = None
    weekend: Optional[dict] = None
    general: Optional[dict] = None


class RecentFocusOut(BaseModel):
    id: UUID
    topic: str
    detected_dates: list
    summary: Optional[str]

    model_config = {"from_attributes": True}


class ProfileOut(BaseModel):
    id: UUID
    nickname: Optional[str]
    gender: Optional[str]
    age_range: Optional[str]
    occupation: Optional[str]
    city: Optional[str]
    version: int
    created_at: datetime
    updated_at: datetime
    social_contacts: list[SocialContactOut] = []
    interests: list[InterestOut] = []
    habits: Optional[HabitOut] = None
    recent_focuses: list[RecentFocusOut] = []

    model_config = {"from_attributes": True}


# ── Diary Schemas ──

class EventMediaOut(BaseModel):
    id: UUID
    media_type: str
    url: str
    thumbnail_url: Optional[str]

    model_config = {"from_attributes": True}


class DiaryKeyEventOut(BaseModel):
    id: UUID
    start_time: Optional[str]
    end_time: Optional[str]
    title: str
    narrative: str
    emotion_tag: Optional[str]
    emotion_note: Optional[str]
    tags: Optional[list] = []
    media: list[EventMediaOut] = []

    model_config = {"from_attributes": True}


class DiaryEntryOut(BaseModel):
    id: UUID
    diary_date: Optional[date]
    diary_date_unknown: bool = False
    insight_type: str
    insight_text: str
    insight_media_type: Optional[str]
    insight_media_url: Optional[str]
    insight_media_thumbnail_url: Optional[str]
    happy_minutes: float
    angry_minutes: float
    calm_minutes: float
    source_video_count: int
    generated_at: datetime
    key_events: list[DiaryKeyEventOut] = []

    model_config = {"from_attributes": True}


class DiaryListItemOut(BaseModel):
    """Lightweight diary item for list view."""
    id: UUID
    diary_date: Optional[date]
    diary_date_unknown: bool = False
    insight_type: str
    insight_text: str
    insight_media_thumbnail_url: Optional[str]
    happy_minutes: float
    angry_minutes: float
    calm_minutes: float
    event_count: int = 0
    generated_at: datetime

    model_config = {"from_attributes": True}


# ── Video Upload Schemas ──

class VideoUploadResponse(BaseModel):
    video_id: UUID
    filename: str
    capture_date: Optional[date]
    capture_date_unknown: bool = False
    status: str


class BatchUploadResponse(BaseModel):
    batch_id: UUID
    video_count: int
    target_date: Optional[date]
    status: str


# ── Workflow Debug Schemas ──

class NodeRunOut(BaseModel):
    id: UUID
    node_id: str
    node_name: str
    status: str
    model_used: Optional[str]
    system_prompt: Optional[str]
    config_params: Optional[dict]
    input_data: Optional[dict]
    output_data: Optional[dict]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_seconds: Optional[float]
    token_usage: Optional[dict]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class WorkflowRunOut(BaseModel):
    id: UUID
    target_date: Optional[date]
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error_message: Optional[str]
    node_runs: list[NodeRunOut] = []

    model_config = {"from_attributes": True}


class NodeConfigUpdate(BaseModel):
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    params: Optional[dict] = None


class RerunNodeRequest(BaseModel):
    workflow_run_id: UUID
    node_id: str
