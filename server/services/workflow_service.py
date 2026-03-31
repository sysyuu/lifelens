"""Workflow orchestration service."""

import uuid
import logging
from datetime import date
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.database import async_session
from server.models.video import UploadBatch, UploadedVideo
from server.models.profile import UserProfile
from server.models.diary import DiaryEntry
from server.workflow.engine import WorkflowEngine

# Import all nodes to register them
import server.workflow.nodes.video_preprocess
import server.workflow.nodes.visual_understanding
import server.workflow.nodes.speaker_diarization
import server.workflow.nodes.asr
import server.workflow.nodes.emotion_recognition
import server.workflow.nodes.event_structuring
import server.workflow.nodes.person_matching
import server.workflow.nodes.profile_update
import server.workflow.nodes.diary_generation
import server.workflow.nodes.media_slicing
import server.workflow.nodes.quality_check
import server.workflow.nodes.storage

logger = logging.getLogger(__name__)


async def trigger_workflow(batch_id: str, profile_id: str):
    """Trigger workflow processing for a batch of videos.

    In production this would be a Celery task. For V1 we run it
    in-process with asyncio for simplicity.
    """
    import asyncio
    asyncio.create_task(_run_workflow(batch_id, profile_id))


async def _run_workflow(batch_id: str, profile_id: str):
    """Execute the full workflow pipeline."""
    async with async_session() as db:
        try:
            batch_uuid = uuid.UUID(batch_id)
            profile_uuid = uuid.UUID(profile_id)

            # Load batch info
            result = await db.execute(
                select(UploadBatch).where(UploadBatch.id == batch_uuid)
            )
            batch = result.scalar_one_or_none()
            if not batch:
                logger.error(f"Batch {batch_id} not found")
                return

            # Update batch status
            batch.status = "processing"
            await db.flush()

            # Load video file paths
            video_ids = batch.video_ids
            result = await db.execute(
                select(UploadedVideo).where(UploadedVideo.id.in_(
                    [uuid.UUID(vid) for vid in video_ids]
                ))
            )
            videos = result.scalars().all()

            video_paths = [v.file_path for v in videos]
            video_id_strs = [str(v.id) for v in videos]

            # Load current profile for context
            profile_data = await _load_profile_as_dict(db, profile_uuid)

            # Load recent diaries for context
            recent_diaries = await _load_recent_diaries(db, profile_uuid, batch.target_date)

            # Load existing social contacts
            existing_contacts = await _load_contacts_as_list(db, profile_uuid)

            # Create and run workflow engine
            engine = WorkflowEngine(db, profile_uuid)

            # Inject initial data
            engine._results["video_paths"] = video_paths
            engine._results["video_ids"] = video_id_strs
            engine._results["current_profile"] = profile_data
            engine._results["recent_diaries"] = recent_diaries
            engine._results["existing_contacts"] = existing_contacts
            engine._results["_db_session"] = db
            engine._results["_profile_id"] = profile_uuid

            workflow_run = await engine.run(batch_uuid, batch.target_date)

            # Update batch status
            batch.status = "completed" if workflow_run.status == "completed" else "failed"
            batch.workflow_run_id = workflow_run.id
            await db.commit()

            logger.info(f"Workflow completed for batch {batch_id}: {workflow_run.status}")

        except Exception as e:
            logger.error(f"Workflow failed for batch {batch_id}: {e}", exc_info=True)
            try:
                batch.status = "failed"
                await db.commit()
            except Exception:
                pass


