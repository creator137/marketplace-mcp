from __future__ import annotations

from datetime import datetime

import structlog
from playwright.async_api import async_playwright

from flru_mcp.config import Settings
from flru_mcp.flru.parsers import parse_auth_status

log = structlog.get_logger(__name__)


class FlruBrowser:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def interactive_login(self, headless: bool | None = None, timeout_seconds: int = 300) -> dict:
        browser_headless = self.settings.headless if headless is None else headless
        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(self.settings.browser_profile),
                headless=browser_headless,
                viewport={"width": 1365, "height": 900},
            )
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                page.on("framenavigated", lambda frame: log.info("browser_navigated", url=frame.url) if frame == page.main_frame else None)
                await page.goto(f"{self.settings.base_url}/account/login/", wait_until="domcontentloaded")
                if self.settings.login:
                    await page.locator("input[name='username']").fill(self.settings.login)
                if self.settings.password:
                    await page.locator("input[name='password']").fill(self.settings.password)
                captcha = await page.locator(".smart-captcha, iframe[src*='captcha']").count()
                if captcha:
                    log.info("manual_verification_required", reason="captcha")
                await page.wait_for_function(
                    "() => document.querySelector('meta[name=\"current-uid\"]')?.content !== '0' || !location.pathname.includes('/account/login')",
                    timeout=timeout_seconds * 1000,
                )
                await page.goto(self.settings.base_url, wait_until="domcontentloaded")
                html = await page.content()
                status = parse_auth_status(html, self.settings.base_url)
                await context.storage_state(path=str(self.settings.storage_state))
                status["status"] = "ok" if status["authenticated"] else "manual_verification_required"
                if not status["authenticated"] and captcha:
                    status["reason"] = "captcha"
                return status
            except Exception as exc:
                if self.settings.debug:
                    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                    await page.screenshot(path=str(self.settings.debug_dir / f"login-failure-{stamp}.png"), full_page=True)
                    (self.settings.debug_dir / f"login-failure-{stamp}.html").write_text(await page.content(), encoding="utf-8")
                return {"authenticated": False, "session_valid": False, "status": "manual_verification_required", "reason": str(exc)}
            finally:
                await context.close()

