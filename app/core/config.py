from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="local", alias="APP_ENV")
    app_port: int = Field(default=8000, alias="APP_PORT")

    openeo_base_url: str = Field(default="", alias="OPENEO_BASE_URL")
    openeo_client_id: str = Field(default="", alias="OPENEO_CLIENT_ID")
    openeo_client_secret: str = Field(default="", alias="OPENEO_CLIENT_SECRET")
    openeo_access_token: str = Field(default="", alias="OPENEO_ACCESS_TOKEN")

    simfat_backend_url: str = Field(default="", alias="SIMFAT_BACKEND_URL")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    def missing_required(self) -> List[str]:
        required = {
            "OPENEO_BASE_URL": self.openeo_base_url,
            "OPENEO_CLIENT_ID": self.openeo_client_id,
            "OPENEO_CLIENT_SECRET": self.openeo_client_secret,
            "SIMFAT_BACKEND_URL": self.simfat_backend_url,
        }
        return [key for key, value in required.items() if not value]


@lru_cache
def get_settings() -> Settings:
    return Settings()
