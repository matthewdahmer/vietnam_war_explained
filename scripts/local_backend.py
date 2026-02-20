#!/usr/bin/env python3
"""Serve static files plus local API endpoints for search and forms."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
SEARCH_INDEX_PATH = ROOT / "assets" / "data" / "search-index.json"
SUBMISSIONS_PATH = ROOT / "data" / "form-submissions.ndjson"
TOKEN_RE = re.compile(r"[a-z0-9]+")


def load_search_pages() -> list[dict[str, str]]:
    if not SEARCH_INDEX_PATH.exists():
        return []
    payload = json.loads(SEARCH_INDEX_PATH.read_text(encoding="utf-8"))
    pages = payload.get("pages", [])
    return pages if isinstance(pages, list) else []


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def score(entry: dict[str, str], query_tokens: list[str]) -> int:
    title = str(entry.get("title", "")).lower()
    body = str(entry.get("text", "")).lower()
    points = 0
    for token in query_tokens:
        if token in title:
            points += 8
        if token in body:
            points += 2
    return points


def search_pages(query: str) -> list[dict[str, str]]:
    tokens = tokenize(query)
    if not tokens:
        return []

    ranked: list[tuple[int, dict[str, str]]] = []
    for entry in load_search_pages():
        rank = score(entry, tokens)
        if rank > 0:
            ranked.append((rank, entry))

    ranked.sort(key=lambda item: item[0], reverse=True)
    results = []
    for _, entry in ranked[:20]:
        results.append(
            {
                "url": entry.get("url", ""),
                "title": entry.get("title", ""),
                "snippet": str(entry.get("text", ""))[:240],
            }
        )
    return results


class LocalHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/api/search":
            query = parse_qs(parsed.query).get("q", [""])[0].strip()
            results = search_pages(query)
            self._send_json({"ok": True, "query": query, "results": results})
            return

        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path != "/api/forms":
            self._send_json({"ok": False, "error": "Unknown endpoint"}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            content_length = 0

        raw = self.rfile.read(content_length)
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self._send_json(
                {"ok": False, "error": "Request body must be valid JSON"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return
        if not isinstance(payload, dict):
            self._send_json(
                {"ok": False, "error": "Request body must be a JSON object"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        form_id = str(payload.get("formId", "")).strip()
        fields = payload.get("fields", {})

        if not form_id:
            self._send_json({"ok": False, "error": "formId is required"}, status=HTTPStatus.BAD_REQUEST)
            return

        if not isinstance(fields, dict) or not fields:
            self._send_json({"ok": False, "error": "fields must be a non-empty object"}, status=HTTPStatus.BAD_REQUEST)
            return

        SUBMISSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "id": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "formId": form_id,
            "page": payload.get("page", ""),
            "fields": fields,
            "userAgent": self.headers.get("User-Agent", ""),
        }

        with SUBMISSIONS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

        self._send_json({"ok": True, "id": record["id"]})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve local static site + form/search APIs")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), LocalHandler)
    print(f"serving {ROOT} on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
