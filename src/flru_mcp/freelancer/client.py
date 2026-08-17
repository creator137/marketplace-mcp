from __future__ import annotations

import asyncio
import json
import random
from pathlib import Path
from urllib.parse import urlencode, urljoin

import httpx

from flru_mcp.config import Settings


class FreelancerClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._client = httpx.AsyncClient(
            base_url=settings.freelancer_base_url,
            follow_redirects=True,
            timeout=settings.http_timeout,
            trust_env=False,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; marketplace-mcp/0.1)",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        self._load_storage_state(settings.freelancer_storage_state)

    async def close(self) -> None:
        await self._client.aclose()

    def _load_storage_state(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return
        for cookie in data.get("cookies", []):
            name = cookie.get("name")
            value = cookie.get("value")
            domain = (cookie.get("domain") or "www.freelancer.com").lstrip(".")
            if name and value:
                self._client.cookies.set(name, value, domain=domain, path=cookie.get("path", "/"))

    async def _delay(self) -> None:
        await asyncio.sleep(random.randint(self.settings.delay_min_ms, self.settings.delay_max_ms) / 1000)

    async def get_text(self, path_or_url: str, params: dict | None = None) -> str:
        await self._delay()
        url = path_or_url if path_or_url.startswith("http") else urljoin(self.settings.freelancer_base_url + "/", path_or_url.lstrip("/"))
        response = await self._client.get(url, params=params)
        response.raise_for_status()
        return response.text

    def jobs_url(self, page: int = 1, query: str | None = None, skill: str | None = None) -> tuple[str, dict]:
        if skill:
            path = f"/jobs/{skill.strip('/')}/"
        else:
            path = "/jobs/"
        params: dict[str, str | int] = {}
        if page > 1:
            params["page"] = page
        if query:
            params["keyword"] = query
        return path, params
