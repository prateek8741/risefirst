from fastapi.testclient import TestClient

from risefirst.application.catalog import JobCatalog
from risefirst.application.ingest import IngestJobs
from risefirst.entrypoints.api.main import app, get_catalog
from tests.fakes import NOW, FakeConnector, InMemoryRepository, posting


def _client() -> TestClient:
    repo = InMemoryRepository()
    IngestJobs([FakeConnector([
        posting("1", "Software Engineering Intern"),
        posting("2", "Analyst", description="Experience not mentioned."),
        posting("3", "Senior Engineer"),
    ])], repo, clock=lambda: NOW).run()
    app.dependency_overrides[get_catalog] = lambda: JobCatalog(repo)
    return TestClient(app)


def test_lists_only_verified_fresher_jobs_by_default() -> None:
    body = _client().get("/api/jobs").json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Software Engineering Intern"
    assert body["items"][0]["verified_fresher"] is True


def test_include_review_adds_unverified() -> None:
    body = _client().get("/api/jobs", params={"include_review": True}).json()
    assert body["total"] == 2


def test_detail_hides_rejected_jobs() -> None:
    client = _client()
    assert client.get("/api/jobs/1").status_code == 200
    assert client.get("/api/jobs/3").status_code == 404
    assert client.get("/api/jobs/999").status_code == 404


def test_validates_filters() -> None:
    client = _client()
    assert client.get("/api/jobs", params={"category": "Astrology"}).status_code == 422
    assert client.get("/api/jobs", params={"page_size": 500}).status_code == 422


def test_ai_fields_and_filter() -> None:
    from risefirst.application.catalog import JobCatalog
    from tests.fakes import FakeEnricher

    repo = InMemoryRepository()
    IngestJobs([FakeConnector([
        posting("1", "Software Engineering Intern"),
        posting("2", "Analyst", description="Join us."),
    ])], repo, FakeEnricher(), clock=lambda: NOW).run()
    app.dependency_overrides[get_catalog] = lambda: JobCatalog(repo)
    client = TestClient(app)
    items = {j["title"]: j for j in client.get("/api/jobs").json()["items"]}
    assert items["Analyst"]["ai_assessed"] and items["Analyst"]["decided_by_ai"]
    assert items["Software Engineering Intern"]["ai_assessed"] and not items["Software Engineering Intern"]["decided_by_ai"]
    assert client.get("/api/stats").json()["ai_assessed_jobs"] == 2
    assert client.get("/api/jobs", params={"ai_assessed": True}).json()["total"] == 2


def test_ai_filter_includes_unclear_jobs_so_it_matches_the_count() -> None:
    from risefirst.application.catalog import JobCatalog
    from tests.fakes import FakeEnricher

    repo = InMemoryRepository()
    IngestJobs([FakeConnector([posting("1", "Software Engineering Intern"), posting("2", "Analyst")])],
               repo, FakeEnricher(fresher=True, confidence=0.5), clock=lambda: NOW).run()  # low confidence: stays unclear
    app.dependency_overrides[get_catalog] = lambda: JobCatalog(repo)
    client = TestClient(app)
    assert client.get("/api/stats").json()["ai_assessed_jobs"] == 2
    assert client.get("/api/jobs", params={"ai_assessed": True}).json()["total"] == 2


def test_symbol_font_bullets_are_displayed_as_bullets() -> None:
    from risefirst.entrypoints.api.schemas import display_text

    assert display_text(" Python\n SQL") == "• Python\n• SQL"
    assert display_text("Plain – text •") == "Plain – text •"
