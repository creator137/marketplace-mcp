from __future__ import annotations

import json
import re
from html import unescape
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Comment, Tag

from flru_mcp.flru.models import Budget, Customer, ProjectDetail, ProjectSummary, ProposalForm


PROJECT_ID_RE = re.compile(r"/projects/(\d+)/")


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = unescape(" ".join(value.replace("\xa0", " ").split()))
    return text or None


def html_to_text(node: Tag | None) -> str | None:
    if node is None:
        return None
    for br in node.find_all("br"):
        br.replace_with("\n")
    text = unescape(node.get_text("\n", strip=True).replace("\xa0", " "))
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def parse_project_id(url: str) -> str | None:
    match = PROJECT_ID_RE.search(url)
    return match.group(1) if match else None


def parse_budget(raw: str | None) -> Budget:
    text = clean_text(raw)
    if not text:
        return Budget(type="unknown", raw=raw)
    lowered = text.lower()
    if "договор" in lowered:
        return Budget(type="negotiable", raw=text)
    number_match = re.search(r"(\d[\d\s]*\d|\d)", text)
    amount = int(number_match.group(1).replace(" ", "")) if number_match else None
    currency = "RUB" if re.search(r"₽|руб", lowered) else None
    return Budget(amount=amount, currency=currency, type="fixed" if amount else "unknown", raw=text)


def parse_proposal_count(text: str | None) -> int | None:
    if not text:
        return None
    lowered = text.lower()
    if "нет ответ" in lowered:
        return 0
    match = re.search(r"(\d+)", lowered)
    return int(match.group(1)) if match else None


def parse_project_list(html: str, base_url: str = "https://www.fl.ru") -> list[ProjectSummary]:
    soup = BeautifulSoup(html, "lxml")
    projects: list[ProjectSummary] = []
    for card in soup.select("#projects-list div[id^='project-item']"):
        link = card.select_one("a[id^='prj_name_'][href*='/projects/']")
        if not link:
            continue
        href = link.get("href") or ""
        project_id = (link.get("data-disposable-project-id") or parse_project_id(href) or "").strip()
        if not project_id:
            continue
        budget_node = card.select_one(".b-post__price")
        desc_node = card.select_one(".b-post__body .b-post__txt")
        footer_text = clean_text(card.select_one(".b-post__foot").get_text(" ", strip=True) if card.select_one(".b-post__foot") else "")
        published_at = None
        pub_match = re.search(r"(?:Заказ|Вакансия)\s+([^Ё]+?назад|\d{2}\.\d{2}\.\d{4}[^ ]*)", footer_text or "", re.IGNORECASE)
        if pub_match:
            published_at = clean_text(pub_match.group(1))
        proposal_node = card.select_one("[data-id='fl-view-count-href']")
        projects.append(
            ProjectSummary(
                id=project_id,
                title=clean_text(link.get_text(" ", strip=True)) or "",
                url=urljoin(base_url, href),
                description_preview=clean_text(desc_node.get_text(" ", strip=True) if desc_node else None),
                budget=parse_budget(budget_node.get_text(" ", strip=True) if budget_node else None),
                published_at=published_at,
                proposal_count=parse_proposal_count(proposal_node.get_text(" ", strip=True) if proposal_node else None),
            )
        )
    return projects


def _json_ld(soup: BeautifulSoup) -> list[dict]:
    entries: list[dict] = []
    for script in soup.select("script[type='application/ld+json']"):
        try:
            data = json.loads(script.string or "{}")
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and isinstance(data.get("@graph"), list):
            entries.extend(item for item in data["@graph"] if isinstance(item, dict))
        elif isinstance(data, dict):
            entries.append(data)
    return entries


def parse_auth_status(html: str, base_url: str = "https://www.fl.ru") -> dict:
    soup = BeautifulSoup(html, "lxml")
    page_text = soup.get_text(" ", strip=True)
    canonical = soup.select_one("link[rel='canonical'], meta[property='og:url']")
    canonical_url = canonical.get("href") or canonical.get("content") if canonical else ""
    if "confirmation-email" in canonical_url or "Введите код из письма" in page_text:
        return {
            "authenticated": False,
            "username": None,
            "profile_url": None,
            "session_valid": False,
            "status": "manual_verification_required",
            "reason": "email_code",
        }
    uid = soup.select_one("meta[name='current-uid']")
    user_meta = soup.select_one("meta[name='user']")
    current_uid = uid.get("content") if uid else "0"
    authenticated = bool(current_uid and current_uid != "0")
    username = None
    profile_url = None
    if user_meta and user_meta.get("content") not in {None, "", "[]"}:
        try:
            user_data = json.loads(user_meta["content"])
            if isinstance(user_data, dict):
                username = user_data.get("login") or user_data.get("name") or user_data.get("username")
                profile_url = user_data.get("url") or user_data.get("profile_url")
        except json.JSONDecodeError:
            pass
    profile_link = soup.select_one("a[href^='/users/'], a[href*='/users/']")
    if not profile_url and profile_link:
        profile_url = urljoin(base_url, profile_link.get("href") or "")
        username = username or clean_text(profile_link.get_text(" ", strip=True))
    return {"authenticated": authenticated, "username": username, "profile_url": profile_url, "session_valid": authenticated}


