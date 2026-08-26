"""Generate the static dashboard folder consumed by GitHub Pages."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB_SRC = ROOT / "web"
SITE_DIR = ROOT / "site"


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
    (data_dir / "latest.json").write_text(
        json.dumps(latest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return dest