async def _load_profile_as_dict(db: AsyncSession, profile_id: uuid.UUID) -> dict:
    """Load profile as a plain dict for LLM context."""
    result = await db.execute(
        select(UserProfile)
        .options(
            selectinload(UserProfile.social_contacts),
            selectinload(UserProfile.interests),
            selectinload(UserProfile.weekday_habits),
            selectinload(UserProfile.weekend_habits),
            selectinload(UserProfile.general_habits),
            selectinload(UserProfile.recent_focuses),
        )
        .where(UserProfile.id == profile_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        return {}

    return {
        "basic": {
            "nickname": profile.nickname,
            "gender": profile.gender,
            "age_range": profile.age_range,
            "occupation": profile.occupation,
            "city": profile.city,
        },
        "social_contacts": [
            {
                "id": str(c.id),
                "label": c.label,
                "relationship_type": c.relationship_type,
                "appearance_description": c.appearance_description,
                "scene_tags": c.scene_tags or [],
                "recent_frequency": c.recent_frequency,
                "last_seen_date": str(c.last_seen_date) if c.last_seen_date else None,
            }
            for c in profile.social_contacts
        ],
        "interests": [
            {
                "name": i.name,
                "confidence": i.confidence,
                "evidence_count": i.evidence_count,
            }
            for i in profile.interests
        ],
        "weekday_habits": {
            "commute_method": profile.weekday_habits.commute_method if profile.weekday_habits else None,
            "usual_start_time": profile.weekday_habits.usual_start_time if profile.weekday_habits else None,
            "usual_end_time": profile.weekday_habits.usual_end_time if profile.weekday_habits else None,
            "breakfast_habit": profile.weekday_habits.breakfast_habit if profile.weekday_habits else None,
            "lunch_habit": profile.weekday_habits.lunch_habit if profile.weekday_habits else None,
            "dinner_habit": profile.weekday_habits.dinner_habit if profile.weekday_habits else None,
        } if profile.weekday_habits else None,
        "weekend_habits": {
            "entertainment_activities": profile.weekend_habits.entertainment_activities if profile.weekend_habits else None,
            "has_children": profile.weekend_habits.has_children if profile.weekend_habits else None,
            "has_pets": profile.weekend_habits.has_pets if profile.weekend_habits else None,
        } if profile.weekend_habits else None,
        "general_habits": {
            "has_exercise_habit": profile.general_habits.has_exercise_habit if profile.general_habits else None,
            "exercise_types": profile.general_habits.exercise_types if profile.general_habits else None,
            "exercise_frequency": profile.general_habits.exercise_frequency if profile.general_habits else None,
            "sleep_pattern": profile.general_habits.sleep_pattern if profile.general_habits else None,
        } if profile.general_habits else None,
        "recent_focus": [
            {"topic": f.topic, "detected_dates": f.detected_dates, "summary": f.summary}
            for f in profile.recent_focuses
        ],
        "version": profile.version,
    }


async def _load_recent_diaries(db: AsyncSession, profile_id: uuid.UUID, target_date: Optional[date]) -> list:
    """Load recent 3 days of diaries for LLM context."""
    query = (
        select(DiaryEntry)
        .where(DiaryEntry.profile_id == profile_id)
        .order_by(DiaryEntry.diary_date.desc().nullslast())
        .limit(3)
    )
    if target_date:
        query = query.where(DiaryEntry.diary_date < target_date)

    result = await db.execute(query)
    diaries = result.scalars().all()

    return [
        {
            "date": str(d.diary_date) if d.diary_date else "unknown",
            "insight": {"type": d.insight_type, "text": d.insight_text},
            "emotion_overview": {
                "happy_minutes": d.happy_minutes,
                "angry_minutes": d.angry_minutes,
                "calm_minutes": d.calm_minutes,
            },
        }
        for d in diaries
    ]


async def _load_contacts_as_list(db: AsyncSession, profile_id: uuid.UUID) -> list:
    """Load social contacts as plain list for LLM context."""
    from server.models.profile import SocialContact
    result = await db.execute(
        select(SocialContact).where(SocialContact.profile_id == profile_id)
    )
    contacts = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "label": c.label,
            "relationship_type": c.relationship_type,
            "appearance_description": c.appearance_description,
            "voiceprint_path": c.voiceprint_path,
            "scene_tags": c.scene_tags or [],
        }
        for c in contacts
    ]
