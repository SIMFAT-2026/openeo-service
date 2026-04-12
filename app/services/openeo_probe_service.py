from app.adapters.openeo_adapter import OpenEOAdapter
from app.schemas.openeo import OpenEOCapabilitiesResponse, OpenEOCollectionsResponse


class OpenEOProbeService:
    def __init__(self, adapter: OpenEOAdapter | None = None) -> None:
        self.adapter = adapter or OpenEOAdapter()

    def get_capabilities(self) -> OpenEOCapabilitiesResponse:
        payload = self.adapter.get_capabilities()
        return OpenEOCapabilitiesResponse(**payload)

    def get_collections(self, limit: int) -> OpenEOCollectionsResponse:
        payload = self.adapter.get_collections(limit=limit)
        return OpenEOCollectionsResponse(**payload)
