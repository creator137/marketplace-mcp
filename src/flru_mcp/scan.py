from __future__ import annotations

import asyncio

from flru_mcp.config import load_expertise_profile, load_settings
from flru_mcp.flru.client import FlruClient
from flru_mcp.flru.projects import ProjectService
from flru_mcp.services.project_matcher import ProjectMatcher
from flru_mcp.storage.database import connect
from flru_mcp.storage.repositories import HistoryRepository


async def run() -> None:
    settings = load_settings()
    client = FlruClient(settings)
    projects = ProjectService(client)
    repo = HistoryRepository(connect(settings.database_path))
    matcher = ProjectMatcher(load_expertise_profile(settings.expertise_profile))
    try:
        for project in await projects.list_projects(limit=50):
            result = matcher.score(project)
            repo.upsert_project(project, relevance_score=result.score)
    finally:
        await client.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()

