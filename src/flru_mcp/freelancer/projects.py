from __future__ import annotations

from urllib.parse import urlparse

from flru_mcp.freelancer.client import FreelancerClient
from flru_mcp.freelancer.models import FreelancerProject, FreelancerProjectDetail
from flru_mcp.freelancer.parsers import parse_project_list, parse_project_page


class FreelancerProjectService:
    def __init__(self, client: FreelancerClient):
        self.client = client

    async def list_projects(self, page: int = 1, limit: int = 20, query: str | None = None, skill: str | None = None) -> list[FreelancerProject]:
        path, params = self.client.jobs_url(page=page, query=query, skill=skill)
        html = await self.client.get_text(path, params=params)
        return parse_project_list(html, self.client.settings.freelancer_base_url)[:limit]

    async def search_projects(self, query: str, page: int = 1, limit: int = 50) -> list[FreelancerProject]:
        return await self.list_projects(page=page, limit=limit, query=query)

    async def get_project(self, project_id: str | None = None, url: str | None = None) -> FreelancerProjectDetail:
        if not url and project_id:
            url = f"{self.client.settings.freelancer_base_url}/projects/{project_id.replace('--', '/')}"
        if not url:
            raise ValueError("project_id or url is required")
        path = urlparse(url).path if url.startswith("http") else url
        html = await self.client.get_text(url)
        return parse_project_page(html, url if url.startswith("http") else path, self.client.settings.freelancer_base_url)
