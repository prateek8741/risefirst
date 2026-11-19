import json
from pathlib import Path

import pytest

from risefirst.infrastructure.connectors.ats import parse_ashby, parse_greenhouse, parse_lever
from risefirst.infrastructure.connectors.registry import load_sources
from risefirst.infrastructure.connectors.text import html_to_text
from risefirst.infrastructure.http import HostNotAllowedError, PoliteHttpClient

FIXTURES = Path(__file__).parents[1] / "fixtures"


def _load(name: str):
    return json.loads((FIXTURES / name).read_text())


def test_greenhouse_parsing() -> None:
    [job] = parse_greenhouse("acme", "Acme", _load("greenhouse.json"))
    assert job.source_key == "greenhouse:acme:101"
    assert job.title == "Software Engineering Intern"
    assert "Bengaluru" in job.location_text
    assert "• Python" in job.description and "<" not in job.description
    assert job.posted_at is not None


def test_lever_parsing() -> None:
    [job] = parse_lever("acme", "Acme", _load("lever.json"))
    assert job.external_id == "abc-123"
    assert job.employment_type_hint == "Intern"
    assert job.work_mode_hint == "hybrid"
    assert "0-1 years" in job.description
    assert job.location_text == "Mumbai | Pune"


def test_ashby_skips_unlisted() -> None:
    jobs = parse_ashby("acme", "Acme", _load("ashby.json"))
    assert [j.title for j in jobs] == ["Associate Analyst"]
    assert jobs[0].work_mode_hint == "Remote"


def test_html_to_text_keeps_structure() -> None:
    text = html_to_text("&lt;p&gt;Hello&lt;/p&gt;&lt;ul&gt;&lt;li&gt;A&lt;/li&gt;&lt;li&gt;B &amp; C&lt;/li&gt;&lt;/ul&gt;")
    assert text == "Hello\n\n• A\n• B & C"


def test_http_client_refuses_unknown_hosts() -> None:
    with pytest.raises(HostNotAllowedError):
        PoliteHttpClient().get_json("https://example.com/jobs")


def test_sources_file_is_valid() -> None:
    sources = load_sources(Path(__file__).parents[3] / "config" / "sources.yaml")
    assert len(sources) >= 70
    assert len({(s.ats, s.board) for s in sources}) == len(sources)


def test_sources_reject_bad_slug(tmp_path: Path) -> None:
    bad = tmp_path / "sources.yaml"
    bad.write_text("boards:\n  - {ats: lever, board: '../evil', company: X}\n")
    with pytest.raises(ValueError):
        load_sources(bad)
