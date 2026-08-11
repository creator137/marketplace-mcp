from __future__ import annotations

import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup


def parse_browser_auth_status(html: str, url: str, base_url: str = "https://www.avito.ru") -> dict:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    lowered = text.lower()
    if "доступ ограничен" in lowered or "проблема с ip" in lowered:
        return {
            "authenticated": False,
            "session_valid": False,
            "source": "browser",
            "status": "manual_verification_required",
            "reason": "ip_captcha",
        }
    if "капч" in lowered or "captcha" in lowered:
        return {
            "authenticated": False,
            "session_valid": False,
            "source": "browser",
            "status": "manual_verification_required",
            "reason": "captcha",
        }
    profile_link = soup.select_one("a[href*='/profile'], a[href*='/user/']")
    login_markers = ("войти", "зарегистрироваться")
    authenticated = bool(profile_link or "/profile" in url) and not all(marker in lowered for marker in login_markers)
    name = None
    profile_url = None
    if profile_link:
        name = profile_link.get_text(" ", strip=True) or None
        profile_url = urljoin(base_url, profile_link.get("href") or "")
    return {
        "authenticated": authenticated,
        "session_valid": authenticated,
        "source": "browser",
        "name": name,
        "profile_url": profile_url,
        "status": "ok" if authenticated else "auth_required",
    }


def normalize_api_item(raw: dict) -> dict:
    item_id = raw.get("id") or raw.get("item_id") or raw.get("itemId") or raw.get("avito_id")
    price = raw.get("price")
    if isinstance(price, dict):
        price = price.get("value") or price.get("amount")
    return {
        "id": str(item_id) if item_id is not None else "",
        "title": raw.get("title") or raw.get("name"),
        "url": raw.get("url") or raw.get("uri"),
        "status": raw.get("status"),
        "price": price if isinstance(price, int) else None,
        "raw": raw,
    }


def extract_items_from_api_payload(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return [normalize_api_item(item) for item in payload if isinstance(item, dict)]
    for key in ("items", "result", "resources", "ads"):
        value = payload.get(key)
        if isinstance(value, list):
            return [normalize_api_item(item) for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = extract_items_from_api_payload(value)
            if nested:
                return nested
    return []


def human_error(payload: object) -> str | None:
    if isinstance(payload, dict):
        for key in ("message", "error", "errors"):
            value = payload.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, list) and value:
                return "; ".join(str(item) for item in value)
            if isinstance(value, dict):
                nested = human_error(value)
                if nested:
                    return nested
        return json.dumps(payload, ensure_ascii=False)[:500]
    if isinstance(payload, str):
        return re.sub(r"\s+", " ", payload).strip()[:500]
    return None
