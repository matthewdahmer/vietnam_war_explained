# FIX_REPORT

## Summary

Fixed the identified non-functional/missing elements while preserving existing educational content and non-commerce behavior.

Primary fixes:

- Added missing SVG icon sprite used by course/course-list UI.
- Fixed broken image requests caused by URL-encoded filename mismatch.
- Added missing `/universal/images-v6/icons/*` assets required by localized CSS.
- Replaced missing course-runtime interactions with local JS:
  - chapter accordion toggles on `courses.html`
  - lesson-completion persistence via localStorage
  - progress bars on course list and course side-nav pages
  - course side-nav open/close controls
  - `Complete & Continue` flow behavior

No files were modified in the reference baseline path.

## Files changed

- `assets/js/local-runtime.js`
- `assets/ui-icons.svg`
- `universal/images-v6/icons/block-indicator-dark.png`
- `universal/images-v6/icons/block-indicator-dark@2x.png`
- `universal/images-v6/icons/icon-searchqueries-20-dark.png`
- `universal/images-v6/icons/icon-searchqueries-20-light.png`
- `universal/images-v6/icons/opentable-icons.png`
- `universal/images-v6/icons/opentable-icons.svg`
- Added decoded filename aliases (12 files):
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/368a2c17-00e5-4fd0-b9bf-b77d7b783298/Flag_of_the_United_States_(DoS_ECA_Color_Standard).svg.png`
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/368a2c17-00e5-4fd0-b9bf-b77d7b783298/Flag_of_the_United_States_(DoS_ECA_Color_Standard).svg__q_2f39b9f0ad5f.png`
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/368a2c17-00e5-4fd0-b9bf-b77d7b783298/Flag_of_the_United_States_(DoS_ECA_Color_Standard).svg__q_ae31c69e37e0.png`
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/f29fb6a1-c501-4526-ad8d-a9f028d5af1e/130522_mia327_022-963x800+(1).jpg`
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/f29fb6a1-c501-4526-ad8d-a9f028d5af1e/130522_mia327_022-963x800+(1)__q_2203e1773de7.jpg`
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/f29fb6a1-c501-4526-ad8d-a9f028d5af1e/130522_mia327_022-963x800+(1)__q_2f39b9f0ad5f.jpg`
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/f29fb6a1-c501-4526-ad8d-a9f028d5af1e/130522_mia327_022-963x800+(1)__q_5dc32fbc134e.jpg`
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/f29fb6a1-c501-4526-ad8d-a9f028d5af1e/130522_mia327_022-963x800+(1)__q_799c3c57e0ea.jpg`
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/f29fb6a1-c501-4526-ad8d-a9f028d5af1e/130522_mia327_022-963x800+(1)__q_ae31c69e37e0.jpg`
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/f29fb6a1-c501-4526-ad8d-a9f028d5af1e/130522_mia327_022-963x800+(1)__q_ba03c59ce59d.jpg`
  - `assets/images.squarespace-cdn.com/content/v1/65cba021fbfe9811b3d7a492/f29fb6a1-c501-4526-ad8d-a9f028d5af1e/130522_mia327_022-963x800+(1)__q_c641dc906bd5.jpg`
  - `assets/static1.squarespace.com/static/65cba021fbfe9811b3d7a492/65cba1aa8a9eed48c1341c67/65e67d17ea42fc43daa7a837/1764858156120/Flag_of_the_United_States_(DoS_ECA_Color_Standard).svg__q_2203e1773de7.png`

## Verification command outputs

### Required command 1

Command:

```bash
rg -n "TODO|FIXME" *.html courses/*.html assets scripts; echo "EXIT:$?"
```

Output:

```text
EXIT:1
```

### Required command 2

Command:

```bash
rg -n "https?://(assets\.squarespace\.com|static1\.squarespace\.com|definitions\.sqspcdn\.com|images\.squarespace-cdn\.com|use\.typekit\.net|p\.typekit\.net)|//(assets\.squarespace\.com|static1\.squarespace\.com|definitions\.sqspcdn\.com|images\.squarespace-cdn\.com|use\.typekit\.net|p\.typekit\.net)" *.html courses/*.html assets; echo "EXIT:$?"
```

Output:

```text
EXIT:1
```

### Additional check: search index regeneration

Command:

```bash
python3 scripts/build_search_index.py
```

Output:

```text
wrote assets/data/search-index.json with 14 pages
```

### Additional check: JS syntax

Command:

```bash
node --check assets/js/local-runtime.js
```

Output:

```text
(no output; exit 0)
```

### Additional check: deep local crawl (HTML refs + CSS url(...) refs)

Output:

```text
DEEP_CRAWL_PAGES 14
DEEP_CRAWL_ASSETS_CHECKED 814
DEEP_CRAWL_BAD_HTML_ASSETS 0
DEEP_CRAWL_BAD_CSS_ASSETS 0
```

### Additional check: search/form behavior

Output:

```text
API_SEARCH_STATUS 200
API_SEARCH_OK True
API_SEARCH_RESULTS 12
API_FORM_SUCCESS_STATUS 200
API_FORM_SUCCESS_OK True
API_FORM_SUCCESS_ID_PRESENT True
API_FORM_FAILURE_STATUS 400
API_FORM_FAILURE_OK False
API_FORM_FAILURE_ERROR formId is required
FORM_SUBMISSIONS_EXISTS True
FORM_SUBMISSIONS_LINE_COUNT 1
```

### Additional check: icon and learning-runtime wiring

Command:

```bash
rg -n "COURSE_PROGRESS_STORAGE_KEY|data-course-item-id|course-list__list-chapter-item-accordion-trigger|course-item__side-nav-toggle-button|data-complete-and-continue|course-item__side-nav-progress-bar|course-list__progress-bar" assets/js/local-runtime.js
```

Output:

```text
5:  var COURSE_PROGRESS_STORAGE_KEY = 'vhc_course_progress_v1';
444:    var raw = window.localStorage.getItem(COURSE_PROGRESS_STORAGE_KEY);
450:    window.localStorage.setItem(COURSE_PROGRESS_STORAGE_KEY, JSON.stringify(state));
458:    return Array.from(document.querySelectorAll('input[type="checkbox"][data-course-item-id]'));
498:    var bars = document.querySelectorAll('.course-list__progress-bar, .course-item__side-nav-progress-bar');
580:    var buttons = document.querySelectorAll('[data-complete-and-continue]');
648:    var triggers = document.querySelectorAll('.course-list__list-chapter-item-accordion-trigger');
695:    var buttons = courseItem.querySelectorAll('.course-item__side-nav-toggle-button');
```

## Remaining blockers

- None identified from this audit/fix pass.
