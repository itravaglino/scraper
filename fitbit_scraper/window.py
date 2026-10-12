"""Date window for every fetch and every kept report.

Dashboard default is Mes (30 days). The scrape window is 90 days so
Día / Semana / Mes / 90 días all filter real item dates. Year/Todo
only see what is inside this window — 2018–2022 recalls stay out unless
the window is widened (max 365).
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from .textutil import parse_datetime

# Covers the dashboard 90-días control. UI still defaults to 30 days.
DEFAULT_SCRAPE_WINDOW_DAYS = 90
MIN_WINDOW_DAYS = 1
MAX_WINDOW_DAYS = 365


def scrape_window_days() -> int:
    raw = os.environ.get("SCRAPE_WINDOW_DAYS", str(DEFAULT_SCRAPE_WINDOW_DAYS))
    try:
        n = int(str(raw).strip())
    except (TypeError, ValueError):
        n = DEFAULT_SCRAPE_WINDOW_DAYS
    return max(MIN_WINDOW_DAYS, min(n, MAX_WINDOW_DAYS))


def window_cutoff(days: int | None = None) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days or scrape_window_days())


def reddit_t_param(days: int | None = None) -> str:
    d = days if days is not None else scrape_window_days()
    if d <= 1:
        return "day"
    if d <= 7:
        return "week"
    if d <= 31:
        return "month"
    return "year"


def google_when_ops(days: int | None = None) -> str:
    """Google News recency only. `after:` zeroes out many site: feeds."""
    d = days if days is not None else scrape_window_days()
    return f"when:{d}d"


def google_date_ops(days: int | None = None) -> str:
    d = days if days is not None else scrape_window_days()
    after = window_cutoff(d).date().isoformat()
    return f"when:{d}d after:{after}"


def hn_since_epoch(days: int | None = None) -> int:
    return int(window_cutoff(days).timestamp())


def parse_iso(value: Optional[str]) -> Optional[str]:
    """Normalize any date string to UTC ISO-8601, or None."""
    if not value:
        return None
    iso = parse_datetime(str(value).strip())
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    # Google Help sometimes emits 14-digit stamps → year 2533+. Drop them.
    if dt.year < 2015 or dt.year > now.year + 1:
        return None
    return dt.astimezone(timezone.utc).isoformat()


def iso_in_window(value: Optional[str], days: int | None = None) -> bool:
    """True only when the timestamp parses and sits inside the scrape window."""
    iso = parse_iso(value)
    if not iso:
        return False
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= window_cutoff(days)


def _is_far_future_stamp(value: Optional[str]) -> bool:
    if not value:
        return False
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.year > datetime.now(timezone.utc).year + 1


def filter_reports_in_window(reports: list[dict], days: int | None = None) -> list[dict]:
    kept = []
    now_iso = datetime.now(timezone.utc).isoformat()
    for r in reports:
        stamp = r.get("created_at") or r.get("published_at")
        iso = parse_iso(stamp)
        if not iso and _is_far_future_stamp(stamp):
            # Far-future Google Help stamps (year 253x): keep the thread, use now.
            iso = now_iso
        if iso_in_window(iso, days):
            rec = dict(r)
            rec["created_at"] = iso
            rec["published_at"] = iso
            kept.append(rec)
    return kept
