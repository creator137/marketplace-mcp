from __future__ import annotations

from flru_mcp.config import ExpertiseProfile
from flru_mcp.freelancer.models import FreelancerMatch, FreelancerProject


class FreelancerMatcher:
    def __init__(self, profile: ExpertiseProfile):
        self.profile = profile

    def score(self, project: FreelancerProject, description: str | None = None) -> FreelancerMatch:
        text = " ".join([project.title, project.description_preview or "", description or "", " ".join(project.skills)]).lower()
        score = 0
        reasons: list[str] = []
        risks: list[str] = []
        for term in self.profile.specializations + self.profile.preferred_projects:
            if term.lower() in text:
                score += 10
                reasons.append(f"mentions {term}")
        for term in self.profile.excluded_projects:
            if term.lower() in text:
                score -= 35
                risks.append(f"excluded term: {term}")
        for term in ["php", "laravel", "python", "fastapi", "api", "crm", "automation", "telegram", "llm", "ai", "bitrix"]:
            if term in text:
                score += 8
                reasons.append(f"keyword: {term}")
        if project.budget.amount_min or project.budget.amount_max:
            score += 4
            reasons.append("budget is specified")
        return FreelancerMatch(project=project, score=max(0, min(100, score)), reasons=reasons[:12], risks=risks[:8])
