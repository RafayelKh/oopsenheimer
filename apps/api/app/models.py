"""Database models for Oops-enheimer scenes and simulation jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class JobStatus(StrEnum):
    QUEUED = "queued"
    COMPILING = "compiling"
    COMPILED = "compiled"
    RUNNING = "running"
    PARSING = "parsing"
    COMPLETED = "completed"
    FAILED = "failed"


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid4())


scene_json_type = JSON().with_variant(JSONB, "postgresql")


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scene_json: Mapped[dict] = mapped_column(scene_json_type, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    simulation_jobs: Mapped[list["SimulationJob"]] = relationship(
        back_populates="scene",
        cascade="all, delete-orphan",
    )


class SimulationJob(Base):
    __tablename__ = "simulation_jobs"
    __table_args__ = (
        CheckConstraint(
            "status in ('queued', 'compiling', 'compiled', 'running', 'parsing', 'completed', 'failed')",
            name="ck_simulation_jobs_status",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.QUEUED.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    fluka_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    compiler_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    histories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cycles: Mapped[int | None] = mapped_column(Integer, nullable=True)

    scene: Mapped[Scene] = relationship(back_populates="simulation_jobs")
