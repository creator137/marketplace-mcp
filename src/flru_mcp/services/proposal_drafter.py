from __future__ import annotations

from flru_mcp.flru.models import ProjectDetail


def proposal_context(project: ProjectDetail) -> dict:
    return {
        "project_id": project.id,
        "title": project.title,
        "description": project.description,
        "customer": project.customer.model_dump(),
        "required_skills": project.skills,
        "budget": project.budget.model_dump(),
        "proposal_form_constraints": project.proposal_form.model_dump(),
        "maximum_proposal_length": project.proposal_form.max_length,
        "existing_user_proposal": project.existing_user_proposal.model_dump() if project.existing_user_proposal else None,
    }

