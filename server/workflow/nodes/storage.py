"""Node 4.3: Storage - Persist diary and profile updates to database."""

import uuid
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from server.workflow.engine import WorkflowNode, registry
from server.models.diary import DiaryEntry, DiaryKeyEvent, EventMedia
from server.models.profile import (
    UserProfile, SocialContact, Interest, RecentFocus,
    WeekdayHabit, WeekendHabit, GeneralHabit,
)

logger = logging.getLogger(__name__)


class StorageNode(WorkflowNode):
    node_id = "4.3_storage"
    node_name = "存储"
    default_model = None  # Non-AI node

    async def execute(self, input_data: dict, config: dict) -> dict:
        """Persist diary and apply profile updates.

        Input from 4.2: quality-checked diary + processed media.
        Also needs profile_diff from 3.1 and db session from context.
        """
        quality_data = input_data.get("4.2_quality_check", {})
        quality_result = quality_data.get("quality_result", {})
        diary_data = quality_data.get("diary", {})
        processed_media = quality_data.get("processed_media", [])
        profile_diff = input_data.get("3.1_profile_update", {}).get("profile_diff", {})

        # If diary_data has raw_content (JSON parse failed earlier), try to recover
        if "raw_content" in diary_data and "insight" not in diary_data:
            import re, json as _json
            raw = diary_data["raw_content"]
            logger.info(f"Diary has raw_content (len={len(raw)}), attempting recovery")
            # Strip markdown fences if present
            fence_match = re.search(r'```(?:json)?\s*\n([\s\S]*?)\n\s*```', raw)
            if fence_match:
                raw = fence_match.group(1).strip()
            try:
                diary_data = _json.loads(raw)
                logger.info(f"Recovered diary data from raw_content, keys: {list(diary_data.keys())}")
            except _json.JSONDecodeError:
                # Try fixing unescaped quotes
                try:
                    from server.workflow.llm_client import _fix_llm_json
                    diary_data = _json.loads(_fix_llm_json(raw))
                    logger.info(f"Recovered diary data after JSON fix, keys: {list(diary_data.keys())}")
                except Exception as e:
                    logger.error(f"Could not recover diary data from raw_content: {e}")

        # Check quality verdict
        verdict = quality_result.get("overall_verdict", "pass")
        if verdict == "needs_revision":
            critical_issues = [
                i for i in quality_result.get("issues", [])
                if i.get("severity") == "critical"
            ]
            logger.warning(f"Diary has {len(critical_issues)} critical issues, storing with flag")

        # Get database session and profile_id from context
        db: AsyncSession = input_data.get("_db_session")
        profile_id = input_data.get("_profile_id")

        logger.info(f"Storage node input keys: {list(input_data.keys())}")
        logger.info(f"db={db}, profile_id={profile_id}")

        if not db or not profile_id:
            return {
                "status": "skipped",
                "reason": "No database session or profile_id in context",
                "diary": diary_data,
            }

        diary_id = await self._store_diary(db, profile_id, diary_data, processed_media)
        await self._apply_profile_updates(db, profile_id, profile_diff)
        await db.flush()  # flush but don't commit — engine will commit at the end

        return {
            "status": "completed",
            "diary_id": str(diary_id),
            "quality_verdict": verdict,
            "quality_score": quality_result.get("score", 0),
        }

    async def _store_diary(
        self, db: AsyncSession, profile_id: uuid.UUID, diary_data: dict, processed_media: list
    ) -> uuid.UUID:
        """Store diary entry and its key events with media."""
        # Build media map: context -> media info
        media_map = {}
        for pm in processed_media:
            ctx = pm.get("ref_context", "")
            if ctx not in media_map:
                media_map[ctx] = []
            media_map[ctx].append(pm)

        # Parse diary date
        diary_date_raw = diary_data.get("date")
        diary_date_val = None
        if diary_date_raw:
            try:
                from datetime import date as date_type
                if isinstance(diary_date_raw, str):
                    diary_date_val = date_type.fromisoformat(diary_date_raw)
                else:
                    diary_date_val = diary_date_raw
            except (ValueError, TypeError):
                logger.warning(f"Could not parse diary date: {diary_date_raw}")

        # Create diary entry
        diary = DiaryEntry(
            profile_id=profile_id,
            diary_date=diary_date_val,
            insight_type=diary_data.get("insight", {}).get("type", "summary"),
            insight_text=diary_data.get("insight", {}).get("text", ""),
            happy_minutes=diary_data.get("emotion_overview", {}).get("happy_minutes", 0),
            angry_minutes=diary_data.get("emotion_overview", {}).get("angry_minutes", 0),
            calm_minutes=diary_data.get("emotion_overview", {}).get("calm_minutes", 0),
            source_video_count=diary_data.get("meta", {}).get("source_video_count", 0),
            total_source_duration_seconds=diary_data.get("meta", {}).get("total_source_duration_seconds", 0),
            profile_version=diary_data.get("meta", {}).get("profile_version", 1),
        )

        # Handle insight media
        insight_media = media_map.get("insight", [])
        if insight_media:
            m = insight_media[0]
            diary.insight_media_type = m.get("type")
            diary.insight_media_url = m.get("url")
            diary.insight_media_thumbnail_url = m.get("thumbnail_url")

        db.add(diary)
        await db.flush()
        logger.info(f"Stored diary entry id={diary.id}, date={diary.diary_date}, insight={diary.insight_type}")

        # Create key events
        for evt_data in diary_data.get("key_events", []):
            event = DiaryKeyEvent(
                diary_id=diary.id,
                start_time=evt_data.get("time_range", {}).get("start"),
                end_time=evt_data.get("time_range", {}).get("end"),
                title=evt_data.get("title", ""),
                narrative=evt_data.get("narrative", ""),
                importance_type=evt_data.get("importance_type", "objective"),
                emotion_tag=evt_data.get("emotion_tag"),
                emotion_note=evt_data.get("emotion_note"),
                tags=evt_data.get("tags", []),
                related_person_ids=evt_data.get("related_person_ids", []),
            )
            db.add(event)
            await db.flush()

            # Attach media
            event_media_key = f"event_{evt_data.get('event_id', '')}"
            for pm in media_map.get(event_media_key, []):
                media = EventMedia(
                    event_id=event.id,
                    media_type=pm.get("type", "keyframe"),
                    url=pm.get("url", ""),
                    thumbnail_url=pm.get("thumbnail_url"),
                    source_video_id=pm.get("source_video_id"),
                    source_timestamp=pm.get("timestamp"),
                    clip_start=pm.get("clip_start"),
                    clip_end=pm.get("clip_end"),
                )
                db.add(media)

        return diary.id

    async def _apply_profile_updates(
        self, db: AsyncSession, profile_id: uuid.UUID, profile_diff: dict
    ):
        """Apply profile updates from the diff."""
        updates = profile_diff.get("profile_updates", [])

        if not updates:
            return

        # Load profile
        result = await db.execute(
            select(UserProfile).where(UserProfile.id == profile_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            return

        for update in updates:
            module = update.get("module")
            action = update.get("action")
            field = update.get("field")
            new_value = update.get("new_value")

            try:
                if module == "interests":
                    await self._update_interest(db, profile_id, action, field, new_value, update)
                elif module == "social_contacts":
                    await self._update_social_contact(db, profile_id, action, field, new_value, update)
                elif module == "recent_focus":
                    await self._update_recent_focus(db, profile_id, action, field, new_value, update)
                # Habits updates can be added similarly
            except Exception as e:
                logger.error(f"Failed to apply profile update {update}: {e}")

        # Increment version
        profile.version += 1
        profile.updated_at = datetime.utcnow()

    async def _update_interest(self, db, profile_id, action, field, new_value, update):
        if action == "new":
            interest = Interest(
                profile_id=profile_id,
                name=new_value if isinstance(new_value, str) else str(new_value),
                confidence=0.25,
                evidence_count=1,
            )
            db.add(interest)
        elif action == "update":
            result = await db.execute(
                select(Interest).where(
                    Interest.profile_id == profile_id,
                    Interest.name == field,
                )
            )
            interest = result.scalar_one_or_none()
            if interest:
                if "confidence" in str(new_value):
                    pass  # Handle confidence updates
                interest.evidence_count += 1
                from datetime import date
                interest.last_detected = date.today()

    async def _update_social_contact(self, db, profile_id, action, field, new_value, update):
        if action == "new" and isinstance(new_value, dict):
            contact = SocialContact(
                profile_id=profile_id,
                label=new_value.get("label", "未命名"),
                relationship_type=new_value.get("relationship_type", "other"),
                appearance_description=new_value.get("appearance", ""),
                scene_tags=new_value.get("scene_tags", []),
            )
            db.add(contact)

    async def _update_recent_focus(self, db, profile_id, action, field, new_value, update):
        if action == "new":
            focus = RecentFocus(
                profile_id=profile_id,
                topic=new_value if isinstance(new_value, str) else str(new_value),
                detected_dates=[str(datetime.utcnow().date())],
            )
            db.add(focus)


registry.register(StorageNode())
