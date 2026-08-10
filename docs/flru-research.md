# FL.ru Research

Date: 2026-08-10

## Scope

Public pages were inspected with HTTP requests against `https://www.fl.ru`. Authenticated pages and proposal forms were not POSTed to. CAPTCHA or other verification must be completed manually.

## Findings

- `GET /projects/` returns server-rendered HTML and can be parsed without JavaScript for basic project discovery.
- The project list contains `#projects-list`; each card uses `div[id^="project-item"]`.
- The project title link uses `a[id^="prj_name_"]` and commonly carries `data-disposable-project-id`.
- List pages also include JSON-LD `ItemList`, but it contains only URLs and names, not budgets/descriptions, so HTML cards are the richer source.
- Search/filtering accepts query parameters on `/projects/`; observed `?kind=1&q=Bitrix24`.
- Category URLs are path based, for example `/projects/category/programmirovanie/` and nested category paths.
- `GET /projects/<id>/<slug>.html` returns server-rendered project detail HTML.
- Project detail pages contain breadcrumbs using schema.org `BreadcrumbList`; those are usable for category/subcategory.
- The project title is in `h1#prj_name_<id>`.
- Full description is in `#projectp<id>` and should preserve line breaks converted from `<br>`.
- Budget appears in a labeled `Бюджет:` block.
- Publication date appears near `Опубликован`.
- Guest detail pages show `#reply_offer` pointing to registration/login flow, not a usable proposal form.
- Login is at `/account/login/` and contains CSRF token, `username`, `password`, and Yandex SmartCaptcha.
- Because SmartCaptcha is present, automated login must not try to bypass verification. Playwright should open the browser and let the user complete it.
- Response headers show `server: ddos-guard`; requests should be slow and sequential.

## Integration Decision

Use a hybrid approach:

- HTTP via `httpx` for public and authenticated page reads where server-rendered HTML is sufficient.
- Playwright persistent browser profile for manual authentication and any future authenticated form inspection.
- SQLite for local state, history, drafts, and duplicate protection.

## Submission Status

Real proposal submission was not enabled from public research because the authenticated proposal form structure was not verified. The implementation supports dry-run previews and duplicate/auth/closed-project checks. Real submission must be enabled only after observing an authenticated freelancer account form and adding tests for the exact form fields and success verification.

