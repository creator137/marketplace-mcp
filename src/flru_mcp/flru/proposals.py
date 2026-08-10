from __future__ import annotations

from datetime import datetime, timezone

import structlog

from flru_mcp.config import Settings
from flru_mcp.flru.client import FlruClient
from flru_mcp.flru.models import SubmittedProposal
from flru_mcp.flru.projects import ProjectService
from flru_mcp.services.deduplication import DuplicateProposalError, ensure_no_duplicate
from flru_mcp.storage.repositories import HistoryRepository

log = structlog.get_logger(__name__)


class ProposalService:
    def __init__(self, settings: Settings, client: FlruClient, projects: ProjectService, repo: HistoryRepository):
        self.settings = settings
        self.client = client
        self.projects = projects
        self.repo = repo

    async def submit(self, project_id: str, text: str, price: int | None = None, delivery_days: int | None = None) -> dict:
        if not text.strip():
            return {"success": False, "error": "VALIDATION_ERROR", "field": "text"}
        auth = await self.client.auth_status()
        if not auth.get("authenticated"):
            return {"success": False, "error": "AUTH_REQUIRED"}
        project = await self.projects.get_project(project_id=project_id)
        self.repo.upsert_project(project)
        try:
            ensure_no_duplicate(self.repo, project)
        except DuplicateProposalError:
            return {"success": False, "error": "PROPOSAL_ALREADY_EXISTS", "project_id": project_id}
        if project.accepts_proposals is False:
            return {"success": False, "error": "PROJECT_CLOSED", "project_id": project_id}
        if project.proposal_form.max_length and len(text) > project.proposal_form.max_length:
            return {"success": False, "error": "VALIDATION_ERROR", "field": "text", "max_length": project.proposal_form.max_length}
        if project.proposal_form.requires_price and price is None:
            return {"success": False, "error": "VALIDATION_ERROR", "field": "price"}
        if project.proposal_form.requires_delivery_days and delivery_days is None:
            return {"success": False, "error": "VALIDATION_ERROR", "field": "delivery_days"}
        if self.settings.dry_run:
            log.info("proposal_preview", project_id=project_id)
            return {"dry_run": True, "would_submit": {"project_id": project_id, "text": text, "price": price, "delivery_days": delivery_days}}
        if not project.proposal_form.available:
            return {
                "success": False,
                "status": "submission_unavailable",
                "error": "PROPOSAL_FORM_NOT_DETECTED",
                "project_id": project_id,
            }
        return {
            "success": False,
            "status": "submission_unknown",
            "error": "REAL_SUBMISSION_NOT_ENABLED_FOR_UNVERIFIED_FORM",
            "project_id": project_id,
        }


def submission_result(project_id: str, proposal_id: str | None = None) -> SubmittedProposal:
    return SubmittedProposal(success=True, project_id=project_id, proposal_id=proposal_id, submitted_at=datetime.now(timezone.utc))

