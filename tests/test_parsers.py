from pathlib import Path

from flru_mcp.flru.parsers import parse_auth_status, parse_budget, parse_project_list, parse_project_page


FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_project_list() -> None:
    projects = parse_project_list((FIXTURES / "project_list.html").read_text(encoding="utf-8"))
    assert len(projects) == 2
    assert projects[0].id == "5517323"
    assert projects[0].budget.amount == 80000
    assert projects[0].proposal_count == 17


def test_parse_budget_negotiable() -> None:
    budget = parse_budget("по договоренности")
    assert budget.type == "negotiable"
    assert budget.amount is None


def test_parse_project_page() -> None:
    project = parse_project_page((FIXTURES / "project_page.html").read_text(encoding="utf-8"), "https://www.fl.ru/projects/5517323/site.html")
    assert project.id == "5517323"
    assert project.category == "Сайты"
    assert project.subcategory == "1С Битрикс"
    assert "будущий интернет-магазин" in project.description
    assert project.accepts_proposals is True


def test_confirmation_email_is_not_valid_auth() -> None:
    status = parse_auth_status((FIXTURES / "confirmation_email.html").read_text(encoding="utf-8"))
    assert status["authenticated"] is False
    assert status["status"] == "manual_verification_required"
    assert status["reason"] == "email_code"
