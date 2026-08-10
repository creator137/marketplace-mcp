from __future__ import annotations

import re

from flru_mcp.config import ExpertiseProfile
from flru_mcp.flru.models import ProjectSummary, RelevanceResult


def _norm(text: str) -> str:
    return text.casefold().replace("ё", "е")


class ProjectMatcher:
    def __init__(self, profile: ExpertiseProfile):
        self.profile = profile

    def score(self, project: ProjectSummary) -> RelevanceResult:
        haystack = _norm(" ".join(filter(None, [project.title, project.description_preview, project.category, project.subcategory])))
        score = 0
        reasons: list[str] = []
        risks: list[str] = []
        for item in self.profile.excluded_projects:
            if _norm(item) in haystack:
                score -= 60
                risks.append(f"Excluded topic mentioned: {item}")
        for item in self.profile.specializations:
            if _norm(item) in haystack:
                score += 14
                reasons.append(f"Specialization mentioned: {item}")
        for item in self.profile.preferred_projects:
            words = [_norm(w) for w in re.findall(r"[\w+.-]+", item) if len(w) > 2]
            matched = [w for w in words if w in haystack]
            if len(matched) >= max(1, min(2, len(words))):
                score += 10
                reasons.append(f"Preferred project signal: {item}")
        if project.budget.amount is not None:
            if project.budget.amount >= 20000:
                score += 8
                reasons.append("Budget is at least 20000 RUB")
            elif project.budget.amount < 5000:
                score -= 8
                risks.append("Budget appears low")
        elif project.budget.type == "negotiable":
            score += 2
            reasons.append("Budget is negotiable")
        if not project.description_preview or len(project.description_preview) < 80:
            risks.append("Requirements are short or vague")
        return RelevanceResult(project=project, score=max(0, min(100, score)), reasons=reasons, risks=risks)

