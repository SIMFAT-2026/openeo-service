from fastapi import APIRouter, Query

from app.schemas.openeo import OpenEOCapabilitiesResponse, OpenEOCollectionsResponse
from app.services.openeo_probe_service import OpenEOProbeService

router = APIRouter(prefix="/openeo", tags=["openeo"])
service = OpenEOProbeService()


@router.get("/capabilities", response_model=OpenEOCapabilitiesResponse)
def get_capabilities() -> OpenEOCapabilitiesResponse:
    return service.get_capabilities()


@router.get("/collections", response_model=OpenEOCollectionsResponse)
def get_collections(limit: int = Query(default=5, ge=1, le=20)) -> OpenEOCollectionsResponse:
    return service.get_collections(limit=limit)
