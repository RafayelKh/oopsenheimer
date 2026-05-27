"""API schemas for the Oops-enheimer skeleton."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok"]
    sim_mode: str = Field(alias="simMode")
    fluka_configured: bool = Field(alias="flukaConfigured")

    model_config = {"populate_by_name": True}


class SceneCreate(BaseModel):
    scene_json: dict[str, Any] | None = Field(default=None, alias="sceneJson")

    model_config = {"populate_by_name": True}


class SceneRecord(BaseModel):
    id: str
    name: str
    scene_json: dict[str, Any] = Field(alias="sceneJson")
    created_at: datetime = Field(alias="createdAt")

    model_config = {"populate_by_name": True}


class SimulationCreate(BaseModel):
    scene_id: str = Field(alias="sceneId")

    model_config = {"populate_by_name": True}


class SimulationRecord(BaseModel):
    id: str
    scene_id: str = Field(alias="sceneId")
    status: str
    progress_percent: int = Field(default=0, alias="progressPercent")
    progress_message: str | None = Field(default=None, alias="progressMessage")
    created_at: datetime = Field(alias="createdAt")
    storage_path: str | None = Field(default=None, alias="storagePath")
    error_message: str | None = Field(default=None, alias="errorMessage")

    model_config = {"populate_by_name": True}


class ArtifactList(BaseModel):
    simulation_id: str = Field(alias="simulationId")
    artifacts: list[str]
    parsed_result: dict[str, Any] | None = Field(default=None, alias="parsedResult")

    model_config = {"populate_by_name": True}
