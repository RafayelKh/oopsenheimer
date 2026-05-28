"""Celery application for Oops-enheimer simulation jobs."""

from __future__ import annotations

from pathlib import Path

from celery import Celery
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    celery_broker_url: str = Field(default="redis://localhost:6379/0", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/0", alias="CELERY_RESULT_BACKEND")
    celery_task_always_eager: bool = Field(default=True, alias="OOPSENHEIMER_CELERY_TASK_ALWAYS_EAGER")
    storage_root: Path = Field(default=Path("storage"), alias="STORAGE_ROOT")
    sim_mode: str = Field(default="mock", alias="OOPSENHEIMER_SIM_MODE")
    fluka_timeout_seconds: int = Field(default=900, ge=1, alias="OOPSENHEIMER_FLUKA_TIMEOUT_SECONDS")
    fluka_stall_timeout_seconds: int = Field(default=180, ge=0, alias="OOPSENHEIMER_FLUKA_STALL_TIMEOUT_SECONDS")
    max_histories: int = Field(default=5000, ge=1, alias="OOPSENHEIMER_MAX_HISTORIES")


settings = WorkerSettings()

celery_app = Celery(
    "oopsenheimer_fluka_runner",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["tasks"],
)
celery_app.conf.task_always_eager = settings.celery_task_always_eager
celery_app.conf.task_eager_propagates = True
