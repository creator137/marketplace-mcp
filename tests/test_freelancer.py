from pathlib import Path

from flru_mcp.freelancer.parsers import parse_project_list, parse_project_page
from flru_mcp.freelancer.matcher import FreelancerMatcher
from flru_mcp.config import ExpertiseProfile
from flru_mcp.storage.database import connect
from flru_mcp.storage.repositories import HistoryRepository


FIXTURES = Path(__file__).parent / "fixtures"


def test_freelancer_project_list_parser():
    projects = parse_project_list((FIXTURES / "freelancer_project_list.html").read_text(encoding="utf-8"))
    assert len(projects) == 1
    project = projects[0]
    assert project.id == "api-integration--react-laravel-feature-enhancements"
    assert project.title == "React & Laravel Feature Enhancements"
    assert project.budget.amount_min == 250
    assert project.budget.amount_max == 750
    assert "Laravel" in project.skills


def test_freelancer_project_page_parser():
    project = parse_project_page(
        (FIXTURES / "freelancer_project_page.html").read_text(encoding="utf-8"),
        "https://www.freelancer.com/projects/api-integration/react-laravel-feature-enhancements",
    )
    assert project.bid_form_available is True
    assert "REST integration" in project.description
    assert project.budget.currency == "USD"


def test_freelancer_matcher_and_storage(tmp_path):
    project = parse_project_list((FIXTURES / "freelancer_project_list.html").read_text(encoding="utf-8"))[0]
    matcher = FreelancerMatcher(
        ExpertiseProfile(
            specializations=["PHP", "Laravel", "REST API"],
            preferred_projects=["API integration"],
            excluded_projects=["casino"],
        )
    )
    result = matcher.score(project)
    assert result.score > 20

    repo = HistoryRepository(connect(tmp_path / "db.sqlite3"))
    repo.upsert_freelancer_project(project, result.score)
    repo.save_freelancer_bid_draft(project.id, "Hello", 500, 7)
    assert repo.get_freelancer_bid_draft(project.id)["bid_amount"] == 500
    repo.record_freelancer_bid(project.id, "Hello", 500, 7)
    assert repo.has_submitted_freelancer_bid(project.id) is True
