#!/usr/bin/env python3
"""Build a local search index from project HTML pages."""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML_GLOBS = ["*.html", "courses/*.html"]
OUTPUT_PATH = ROOT / "assets" / "data" / "search-index.json"

SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def normalize_text(raw: str) -> str:
    no_script = SCRIPT_RE.sub(" ", raw)
    no_style = STYLE_RE.sub(" ", no_script)
    no_tags = TAG_RE.sub(" ", no_style)
    decoded = html.unescape(no_tags)
    return WS_RE.sub(" ", decoded).strip()


def get_title(raw: str, fallback: str) -> str:
    match = TITLE_RE.search(raw)
    if not match:
        return fallback
    return WS_RE.sub(" ", html.unescape(match.group(1))).strip() or fallback


def collect_pages() -> list[dict[str, str]]:
    files: list[Path] = []
    for pattern in HTML_GLOBS:
        files.extend(ROOT.glob(pattern))

    pages: list[dict[str, str]] = []
    for path in sorted(files):
        raw = path.read_text(encoding="utf-8", errors="ignore")
        text = normalize_text(raw)
        title = get_title(raw, path.stem)
        pages.append(
            {
                "url": path.relative_to(ROOT).as_posix(),
                "title": title,
                "text": text,
            }
        )

    return pages


def main() -> None:
    pages = collect_pages()
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "page_count": len(pages),
        "pages": pages,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {OUTPUT_PATH.relative_to(ROOT)} with {len(pages)} pages")


if __name__ == "__main__":
    main()
