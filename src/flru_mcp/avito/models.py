from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AvitoAuthStatus(BaseModel):
    authenticated: bool
    session_valid: bool
    source: str
    user_id: str | None = None
    name: str | None = None
    profile_url: str | None = None
    status: str | None = None
    reason: str | None = None


class AvitoAdDraft(BaseModel):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    category: str | None = None
    price: int | None = None
    location: str | None = None
    contact_name: str | None = None
    images: list[str] = Field(default_factory=list)
    params: dict[str, Any] = Field(default_factory=dict)


class AvitoItem(BaseModel):
    id: str
    title: str | None = None
    url: str | None = None
    status: str | None = None
    price: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
