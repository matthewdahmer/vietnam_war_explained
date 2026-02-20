# PHASE2 Report

## Outcome

Phase 2 is complete in scope: Squarespace runtime/bootstrap execution has been removed from the 14-page site, replaced with local runtime code for navigation/search/forms/non-commerce cart handling, and verified with required checks.

## Replacement architecture

- `assets/js/local-runtime.js`
  - Replaces header menu toggle behavior.
  - Adds local search overlay and local index usage.
  - Handles local non-commerce cart badge/state.
  - Handles local form validation and submit flow to `/api/forms`.
- `assets/css/local-runtime.css`
  - Styles local search overlay, local cart panel, and local feedback form states.
- `assets/data/search-index.json`
  - Local search corpus used by runtime.
- `scripts/build_search_index.py`
  - Regenerates `assets/data/search-index.json` from all 14 HTML pages.
- `scripts/local_backend.py`
  - Serves static pages and local APIs:
    - `GET /api/search`
    - `POST /api/forms` (persisted to `data/form-submissions.ndjson`)
- `cart.html`
  - Legacy cart checkout surface replaced with non-transactional informational panel + feedback form.
- `phase2-behavior-matrix.json`
  - Machine-readable behavior inventory mapping existing mechanism, dependency source, replacement, and status per page behavior.

## Files changed

- Modified HTML pages:
  - `index.html`
  - `courses.html`
  - `cart.html`
  - `courses/introduction-mz3ln-zl9cb-8en9w-45a4d.html`
  - `courses/vietnam-before-the-war.html`
  - `courses/lesson-2-ingredients-djem8-zdxkd-92cfm-j5ddc.html`
  - `courses/the-war-in-vietnam.html`
  - `courses/the-soldiers.html`
  - `courses/cointelpro.html`
  - `courses/antiwar-movement.html`
  - `courses/social-groups-and-activism.html`
  - `courses/feminist-movement.html`
  - `courses/the-civil-rights-acts.html`
  - `courses/paris-peace-accords.html`
- Added runtime/support files:
  - `assets/js/local-runtime.js`
  - `assets/css/local-runtime.css`
  - `assets/data/search-index.json`
  - `scripts/build_search_index.py`
  - `scripts/local_backend.py`
  - `scripts/phase2_replace_runtime.py`
  - `phase2-behavior-matrix.json`
  - `PHASE2_RUNBOOK.md`
- Removed obsolete Squarespace runtime bundles:
  - `assets/assets.squarespace.com/universal/scripts-compressed/*` (44 files removed)
  - `assets/static1.squarespace.com/static/vta/5c5a519771c10ba3470d8101/scripts/site-bundle.4048606de8bae1a858c59c5fe6cb8a21.js`

## Required verification command outputs

Command:

```bash
rg -n "https?://(assets\.squarespace\.com|static1\.squarespace\.com|definitions\.sqspcdn\.com|images\.squarespace-cdn\.com|use\.typekit\.net|p\.typekit\.net)|//(assets\.squarespace\.com|static1\.squarespace\.com|definitions\.sqspcdn\.com|images\.squarespace-cdn\.com|use\.typekit\.net|p\.typekit\.net)" *.html courses/*.html assets; echo "EXIT:$?"
```

Output:

```text
EXIT:1
```

Command:

```bash
rg -n "Static\.SQUARESPACE_CONTEXT|SQUARESPACE_CONTEXT|squarespace\.com/universal/scripts|data-block-scripts|data-block-css" *.html courses/*.html assets; echo "EXIT:$?"
```

Output:

```text
EXIT:1
```

## Additional validation checks and outputs

### Search index generation + coverage

Command:

```bash
python3 scripts/build_search_index.py && python3 -c "import json; d=json.load(open('assets/data/search-index.json')); print('SEARCH_INDEX_PAGE_COUNT', d.get('page_count')); print('SEARCH_INDEX_LEN', len(d.get('pages', [])))"
```

Output:

