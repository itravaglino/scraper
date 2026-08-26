"""Generate the static dashboard folder consumed by GitHub Pages."""

from __future__ import annotations

import html
import json
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_SRC = ROOT / "web"
SITE_DIR = ROOT / "site"
SEED_MARK = '{"__SEED__":true}'
STATIC_CASES_MARK = "<!--STATIC_CASES-->"
GENERATED_MARK = "__GENERATED_AT__"
STAMP_TEXT_MARK = "__STAMP_TEXT__"
WINDOW_MARK = "__WINDOW_DAYS__"


def _dashboard_payload(latest: dict) -> dict:
    """Inline copy used when fetch('data/latest.json') fails on GitHub Pages."""
    return {k: v for k, v in latest.items() if k != "reports"}


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _format_stamp(iso: str | None, zone: str) -> str:
    dt = _parse_iso(iso)
    if not dt:
        return "sin datos"
    try:
        from zoneinfo import ZoneInfo

        dt = dt.astimezone(ZoneInfo(zone))
    except Exception:
        dt = dt.astimezone(timezone(timedelta(hours=-3)))
    months = (
        "ene", "feb", "mar", "abr", "may", "jun",
        "jul", "ago", "sep", "oct", "nov", "dic",
    )
    return f"{dt.day} {months[dt.month - 1]} {dt.year}, {dt.strftime('%H:%M')} {zone}"


def _in_default_month(iso: str | None, generated_at: str | None) -> bool:
    dt = _parse_iso(iso)
    gen = _parse_iso(generated_at) or datetime.now(timezone.utc)
    if not dt:
        return False
    return gen - dt <= timedelta(days=30)


def _preview_cards_html(latest: dict) -> str:
    """First-paint cases so the board is never an empty shell before JS."""
    generated = latest.get("generated_at")
    clusters = [
        c
        for c in (latest.get("clusters") or [])
        if (c.get("polarity") or "revisar") == "mala"
        and _in_default_month(c.get("last_report_at"), generated)
        and (c.get("confidence") is None or float(c.get("confidence") or 0) >= 0.5)
    ]
    if not clusters:
        clusters = [c for c in (latest.get("clusters") or []) if (c.get("polarity") or "") == "mala"][:6]
    cards = []
    for c in clusters[:8]:
        title = html.escape(c.get("title") or "Caso")
        meta = html.escape(
            " · ".join(
                x
                for x in (
                    (c.get("last_report_at") or "")[:10],
                    f"{c.get('count') or 0} reportes",
                    c.get("category_label") or "",
                    (c.get("models") or ["Sin modelo"])[0],
                )
                if x
            )
        )
        quote = ""
        qs = c.get("quotes") or []
        if qs:
            quote = html.escape((qs[0].get("text") or "")[:220])
        cards.append(
            f'<article class="card {html.escape(c.get("severity") or "baja")}" data-id="{html.escape(c.get("id") or "")}">'
            f"<h3>{title}</h3>"
            f'<p class="case-meta">{meta}</p>'
            + (f'<blockquote class="quote">{quote}</blockquote>' if quote else "")
            + "</article>"
        )
    if not cards:
        return (
            '<p class="skel-note">Cargando casos del último mes…</p>'
            '<div class="skel card" aria-hidden="true"></div>'
            '<div class="skel card" aria-hidden="true"></div>'
            '<div class="skel card" aria-hidden="true"></div>'
        )
    return "\n".join(cards)


def generate_site(latest: dict, dest: Path | None = None) -> Path:
    dest = dest or SITE_DIR
    dest.mkdir(parents=True, exist_ok=True)
    if not WEB_SRC.exists():
        raise FileNotFoundError(f"missing dashboard templates: {WEB_SRC}")
    for item in WEB_SRC.iterdir():
        target = dest / item.name
        if item.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)
    data_dir = dest / "data"
    data_dir.mkdir(exist_ok=True)
    payload = json.dumps(latest, ensure_ascii=False, indent=2)
    (data_dir / "latest.json").write_text(payload, encoding="utf-8")

    index = dest / "index.html"
    html_text = index.read_text(encoding="utf-8")
    seed = json.dumps(_dashboard_payload(latest), ensure_ascii=False, separators=(",", ":"))
    seed = seed.replace("<", "\\u003c")
    if SEED_MARK not in html_text:
        raise RuntimeError("index.html missing seed placeholder")
    zone = latest.get("timezone") or "America/Buenos_Aires"
    generated = latest.get("generated_at") or ""
    window = str(latest.get("scrape_window_days") or 90)
    html_text = html_text.replace(SEED_MARK, seed)
    html_text = html_text.replace(GENERATED_MARK, html.escape(generated, quote=True))
    html_text = html_text.replace(STAMP_TEXT_MARK, html.escape(_format_stamp(generated, zone)))
    html_text = html_text.replace(WINDOW_MARK, html.escape(window))
    if STATIC_CASES_MARK in html_text:
        html_text = html_text.replace(STATIC_CASES_MARK, _preview_cards_html(latest))
    index.write_text(html_text, encoding="utf-8")
    return dest
