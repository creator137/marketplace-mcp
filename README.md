# marketplace-mcp

Local MCP server for working with marketplace and freelance platforms. The current implementation supports FL.ru, Avito, and Freelancer.com: Codex or another MCP client can browse projects, inspect details, score relevance, keep local history, save proposal/bid drafts, and preview submission in dry-run mode.

The server is intentionally not an autonomous proposal bot. Sending proposals is a separate tool and defaults to dry-run.

## Requirements

- Python 3.12+
- `uv`
- Chromium for Playwright
- FL.ru account for authenticated features
- Freelancer.com account for authenticated bid features

## Installation

```bash
uv sync --extra dev
uv run playwright install chromium
```

Copy `.env.example` to `.env` and fill only local secrets there:

```bash
cp .env.example .env
```

Important defaults:

- `FLRU_DRY_RUN=true`
- `FLRU_BROWSER_PROFILE=./data/browser-profile`
- `FLRU_STORAGE_STATE=./data/storage_state.json`
- `FLRU_DATABASE=./data/flru_mcp.sqlite3`
- `FLRU_EXPERTISE_PROFILE=./config/expertise.yml`

Avito defaults:

- `AVITO_DRY_RUN=true`
- `AVITO_BROWSER_PROFILE=./data/avito-browser-profile`
- `AVITO_STORAGE_STATE=./data/avito_storage_state.json`
- `AVITO_CLIENT_ID=` and `AVITO_CLIENT_SECRET=` are optional, but required for official API calls.

Freelancer.com defaults:

- `FREELANCER_DRY_RUN=true`
- `FREELANCER_BROWSER_PROFILE=./data/freelancer-browser-profile`
- `FREELANCER_STORAGE_STATE=./data/freelancer_storage_state.json`
- `FREELANCER_LOGIN=` and `FREELANCER_PASSWORD=` are optional, but allow Playwright to prefill login.

## First Authentication

FL.ru login currently shows Yandex SmartCaptcha. The server does not bypass it.

Run the MCP tool `flru_login` from a client, or run the server and call the tool with:

```json
{ "headless": false }
```

Playwright opens FL.ru login. Complete login and any CAPTCHA/2FA manually. The resulting browser storage state is saved under `data/`.

Freelancer.com authentication works the same way through `freelancer_login`. The server can prefill credentials from `.env`, but captcha, email confirmation, 2FA, billing/profile prompts, and other checks must be completed manually.

## Launch MCP Server

```bash
uv run marketplace-mcp
```

Codex MCP configuration example:

```json
{
  "mcpServers": {
    "flru": {
      "command": "uv",
      "args": ["run", "marketplace-mcp"],
      "cwd": "/home/stepanov-sv/projects/marketplace-mcp",
      "env": {
        "FLRU_DRY_RUN": "true"
      }
    }
  }
}
```

## Tools

FL.ru:

- `flru_auth_status`
- `flru_login`
- `flru_list_projects`
- `flru_search_projects`
- `flru_get_project`
- `flru_find_relevant_projects`
- `flru_mark_project_seen`
- `flru_get_unseen_projects`
- `flru_get_project_history`
- `flru_get_proposal_context`
- `flru_save_proposal_draft`
- `flru_get_proposal_draft`
- `flru_submit_proposal`
- `flru_get_customer`
- `flru_list_conversations`
- `flru_get_conversation`
- `flru_send_message`

Avito:

- `avito_auth_status`
- `avito_login`
- `avito_list_my_ads`
- `avito_get_ad`
- `avito_create_ad_draft`
- `avito_get_ad_draft`
- `avito_list_ad_drafts`
- `avito_open_create_ad_page`
- `avito_publish_ad`

Freelancer.com:

- `freelancer_auth_status`
- `freelancer_login`
- `freelancer_list_projects`
- `freelancer_search_projects`
- `freelancer_get_project`
- `freelancer_find_relevant_projects`
- `freelancer_get_bid_context`
- `freelancer_save_bid_draft`
- `freelancer_get_bid_draft`
- `freelancer_submit_bid`

