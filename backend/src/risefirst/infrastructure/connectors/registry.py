"""Loads the reviewed source list (config/sources.yaml) into connectors."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from risefirst.infrastructure.connectors.ats import AtsBoardConnector
from risefirst.infrastructure.http import PoliteHttpClient

SUPPORTED_ATS = {"greenhouse", "lever", "ashby"}
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,80}$")


@dataclass(frozen=True)
class SourceConfig:
    ats: str
    board: str
    company: str
    enabled: bool = True


def load_sources(path: Path) -> list[SourceConfig]:
    data = yaml.safe_load(path.read_text()) or {}
    sources = []
    for entry in data.get("boards", []):
        source = SourceConfig(
            ats=str(entry["ats"]).lower(),
            board=str(entry["board"]).lower(),
            company=str(entry["company"]),
            enabled=bool(entry.get("enabled", True)),
        )
        if source.ats not in SUPPORTED_ATS:
            raise ValueError(f"{path}: unsupported ats '{source.ats}' for {source.board}")
        if not _SLUG.match(source.board):  # slugs are interpolated into URLs
            raise ValueError(f"{path}: invalid board slug '{source.board}'")
        sources.append(source)
    return sources


def build_connectors(
    sources: list[SourceConfig], http: PoliteHttpClient, only: str | None = None
) -> list[AtsBoardConnector]:
    return [
        AtsBoardConnector(s.ats, s.board, s.company, http)
        for s in sources
        if s.enabled and (only is None or only in (s.board, f"{s.ats}:{s.board}"))
    ]
