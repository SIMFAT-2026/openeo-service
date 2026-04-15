from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.job import IndicatorType


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


class OpenEOIndicatorLatestResponse(BaseModel):
    status: str = "ok"
    source: str = "openEO"
    cached: bool
    fetched_at: datetime = Field(alias="fetchedAt")
    measured_at: datetime = Field(alias="measuredAt")
    indicator_type: IndicatorType = Field(alias="indicatorType")
    region_id: str | None = Field(default=None, alias="regionId")
    period_start: date = Field(alias="periodStart")
    period_end: date = Field(alias="periodEnd")
    collection_id: str = Field(alias="collectionId")
    value: float | None = None

    model_config = {"populate_by_name": True}
