from risefirst.application.ingest import IngestJobs
from risefirst.domain.enums import ClassifiedBy, Eligibility, JobStatus
from tests.fakes import NOW, FakeConnector, FakeEnricher, InMemoryRepository, posting


def run(connectors, repo, enricher=None, budget=100):
    return IngestJobs(connectors, repo, enricher, ai_call_budget=budget, clock=lambda: NOW).run()


def test_keeps_only_india_and_classifies() -> None:
    repo = InMemoryRepository()
    report = run([FakeConnector([
        posting("1", "Software Engineering Intern", "Bengaluru"),
        posting("2", "Senior Engineer", "Pune"),
        posting("3", "Software Engineering Intern", "London"),
    ])], repo)
    assert report.fetched == 3 and report.india == 2
    assert report.eligible == 1 and report.rejected == 1
    assert len(repo.runs) == 1


def test_failing_source_does_not_stop_others() -> None:
    repo = InMemoryRepository()
    report = run([
        FakeConnector([], name="lever:broken", error=RuntimeError("HTTP 500")),
        FakeConnector([posting("1")]),
    ], repo)
    assert "lever:broken" in report.sources_failed
    assert report.sources_ok == ["greenhouse:acme"]
    assert len(repo.jobs) == 1


def test_job_closes_after_two_missed_runs() -> None:
    repo = InMemoryRepository()
    run([FakeConnector([posting("1"), posting("2", "Data Intern")])], repo)
    run([FakeConnector([posting("1")])], repo)
    assert repo.jobs["greenhouse:acme:2"].status is JobStatus.ACTIVE  # one miss: kept
    report = run([FakeConnector([posting("1")])], repo)
    assert report.closed == 1
    assert repo.jobs["greenhouse:acme:2"].status is JobStatus.CLOSED


def test_failed_fetch_never_closes_jobs() -> None:
    repo = InMemoryRepository()
    run([FakeConnector([posting("1")])], repo)
    for _ in range(3):
        run([FakeConnector([], error=TimeoutError("timeout"))], repo)
    assert repo.jobs["greenhouse:acme:1"].status is JobStatus.ACTIVE


def test_reappearing_job_reopens_and_keeps_first_seen() -> None:
    repo = InMemoryRepository()
    run([FakeConnector([posting("1")])], repo)
    first_seen = repo.jobs["greenhouse:acme:1"].first_seen_at
    run([FakeConnector([])], repo)
    run([FakeConnector([])], repo)
    run([FakeConnector([posting("1")])], repo)
    job = repo.jobs["greenhouse:acme:1"]
    assert job.status is JobStatus.ACTIVE and job.first_seen_at == first_seen


def test_ai_only_for_non_rejected_and_cached_when_unchanged() -> None:
    repo, enricher = InMemoryRepository(), FakeEnricher()
    postings = [posting("1", "Analyst", description="Join our team."), posting("2", "Senior Analyst")]
    report = run([FakeConnector(postings)], repo, enricher)
    assert enricher.calls == ["greenhouse:acme:1"]  # the senior role never reached the AI
    job = repo.jobs["greenhouse:acme:1"]
    assert job.eligibility is Eligibility.ELIGIBLE and job.classified_by is ClassifiedBy.AI
    assert job.skills == ["Python", "SQL"]

    report = run([FakeConnector(postings)], repo, enricher)
    assert report.ai_calls == 0 and report.ai_cache_hits == 1
    assert repo.jobs["greenhouse:acme:1"].eligibility is Eligibility.ELIGIBLE


def test_ai_budget_is_respected() -> None:
    repo, enricher = InMemoryRepository(), FakeEnricher()
    run([FakeConnector([posting(str(i), "Analyst") for i in range(5)])], repo, enricher, budget=2)
    assert len(enricher.calls) == 2


def test_cross_board_duplicates_collapse() -> None:
    repo = InMemoryRepository()
    run([
        FakeConnector([posting("1", "Data Intern", board="acme")], name="greenhouse:acme"),
        FakeConnector([posting("9", "Data Intern", board="acme-india")], name="greenhouse:acme-india"),
    ], repo)
    assert len(repo.visible()) == 1


def test_ai_unavailable_stops_calls_but_run_completes() -> None:
    from risefirst.application.ports import EnricherUnavailable

    class QuotaEnricher(FakeEnricher):
        def enrich(self, p):
            if len(self.calls) >= 1:
                self.calls.append(p.source_key)
                raise EnricherUnavailable("daily quota used up")
            return super().enrich(p)  # records the call itself

    repo, enricher = InMemoryRepository(), QuotaEnricher()
    report = IngestJobs([FakeConnector([posting(str(i), "Analyst") for i in range(6)])], repo, enricher,
                        ai_concurrency=1, clock=lambda: NOW).run()
    assert len(enricher.calls) == 2
    assert report.ai_calls == 2 and report.ai_skipped == 4
    assert len(repo.jobs) == 6  # every job still saved, on rules alone
