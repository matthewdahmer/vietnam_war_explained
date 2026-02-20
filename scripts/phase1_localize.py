#!/usr/bin/env python3
"""Phase 1 asset localization for Squarespace-exported static pages.

This script:
1. Inventories external URLs in HTML pages.
2. Classifies URLs into target assets vs external references.
3. Downloads all target assets into local ./assets paths.
4. Recursively discovers target-domain URLs inside downloaded text assets.
5. Rewrites URLs in HTML and downloaded text assets to local relative paths.
6. Writes asset-map.json and PHASE1_REPORT.md.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
HTML_FILES = sorted(
    [*REPO_ROOT.glob("*.html"), *REPO_ROOT.glob("courses/*.html")],
    key=lambda p: p.as_posix(),
)
TARGET_DOMAINS = {
    "assets.squarespace.com",
    "static1.squarespace.com",
    "definitions.sqspcdn.com",
    "images.squarespace-cdn.com",
    "use.typekit.net",
    "p.typekit.net",
}

# Matches http(s)://... , //... , and escaped https:\/\/... , \/\/...
URL_PATTERN = re.compile(
    r'(?:(?:https?:)?(?://|\\\/\\\/))[A-Za-z0-9.-]+[^\s"\'<>\]\),;]+',
    re.IGNORECASE,
)

TEXT_EXTENSIONS = {
    ".css",
    ".js",
    ".json",
    ".html",
    ".htm",
    ".txt",
    ".xml",
    ".svg",
    ".map",
}

STOPPERS = ("&quot;", "&#34;", "&apos;", "&#39;", "&gt;", "&lt;")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="surrogateescape")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", errors="surrogateescape")


def normalize_url_token(token: str) -> str:
    value = html.unescape(token.strip())
    value = value.replace("\\/", "/")
    for stopper in STOPPERS:
        if stopper in value:
            value = value.split(stopper, 1)[0]
    # Defensive trim for odd punctuation joins.
    while value and value[-1] in "\\.,)]};":
        value = value[:-1]
    return value


def canonicalize_url(normalized: str) -> str:
    if normalized.startswith("//"):
        return "https:" + normalized
    return normalized


def get_hostname(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def is_target_url(url: str) -> bool:
    return get_hostname(url) in TARGET_DOMAINS


def extract_urls_from_text(text: str) -> Set[str]:
    return {normalize_url_token(m.group(0)) for m in URL_PATTERN.finditer(text)}


def collect_html_inventory(
    html_files: Iterable[Path],
) -> Tuple[Set[str], Set[str], Set[str], Dict[Path, Set[str]], Dict[Path, Set[str]]]:
    """Return all/external/target URLs and file-level token occurrences."""
    all_urls: Set[str] = set()
    target_urls: Set[str] = set()
    external_urls: Set[str] = set()
    file_target_tokens: Dict[Path, Set[str]] = {}
    file_all_tokens: Dict[Path, Set[str]] = {}

    for path in html_files:
        content = read_text(path)
        decoded = html.unescape(content)
        tokens = extract_urls_from_text(decoded)
        file_all_tokens[path] = set()
        file_target_tokens[path] = set()
        for token in tokens:
            if not token:
                continue
            file_all_tokens[path].add(token)
            canonical = canonicalize_url(token)
            if canonical.startswith(("http://", "https://", "//")):
                all_urls.add(token)
            if is_target_url(canonical):
                target_urls.add(token)
                file_target_tokens[path].add(token)
            else:
                external_urls.add(token)
    return all_urls, target_urls, external_urls, file_target_tokens, file_all_tokens


def local_paths_for_canonical(canonical_url: str) -> Tuple[str, str]:
    """Return (local_ref_path, local_storage_file_path), both repo-relative POSIX."""
    split = urllib.parse.urlsplit(canonical_url)
    host = (split.hostname or split.netloc or "unknown-host").lower()
    path_part = split.path or "/"
    rel_base = Path("assets") / host
    stripped = path_part.lstrip("/")
    if stripped:
        rel_base = rel_base / stripped

    if path_part.endswith("/"):
        rel_ref = rel_base.as_posix() + "/"
        rel_store = (rel_base / "index.html").as_posix()
        return rel_ref, rel_store

    rel_file = rel_base
    if split.query:
        qhash = hashlib.sha256(split.query.encode("utf-8")).hexdigest()[:12]
        stem = rel_file.stem or "file"
        suffix = rel_file.suffix
        rel_file = rel_file.with_name(f"{stem}__q_{qhash}{suffix}")
    rel_ref = rel_file.as_posix()
    rel_store = rel_ref
    return rel_ref, rel_store


def is_text_file(path: Path, content_type: str) -> bool:
    suffix = path.suffix.lower()
    if suffix in TEXT_EXTENSIONS:
        return True
    ctype = (content_type or "").lower()
    if ctype.startswith("text/"):
        return True
    for marker in ("javascript", "json", "xml", "svg"):
        if marker in ctype:
            return True
    return False


def fetch_bytes(url: str, retries: int = 3) -> Tuple[bytes, str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Phase1Localizer)",
        "Accept": "*/*",
    }
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                body = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                return body, content_type
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            if attempt == retries:
                raise
            time.sleep(1.2 * attempt)
    raise RuntimeError(f"Unreachable retry loop for {url}")


def make_relative_ref(source_file: Path, target_rel_ref: str) -> str:
    source_dir = source_file.parent
    if target_rel_ref.endswith("/"):
        target_abs = REPO_ROOT / target_rel_ref.rstrip("/")
        rel = os.path.relpath(target_abs, source_dir).replace(os.sep, "/")
        return rel + "/"
    target_abs = REPO_ROOT / target_rel_ref
    return os.path.relpath(target_abs, source_dir).replace(os.sep, "/")


def rewrite_file_tokens(
    path: Path,
    tokens: Set[str],
    normalized_to_ref: Dict[str, str],
) -> bool:
    original = read_text(path)
    updated = original
    for token in sorted(tokens, key=len, reverse=True):
        normalized = normalize_url_token(token)
        if normalized not in normalized_to_ref:
            continue
        replacement = make_relative_ref(path, normalized_to_ref[normalized])
        if "\\/" in token:
            replacement = replacement.replace("/", "\\/")
        updated = updated.replace(token, replacement)
    if updated != original:
        write_text(path, updated)
        return True
    return False


def run_cmd(cmd: List[str]) -> str:
    res = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    output = (res.stdout or "") + (res.stderr or "")
    return output.rstrip()


def main() -> int:
    if len(HTML_FILES) != 14:
        print(f"Expected 14 HTML files, found {len(HTML_FILES)}", file=sys.stderr)

    # 1) HTML inventory and classification.
    (
        all_urls_in_html,
        target_urls_in_html,
        external_urls_in_html,
        html_target_tokens,
        _html_all_tokens,
    ) = collect_html_inventory(HTML_FILES)

    # Structures used through crawl and rewrite.
    normalized_to_ref_path: Dict[str, str] = {}
    normalized_to_store_path: Dict[str, str] = {}
    canonical_to_store_path: Dict[str, str] = {}
    canonical_to_ref_path: Dict[str, str] = {}
    failed_urls: Dict[str, str] = {}
    queued: Set[str] = set()
    processed: Set[str] = set()
    discovered_target_tokens_by_file: Dict[Path, Set[str]] = {
        path: set(tokens) for path, tokens in html_target_tokens.items()
    }
    all_target_normalized_urls: Set[str] = set(target_urls_in_html)

    # Seed queue from HTML-discovered target URLs.
    to_process: List[str] = []
    for token in target_urls_in_html:
        canonical = canonicalize_url(token)
        if canonical not in queued:
            queued.add(canonical)
            to_process.append(canonical)
        ref_path, store_path = local_paths_for_canonical(canonical)
        normalized_to_ref_path[token] = ref_path
        normalized_to_store_path[token] = store_path
        canonical_to_ref_path[canonical] = ref_path
        canonical_to_store_path[canonical] = store_path

    # 2) Recursive download and discovery.
    while to_process:
        batch = list(to_process)
        to_process = []
        results: List[Tuple[str, bytes, str]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
            future_map = {
                pool.submit(fetch_bytes, canonical): canonical
                for canonical in batch
                if canonical not in processed
            }
            for future in concurrent.futures.as_completed(future_map):
                canonical = future_map[future]
                try:
                    body, content_type = future.result()
                    results.append((canonical, body, content_type))
                except Exception as exc:  # noqa: BLE001
                    failed_urls[canonical] = str(exc)

        for canonical, body, content_type in results:
            processed.add(canonical)
            store_rel = canonical_to_store_path[canonical]
            store_abs = REPO_ROOT / store_rel
            store_abs.parent.mkdir(parents=True, exist_ok=True)
            store_abs.write_bytes(body)

            if not is_text_file(store_abs, content_type):
                continue

            text = body.decode("utf-8", errors="surrogateescape")
            decoded = html.unescape(text)
            tokens = extract_urls_from_text(decoded)
            if tokens:
                discovered_target_tokens_by_file.setdefault(store_abs, set())
            for token in tokens:
                if not token:
                    continue
                token_canonical = canonicalize_url(token)
                if not is_target_url(token_canonical):
                    continue
                all_target_normalized_urls.add(token)
                discovered_target_tokens_by_file[store_abs].add(token)
                if token not in normalized_to_ref_path:
                    ref_path, store_path = local_paths_for_canonical(token_canonical)
                    normalized_to_ref_path[token] = ref_path
                    normalized_to_store_path[token] = store_path
                if token_canonical not in canonical_to_ref_path:
                    ref_path, store_path = local_paths_for_canonical(token_canonical)
                    canonical_to_ref_path[token_canonical] = ref_path
                    canonical_to_store_path[token_canonical] = store_path
                if token_canonical not in queued:
                    queued.add(token_canonical)
                    to_process.append(token_canonical)

    # Include canonical and protocol-relative forms in map for completeness.
    for canonical, ref_path in canonical_to_ref_path.items():
        normalized_to_ref_path.setdefault(canonical, ref_path)
        split = urllib.parse.urlsplit(canonical)
        proto_rel = f"//{split.netloc}{split.path}"
        if split.query:
            proto_rel = proto_rel + "?" + split.query
        normalized_to_ref_path.setdefault(proto_rel, ref_path)

    # 3) Rewrite URLs in HTML + downloaded text assets.
    changed_files: List[Path] = []
    for path, tokens in discovered_target_tokens_by_file.items():
        if not tokens or not path.exists():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path not in HTML_FILES:
            # Skip non-text files that happened to get tokens map entries.
            continue
        if rewrite_file_tokens(path, tokens, normalized_to_ref_path):
            changed_files.append(path)

    # 4) Write asset map.
    asset_map = {
        key: normalized_to_ref_path[key]
        for key in sorted(normalized_to_ref_path.keys())
    }
    (REPO_ROOT / "asset-map.json").write_text(
        json.dumps(asset_map, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # 5) Verification commands.
    verify_cmd = (
        r'rg -n "https?://(assets\.squarespace\.com|static1\.squarespace\.com|'
        r'definitions\.sqspcdn\.com|images\.squarespace-cdn\.com|use\.typekit\.net|'
        r'p\.typekit\.net)|//(assets\.squarespace\.com|static1\.squarespace\.com|'
        r'definitions\.sqspcdn\.com|images\.squarespace-cdn\.com|use\.typekit\.net|'
        r'p\.typekit\.net)" *.html courses/*.html'
    )
    verify_output = run_cmd(["zsh", "-lc", verify_cmd])

    extra_verify_assets_cmd = (
        r'rg -n "https?://(assets\.squarespace\.com|static1\.squarespace\.com|'
        r'definitions\.sqspcdn\.com|images\.squarespace-cdn\.com|use\.typekit\.net|'
        r'p\.typekit\.net)|//(assets\.squarespace\.com|static1\.squarespace\.com|'
        r'definitions\.sqspcdn\.com|images\.squarespace-cdn\.com|use\.typekit\.net|'
        r'p\.typekit\.net)" assets'
    )
    verify_assets_output = run_cmd(["zsh", "-lc", extra_verify_assets_cmd])

    changed_files_sorted = sorted({p.relative_to(REPO_ROOT).as_posix() for p in changed_files})

    # 6) Report.
    report_lines = [
        "# PHASE1_REPORT",
        "",
        "## Summary",
        f"- Total URLs found in HTML inventory (unique): {len(all_urls_in_html)}",
        f"- Total URLs classified as asset_to_localize (unique): {len(target_urls_in_html)}",
        f"- Total URLs intentionally external (unique): {len(external_urls_in_html)}",
        f"- Total localized target URLs after recursive discovery (unique): {len(all_target_normalized_urls)}",
        f"- Total downloaded canonical assets: {len(processed)}",
        f"- Unresolved/failed URLs: {len(failed_urls)}",
        "",
        "## Files Changed",
    ]
    if changed_files_sorted:
        report_lines.extend([f"- {p}" for p in changed_files_sorted])
    else:
        report_lines.append("- (none)")

    report_lines.extend(
        [
            "",
            "## Required Verification Command",
            "```bash",
            verify_cmd,
            "```",
            "```text",
            verify_output or "(no matches)",
            "```",
            "",
            "## Additional Verification (localized assets)",
            "```bash",
            extra_verify_assets_cmd,
            "```",
            "```text",
            verify_assets_output or "(no matches)",
            "```",
        ]
    )

    if failed_urls:
        report_lines.extend(["", "## Failures"])
        for url in sorted(failed_urls):
            report_lines.append(f"- {url}: {failed_urls[url]}")

    (REPO_ROOT / "PHASE1_REPORT.md").write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )

    # Also persist classification artifacts for traceability.
    classification = {
        "asset_to_localize": sorted(target_urls_in_html),
        "external_reference": sorted(external_urls_in_html),
    }
    (REPO_ROOT / "phase1-classification.json").write_text(
        json.dumps(classification, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Exit non-zero if unresolved assets remain.
    if failed_urls:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
