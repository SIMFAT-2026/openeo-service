from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OpenEOCapabilitiesResponse(BaseModel):
    status: str = "ok"
    source: str = "openEO"
    cached: bool
    fetched_at: datetime = Field(alias="fetchedAt")
    data: dict[str, Any]

    model_config = {"populate_by_name": True}


class OpenEOCollectionsResponse(BaseModel):
    status: str = "ok"
    source: str = "openEO"
    cached: bool
    fetched_at: datetime = Field(alias="fetchedAt")
    limit: int
    count: int
    collections: list[dict[str, Any]]

    model_config = {"populate_by_name": True}
