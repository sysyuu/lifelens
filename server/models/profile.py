"""User Profile data models."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Boolean, Date, DateTime, Text, JSON, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY

from .database import Base


class UserProfile(Base):
    """Root user profile table."""

    __tablename__ = "user_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic info (onboarding)
    nickname: Mapped[Optional[str]] = mapped_column(String(50))
    gender: Mapped[Optional[str]] = mapped_column(String(10))  # male / female / undisclosed
    age_range: Mapped[Optional[str]] = mapped_column(String(10))  # 18-24 / 25-30 / 31-40 / 41-50 / 50+
    occupation: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))

    # Voiceprint embedding (registered during onboarding)
    voiceprint_path: Mapped[Optional[str]] = mapped_column(String(500))

    # Dietary preferences (V2 placeholder)
    dietary_tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    daily_calorie_goal: Mapped[Optional[int]] = mapped_column(Integer)

    # Meta
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    social_contacts: Mapped[list["SocialContact"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    interests: Mapped[list["Interest"]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    weekday_habits: Mapped[Optional["WeekdayHabit"]] = relationship(back_populates="profile", uselist=False, cascade="all, delete-orphan")
    weekend_habits: Mapped[Optional["WeekendHabit"]] = relationship(back_populates="profile", uselist=False, cascade="all, delete-orphan")
    general_habits: Mapped[Optional["GeneralHabit"]] = relationship(back_populates="profile", uselist=False, cascade="all, delete-orphan")
    recent_focuses: Mapped[list["RecentFocus"]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class SocialContact(Base):
    """Social relationship graph entries."""

    __tablename__ = "social_contacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    label: Mapped[Optional[str]] = mapped_column(String(100))  # User-editable name, e.g. "老婆", "同事小王"
    relationship_type: Mapped[Optional[str]] = mapped_column(String(20))  # family / friend / colleague / acquaintance / other
    appearance_description: Mapped[Optional[str]] = mapped_column(Text)  # AI-generated appearance description
    voiceprint_path: Mapped[Optional[str]] = mapped_column(String(500))  # Voiceprint embedding file path
    scene_tags: Mapped[Optional[list]] = mapped_column(JSON, default=list)  # User-editable, e.g. ["午饭搭子", "健身伙伴"]
    recent_frequency: Mapped[int] = mapped_column(Integer, default=0)  # Appearances in last 14 days
    last_seen_date: Mapped[Optional[date]] = mapped_column(Date)

    profile: Mapped["UserProfile"] = relationship(back_populates="social_contacts")


class Interest(Base):
    """User interests and hobbies."""

    __tablename__ = "interests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    name: Mapped[str] = mapped_column(String(100))
    confidence: Mapped[float] = mapped_column(Float, default=0.25)
    evidence_count: Mapped[int] = mapped_column(Integer, default=1)
    first_detected: Mapped[date] = mapped_column(Date, default=date.today)
    last_detected: Mapped[date] = mapped_column(Date, default=date.today)

    profile: Mapped["UserProfile"] = relationship(back_populates="interests")


class WeekdayHabit(Base):
    """Weekday habits."""

    __tablename__ = "weekday_habits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), unique=True)

    commute_method: Mapped[Optional[str]] = mapped_column(String(50))
    commute_duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    usual_start_time: Mapped[Optional[str]] = mapped_column(String(10))  # HH:MM
    usual_end_time: Mapped[Optional[str]] = mapped_column(String(10))  # HH:MM
    breakfast_habit: Mapped[Optional[str]] = mapped_column(String(200))
    lunch_habit: Mapped[Optional[str]] = mapped_column(String(200))
    dinner_habit: Mapped[Optional[str]] = mapped_column(String(200))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    profile: Mapped["UserProfile"] = relationship(back_populates="weekday_habits")


class WeekendHabit(Base):
    """Weekend habits."""

    __tablename__ = "weekend_habits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), unique=True)

    entertainment_activities: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    has_children: Mapped[Optional[bool]] = mapped_column(Boolean)
    has_pets: Mapped[Optional[bool]] = mapped_column(Boolean)
    pet_type: Mapped[Optional[str]] = mapped_column(String(50))
    cooks_regularly: Mapped[Optional[bool]] = mapped_column(Boolean)
    typical_wake_time: Mapped[Optional[str]] = mapped_column(String(10))
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    profile: Mapped["UserProfile"] = relationship(back_populates="weekend_habits")


class GeneralHabit(Base):
    """General daily habits."""

    __tablename__ = "general_habits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"), unique=True)

    has_exercise_habit: Mapped[Optional[bool]] = mapped_column(Boolean)
    exercise_types: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    exercise_frequency: Mapped[Optional[str]] = mapped_column(String(50))
    exercise_time_range: Mapped[Optional[str]] = mapped_column(String(50))  # e.g. "07:00-08:00"
    sleep_pattern: Mapped[Optional[str]] = mapped_column(String(100))  # e.g. "早睡早起型"
    confidence: Mapped[float] = mapped_column(Float, default=0.5)

    profile: Mapped["UserProfile"] = relationship(back_populates="general_habits")


class RecentFocus(Base):
    """Recent focus topics (14-day rolling window)."""

    __tablename__ = "recent_focuses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    topic: Mapped[str] = mapped_column(String(200))
    detected_dates: Mapped[list] = mapped_column(JSON, default=list)  # list of date strings
    summary: Mapped[Optional[str]] = mapped_column(Text)

    profile: Mapped["UserProfile"] = relationship(back_populates="recent_focuses")
