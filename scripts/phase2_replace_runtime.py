#!/usr/bin/env python3
"""Phase 2 HTML transform: remove Squarespace runtime and wire local runtime."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = sorted([*ROOT.glob('*.html'), *ROOT.glob('courses/*.html')])

SCRIPT_BLOCK_RE = re.compile(r'<script\b[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL)
SCRIPT_OPEN_RE = re.compile(r'<script\b([^>]*)>', re.IGNORECASE | re.DOTALL)
SRC_RE = re.compile(r'\bsrc\s*=\s*(["\'])(.*?)\1', re.IGNORECASE | re.DOTALL)
TYPE_RE = re.compile(r'\btype\s*=\s*(["\'])(.*?)\1', re.IGNORECASE | re.DOTALL)

DATA_BLOCK_ATTR_RE = re.compile(r'\sdata-block-(?:scripts|css)\s*=\s*(["\']).*?\1', re.IGNORECASE | re.DOTALL)

RUNTIME_SRC_PATTERNS = [
    'assets.squarespace.com/@sqs/polyfiller/',
    'assets.squarespace.com/universal/scripts',
    'static1.squarespace.com/static/vta/',
    'definitions.sqspcdn.com/website-component-definition/static-assets/',
]
INLINE_DROP_PATTERNS = [
    'SQUARESPACE_ROLLUPS',
    'SQUARESPACE_CONTEXT',
    'Static.COOKIE_BANNER_CAPABLE',
]

LOCAL_CART_RE = re.compile(
    r'<div id="sqs-cart-root">.*?<div id="sqs-cart-container"></div>\s*</div>',
    re.IGNORECASE | re.DOTALL,
)


def is_runtime_script(script_html: str) -> bool:
    open_tag_match = SCRIPT_OPEN_RE.search(script_html)
    if not open_tag_match:
        return False

    open_tag = open_tag_match.group(1)
    src_match = SRC_RE.search(open_tag)
    type_match = TYPE_RE.search(open_tag)
    script_type = (type_match.group(2).strip().lower() if type_match else '')

    if script_type == 'application/ld+json':
        return False

    if src_match:
        src = src_match.group(2)
        if '/scripts/site-bundle.' in src:
            return True
        if any(pattern in src for pattern in RUNTIME_SRC_PATTERNS):
            if src.endswith('.css'):
                return False
            if src.endswith('.js') or '/scripts/' in src or '/scripts-compressed/' in src:
                return True
            if 'website-component-definition' in src and src.endswith('.js'):
                return True
        return False

    body_start = open_tag_match.end()
    body_end = script_html.lower().rfind('</script>')
    body = script_html[body_start:body_end if body_end != -1 else len(script_html)]
    return any(pattern in body for pattern in INLINE_DROP_PATTERNS)


def remove_runtime_scripts(text: str) -> str:
    parts = []
    last_index = 0
    for match in SCRIPT_BLOCK_RE.finditer(text):
        parts.append(text[last_index:match.start()])
        block = match.group(0)
        if not is_runtime_script(block):
            parts.append(block)
        last_index = match.end()
    parts.append(text[last_index:])
    return ''.join(parts)


def ensure_local_assets(text: str, prefix: str) -> str:
    css_href = f'{prefix}assets/css/local-runtime.css'
    js_src = f'{prefix}assets/js/local-runtime.js'

    css_tag = f'<link rel="stylesheet" type="text/css" href="{css_href}"/>'
    js_tag = f'<script defer="true" src="{js_src}" type="text/javascript"></script>'

    if css_href not in text:
        text = text.replace('</head>', f'    {css_tag}\n  </head>')

    if js_src not in text:
        text = text.replace('</body>', f'    {js_tag}\n\n  </body>')

    return text


def replace_cart_root(text: str) -> str:
    replacement = '''<div id="local-cart-root" class="local-cart-panel">
  <h1>Educational Resource Hub</h1>
  <p class="local-cart-note">This site is free and does not process purchases or checkout.</p>
  <p class="local-cart-note">Local saved-item count: <strong data-local-cart-count>0</strong></p>
  <div class="local-cart-actions">
    <button type="button" data-local-clear-cart>Clear saved item state</button>
  </div>

  <h2>Send Feedback</h2>
  <form class="local-form" data-local-form="site-feedback" novalidate>
    <div class="local-form-grid">
      <div>
        <label for="feedback-name">Name</label>
        <input id="feedback-name" name="name" type="text" required />
      </div>
      <div>
        <label for="feedback-email">Email</label>
        <input id="feedback-email" name="email" type="email" required />
      </div>
      <div>
        <label for="feedback-message">Message</label>
        <textarea id="feedback-message" name="message" required></textarea>
      </div>
      <button class="local-form-submit" type="submit">Submit Feedback</button>
    </div>
    <p class="local-form-status" data-local-form-status></p>
  </form>
</div>'''

    return LOCAL_CART_RE.sub(replacement, text, count=1)


def transform_file(path: Path) -> bool:
    original = path.read_text(encoding='utf-8', errors='ignore')
    text = original

    text = remove_runtime_scripts(text)
    text = DATA_BLOCK_ATTR_RE.sub('', text)

    if path.name == 'cart.html':
        text = replace_cart_root(text)

    prefix = '../' if path.parent.name == 'courses' else ''
    text = ensure_local_assets(text, prefix)

    if text != original:
        path.write_text(text, encoding='utf-8')
        return True
    return False


def main() -> None:
    changed = []
    for html_file in FILES:
        if transform_file(html_file):
            changed.append(str(html_file.relative_to(ROOT)))

    print(f'changed {len(changed)} files')
    for rel in changed:
        print(rel)


if __name__ == '__main__':
    main()
