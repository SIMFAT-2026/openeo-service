from uuid import UUID, uuid4

from app.models.job import IndicatorType
from app.schemas.jobs import IndicatorJobRequest


class OpenEOClient:
    """
    Placeholder client for future real integration with openEO/Copernicus API.
    """

    def __init__(self, base_url: str, client_id: str, client_secret: str) -> None:
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret

    def submit_indicator_job(self, indicator_type: IndicatorType, payload: IndicatorJobRequest) -> UUID:
        _ = (indicator_type, payload)
        return uuid4()
