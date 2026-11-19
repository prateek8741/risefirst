"""Sourcing spike, phase 1: discover which candidate slugs have public ATS boards.

Throwaway measurement code (stdlib only). It is NOT the production connector
layer; it exists to answer "how many fresher jobs in India can we reach from
compliant public ATS APIs?" before we build anything.

Compliance (checked 2026-11-17):
  boards-api.greenhouse.io  robots: only /embed/ disallowed
  api.lever.co              robots: Allow /, Crawl-delay 1  -> 1 req/s here
  api.ashbyhq.com           no robots.txt; documented public posting API
  apply.workable.com        robots: Disallow nothing; search=yes, ai-input=yes, ai-train=no
  <slug>.recruitee.com      robots: only /v/ disallowed

Usage: python3 -I probe.py <raw_output_dir>
"""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from candidates import ALL_CANDIDATES  # noqa: E402

USER_AGENT = "RiseFirst-sourcing-probe/0.1 (job discovery research; polite, low-rate)"
TIMEOUT_SECONDS = 20

# ATS -> (url template, minimum seconds between requests to that ATS)
ATS_ENDPOINTS: dict[str, tuple[str, float]] = {
    "greenhouse": ("https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", 0.25),
    "lever": ("https://api.lever.co/v0/postings/{slug}?mode=json", 1.0),
    "ashby": ("https://api.ashbyhq.com/posting-api/job-board/{slug}", 0.25),
    "workable": ("https://apply.workable.com/api/v1/widget/accounts/{slug}?details=true", 0.5),
    "recruitee": ("https://{slug}.recruitee.com/api/offers/", 0.25),
}
GREENHOUSE_CONTENT_URL = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"


def fetch_json(url: str) -> tuple[int, object | None]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ConnectionError) as error:
        print(f"  network/parse error {url}: {type(error).__name__}", file=sys.stderr)
        return 0, None


def count_jobs(ats: str, payload: object) -> int:
    if ats == "lever":
        return len(payload) if isinstance(payload, list) else 0
    if not isinstance(payload, dict):
        return 0
    key = {"greenhouse": "jobs", "ashby": "jobs", "workable": "jobs", "recruitee": "offers"}[ats]
    jobs = payload.get(key)
    return len(jobs) if isinstance(jobs, list) else 0


def probe_ats(ats: str, slugs: list[str], raw_dir: Path, results: dict, lock: threading.Lock) -> None:
    url_template, min_interval = ATS_ENDPOINTS[ats]
    for slug in slugs:
        started = time.monotonic()
        status, payload = fetch_json(url_template.format(slug=slug))
        job_count = count_jobs(ats, payload) if payload is not None else 0
        if job_count:
            (raw_dir / ats).mkdir(parents=True, exist_ok=True)
            (raw_dir / ats / f"{slug}.json").write_text(json.dumps(payload))
        with lock:
            results.setdefault(ats, {})[slug] = {"status": status, "jobs": job_count}
        elapsed = time.monotonic() - started
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
    print(f"{ats}: done, {sum(1 for r in results[ats].values() if r['jobs'])} boards with jobs", flush=True)


def fetch_greenhouse_content(raw_dir: Path) -> None:
    """Greenhouse list omits descriptions; refetch with content only for boards that have jobs."""
    for path in sorted((raw_dir / "greenhouse").glob("*.json")):
        status, payload = fetch_json(GREENHOUSE_CONTENT_URL.format(slug=path.stem))
        if status == 200 and payload is not None:
            path.write_text(json.dumps(payload))
        time.sleep(0.25)


def main() -> None:
    raw_dir = Path(sys.argv[1])
    raw_dir.mkdir(parents=True, exist_ok=True)
    results: dict = {}
    lock = threading.Lock()
    print(f"probing {len(ALL_CANDIDATES)} slugs x {len(ATS_ENDPOINTS)} ATSs", flush=True)
    with ThreadPoolExecutor(max_workers=len(ATS_ENDPOINTS)) as pool:
        for ats in ATS_ENDPOINTS:
            pool.submit(probe_ats, ats, ALL_CANDIDATES, raw_dir, results, lock)
    fetch_greenhouse_content(raw_dir)
    (raw_dir / "discovery.json").write_text(json.dumps(results, indent=1))
    print("discovery complete", flush=True)


if __name__ == "__main__":
    main()
