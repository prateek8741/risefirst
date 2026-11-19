"""HTML job descriptions -> readable plain text. The site renders plain text only (no XSS surface)."""

from __future__ import annotations

import html
import re
from datetime import UTC, datetime

_BLOCK_END = re.compile(r"</(p|div|h[1-6]|ul|ol|tr|section)>|<br\s*/?>", re.IGNORECASE)
_LIST_ITEM = re.compile(r"<li[^>]*>", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"[ \t ]+")
_BLANK_LINES = re.compile(r"\n\s*\n+")


def html_to_text(raw: str | None) -> str:
    text = html.unescape(raw or "")  # Greenhouse double-escapes its HTML
    text = _LIST_ITEM.sub("\n• ", _BLOCK_END.sub("\n", text))
    text = html.unescape(_TAG.sub(" ", text))
    lines = [_SPACES.sub(" ", line).strip() for line in text.splitlines()]
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def from_epoch_ms(value: int | float | None) -> datetime | None:
    return datetime.fromtimestamp(value / 1000, tz=UTC) if value else None
