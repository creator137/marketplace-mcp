# Avito Research

Date: 2026-08-11

## Scope

Avito was inspected from this local environment using direct HTTP and Playwright. The goal was to determine the safest integration method for account login, listing existing ads, drafting ads, and eventual publication.

## Findings

- Direct public HTTP requests to `https://www.avito.ru/`, `/profile`, `/additem`, and search pages returned `403` in this environment.
- Headless Playwright navigation to the same pages returned `429` with a page titled `Доступ ограничен: проблема с IP`.
- The Avito restriction page says a user must press `Продолжить` and solve a CAPTCHA/manual check. The MCP server must not bypass this.
- `/additem` appears to be the current human-facing entry point for creating an ad, but the form was not reachable from this IP/session during research.
- A browser-based publish flow is therefore not reliable enough to implement as an automatic POST yet.
- Avito has an official business API at `https://api.avito.ru`.
- Official API authentication uses OAuth2 client credentials via `POST /token` with `grant_type=client_credentials`, `client_id`, and `client_secret`.
- The official account endpoint is `GET /core/v1/accounts/self`.
- The official item listing endpoint is `GET /core/v1/items`.
- User ID for API operations is the numeric Avito account ID and can be discovered from `/core/v1/accounts/self`.
- Some operations may require broader OAuth authorization-code scopes rather than client credentials.

## Integration Decision

Use a hybrid approach:

- Official Avito API for account status and existing ads when `AVITO_CLIENT_ID` and `AVITO_CLIENT_SECRET` are configured.
- Playwright persistent profile only for manual login and manual add-item page inspection.
- SQLite for local ad drafts and publication history.
- Keep `AVITO_DRY_RUN=true` by default.

## Publication Status

Real ad publication is intentionally not enabled yet. The local MCP can create and inspect drafts, open Avito's add-item page for manual work, and return a dry-run publication preview. Real automated publication must wait until either:

- an official API endpoint suitable for the target category/ad type is configured and tested; or
- the authenticated browser form is manually inspected, selectors are documented, paid/moderation steps are detected, and success verification is implemented.

The MCP must stop and return structured status if Avito shows CAPTCHA, IP restriction, paid placement, moderation, or any other manual verification step.
