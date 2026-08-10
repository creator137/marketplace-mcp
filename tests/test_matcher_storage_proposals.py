from pathlib import Path

import pytest

from flru_mcp.config import ExpertiseProfile, Settings
from flru_mcp.flru.models import ProjectDetail, ProjectSummary
from flru_mcp.flru.proposals import ProposalService
from flru_mcp.services.project_matcher import ProjectMatcher
from flru_mcp.storage.database import connect
from flru_mcp.storage.repositories import HistoryRepository


def test_relevance_scoring() -> None:
    profile = ExpertiseProfile(["Bitrix24", "PHP", "REST API"], ["CRM integrations"], ["mass spam"])
    project = ProjectSummary(
        id="1",
        title="Bitrix24 REST API integration",
        url="https://www.fl.ru/projects/1/",
        description_preview="Need PHP CRM integration with Bitrix24 REST API.",
    )
    result = ProjectMatcher(profile).score(project)
    assert result.score >= 40
    assert result.reasons


def test_sqlite_history_and_draft(tmp_path: Path) -> None:
    repo = HistoryRepository(connect(tmp_path / "db.sqlite3"))
    project = ProjectSummary(id="1", title="Test", url="https://www.fl.ru/projects/1/")
    repo.upsert_project(project, relevance_score=70)
    repo.save_draft("1", "Здравствуйте")
    repo.mark_seen("1")
    history = repo.history("1")
    assert history["project"]["inspected"] == 1
    assert history["draft"]["text"] == "Здравствуйте"


class FakeClient:
    async def auth_status(self):
        return {"authenticated": True}


class UnauthenticatedClient:
    async def auth_status(self):
        return {"authenticated": False}


class FakeProjectService:
    async def get_project(self, project_id=None, url=None):
        return ProjectDetail(id=project_id, title="Open", url=f"https://www.fl.ru/projects/{project_id}/", accepts_proposals=True)


class ClosedProjectService:
    async def get_project(self, project_id=None, url=None):
        return ProjectDetail(id=project_id, title="Closed", url=f"https://www.fl.ru/projects/{project_id}/", accepts_proposals=False)


@pytest.mark.asyncio
async def test_dry_run_submission(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "db.sqlite3", dry_run=True)
    repo = HistoryRepository(connect(settings.database_path))
    service = ProposalService(settings, FakeClient(), FakeProjectService(), repo)
    result = await service.submit("1", "Здравствуйте")
    assert result["dry_run"] is True
    assert result["would_submit"]["project_id"] == "1"


@pytest.mark.asyncio
async def test_duplicate_prevention(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "db.sqlite3", dry_run=True)
    repo = HistoryRepository(connect(settings.database_path))
    repo.record_submission("1", "text", None, None, None)
    service = ProposalService(settings, FakeClient(), FakeProjectService(), repo)
    result = await service.submit("1", "Здравствуйте")
    assert result["error"] == "PROPOSAL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_expired_auth_blocks_submission(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "db.sqlite3", dry_run=True)
    repo = HistoryRepository(connect(settings.database_path))
    service = ProposalService(settings, UnauthenticatedClient(), FakeProjectService(), repo)
    result = await service.submit("1", "Здравствуйте")
    assert result["error"] == "AUTH_REQUIRED"


@pytest.mark.asyncio
async def test_closed_project_blocks_submission(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "db.sqlite3", dry_run=True)
    repo = HistoryRepository(connect(settings.database_path))
    service = ProposalService(settings, FakeClient(), ClosedProjectService(), repo)
    result = await service.submit("1", "Здравствуйте")
    assert result["error"] == "PROJECT_CLOSED"
