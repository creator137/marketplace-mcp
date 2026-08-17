# Freelancer.com Research

Date: 2026-08-17

## Observed behavior

- `https://www.freelancer.com/jobs/` returns server-rendered HTML with project cards under `#project-list`.
- Cards use `JobSearchCard` markup and links like `/projects/api-integration/react-laravel-feature-enhancements`.
- Skill/category pages are path based, for example `/jobs/php/`.
- Login is a JavaScript application at `/login`, so authentication is handled with Playwright and a persistent browser profile.

## Integration choice

- Public project discovery: HTTP GET plus HTML parsing.
- Authenticated session and bid forms: Playwright, because Freelancer can require captcha, email checks, 2FA, account setup, payment/profile prompts, or dynamic bid UI.
- Bid submission: implemented as a separate MCP tool, dry-run by default until a live authenticated bid form is manually verified.

## Safety

- The integration does not bypass captcha, email verification, 2FA, payment, or account restrictions.
- Credentials are read from `.env` or environment variables only.
- Session state is stored under `data/freelancer-browser-profile` and `data/freelancer_storage_state.json`.
