from __future__ import annotations

import sys
from typing import Any

import structlog
from mcp.server.fastmcp import FastMCP

from flru_mcp.avito.ads import AvitoAdService
from flru_mcp.avito.browser import AvitoBrowser
from flru_mcp.avito.client import AvitoApiClient
from flru_mcp.config import load_expertise_profile, load_settings
from flru_mcp.flru.auth import AuthService
from flru_mcp.flru.browser import FlruBrowser
from flru_mcp.flru.client import FlruClient
from flru_mcp.flru.customer import CustomerService
from flru_mcp.flru.messages import MessageService
from flru_mcp.flru.projects import ProjectService
from flru_mcp.flru.proposals import ProposalService
from flru_mcp.freelancer.bids import FreelancerBidService
from flru_mcp.freelancer.browser import FreelancerBrowser
from flru_mcp.freelancer.client import FreelancerClient
from flru_mcp.freelancer.matcher import FreelancerMatcher
from flru_mcp.freelancer.projects import FreelancerProjectService
from flru_mcp.services.project_matcher import ProjectMatcher
from flru_mcp.services.proposal_drafter import proposal_context
from flru_mcp.storage.database import connect
from flru_mcp.storage.repositories import HistoryRepository

structlog.configure(
    processors=[structlog.processors.JSONRenderer()],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)

settings = load_settings()
client = FlruClient(settings)
project_service = ProjectService(client)
repo = HistoryRepository(connect(settings.database_path))
matcher = ProjectMatcher(load_expertise_profile(settings.expertise_profile))
auth_service = AuthService(client, FlruBrowser(settings))
proposal_service = ProposalService(settings, client, project_service, repo)
message_service = MessageService()
customer_service = CustomerService(client)
avito_service = AvitoAdService(settings, AvitoApiClient(settings), AvitoBrowser(settings), repo)
freelancer_client = FreelancerClient(settings)
freelancer_projects = FreelancerProjectService(freelancer_client)
freelancer_browser = FreelancerBrowser(settings)
freelancer_matcher = FreelancerMatcher(load_expertise_profile(settings.expertise_profile))
freelancer_bids = FreelancerBidService(settings, freelancer_browser, freelancer_projects, repo)

mcp = FastMCP("marketplace-mcp")


def dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, list):
        return [dump(item) for item in value]
    return value


@mcp.tool()
async def flru_auth_status() -> dict:
    """Checks whether the current FL.ru session is authenticated."""
    return await auth_service.status()


@mcp.tool()
async def flru_login(headless: bool = False) -> dict:
    """Starts a manual Playwright login session and persists browser storage state."""
    return await auth_service.login(headless=headless)


@mcp.tool()
async def flru_list_projects(
    page: int = 1,
    limit: int = 20,
    category: str | None = None,
    subcategory: str | None = None,
    query: str | None = None,
    budget_min: int | None = None,
    budget_max: int | None = None,
    only_new: bool = False,
) -> dict:
    projects = await project_service.list_projects(page, limit, category, subcategory, query, budget_min, budget_max, only_new)
    for project in projects:
        repo.upsert_project(project)
    return {"projects": dump(projects)}


@mcp.tool()
async def flru_search_projects(query: str, page: int = 1, limit: int = 50) -> dict:
    projects = await project_service.search_projects(query=query, page=page, limit=limit)
    for project in projects:
        repo.upsert_project(project)
    return {"projects": dump(projects)}


@mcp.tool()
async def flru_get_project(project_id: str | None = None, url: str | None = None) -> dict:
    project = await project_service.get_project(project_id=project_id, url=url)
    repo.upsert_project(project)
    repo.mark_seen(project.id)
    return dump(project)


