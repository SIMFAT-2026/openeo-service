from fastapi import APIRouter, status

from app.schemas.jobs import IndicatorJobRequest, IndicatorJobResponse
from app.services.indicator_service import IndicatorService

router = APIRouter(prefix="/jobs", tags=["jobs"])
service = IndicatorService()


@router.post(
    "/ndvi",
    response_model=IndicatorJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_ndvi_job(payload: IndicatorJobRequest) -> IndicatorJobResponse:
    return service.create_ndvi_job(payload)


@router.post(
    "/ndmi",
    response_model=IndicatorJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_ndmi_job(payload: IndicatorJobRequest) -> IndicatorJobResponse:
    return service.create_ndmi_job(payload)
