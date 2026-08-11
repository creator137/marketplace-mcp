from pathlib import Path

import pytest

from flru_mcp.avito.ads import AvitoAdService
from flru_mcp.avito.parsers import extract_items_from_api_payload, parse_browser_auth_status
from flru_mcp.config import Settings
from flru_mcp.storage.database import connect
from flru_mcp.storage.repositories import HistoryRepository


class FakeApi:
    async def auth_status(self):
        return {"authenticated": False, "session_valid": False, "source": "api", "status": "credentials_required"}

    async def list_items(self, limit=50, offset=0, status=None):
        return {"items": []}


class FakeBrowser:
    async def interactive_login(self, headless=False):
        return {"authenticated": False, "status": "manual_verification_required"}

    async def open_create_ad(self, headless=False):
        return {"opened": True, "url": "https://www.avito.ru/additem"}


def test_avito_ip_restriction_detected() -> None:
    status = parse_browser_auth_status("<html><title>Доступ ограничен: проблема с IP</title><body>Продолжить</body></html>", "https://www.avito.ru/")
    assert status["status"] == "manual_verification_required"
    assert status["reason"] == "ip_captcha"


def test_avito_items_payload_normalization() -> None:
    items = extract_items_from_api_payload({"items": [{"id": 42, "title": "Test", "price": {"value": 1000}}]})
    assert items[0]["id"] == "42"
    assert items[0]["price"] == 1000


@pytest.mark.asyncio
async def test_avito_draft_and_dry_run_publish(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "db.sqlite3", avito_dry_run=True)
    repo = HistoryRepository(connect(settings.database_path))
    service = AvitoAdService(settings, FakeApi(), FakeBrowser(), repo)
    created = service.create_draft({"title": "Продам ноутбук", "description": "Описание", "price": 10000})
    assert created["success"] is True
    draft_id = created["draft"]["draft_id"]
    result = await service.publish_ad(draft_id)
    assert result["dry_run"] is True
    assert result["would_publish"]["draft_id"] == draft_id


def test_avito_draft_validation(tmp_path: Path) -> None:
    settings = Settings(database_path=tmp_path / "db.sqlite3")
    repo = HistoryRepository(connect(settings.database_path))
    service = AvitoAdService(settings, FakeApi(), FakeBrowser(), repo)
    result = service.create_draft({"title": "", "description": ""})
    assert result["error"] == "VALIDATION_ERROR"
