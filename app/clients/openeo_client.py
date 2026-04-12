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

    def __init__(self, base_url: str, client_id: str, client_secret: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
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
