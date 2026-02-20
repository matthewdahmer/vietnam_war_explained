# Phase 2 Local Runtime Runbook

## 1) Rebuild search index

```bash
python3 scripts/build_search_index.py
```

## 2) Start local runtime backend

```bash
python3 scripts/local_backend.py --host 127.0.0.1 --port 8000
```

## 3) Open the site locally

Use a browser and open:

- `http://127.0.0.1:8000/index.html`
- `http://127.0.0.1:8000/courses.html`
- `http://127.0.0.1:8000/cart.html`

## 4) Verify key Phase 2 behaviors manually

- Mobile menu: burger button toggles menu open/close.
- Search: press `/` or `Ctrl/Cmd + K` and confirm local results open page links.
- Non-commerce cart page: informational panel is shown (no checkout flow).
- Feedback form: submit on `cart.html`, then inspect `data/form-submissions.ndjson`.
