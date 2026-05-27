"""Configuration for the Oops-enheimer API."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    storage_root: Path = Field(default=Path("storage"), alias="STORAGE_ROOT")
    database_url: str = Field(default="sqlite:///./storage/oopsenheimer.db", alias="DATABASE_URL")
    sim_mode: str = Field(default="mock", alias="OOPSENHEIMER_SIM_MODE")
    fluka_bin: str | None = Field(default=None, alias="FLUKA_BIN")


settings = Settings()
