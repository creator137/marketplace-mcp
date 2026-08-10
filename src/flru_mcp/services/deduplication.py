from __future__ import annotations

from flru_mcp.flru.models import ProjectDetail
from flru_mcp.storage.repositories import HistoryRepository


class DuplicateProposalError(RuntimeError):
    pass


def ensure_no_duplicate(repo: HistoryRepository, project: ProjectDetail) -> None:
    if repo.has_submitted(project.id):
        raise DuplicateProposalError("PROPOSAL_ALREADY_EXISTS")
    if project.existing_user_proposal:
        raise DuplicateProposalError("PROPOSAL_ALREADY_EXISTS")