@mcp.tool()
async def flru_find_relevant_projects(limit: int = 20, min_score: int = 60, max_pages: int = 5, only_unseen: bool = True) -> dict:
    results = []
    for page in range(1, max_pages + 1):
        projects = await project_service.list_projects(page=page, limit=50)
        for project in projects:
            if only_unseen and repo.is_inspected(project.id):
                continue
            result = matcher.score(project)
            repo.upsert_project(project, relevance_score=result.score)
            if result.score >= min_score:
                results.append(result)
    results.sort(key=lambda item: item.score, reverse=True)
    return {"projects": dump(results[:limit])}


@mcp.tool()
async def flru_mark_project_seen(project_id: str) -> dict:
    repo.mark_seen(project_id)
    return {"success": True, "project_id": project_id}


@mcp.tool()
async def flru_get_unseen_projects(limit: int = 50) -> dict:
    return {"projects": repo.unseen_projects(limit)}


@mcp.tool()
async def flru_get_project_history(project_id: str) -> dict:
    return repo.history(project_id)


@mcp.tool()
async def flru_get_proposal_context(project_id: str) -> dict:
    project = await project_service.get_project(project_id=project_id)
    repo.upsert_project(project)
    return proposal_context(project)


@mcp.tool()
async def flru_save_proposal_draft(project_id: str, text: str) -> dict:
    repo.save_draft(project_id, text)
    return {"success": True, "project_id": project_id}


@mcp.tool()
async def flru_get_proposal_draft(project_id: str) -> dict:
    return {"draft": repo.get_draft(project_id)}


@mcp.tool()
async def flru_submit_proposal(project_id: str, text: str, price: int | None = None, delivery_days: int | None = None) -> dict:
    return await proposal_service.submit(project_id, text, price, delivery_days)


@mcp.tool()
async def flru_list_conversations() -> dict:
    return await message_service.list_conversations()


@mcp.tool()
async def flru_get_conversation(conversation_id: str) -> dict:
    return await message_service.get_conversation(conversation_id)


@mcp.tool()
async def flru_send_message(conversation_id: str, text: str) -> dict:
    return await message_service.send_message(conversation_id, text)


@mcp.tool()
async def flru_get_customer(profile_url: str) -> dict:
    return await customer_service.get_customer(profile_url)


@mcp.tool()
async def avito_auth_status() -> dict:
    """Checks Avito API credentials and local browser-session state."""
    return await avito_service.auth_status()


@mcp.tool()
async def avito_login(headless: bool = False) -> dict:
    """Starts a manual Avito browser login session. CAPTCHA or IP checks must be completed by the user."""
    return await avito_service.login(headless=headless)


@mcp.tool()
async def avito_list_my_ads(limit: int = 50, offset: int = 0, status: str | None = None) -> dict:
    """Lists current account ads through the official Avito API when API credentials are configured."""
    return await avito_service.list_my_ads(limit=limit, offset=offset, status=status)


@mcp.tool()
async def avito_get_ad(item_id: str) -> dict:
    """Gets one Avito ad through the official Avito API."""
    return await avito_service.get_ad(item_id=item_id)


@mcp.tool()
async def avito_create_ad_draft(
    title: str,
    description: str,
    category: str | None = None,
    price: int | None = None,
    location: str | None = None,
    contact_name: str | None = None,
    images: list[str] | None = None,
    params: dict | None = None,
) -> dict:
    """Stores an Avito ad draft locally. This does not publish anything."""
    return avito_service.create_draft(
        {
            "title": title,
            "description": description,
            "category": category,
            "price": price,
            "location": location,
            "contact_name": contact_name,
            "images": images or [],
            "params": params or {},
        }
    )


@mcp.tool()
async def avito_get_ad_draft(draft_id: str) -> dict:
    """Gets a locally stored Avito ad draft."""
    return avito_service.get_draft(draft_id)


@mcp.tool()
async def avito_list_ad_drafts(limit: int = 50) -> dict:
    """Lists locally stored Avito ad drafts."""
    return avito_service.list_drafts(limit=limit)


@mcp.tool()
async def avito_open_create_ad_page(headless: bool = False) -> dict:
    """Opens Avito's add-item page in a manual browser session for inspection or manual completion."""
    return await avito_service.open_create_ad_page(headless=headless)


