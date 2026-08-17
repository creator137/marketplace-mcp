from __future__ import annotations

from playwright.async_api import TimeoutError as PlaywrightTimeoutError, async_playwright

from flru_mcp.config import Settings


class FreelancerBrowser:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def login(self, headless: bool | None = None, timeout_seconds: int = 300) -> dict:
        browser_headless = self.settings.freelancer_headless if headless is None else headless
        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(self.settings.freelancer_browser_profile),
                headless=browser_headless,
                viewport={"width": 1365, "height": 900},
                args=["--no-proxy-server", "--proxy-server=direct://"],
            )
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                await page.goto(f"{self.settings.freelancer_base_url}/login", wait_until="domcontentloaded")
                if self.settings.freelancer_login:
                    await self._try_fill(page, ["input[type=email]", "input[name=email]", "input[name=username]"], self.settings.freelancer_login)
                if self.settings.freelancer_password:
                    await self._try_fill(page, ["input[type=password]", "input[name=password]"], self.settings.freelancer_password)
                if self.settings.freelancer_login and self.settings.freelancer_password:
                    await self._try_click(page, ["button[type=submit]", "button:has-text('Log In')", "button:has-text('Login')"])
                captcha = await page.locator("iframe[src*='captcha'], iframe[src*='recaptcha'], .g-recaptcha").count()
                try:
                    await page.wait_for_function(
                        """() => {
                            const text = document.body.innerText.toLowerCase();
                            return !location.pathname.includes('/login')
                                || text.includes('dashboard')
                                || text.includes('my projects')
                                || text.includes('inbox')
                                || text.includes('verify')
                                || text.includes('captcha');
                        }""",
                        timeout=timeout_seconds * 1000,
                    )
                except PlaywrightTimeoutError:
                    return {
                        "status": "manual_verification_required",
                        "reason": "login_timeout",
                        "current_url": page.url,
                        "message": "Complete Freelancer login manually and call freelancer_auth_status.",
                    }
                await context.storage_state(path=str(self.settings.freelancer_storage_state))
                body = (await page.locator("body").inner_text(timeout=10000)).lower()
                authenticated = any(token in body for token in ["dashboard", "my projects", "post a project", "inbox"]) and "log in" not in body[:1000]
                return {
                    "status": "authenticated" if authenticated else "manual_verification_required",
                    "current_url": page.url,
                    "authenticated": authenticated,
                    "manual_verification_required": (not authenticated) or bool(captcha),
                    "message": "Complete Freelancer login manually if captcha, 2FA, email verification, or profile checks appear.",
                }
            finally:
                await context.storage_state(path=str(self.settings.freelancer_storage_state))
                await context.close()

    async def auth_status(self) -> dict:
        async with async_playwright() as pw:
            context = await pw.chromium.launch_persistent_context(
                user_data_dir=str(self.settings.freelancer_browser_profile),
                headless=True,
                viewport={"width": 1365, "height": 900},
                args=["--no-proxy-server", "--proxy-server=direct://"],
            )
            page = context.pages[0] if context.pages else await context.new_page()
            try:
                await page.goto(self.settings.freelancer_base_url, wait_until="domcontentloaded")
                text = (await page.locator("body").inner_text(timeout=10000)).lower()
                url = page.url
                authenticated = any(token in text for token in ["dashboard", "my projects", "post a project", "inbox"]) and "log in" not in text[:1000]
                if authenticated:
                    await context.storage_state(path=str(self.settings.freelancer_storage_state))
                return {
                    "authenticated": authenticated,
                    "session_valid": authenticated,
                    "current_url": url,
                    "storage_state": str(self.settings.freelancer_storage_state),
                }
            finally:
                await context.close()

    @staticmethod
    async def _try_fill(page, selectors: list[str], value: str) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count():
                    await locator.fill(value, timeout=2000)
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    async def _try_click(page, selectors: list[str]) -> bool:
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count():
                    await locator.click(timeout=3000)
                    return True
            except Exception:
                continue
        return False
