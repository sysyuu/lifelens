"""Profile API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from server.models.database import get_db
from server.models.profile import (
    UserProfile, SocialContact, Interest,
    WeekdayHabit, WeekendHabit, GeneralHabit, RecentFocus,
)
from server.api.schemas import (
    ProfileBasicInfoCreate, ProfileOut, SocialContactUpdate,
    SocialContactOut, InterestOut, HabitOut, RecentFocusOut,
)

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.post("/", response_model=ProfileOut)
async def create_profile(data: ProfileBasicInfoCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user profile (onboarding)."""
    profile = UserProfile(
        nickname=data.nickname,
        gender=data.gender,
        age_range=data.age_range,
        occupation=data.occupation,
        city=data.city,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return await _load_full_profile(db, profile.id)


@router.get("/{profile_id}", response_model=ProfileOut)
async def get_profile(profile_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get full user profile."""
    profile = await _load_full_profile(db, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/{profile_id}")
async def update_profile_basic(
    profile_id: UUID, data: ProfileBasicInfoCreate, db: AsyncSession = Depends(get_db)
):
    """Update basic profile info."""
    result = await db.execute(select(UserProfile).where(UserProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    await db.commit()
    return {"status": "updated"}


@router.patch("/{profile_id}/contacts/{contact_id}")
async def update_contact(
    profile_id: UUID, contact_id: UUID, data: SocialContactUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a social contact (user-editable fields: label, relationship_type, scene_tags)."""
    result = await db.execute(
        select(SocialContact).where(
            SocialContact.id == contact_id,
            SocialContact.profile_id == profile_id,
        )
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contact, key, value)

    await db.commit()
    return {"status": "updated"}


async def _load_full_profile(db: AsyncSession, profile_id: UUID):
    """Load profile with all relationships."""
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
        return None

    # Build habits dict
    habits = HabitOut()
    if profile.weekday_habits:
        h = profile.weekday_habits
        habits.weekday = {
            "commute_method": h.commute_method,
            "commute_duration_minutes": h.commute_duration_minutes,
            "usual_start_time": h.usual_start_time,
            "usual_end_time": h.usual_end_time,
            "breakfast_habit": h.breakfast_habit,
            "lunch_habit": h.lunch_habit,
            "dinner_habit": h.dinner_habit,
            "confidence": h.confidence,
        }
    if profile.weekend_habits:
        h = profile.weekend_habits
        habits.weekend = {
            "entertainment_activities": h.entertainment_activities,
            "has_children": h.has_children,
            "has_pets": h.has_pets,
            "pet_type": h.pet_type,
            "cooks_regularly": h.cooks_regularly,
            "typical_wake_time": h.typical_wake_time,
            "confidence": h.confidence,
        }
    if profile.general_habits:
        h = profile.general_habits
        habits.general = {
            "has_exercise_habit": h.has_exercise_habit,
            "exercise_types": h.exercise_types,
            "exercise_frequency": h.exercise_frequency,
            "exercise_time_range": h.exercise_time_range,
            "sleep_pattern": h.sleep_pattern,
            "confidence": h.confidence,
        }

    return ProfileOut(
        id=profile.id,
        nickname=profile.nickname,
        gender=profile.gender,
        age_range=profile.age_range,
        occupation=profile.occupation,
        city=profile.city,
        version=profile.version,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        social_contacts=[SocialContactOut.model_validate(c) for c in profile.social_contacts],
        interests=[InterestOut.model_validate(i) for i in profile.interests],
        habits=habits,
        recent_focuses=[RecentFocusOut.model_validate(f) for f in profile.recent_focuses],
    )