Message tools currently return `NOT_IMPLEMENTED` until authenticated message endpoints are verified.

## Avito Workflow

Avito support uses the official API where possible and Playwright only for manual browser sessions.

To use API-backed tools, create Avito API credentials in the Avito account/API settings and set:

```env
AVITO_CLIENT_ID=...
AVITO_CLIENT_SECRET=...
```

Then:

```text
1. avito_auth_status
2. avito_list_my_ads
3. avito_create_ad_draft
4. avito_publish_ad
```

`avito_publish_ad` returns a dry-run preview while `AVITO_DRY_RUN=true`.

Real automated publication is not enabled yet because Avito returned IP/CAPTCHA protection during research and the authenticated add-item form was not safely verified. Use `avito_open_create_ad_page` to open the human page for manual inspection/completion. The server must not bypass CAPTCHA, IP checks, paid placement, moderation, or other manual verification.

## Freelancer.com Workflow

Freelancer.com public project discovery uses HTTP and server-rendered job pages. Authentication and bid-related checks use Playwright because the login and bid UI are dynamic and can require manual verification.

Typical dry-run flow:

```text
1. freelancer_list_projects or freelancer_find_relevant_projects
2. freelancer_get_project for selected candidates
3. freelancer_get_bid_context
4. Client drafts a tailored bid
5. freelancer_save_bid_draft
6. freelancer_submit_bid returns a preview because FREELANCER_DRY_RUN=true
```

Real bid submission is intentionally disabled until the authenticated bid form is verified with fixtures and success checks. With `FREELANCER_DRY_RUN=false`, `freelancer_submit_bid` still checks authentication, project state, and local duplicates, then returns `REAL_FREELANCER_BID_SUBMISSION_NOT_VERIFIED`.

## Dry-Run Workflow

```text
1. flru_find_relevant_projects
2. flru_get_project for selected candidates
3. Client drafts a proposal from source data
4. flru_save_proposal_draft
5. flru_submit_proposal returns a preview because FLRU_DRY_RUN=true
```

No FL.ru modification is made in dry-run.

## Real Submission Workflow

Real submission is intentionally not enabled yet because the authenticated freelancer proposal form was not verified during public-page research. With `FLRU_DRY_RUN=false`, `flru_submit_proposal` still performs auth, project, duplicate, closed-project, and form checks, then returns `REAL_SUBMISSION_NOT_ENABLED_FOR_UNVERIFIED_FORM` unless a verified proposal form is parsed.

Before enabling real submission, inspect the authenticated form with Playwright, document fields in `docs/flru-research.md`, add fixtures/tests, and verify success from the project page after submit. Never retry ambiguous POSTs automatically.

## Debugging

Set:

```env
FLRU_HEADLESS=false
FLRU_DEBUG=true
```

Browser failure screenshots and HTML snapshots are stored under `data/debug/`.

## Local Scanner

```bash
uv run flru-scan
```

The scanner discovers and scores projects into SQLite. It never submits proposals.

## Tests

```bash
uv run pytest
```

Current tests cover parsers, budgets, project detail extraction, relevance scoring, SQLite history/drafts, dry-run submission, and duplicate prevention.

## Known FL.ru Limitations

- Public project pages are server-rendered and parseable over HTTP.
- Login includes SmartCaptcha, so authentication is manual through Playwright.
- FL.ru uses DDoS-Guard; crawling is sequential with respectful delays.
- Authenticated proposal and message forms were not verified from public research, so real sending is disabled.
- CSS selectors are isolated in parser functions and documented in `docs/flru-research.md`.

## Known Freelancer.com Limitations

- Public project lists are parseable over HTTP from `/jobs/` and skill pages such as `/jobs/php/`.
- Login is an Angular/SPA flow, so Playwright is used for authentication.
- Captcha, 2FA, email checks, profile completion, and paid/billing prompts are never bypassed.
- Real bid submission is not enabled until the authenticated form is documented in `docs/freelancer-research.md` and covered by tests.
