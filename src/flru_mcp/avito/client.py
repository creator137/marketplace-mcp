from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

from flru_mcp.avito.parsers import extract_items_from_api_payload, human_error, normalize_api_item
from flru_mcp.config import Settings

log = structlog.get_logger(__name__)


class AvitoApiError(RuntimeError):
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.payload = payload
        super().__init__(human_error(payload) or f"Avito API error {status_code}")


class AvitoApiClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._access_token: str | None = None
        self._expires_at = 0.0

    def configured(self) -> bool:
        return bool(self.settings.avito_client_id and self.settings.avito_client_secret)

    async def _token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token
        if not self.configured():
            raise AvitoApiError(401, {"error": "AVITO_API_CREDENTIALS_REQUIRED"})
        async with httpx.AsyncClient(timeout=self.settings.http_timeout, trust_env=False) as client:
            response = await client.post(
                f"{self.settings.avito_api_base_url}/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.settings.avito_client_id,
                    "client_secret": self.settings.avito_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        payload = _json_or_text(response)
        if response.status_code >= 400:
            raise AvitoApiError(response.status_code, payload)
        self._access_token = payload["access_token"]
        self._expires_at = time.time() + int(payload.get("expires_in") or 86400)
        log.info("avito_token_refreshed", expires_in=payload.get("expires_in"))
        return self._access_token

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        token = await self._token()
        headers = dict(kwargs.pop("headers", {}) or {})
        headers["Authorization"] = f"Bearer {token}"
        async with httpx.AsyncClient(timeout=self.settings.http_timeout, trust_env=False) as client:
            response = await client.request(method, f"{self.settings.avito_api_base_url}{path}", headers=headers, **kwargs)
            if response.status_code == 401:
                self._access_token = None
                token = await self._token()
                headers["Authorization"] = f"Bearer {token}"
                response = await client.request(method, f"{self.settings.avito_api_base_url}{path}", headers=headers, **kwargs)
        payload = _json_or_text(response)
        if response.status_code >= 400:
            raise AvitoApiError(response.status_code, payload)
        return payload

    async def auth_status(self) -> dict:
        if not self.configured():
            return {
                "authenticated": False,
                "session_valid": False,
                "source": "api",
                "status": "credentials_required",
                "error": "AVITO_API_CREDENTIALS_REQUIRED",
            }
        try:
            payload = await self.request("GET", "/core/v1/accounts/self")
        except AvitoApiError as exc:
            return {
                "authenticated": False,
                "session_valid": False,
                "source": "api",
                "status": "api_error",
                "http_status": exc.status_code,
                "error": human_error(exc.payload),
            }
        user_id = payload.get("id") or payload.get("user_id") or payload.get("userId")
        return {
            "authenticated": True,
            "session_valid": True,
            "source": "api",
            "user_id": str(user_id) if user_id is not None else None,
            "name": payload.get("name") or payload.get("login"),
            "raw": payload,
        }

    async def list_items(self, limit: int = 50, offset: int = 0, status: str | None = None) -> dict:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        payload = await self.request("GET", "/core/v1/items", params=params)
        return {"items": extract_items_from_api_payload(payload), "raw": payload}

    async def get_item(self, item_id: str) -> dict:
        payload = await self.request("GET", f"/core/v1/items/{item_id}")
        return normalize_api_item(payload)


def _json_or_text(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text
