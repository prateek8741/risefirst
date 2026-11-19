"""Polite HTTP client: host allowlist, per-host rate limit, timeouts and retries with backoff."""

from __future__ import annotations

import threading
import time
from typing import Any
from urllib.parse import urlparse

import httpx

USER_AGENT = "RiseFirstBot/0.1 (fresher job discovery; low-rate; honours robots.txt)"

# Only these hosts may be fetched. Stops a bad config value from turning the
# ingester into a request proxy (SSRF), and documents exactly where data comes from.
ALLOWED_HOSTS: dict[str, float] = {
    # host: minimum seconds between requests (from each host's robots.txt / docs)
    "boards-api.greenhouse.io": 0.25,
    "api.lever.co": 1.0,  # robots.txt: Crawl-delay 1
    "api.ashbyhq.com": 0.25,
}

_RETRY_STATUS = {429, 500, 502, 503, 504}


class HostNotAllowedError(ValueError):
    pass


class PoliteHttpClient:
    def __init__(self, timeout_seconds: float = 20.0, max_retries: int = 3) -> None:
        self._client = httpx.Client(
            timeout=timeout_seconds, headers={"User-Agent": USER_AGENT}, follow_redirects=False
        )
        self._max_retries = max_retries
        self._last_request: dict[str, float] = {}
        self._locks = {host: threading.Lock() for host in ALLOWED_HOSTS}

    def get_json(self, url: str, params: dict[str, str] | None = None) -> Any:
        host = urlparse(url).hostname or ""
        if host not in ALLOWED_HOSTS or urlparse(url).scheme != "https":
            raise HostNotAllowedError(f"host not in allowlist: {host}")

        for attempt in range(self._max_retries + 1):
            self._wait_turn(host)
            try:
                response = self._client.get(url, params=params)
            except httpx.TransportError:
                if attempt == self._max_retries:
                    raise
                time.sleep(2**attempt)
                continue
            if response.status_code in _RETRY_STATUS and attempt < self._max_retries:
                retry_after = response.headers.get("Retry-After", "")
                time.sleep(float(retry_after) if retry_after.isdigit() else 2**attempt)
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError("unreachable")

    def _wait_turn(self, host: str) -> None:
        with self._locks[host]:
            wait = self._last_request.get(host, 0.0) + ALLOWED_HOSTS[host] - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_request[host] = time.monotonic()

    def close(self) -> None:
        self._client.close()
