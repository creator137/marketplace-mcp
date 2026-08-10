from __future__ import annotations

from urllib.parse import urljoin

from flru_mcp.flru.client import FlruClient
from flru_mcp.flru.models import ProjectDetail, ProjectSummary
from flru_mcp.flru.parsers import parse_project_list, parse_project_page


class ProjectService:
    def __init__(self, client: FlruClient):
        self.client = client

    async def list_projects(
        self,
        page: int = 1,
        limit: int = 20,
        category: str | None = None,
        subcategory: str | None = None,
        query: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
        only_new: bool = False,
    ) -> list[ProjectSummary]:
        category_path = "/".join(part.strip("/") for part in [category, subcategory] if part)
        path, params = self.client.projects_url(page=page, category=category_path or None, query=query)
        html = await self.client.get_text(path, params=params)
        projects = parse_project_list(html, self.client.settings.base_url)
        filtered = []
        for project in projects:
            amount = project.budget.amount
            if budget_min is not None and amount is not None and amount < budget_min:
                continue
            if budget_max is not None and amount is not None and amount > budget_max:
                continue
            filtered.append(project)
        return filtered[:limit]

    async def search_projects(self, query: str, page: int = 1, limit: int = 50) -> list[ProjectSummary]:
        return await self.list_projects(page=page, limit=limit, query=query)

    async def get_project(self, project_id: str | None = None, url: str | None = None) -> ProjectDetail:
        if not url and project_id:
            url = urljoin(self.client.settings.base_url, f"/projects/{project_id}/")
        if not url:
            raise ValueError("project_id or url is required")
        html = await self.client.get_text(url)
        detail = parse_project_page(html, url, self.client.settings.base_url)
        if project_id and detail.id and detail.id != project_id:
            raise ValueError("PROJECT_ID_MISMATCH")
        return detail

