# ISSUE_AUDIT

## Comparison basis

- Target repo: `./`
- Reference baseline (read-only): `/Users/matthewdahmer/Documents/kevin_henkel/pomegranate-cyan-4gjn.squarespace.com`
- Scope: all root HTML pages + `courses/*.html` (14 pages total)

## Issue inventory

| ID | Page(s) | Selector / Component | Symptom | Expected behavior (reference) | Root cause | Severity | Status |
|---|---|---|---|---|---|---|---|
| I-001 | `courses.html`, all `courses/*.html` | `xlink:href="/assets/ui-icons.svg#..."` | Missing hamburger/caret/video/chevron icons in course UI | Icons render in nav/buttons/course cards | `assets/ui-icons.svg` sprite missing locally | Medium | Resolved |
| I-002 | `index.html`, `courses.html`, `courses/introduction-mz3ln-zl9cb-8en9w-45a4d.html`, `courses/paris-peace-accords.html` | Image refs with URL-encoded filename segments (e.g. `%28`) | Image 404s for specific hero/thumb assets | Images load without missing placeholders | Files were stored with literal `%xx` names; server decodes URL path and looked for decoded filename | Major | Resolved |
| I-003 | All 14 pages (shared stylesheet path) | CSS `url(/universal/images-v6/icons/...)` assets from `site.css` | Repeated 404s for CSS-linked icon assets | No 404s for stylesheet dependencies | Required `/universal/images-v6/icons/*` files absent in localized tree | Medium | Resolved |
| I-004 | `courses.html` | `.course-list__list-chapter-item-accordion-trigger`, `.course-list__checkbox`, `.course-list__progress-bar` | Chapter accordion + progress/completion behavior not active | Chapter sections toggle and progress updates from lesson completion | Squarespace runtime removed; no local replacement existed for course-list interactions | Major | Resolved |
| I-005 | All `courses/*.html` | `.course-item` side-nav toggles, `.course-item__side-nav-checkbox`, `[data-complete-and-continue]`, side-nav progress bar | Side-nav open/close and learning flow controls inactive or not persisted | Side-nav toggle works; completion persists; progress updates; complete-and-continue advances lesson flow | Squarespace `CourseItem` runtime removed; no local replacement existed | Major | Resolved |

## Page-by-page audit map

| Page | Issues found |
|---|---|
| `index.html` | I-002, I-003 |
| `courses.html` | I-001, I-002, I-003, I-004 |
| `cart.html` | I-003 (shared CSS dependency only) |
| `courses/introduction-mz3ln-zl9cb-8en9w-45a4d.html` | I-001, I-002, I-003, I-005 |
| `courses/vietnam-before-the-war.html` | I-001, I-003, I-005 |
| `courses/lesson-2-ingredients-djem8-zdxkd-92cfm-j5ddc.html` | I-001, I-003, I-005 |
| `courses/the-war-in-vietnam.html` | I-001, I-003, I-005 |
| `courses/the-soldiers.html` | I-001, I-003, I-005 |
| `courses/cointelpro.html` | I-001, I-003, I-005 |
| `courses/antiwar-movement.html` | I-001, I-003, I-005 |
| `courses/social-groups-and-activism.html` | I-001, I-003, I-005 |
| `courses/feminist-movement.html` | I-001, I-003, I-005 |
| `courses/the-civil-rights-acts.html` | I-001, I-003, I-005 |
| `courses/paris-peace-accords.html` | I-001, I-002, I-003, I-005 |

## Re-audit result

- All identified Major/Medium issues above are resolved.
- Post-fix deep crawl across 14 pages reported:
  - `DEEP_CRAWL_BAD_HTML_ASSETS 0`
  - `DEEP_CRAWL_BAD_CSS_ASSETS 0`