@mcp.tool()
async def avito_publish_ad(draft_id: str, confirm: bool = False) -> dict:
    """Explicit high-impact action for publishing an Avito draft. Defaults to dry-run and never bypasses Avito checks."""
    return await avito_service.publish_ad(draft_id=draft_id, confirm=confirm)


@mcp.tool()
async def freelancer_auth_status() -> dict:
    """Checks whether the current Freelancer.com browser session is authenticated."""
    return await freelancer_browser.auth_status()


@mcp.tool()
async def freelancer_login(headless: bool = False) -> dict:
    """Opens Freelancer.com login in Playwright. CAPTCHA/2FA/email checks must be completed manually."""
    return await freelancer_browser.login(headless=headless)


@mcp.tool()
async def freelancer_list_projects(page: int = 1, limit: int = 20, query: str | None = None, skill: str | None = None) -> dict:
    """Lists Freelancer.com projects from public job pages."""
    projects = await freelancer_projects.list_projects(page=page, limit=limit, query=query, skill=skill)
    for project in projects:
        repo.upsert_freelancer_project(project)
    return {"projects": dump(projects)}


@mcp.tool()
async def freelancer_search_projects(query: str, page: int = 1, limit: int = 50) -> dict:
    """Searches Freelancer.com projects by free text."""
    return await freelancer_list_projects(page=page, limit=limit, query=query)


@mcp.tool()
async def freelancer_get_project(project_id: str | None = None, url: str | None = None) -> dict:
    """Gets one Freelancer.com project detail page."""
    project = await freelancer_projects.get_project(project_id=project_id, url=url)
    repo.upsert_freelancer_project(project)
    return dump(project)


@mcp.tool()
async def freelancer_find_relevant_projects(limit: int = 20, min_score: int = 60, max_pages: int = 2) -> dict:
    """Finds relevant Freelancer.com projects using deterministic stack matching."""
    results = []
    skills = [None, "php", "python", "laravel", "api", "crm", "ai", "golang"]
    for skill in skills:
        for page in range(1, max_pages + 1):
            projects = await freelancer_projects.list_projects(page=page, limit=50, skill=skill)
            for project in projects:
                if repo.has_submitted_freelancer_bid(project.id):
                    continue
                match = freelancer_matcher.score(project)
                repo.upsert_freelancer_project(project, relevance_score=match.score)
                if match.score >= min_score:
                    results.append(match)
    results.sort(key=lambda item: item.score, reverse=True)
    return {"projects": dump(results[:limit])}


@mcp.tool()
async def freelancer_get_bid_context(project_id: str | None = None, url: str | None = None) -> dict:
    """Returns project details and known bid constraints for drafting a Freelancer.com bid."""
    return await freelancer_bids.context(project_id=project_id, url=url)


@mcp.tool()
async def freelancer_save_bid_draft(project_id: str, text: str, bid_amount: float | None = None, delivery_days: int | None = None) -> dict:
    """Stores a local Freelancer.com bid draft without submitting it."""
    repo.save_freelancer_bid_draft(project_id, text, bid_amount, delivery_days)
    return {"success": True, "project_id": project_id}


@mcp.tool()
async def freelancer_get_bid_draft(project_id: str) -> dict:
    """Gets a local Freelancer.com bid draft."""
    return {"draft": repo.get_freelancer_bid_draft(project_id)}


@mcp.tool()
async def freelancer_submit_bid(
    project_id: str,
    text: str,
    bid_amount: float | None = None,
    delivery_days: int | None = None,
    confirm: bool = False,
) -> dict:
    """Explicit high-impact action for Freelancer.com bidding. Defaults to dry-run until the live form is verified."""
    return await freelancer_bids.submit(project_id=project_id, text=text, bid_amount=bid_amount, delivery_days=delivery_days, confirm=confirm)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
