# flru-mcp

Local MCP server for working with the FL.ru freelance marketplace. It lets Codex or another MCP client browse projects, inspect details, score relevance, keep local history, save proposal drafts, and preview proposal submission in dry-run mode.

The server is intentionally not an autonomous proposal bot. Sending proposals is a separate tool and defaults to dry-run.

## Requirements

- Python 3.12+
- `uv`
- Chromium for Playwright
- FL.ru account for authenticated features

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

## First Authentication

FL.ru login currently shows Yandex SmartCaptcha. The server does not bypass it.

Run the MCP tool `flru_login` from a client, or run the server and call the tool with:

```json
{ "headless": false }
```

Playwright opens FL.ru login. Complete login and any CAPTCHA/2FA manually. The resulting browser storage state is saved under `data/`.

## Launch MCP Server

```bash
uv run flru-mcp
```

Codex MCP configuration example:

```json
{
  "mcpServers": {
    "flru": {
      "command": "uv",
      "args": ["run", "flru-mcp"],
      "cwd": "/home/stepanov-sv/projects/fl.ru",
      "env": {
        "FLRU_DRY_RUN": "true"
      }
    }
  }
}
```

## Tools

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

Message tools currently return `NOT_IMPLEMENTED` until authenticated message endpoints are verified.

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

