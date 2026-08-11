from __future__ import annotations

from typing import Any

import structlog
from pydantic import ValidationError

from flru_mcp.avito.browser import AvitoBrowser
from flru_mcp.avito.client import AvitoApiClient, AvitoApiError
from flru_mcp.avito.models import AvitoAdDraft
from flru_mcp.avito.parsers import human_error
from flru_mcp.config import Settings
from flru_mcp.storage.repositories import HistoryRepository

log = structlog.get_logger(__name__)


class AvitoAdService:
    def __init__(self, settings: Settings, api: AvitoApiClient, browser: AvitoBrowser, repo: HistoryRepository):
        self.settings = settings
        self.api = api
        self.browser = browser
        self.repo = repo

    async def auth_status(self) -> dict:
        api_status = await self.api.auth_status()
        return {
            "api": api_status,
            "browser": {
                "storage_state_exists": self.settings.avito_storage_state.exists(),
                "profile_dir": str(self.settings.avito_browser_profile),
            },
        }

    async def login(self, headless: bool = False) -> dict:
        return await self.browser.interactive_login(headless=headless)

    async def list_my_ads(self, limit: int = 50, offset: int = 0, status: str | None = None) -> dict:
        try:
            return await self.api.list_items(limit=limit, offset=offset, status=status)
        except AvitoApiError as exc:
            return {"error": "AVITO_API_ERROR", "http_status": exc.status_code, "message": human_error(exc.payload), "payload": exc.payload}

    async def get_ad(self, item_id: str) -> dict:
        try:
            return {"ad": await self.api.get_item(item_id)}
        except AvitoApiError as exc:
            return {"error": "AVITO_API_ERROR", "http_status": exc.status_code, "message": human_error(exc.payload), "payload": exc.payload}

    def create_draft(self, payload: dict[str, Any], draft_id: str | None = None) -> dict:
        try:
            draft = AvitoAdDraft(**payload)
        except ValidationError as exc:
            return {"success": False, "error": "VALIDATION_ERROR", "details": exc.errors()}
        saved = self.repo.save_avito_draft(draft.model_dump(), draft_id=draft_id)
        return {"success": True, "draft": saved}

    def get_draft(self, draft_id: str) -> dict:
        draft = self.repo.get_avito_draft(draft_id)
        if not draft:
            return {"error": "AVITO_DRAFT_NOT_FOUND", "draft_id": draft_id}
        return {"draft": draft}

    def list_drafts(self, limit: int = 50) -> dict:
        return {"drafts": self.repo.list_avito_drafts(limit)}

    async def open_create_ad_page(self, headless: bool = False) -> dict:
        return await self.browser.open_create_ad(headless=headless)

    async def publish_ad(self, draft_id: str, confirm: bool = False) -> dict:
        draft = self.repo.get_avito_draft(draft_id)
        if not draft:
            return {"success": False, "error": "AVITO_DRAFT_NOT_FOUND", "draft_id": draft_id}
        if self.repo.has_published_avito_draft(draft_id):
            return {"success": False, "error": "AVITO_AD_ALREADY_PUBLISHED", "draft_id": draft_id}
        if self.settings.avito_dry_run:
            log.info("avito_publish_preview", draft_id=draft_id)
            return {"dry_run": True, "would_publish": draft}
        if not confirm:
            return {"success": False, "error": "EXPLICIT_CONFIRMATION_REQUIRED", "draft_id": draft_id}
        return {
            "success": False,
            "status": "publication_unavailable",
            "error": "REAL_AVITO_PUBLISH_NOT_ENABLED_FOR_UNVERIFIED_FORM",
            "draft_id": draft_id,
            "reason": "Avito add-item web flow currently shows IP/captcha protection in this environment; no form POST has been verified.",
        }
