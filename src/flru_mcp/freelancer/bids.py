from __future__ import annotations

from flru_mcp.config import Settings
from flru_mcp.freelancer.browser import FreelancerBrowser
from flru_mcp.freelancer.projects import FreelancerProjectService
from flru_mcp.storage.repositories import HistoryRepository


class FreelancerBidService:
    def __init__(self, settings: Settings, browser: FreelancerBrowser, projects: FreelancerProjectService, repo: HistoryRepository):
        self.settings = settings
        self.browser = browser
        self.projects = projects
        self.repo = repo

    async def context(self, project_id: str | None = None, url: str | None = None) -> dict:
        project = await self.projects.get_project(project_id=project_id, url=url)
        return {
            "project": project.model_dump(),
            "bid_form_constraints": {
                "requires_amount": "unknown_until_authenticated",
                "requires_delivery_days": "unknown_until_authenticated",
                "max_cover_letter_length": None,
            },
            "existing_local_draft": self.repo.get_freelancer_bid_draft(project.id),
            "existing_user_bid": project.existing_user_bid,
        }

    async def submit(self, project_id: str, text: str, bid_amount: float | None = None, delivery_days: int | None = None, confirm: bool = False) -> dict:
        if not text.strip():
            return {"success": False, "error": "VALIDATION_ERROR", "field": "text"}
        if self.repo.has_submitted_freelancer_bid(project_id):
            return {"success": False, "error": "BID_ALREADY_EXISTS", "project_id": project_id}
        auth = await self.browser.auth_status()
        if not auth.get("authenticated"):
            return {"success": False, "error": "AUTH_REQUIRED", "auth": auth}
        project = await self.projects.get_project(project_id=project_id)
        if project.existing_user_bid:
            return {"success": False, "error": "BID_ALREADY_EXISTS", "source": "freelancer_page", "project_id": project_id}
        if self.settings.freelancer_dry_run or not confirm:
            return {
                "dry_run": True,
                "would_submit": {
                    "project_id": project_id,
                    "url": project.url,
                    "text": text,
                    "bid_amount": bid_amount,
                    "delivery_days": delivery_days,
                },
            }
        return {
            "success": False,
            "status": "submission_unimplemented",
            "error": "REAL_FREELANCER_BID_SUBMISSION_NOT_VERIFIED",
            "project_id": project_id,
        }
