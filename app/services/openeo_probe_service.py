from app.core.exceptions import ValidationError
from app.models.job import IndicatorType
from app.adapters.openeo_adapter import OpenEOAdapter
from app.schemas.jobs import IndicatorJobRequest
from app.schemas.openeo import (
    OpenEOCapabilitiesResponse,
    OpenEOCollectionsResponse,
    OpenEOIndicatorLatestResponse,
)


class OpenEOProbeService:
    def __init__(self, adapter: OpenEOAdapter | None = None) -> None:
        self.adapter = adapter or OpenEOAdapter()

    def get_capabilities(self) -> OpenEOCapabilitiesResponse:
        payload = self.adapter.get_capabilities()
        return OpenEOCapabilitiesResponse(**payload)

    def get_collections(self, limit: int) -> OpenEOCollectionsResponse:
        payload = self.adapter.get_collections(limit=limit)
        return OpenEOCollectionsResponse(**payload)

    def get_indicator_latest(
        self,
        indicator_type: IndicatorType,
        payload: IndicatorJobRequest,
    ) -> OpenEOIndicatorLatestResponse:
        if not payload.aoi:
            raise ValidationError("aoi is required to compute indicator values")
        if payload.aoi.type != "bbox":
            raise ValidationError("Only bbox aoi is supported for now")
        if len(payload.aoi.coordinates) != 4:
            raise ValidationError("bbox coordinates must include exactly 4 values")

        data = self.adapter.get_indicator_latest(indicator_type=indicator_type, payload=payload)
        return OpenEOIndicatorLatestResponse(**data)
