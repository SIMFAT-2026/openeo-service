from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import httpx

from app.core.exceptions import ExternalServiceError
from app.models.job import IndicatorType
from app.schemas.jobs import IndicatorJobRequest


class OpenEOClient:
    """
    Placeholder client for future real integration with openEO/Copernicus API.
    """

    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        access_token: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token.strip()
        self.identity_token_url = (
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
        )
        self.timeout_seconds = 10
        self._token_cache: dict[str, Any] = {}
        self._response_cache: dict[str, Any] = {}
        self._api_base_url_cache: dict[str, Any] = {}

    def submit_indicator_job(self, indicator_type: IndicatorType, payload: IndicatorJobRequest) -> UUID:
        _ = (indicator_type, payload)
        return uuid4()

    def fetch_capabilities(self) -> dict[str, Any]:
        cache_key = "capabilities"
        cached_value = self._get_cached_response(cache_key)
        if cached_value:
            return cached_value

        token = self._get_access_token()
        url = f"{self.base_url}/.well-known/openeo"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, headers={"Authorization": f"Bearer {token}"})
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"openEO connectivity error while loading capabilities: {exc}") from exc

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"openEO capabilities request failed with status {response.status_code}"
            )

        payload = {
            "cached": False,
            "fetchedAt": datetime.now(timezone.utc),
            "data": response.json(),
        }
        self._set_cached_response(cache_key, payload, ttl_seconds=300)
        return payload

    def fetch_collections(self, limit: int) -> dict[str, Any]:
        cache_key = f"collections:{limit}"
        cached_value = self._get_cached_response(cache_key)
        if cached_value:
            return cached_value

        token = self._get_access_token()
        api_base_url = self._resolve_api_base_url()
        url = f"{api_base_url}/collections"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(
                    url,
                    params={"limit": limit},
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"openEO connectivity error while loading collections: {exc}") from exc

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"openEO collections request failed with status {response.status_code}"
            )

        data = response.json()
        collections = data.get("collections", [])
        sliced = collections[:limit]
        payload = {
            "cached": False,
            "fetchedAt": datetime.now(timezone.utc),
            "limit": limit,
            "count": len(sliced),
            "collections": sliced,
        }
        self._set_cached_response(cache_key, payload, ttl_seconds=300)
        return payload

    def fetch_indicator_latest(
        self,
        indicator_type: IndicatorType,
        payload: IndicatorJobRequest,
    ) -> dict[str, Any]:
        if not payload.aoi or payload.aoi.type != "bbox" or len(payload.aoi.coordinates) != 4:
            raise ExternalServiceError("A bbox aoi with 4 coordinates is required to query indicator values", 400)

        cache_key = (
            f"indicator:{indicator_type.value}:{payload.period_start.isoformat()}:{payload.period_end.isoformat()}:"
            f"{','.join(str(v) for v in payload.aoi.coordinates)}"
        )
        cached_value = self._get_cached_response(cache_key)
        if cached_value:
            return cached_value

        token = self._get_processing_access_token()
        api_base_url = self._resolve_api_base_url()
        bbox = self._build_spatial_extent(payload.aoi.coordinates)
        polygon = self._bbox_to_polygon(payload.aoi.coordinates)
        process_graph = self._build_indicator_process_graph(
            indicator_type=indicator_type,
            temporal_extent=[payload.period_start.isoformat(), payload.period_end.isoformat()],
            spatial_extent=bbox,
            polygon=polygon,
        )

        try:
            with httpx.Client(timeout=60) as client:
                response = client.post(
                    f"{api_base_url}/result",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={"process": {"process_graph": process_graph}},
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"openEO connectivity error while loading indicator value: {exc}") from exc

        if response.status_code >= 400:
            message = self._extract_openeo_error(response)
            raise ExternalServiceError(
                f"openEO indicator request failed with status {response.status_code}: {message}"
            )

        measured_value = self._extract_first_numeric(response)
        now = datetime.now(timezone.utc)
        result = {
            "cached": False,
            "fetchedAt": now,
            "measuredAt": now,
            "indicatorType": indicator_type.value,
            "regionId": payload.region_id,
            "periodStart": payload.period_start,
            "periodEnd": payload.period_end,
            "collectionId": "SENTINEL2_L2A",
            "value": measured_value,
        }
        self._set_cached_response(cache_key, result, ttl_seconds=300)
        return result

    def _get_access_token(self) -> str:
        cached_token = self._token_cache.get("access_token")
        expires_at = self._token_cache.get("expires_at")
        if cached_token and expires_at and datetime.now(timezone.utc) < expires_at:
            return cached_token

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    self.identity_token_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"Identity connectivity error while requesting token: {exc}") from exc

        if response.status_code >= 400:
            raise ExternalServiceError(
                f"Identity token request failed with status {response.status_code}"
            )

        payload = response.json()
        access_token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 1800))
        if not access_token:
            raise ExternalServiceError("Identity token response did not include access_token")

        safe_ttl = max(expires_in - 60, 60)
        self._token_cache["access_token"] = access_token
        self._token_cache["expires_at"] = datetime.now(timezone.utc) + timedelta(seconds=safe_ttl)
        return access_token

    def _get_processing_access_token(self) -> str:
        if self.access_token:
            return self.access_token

        raise ExternalServiceError(
            "OPENEO_ACCESS_TOKEN is required for processing endpoints "
            "(/result, /jobs). The configured client_credentials token only supports metadata probes in CDSE."
        )

    def _build_spatial_extent(self, bbox: list[float]) -> dict[str, Any]:
        return {
            "west": bbox[0],
            "south": bbox[1],
            "east": bbox[2],
            "north": bbox[3],
            "crs": "EPSG:4326",
        }

    def _bbox_to_polygon(self, bbox: list[float]) -> dict[str, Any]:
        west, south, east, north = bbox
        return {
            "type": "Polygon",
            "coordinates": [
                [
                    [west, south],
                    [east, south],
                    [east, north],
                    [west, north],
                    [west, south],
                ]
            ],
        }

    def _build_indicator_process_graph(
        self,
        indicator_type: IndicatorType,
        temporal_extent: list[str],
        spatial_extent: dict[str, Any],
        polygon: dict[str, Any],
    ) -> dict[str, Any]:
        if indicator_type == IndicatorType.NDVI:
            nir_band = "B08"
            red_band = "B04"
        else:
            nir_band = "B08"
            red_band = "B11"

        mean_reducer = {
            "process_graph": {
                "mean1": {
                    "process_id": "mean",
                    "arguments": {"data": {"from_parameter": "data"}},
                    "result": True,
                }
            }
        }
        return {
            "load_collection": {
                "process_id": "load_collection",
                "arguments": {
                    "id": "SENTINEL2_L2A",
                    "spatial_extent": spatial_extent,
                    "temporal_extent": temporal_extent,
                    "bands": [red_band, nir_band],
                },
            },
            "index": {
                "process_id": "ndvi",
                "arguments": {
                    "data": {"from_node": "load_collection"},
                    "nir": nir_band,
                    "red": red_band,
                },
            },
            "aggregate_spatial": {
                "process_id": "aggregate_spatial",
                "arguments": {
                    "data": {"from_node": "index"},
                    "geometries": polygon,
                    "reducer": mean_reducer,
                },
            },
            "reduce_time": {
                "process_id": "reduce_dimension",
                "arguments": {
                    "data": {"from_node": "aggregate_spatial"},
                    "dimension": "t",
                    "reducer": mean_reducer,
                },
            },
            "save": {
                "process_id": "save_result",
                "arguments": {
                    "data": {"from_node": "reduce_time"},
                    "format": "JSON",
                },
                "result": True,
            },
        }

    def _extract_openeo_error(self, response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:300]

        if isinstance(payload, dict):
            if isinstance(payload.get("message"), str):
                return payload["message"]
            errors = payload.get("errors")
            if isinstance(errors, list) and errors:
                first = errors[0]
                if isinstance(first, dict) and isinstance(first.get("message"), str):
                    return first["message"]
        return str(payload)[:300]

    def _extract_first_numeric(self, response: httpx.Response) -> float | None:
        try:
            payload = response.json()
        except ValueError:
            return None

        value = self._extract_numeric_recursive(payload)
        return float(value) if value is not None else None

    def _extract_numeric_recursive(self, payload: Any) -> float | int | None:
        if isinstance(payload, bool):
            return None
        if isinstance(payload, (float, int)):
            return payload
        if isinstance(payload, list):
            for item in payload:
                value = self._extract_numeric_recursive(item)
                if value is not None:
                    return value
            return None
        if isinstance(payload, dict):
            for item in payload.values():
                value = self._extract_numeric_recursive(item)
                if value is not None:
                    return value
            return None
        return None

    def _get_cached_response(self, key: str) -> dict[str, Any] | None:
        item = self._response_cache.get(key)
        if not item:
            return None

        expires_at = item.get("expires_at")
        if not expires_at or datetime.now(timezone.utc) >= expires_at:
            self._response_cache.pop(key, None)
            return None

        value = dict(item["value"])
        value["cached"] = True
        return value

    def _set_cached_response(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self._response_cache[key] = {
            "value": dict(value),
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        }

    def _resolve_api_base_url(self) -> str:
        cached_value = self._api_base_url_cache.get("url")
        cached_expiry = self._api_base_url_cache.get("expires_at")
        if cached_value and cached_expiry and datetime.now(timezone.utc) < cached_expiry:
            return cached_value

        discovery_url = f"{self.base_url}/.well-known/openeo"
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(discovery_url)
        except httpx.HTTPError as exc:
            raise ExternalServiceError(f"openEO discovery connectivity error: {exc}") from exc

        if response.status_code >= 400:
            raise ExternalServiceError(f"openEO discovery request failed with status {response.status_code}")

        versions = response.json().get("versions", [])
        production_versions = [entry for entry in versions if entry.get("production") is True]
        if not production_versions:
            raise ExternalServiceError("openEO discovery did not return production API versions")

        # Prefer the highest stable production API version.
        def version_key(item: dict[str, Any]) -> tuple[int, ...]:
            raw = str(item.get("api_version", "0.0.0"))
            return tuple(int(part) for part in raw.split(".") if part.isdigit())

        production_versions.sort(key=version_key, reverse=True)
        selected_url = str(production_versions[0].get("url", "")).rstrip("/")
        if not selected_url:
            raise ExternalServiceError("openEO discovery did not provide an API URL")

        self._api_base_url_cache = {
            "url": selected_url,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        return selected_url
