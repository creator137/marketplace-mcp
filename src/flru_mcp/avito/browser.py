from __future__ import annotations

from datetime import datetime

import structlog
from playwright.async_api import async_playwright

from flru_mcp.avito.parsers import parse_browser_auth_status
from flru_mcp.config import Settings

log = structlog.get_logger(__name__)


class AvitoBrowser:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def interactive_login(self, headless: bool | None = None, timeout_seconds: int = 300) -> dict:
        browser_headless = self.settings.avito_headless if headless is None else headless
        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(self.settings.avito_browser_profile),
                headless=browser_headless,
                viewport={"width": 1365, "height": 900},
            )
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                page.on("framenavigated", lambda frame: log.info("avito_browser_navigated", url=frame.url) if frame == page.main_frame else None)
                await page.goto(f"{self.settings.avito_base_url}/profile", wait_until="domcontentloaded")
                await page.wait_for_timeout(1000)
                status = parse_browser_auth_status(await page.content(), page.url, self.settings.avito_base_url)
                if status.get("reason") in {"captcha", "ip_captcha"} or not status.get("authenticated"):
                    log.info("avito_manual_verification_required", reason=status.get("reason") or "auth_required")
                    await page.wait_for_timeout(timeout_seconds * 1000)
                    status = parse_browser_auth_status(await page.content(), page.url, self.settings.avito_base_url)
                await context.storage_state(path=str(self.settings.avito_storage_state))
                return status
            except Exception as exc:
                if self.settings.debug:
                    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                    self.settings.debug_dir.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(self.settings.debug_dir / f"avito-login-failure-{stamp}.png"), full_page=True)
                    (self.settings.debug_dir / f"avito-login-failure-{stamp}.html").write_text(await page.content(), encoding="utf-8")
                return {
                    "authenticated": False,
                    "session_valid": False,
                    "source": "browser",
                    "status": "manual_verification_required",
                    "reason": str(exc),
                }
            finally:
                await context.close()

    async def open_create_ad(self, headless: bool | None = None) -> dict:
        browser_headless = self.settings.avito_headless if headless is None else headless
        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(self.settings.avito_browser_profile),
                headless=browser_headless,
                viewport={"width": 1365, "height": 900},
            )
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                await page.goto(f"{self.settings.avito_base_url}/additem", wait_until="domcontentloaded")
                await page.wait_for_timeout(1000)
                status = parse_browser_auth_status(await page.content(), page.url, self.settings.avito_base_url)
                await context.storage_state(path=str(self.settings.avito_storage_state))
                return {"opened": True, "url": page.url, "auth": status}
            finally:
                await context.close()
