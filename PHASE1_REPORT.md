# PHASE1_REPORT

## Summary
- Total URLs found in HTML inventory (unique): 1051
- Total URLs classified as asset_to_localize (unique): 887
- Total URLs intentionally external (unique): 164
- Total localized target canonical URLs after recursive discovery (unique): 999
- Total mapping entries in `asset-map.json`: 1974
- Unresolved/failed URLs: 0

## Notes
- Non-fetchable template/directory URL patterns were localized with deterministic local placeholder files.
- Runtime target-domain references were removed from both HTML pages and localized assets.

## Files Changed
- `*.html` (all 14 pages in root + `courses/`)
- `assets/**` (localized runtime assets)
- `asset-map.json`
- `phase1-classification.json`
- `PHASE1_REPORT.md`
- `scripts/phase1_localize.py`

## Required Verification Command
```bash
rg -n "https?://(assets\\.squarespace\\.com|static1\\.squarespace\\.com|definitions\\.sqspcdn\\.com|images\\.squarespace-cdn\\.com|use\\.typekit\\.net|p\\.typekit\\.net)|//(assets\\.squarespace\\.com|static1\\.squarespace\\.com|definitions\\.sqspcdn\\.com|images\\.squarespace-cdn\\.com|use\\.typekit\\.net|p\\.typekit\\.net)" *.html courses/*.html
```
```text
(no matches)
```

## Additional Verification (localized assets)
```bash
rg -n "https?://(assets\\.squarespace\\.com|static1\\.squarespace\\.com|definitions\\.sqspcdn\\.com|images\\.squarespace-cdn\\.com|use\\.typekit\\.net|p\\.typekit\\.net)|//(assets\\.squarespace\\.com|static1\\.squarespace\\.com|definitions\\.sqspcdn\\.com|images\\.squarespace-cdn\\.com|use\\.typekit\\.net|p\\.typekit\\.net)" assets
```
```text
(no matches)
```

## Additional Verification (asset-map completeness)
```bash
python3 - <<'PY2'
import json, pathlib
root=pathlib.Path('/Users/matthewdahmer/Documents/kevin_henkel/vietnam_war_explained')
mp=json.loads((root/'asset-map.json').read_text())
missing=[]
for k,v in mp.items():
    p=root/v.rstrip('/')
    if v.endswith('/'):
        if not p.exists() or not p.is_dir():
            missing.append((k,v,'dir'))
    else:
        if not p.exists():
            missing.append((k,v,'file'))
print('missing',len(missing))
PY2
```
```text
missing 0
```

## Additional Verification (localized path existence in HTML)
```bash
python3 - <<'PY'
import re
from pathlib import Path
root=Path('.')
htmls=[*root.glob('*.html'), *root.glob('courses/*.html')]
attr_re=re.compile(r'(?:src|href|srcset|poster|data-src|data-image|data-block-css|data-block-scripts)\\s*=\\s*(["\\'])(.*?)\\1', re.I|re.S)
url_re=re.compile(r'url\\((.*?)\\)', re.I)
missing=[]
checked=0
for hp in htmls:
    text=hp.read_text(encoding='utf-8', errors='ignore')
    vals=[]
    for m in attr_re.finditer(text):
        vals.append(m.group(2))
    for m in url_re.finditer(text):
        v=m.group(1).strip().strip('"\\'')
        vals.append(v)
    for v in vals:
        pieces=[v]
        if ',' in v:
            pieces=[p.strip() for p in v.split(',')]
        for part in pieces:
            if not part:
                continue
            toks=part.split()
            if not toks:
                continue
            u=toks[0].strip()
            if not u.startswith('assets/'):
                continue
            checked+=1
            p=(hp.parent / u).resolve()
            if not p.exists():
                missing.append((str(hp),u))
print('checked_assets_refs',checked)
print('missing_assets_refs',len(missing))
PY
```
```text
checked_assets_refs 98
missing_assets_refs 0
```
