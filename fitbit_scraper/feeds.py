"""Parse public RSS/Atom feeds without extra dependencies."""

from __future__ import annotations

from typing import Any
from xml.etree import ElementTree as ET

from .textutil import parse_datetime, strip_html


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def _child_text(el: ET.Element, names: set[str]) -> str:
    for child in list(el):
        if _local(child.tag) in names:
            return (child.text or "") + "".join(ET.tostring(c, encoding="unicode") for c in list(child))
    return ""


def _link(el: ET.Element) -> str:
    for child in list(el):
        if _local(child.tag) != "link":
            continue
        href = child.get("href") or child.get("url")
        if href:
            rel = child.get("rel") or "alternate"
            if rel in {"alternate", "self"} or rel.startswith("http"):
                return href
            # Prefer alternate; fall back later.
        if child.text and child.text.strip().startswith("http"):
            return child.text.strip()
    for child in list(el):
        if _local(child.tag) == "link":
            return child.get("href") or (child.text or "").strip()
    return ""


def _author(el: ET.Element) -> str:
    for child in list(el):
        if _local(child.tag) == "author":
            name = _child_text(child, {"name"})
            if name:
                return strip_html(name)
            return strip_html(child.text or "")
        if _local(child.tag) in {"creator", "name"}:
            return strip_html(child.text or "")
    return ""


def parse_feed(xml_text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    items: list[ET.Element] = []
    for el in root.iter():
        if _local(el.tag) in {"entry", "item"}:
            items.append(el)
    reports = []
    for el in items:
        title = strip_html(_child_text(el, {"title"}))
        content = strip_html(
            _child_text(el, {"content", "description", "summary", "encoded"})
        )
        ident = strip_html(_child_text(el, {"id", "guid"}))
        updated = parse_datetime(
            strip_html(_child_text(el, {"updated", "published", "pubDate", "date"}))
        )
        reports.append(
            {
                "id": ident,
                "title": title,
                "text": content,
                "url": _link(el),
                "created_at": updated,
                "author": _author(el),
            }
        )
    return reports
