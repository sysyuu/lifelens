"""Workflow execution and debug models."""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Date, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from .database import Base


class WorkflowRun(Base):
    """A complete workflow execution for one day's videos."""

    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("upload_batches.id"))

    target_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / running / completed / failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Output references
    diary_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    profile_version_before: Mapped[Optional[int]] = mapped_column(Integer)
    profile_version_after: Mapped[Optional[int]] = mapped_column(Integer)

    # Relationships
    node_runs: Mapped[list["NodeRun"]] = relationship(
        back_populates="workflow_run", cascade="all, delete-orphan", order_by="NodeRun.started_at"
    )


class NodeRun(Base):
    """Execution record for a single workflow node."""

    __tablename__ = "node_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_runs.id"))

    node_id: Mapped[str] = mapped_column(String(50))  # e.g. "1.2_visual_understanding"
    node_name: Mapped[str] = mapped_column(String(100))  # e.g. "画面理解"
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / running / completed / failed / skipped

    # Configuration snapshot (for debug panel)
    model_used: Mapped[Optional[str]] = mapped_column(String(50))
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)
    config_params: Mapped[Optional[dict]] = mapped_column(JSON)  # Node-specific params

    # Input/Output (stored as JSON for debug panel inspection)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON)

    # Performance metrics
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float)
    token_usage: Mapped[Optional[dict]] = mapped_column(JSON)  # {prompt_tokens, completion_tokens, total_tokens}
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    workflow_run: Mapped["WorkflowRun"] = relationship(back_populates="node_runs")


class NodeConfig(Base):
    """Persistent node configuration (editable via debug panel)."""

    __tablename__ = "node_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user_profiles.id"))

    node_id: Mapped[str] = mapped_column(String(50))
    model: Mapped[Optional[str]] = mapped_column(String(50))  # Model override
    system_prompt: Mapped[Optional[str]] = mapped_column(Text)  # Prompt override
    params: Mapped[Optional[dict]] = mapped_column(JSON)  # Additional params override

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
