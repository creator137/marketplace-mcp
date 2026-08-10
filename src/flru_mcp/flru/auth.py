from __future__ import annotations

from flru_mcp.flru.browser import FlruBrowser
from flru_mcp.flru.client import FlruClient


class AuthService:
    def __init__(self, client: FlruClient, browser: FlruBrowser):
        self.client = client
        self.browser = browser

    async def status(self) -> dict:
        return await self.client.auth_status()

    async def login(self, headless: bool | None = None) -> dict:
        return await self.browser.interactive_login(headless=headless)