```text
wrote assets/data/search-index.json with 14 pages
SEARCH_INDEX_PAGE_COUNT 14
SEARCH_INDEX_LEN 14
```

### Search/form API success/failure path

Command:

```bash
set -euo pipefail
python3 scripts/local_backend.py --host 127.0.0.1 --port 8765 >/tmp/phase2_backend.log 2>&1 &
PID=$!
sleep 1
echo "BACKEND_PID:$PID"
echo "API_SEARCH_CHECK"
curl -sS "http://127.0.0.1:8765/api/search?q=antiwar" | python3 -c "import sys, json; d=json.load(sys.stdin); print('ok', d.get('ok')); print('query', d.get('query')); print('results', len(d.get('results', []))); print('top_url', d.get('results', [{}])[0].get('url', ''))"
echo "API_FORM_SUCCESS_CHECK"
curl -sS -X POST "http://127.0.0.1:8765/api/forms" -H "Content-Type: application/json" --data '{"formId":"site-feedback","page":"/cart.html","fields":{"name":"Phase2 Tester","email":"phase2@example.com","message":"success path"}}' | python3 -c "import sys, json; d=json.load(sys.stdin); print('ok', d.get('ok')); print('id_present', bool(d.get('id')))"
echo "API_FORM_FAILURE_CHECK"
curl -sS -X POST "http://127.0.0.1:8765/api/forms" -H "Content-Type: application/json" --data '{"formId":"","fields":{}}' | python3 -c "import sys, json; d=json.load(sys.stdin); print('ok', d.get('ok')); print('error', d.get('error'))"
kill "$PID"
wait "$PID" 2>/dev/null || true
echo "FORM_FILE_CHECK"
python3 -c "from pathlib import Path; p=Path('data/form-submissions.ndjson'); print('exists', p.exists()); print('line_count', len(p.read_text().splitlines()) if p.exists() else 0)"
```

Output:

```text
BACKEND_PID:73994
API_SEARCH_CHECK
ok True
query antiwar
results 12
top_url courses/antiwar-movement.html
API_FORM_SUCCESS_CHECK
ok True
id_present True
API_FORM_FAILURE_CHECK
ok False
error formId is required
FORM_FILE_CHECK
exists True
line_count 2
```

### Non-transactional legacy cart handling

Command:

```bash
echo "NON_TRANSACTIONAL_PRESENCE" && rg -n "id=\"local-cart-root\"|does not process purchases or checkout|data-local-clear-cart|data-local-form=\"site-feedback\"" cart.html && echo "NON_TRANSACTIONAL_ABSENCE" && rg -n "id=\"sqs-cart-root\"|id=\"sqs-cart-container\"|data-commerce-" cart.html; echo "EXIT:$?"
```

Output:

```text
NON_TRANSACTIONAL_PRESENCE
904:            <div id="local-cart-root" class="local-cart-panel">
906:  <p class="local-cart-note">This site is free and does not process purchases or checkout.</p>
909:    <button type="button" data-local-clear-cart>Clear saved item state</button>
913:  <form class="local-form" data-local-form="site-feedback" novalidate>
NON_TRANSACTIONAL_ABSENCE
EXIT:1
```

### Local runtime wiring checks

Command:

```bash
rg -n "local-runtime\.js|local-runtime\.css" *.html courses/*.html | wc -l
```

Output:

```text
28
```

Command:

```bash
rg -n "search-index\.json|/api/forms|header--menu-open|local-search-overlay" assets/js/local-runtime.js
```

Output:

```text
19:      return new URL('../data/search-index.json', script.src).toString();
21:    return 'assets/data/search-index.json';
56:      body.classList.toggle('header--menu-open', isOpen);
63:      setOpen(!body.classList.contains('header--menu-open'));
192:    if (document.getElementById('local-search-overlay')) {
193:      return document.getElementById('local-search-overlay');
197:    overlay.id = 'local-search-overlay';
198:    overlay.className = 'local-search-overlay';
412:        fetch('/api/forms', {
```

## Blockers

None.

## Final status

Phase 2 is fully complete.
