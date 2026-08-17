from __future__ import annotations

import hashlib
import re
from html import unescape
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from flru_mcp.freelancer.models import FreelancerBudget, FreelancerProject, FreelancerProjectDetail


PROJECT_ID_RE = re.compile(r"/projects/([^/?#]+(?:/[^/?#]+)?)")


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    text = re.sub(r"\s+", " ", unescape(value)).strip()
    return text or None


def _text(node: Tag | None) -> str | None:
    return clean_text(node.get_text(" ", strip=True) if node else None)


def project_id_from_url(url: str) -> str:
    match = PROJECT_ID_RE.search(url)
    if match:
        parts = [re.sub(r"[^a-zA-Z0-9_-]+", "-", part).strip("-") for part in match.group(1).split("/")]
        parts = [part for part in parts if part]
        if parts:
            return "--".join(parts)
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def parse_budget(text: str | None) -> FreelancerBudget:
    raw = clean_text(text)
    if not raw:
        return FreelancerBudget()
    nums = [float(n.replace(",", "")) for n in re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?", raw)]
    currency = None
    if "$" in raw or "USD" in raw.upper():
        currency = "USD"
    elif "€" in raw or "EUR" in raw.upper():
        currency = "EUR"
    elif "₹" in raw or "INR" in raw.upper():
        currency = "INR"
    kind = "hourly" if "/hr" in raw.lower() or "hour" in raw.lower() else "fixed"
    return FreelancerBudget(raw=raw, amount_min=nums[0] if nums else None, amount_max=nums[-1] if len(nums) > 1 else None, currency=currency, type=kind)


def _extract_skills(card: Tag) -> list[str]:
    skills: list[str] = []
    for node in card.select(".JobSearchCard-primary-tagsLink, a[href*='/jobs/'], .ProjectViewSkills-tag"):
        text = _text(node)
        if text and len(text) < 50 and text not in skills:
            skills.append(text)
    return skills[:20]


def parse_project_list(html: str, base_url: str = "https://www.freelancer.com") -> list[FreelancerProject]:
    soup = BeautifulSoup(html, "lxml")
    cards = soup.select("[data-project-card='true'], .JobSearchCard-item")
    projects: list[FreelancerProject] = []
    seen: set[str] = set()
    for card in cards:
        link = card.select_one("a.JobSearchCard-primary-heading-link[href*='/projects/'], a[href*='/projects/']")
        if not link:
            continue
        href = link.get("href") or ""
        url = urljoin(base_url, href)
        project_id = project_id_from_url(url)
        if project_id in seen:
            continue
        seen.add(project_id)
        title = _text(link)
        if not title:
            continue
        desc = _text(card.select_one(".JobSearchCard-primary-description, .JobSearchCard-primary-description-Paragraph"))
        budget_text = _text(card.select_one(".JobSearchCard-secondary-price, .JobSearchCard-secondary-entry"))
        bid_text = _text(card.select_one(".JobSearchCard-secondary-entry, .JobSearchCard-secondary-avgBid"))
        bid_count = None
        if bid_text:
            match = re.search(r"(\d+)\s+bid", bid_text, re.I)
            if match:
                bid_count = int(match.group(1))
        projects.append(
            FreelancerProject(
                id=project_id,
                title=title,
                url=url,
                description_preview=desc,
                budget=parse_budget(budget_text),
                skills=_extract_skills(card),
                bid_count=bid_count,
                published_at=_text(card.select_one(".JobSearchCard-primary-heading-days")),
            )
        )
    return projects


def parse_project_page(html: str, url: str, base_url: str = "https://www.freelancer.com") -> FreelancerProjectDetail:
    soup = BeautifulSoup(html, "lxml")
    title = _text(soup.select_one("h1")) or _text(soup.select_one("[data-testid='project-title']")) or "Untitled project"
    project_id = project_id_from_url(url)
    main = soup.select_one("main") or soup
    description = _text(
        soup.select_one("[data-testid='project-description'], .ProjectDescription, .NativeElement, .project-description")
        or main
    )
    budget = parse_budget(_text(soup.select_one("[data-testid='budget'], .ProjectViewDetails-budget, .Budget, .ProjectViewDetails-budgetText")))
    skills = _extract_skills(soup)
    page_text = soup.get_text(" ", strip=True).lower()
    bid_form_available = any(token in page_text for token in ["place bid", "bid on this project", "submit proposal"])
    existing_user_bid = "you have bid" if any(token in page_text for token in ["you have bid", "your bid", "edit bid"]) else None
    return FreelancerProjectDetail(
        id=project_id,
        title=title,
        url=urljoin(base_url, url),
        description_preview=description[:300] if description else None,
        description=description,
        budget=budget,
        skills=skills,
        bid_form_available=bid_form_available,
        existing_user_bid=existing_user_bid,
        raw={"title": title},
    )
