from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class Budget(BaseModel):
    amount: int | None = None
    currency: str | None = "RUB"
    type: Literal["fixed", "hourly", "negotiable", "unknown"] = "unknown"
    raw: str | None = None


class Customer(BaseModel):
    name: str | None = None
    profile_url: str | None = None
    rating: float | None = None
    reviews: int | None = None
    projects_published: int | None = None
    projects_completed: int | None = None
    registration_date: str | None = None


class Attachment(BaseModel):
    name: str
    url: str


class ExistingProposal(BaseModel):
    text: str | None = None
    submitted_at: str | None = None
    proposal_id: str | None = None


class ProposalForm(BaseModel):
    available: bool = False
    action_url: str | None = None
    method: str | None = None
    csrf_token: str | None = None
    max_length: int | None = None
    requires_price: bool = False
    requires_delivery_days: bool = False
    raw_fields: dict[str, Any] = Field(default_factory=dict)


class ProjectSummary(BaseModel):
    id: str
    title: str
    url: str
    description_preview: str | None = None
    budget: Budget = Field(default_factory=Budget)
    category: str | None = None
    subcategory: str | None = None
    published_at: str | None = None
    customer: Customer = Field(default_factory=Customer)
    proposal_count: int | None = None


class ProjectDetail(ProjectSummary):
    description: str | None = None
    skills: list[str] = Field(default_factory=list)
    deadline: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)
    existing_user_proposal: ExistingProposal | None = None
    proposal_form: ProposalForm = Field(default_factory=ProposalForm)
    accepts_proposals: bool | None = None


class RelevanceResult(BaseModel):
    project: ProjectSummary
    score: int
    reasons: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class AuthStatus(BaseModel):
    authenticated: bool
    username: str | None = None
    profile_url: str | None = None
    session_valid: bool = False
    status: str | None = None
    reason: str | None = None


class SubmittedProposal(BaseModel):
    success: bool
    project_id: str
    submitted_at: datetime | None = None
    proposal_id: str | None = None
    status: str | None = None
    error: str | None = None

