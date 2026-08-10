from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from urllib.parse import urlencode, urljoin

import httpx
import structlog

from flru_mcp.config import Settings
from flru_mcp.flru.parsers import parse_auth_status

log = structlog.get_logger(__name__)


class FlruClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=settings.http_timeout,
            headers={
                "User-Agent": "flru-mcp/0.1 local user agent",
                "Accept-Language": "ru,en;q=0.8",
            },
            follow_redirects=True,
            trust_env=False,
        )
        self._load_storage_state(settings.storage_state)

    async def close(self) -> None:
        await self._client.aclose()

    def _load_storage_state(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("storage_state_invalid", path=str(path))
            return
        for cookie in data.get("cookies", []):
            name = cookie.get("name")
            value = cookie.get("value")
            domain = cookie.get("domain", "www.fl.ru").lstrip(".")
            if name and value:
                self._client.cookies.set(name, value, domain=domain, path=cookie.get("path", "/"))

    async def _respect_delay(self) -> None:
        delay = random.randint(self.settings.delay_min_ms, self.settings.delay_max_ms) / 1000
        await asyncio.sleep(delay)

    async def get_text(self, path_or_url: str, params: dict | None = None) -> str:
        await self._respect_delay()
        url = path_or_url if path_or_url.startswith("http") else urljoin(self.settings.base_url + "/", path_or_url.lstrip("/"))
        log.info("flru_http_get", url=url, params=params)
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.text

    async def auth_status(self) -> dict:
        html = await self.get_text("/")
        return parse_auth_status(html, self.settings.base_url)

    def projects_url(self, page: int = 1, category: str | None = None, query: str | None = None, kind: int | None = 1) -> tuple[str, dict]:
        path = "/projects/"
        if category:
            path = f"/projects/category/{category.strip('/')}/"
        params: dict[str, str | int] = {}
        if page > 1:
            params["page"] = page
        if kind is not None:
            params["kind"] = kind
        if query:
            params["q"] = query
        return path, params
