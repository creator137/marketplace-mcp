from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FreelancerBudget(BaseModel):
    raw: str | None = None
    amount_min: float | None = None
    amount_max: float | None = None
    currency: str | None = None
    type: str = "unknown"


class FreelancerEmployer(BaseModel):
    name: str | None = None
    profile_url: str | None = None
    rating: float | None = None
    reviews: int | None = None
    verified: bool | None = None


class FreelancerProject(BaseModel):
    id: str
    title: str
    url: str
    description_preview: str | None = None
    budget: FreelancerBudget = Field(default_factory=FreelancerBudget)
    skills: list[str] = Field(default_factory=list)
    employer: FreelancerEmployer = Field(default_factory=FreelancerEmployer)
    bid_count: int | None = None
    published_at: str | None = None
    source: str = "freelancer"


class FreelancerProjectDetail(FreelancerProject):
    description: str | None = None
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    bid_form_available: bool | None = None
    existing_user_bid: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class FreelancerMatch(BaseModel):
    project: FreelancerProject
    score: int
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