def parse_project_page(html: str, url: str, base_url: str = "https://www.fl.ru") -> ProjectDetail:
    soup = BeautifulSoup(html, "lxml")
    project_id = parse_project_id(url) or ""
    title_node = soup.select_one(f"#prj_name_{project_id}") or soup.select_one("h1[id^='prj_name_']") or soup.select_one("h1")
    description_node = soup.select_one(f"#projectp{project_id}") or soup.select_one("[id^='projectp']")
    budget_text = None
    for node in soup.find_all(string=re.compile("Бюджет", re.IGNORECASE)):
        if isinstance(node, Comment):
            continue
        parent = node.find_parent()
        while parent:
            text = clean_text(parent.get_text(" ", strip=True))
            if text and "Бюджет" in text and len(text) <= 120:
                budget_text = re.sub(r"^\s*Бюджет:\s*", "", text, flags=re.IGNORECASE).strip()
                break
            parent = parent.find_parent()
        if budget_text:
            break
    breadcrumbs = [clean_text(a.get_text(" ", strip=True)) for a in soup.select("[itemtype='https://schema.org/BreadcrumbList'] a span[itemprop='name']")]
    breadcrumbs = [item for item in breadcrumbs if item and item.lower() not in {"все проекты"}]
    category = breadcrumbs[0] if breadcrumbs else None
    subcategory = breadcrumbs[-1] if len(breadcrumbs) > 1 else None
    published_at = None
    published_node = soup.find(string=re.compile("Опубликован", re.IGNORECASE))
    if published_node and published_node.parent:
        published_at = clean_text(published_node.parent.get_text(" ", strip=True).replace("Опубликован", ""))
    customer = Customer()
    customer_section = soup.select_one(".fl-project-sidebar")
    if customer_section:
        text = customer_section.get_text(" ", strip=True)
        reg_match = re.search(r"Зарегистрирован:\s*([^О]+?)(?:\s{2,}|$)", text)
        customer.registration_date = clean_text(reg_match.group(1)) if reg_match else None
        user_link = customer_section.select_one("a[href^='/users/'], a[href*='/users/']")
        if user_link:
            customer.profile_url = urljoin(base_url, user_link.get("href") or "")
            customer.name = clean_text(user_link.get_text(" ", strip=True))
    attachments = []
    for link in soup.select("a[href*='/download/'], a[href*='/upload/'], a[href*='attachedfiles']"):
        href = link.get("href")
        if href:
            attachments.append({"name": clean_text(link.get_text(" ", strip=True)) or href.rsplit("/", 1)[-1], "url": urljoin(base_url, href)})
    reply = soup.select_one("#reply_offer")
    accepts = bool(reply and "Откликнуться" in reply.get_text(" ", strip=True))
    return ProjectDetail(
        id=project_id,
        title=clean_text(title_node.get_text(" ", strip=True) if title_node else None) or "",
        url=url,
        description_preview=clean_text(description_node.get_text(" ", strip=True)[:300] if description_node else None),
        description=html_to_text(description_node),
        budget=parse_budget(budget_text),
        category=category,
        subcategory=subcategory,
        published_at=published_at,
        customer=customer,
        proposal_count=parse_proposal_count(soup.get_text(" ", strip=True)),
        attachments=attachments,
        proposal_form=parse_proposal_form(html),
        accepts_proposals=accepts,
    )


def parse_proposal_form(html: str, base_url: str = "https://www.fl.ru") -> ProposalForm:
    soup = BeautifulSoup(html, "lxml")
    csrf = soup.select_one("meta[name='csrf-token']")
    form = soup.select_one("form[action*='offer'], form[action*='proposal'], form:has(textarea)")
    if not form:
        return ProposalForm(available=False, csrf_token=csrf.get("content") if csrf else None)
    textarea = form.select_one("textarea")
    fields = {tag.get("name"): tag.get("value") for tag in form.select("input[name]") if tag.get("name")}
    max_length = int(textarea.get("maxlength")) if textarea and textarea.get("maxlength", "").isdigit() else None
    text = form.get_text(" ", strip=True).lower()
    return ProposalForm(
        available=True,
        action_url=urljoin(base_url, form.get("action") or ""),
        method=(form.get("method") or "POST").upper(),
        csrf_token=csrf.get("content") if csrf else fields.get("_token"),
        max_length=max_length,
        requires_price="цена" in text or "стоимость" in text,
        requires_delivery_days="срок" in text,
        raw_fields=fields,
    )
