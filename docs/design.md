# `bd` — Buttondown CLI

**Date:** 2026-03-14
**Status:** Approved
**Repo:** https://github.com/stavxyz/buttondown-cli-python

## Purpose

A generic CLI tool for Buttondown newsletter administration. The immediate use case: sending a previously published email to new subscribers who didn't receive it, without duplicating to existing recipients. Designed to work with any Buttondown account and any newsletter under that account.

## Auth & Config

Three layers with strict precedence: **CLI flags > env vars > config file**.

### Config file

Location: `~/.config/bd/config.toml`

```toml
[default]
api_key = "your-key"

[nbbw]
api_key = "different-key"
newsletter = "newsletter_abc123"
```

Profiles are selected via `--profile` flag (defaults to `default`). The config file is optional — env vars or CLI flags are sufficient.

### Environment variables

| Variable | Description |
|----------|-------------|
| `BD_API_KEY` | API key (required if not in config/flags) |
| `BD_NEWSLETTER` | Newsletter ID (optional, for multi-newsletter accounts) |

### CLI flags (global)

| Flag | Description |
|------|-------------|
| `--api-key` | API key override |
| `--newsletter` | Newsletter ID override |
| `--profile` | Config profile name (default: `default`) |

### Resolution order

1. CLI flag provided? Use it.
2. Env var set? Use it.
3. Config file profile has the value? Use it.
4. Otherwise: error (for api_key) or omit (for newsletter).

## API

- **Base URL:** `https://api.buttondown.com/v1/`
- **Auth header:** `Authorization: Token <api_key>`
- **OpenAPI spec:** https://github.com/buttondown/openapi

## Commands

### `bd emails`

List emails with key metadata.

```
bd emails [--status published|draft|scheduled] [--limit N]
```

**API:** `GET /emails` with optional `status` filter.

**Output:** Rich table with columns: ID (truncated), Subject, Date, Status, Deliveries.

### `bd subscribers`

List subscribers with summary stats.

```
bd subscribers [--limit N] [--recent]
```

**API:** `GET /subscribers` with optional ordering by `creation_date`.

**Output:**
- Summary line: total count of active subscribers.
- Rich table with columns: Email, Subscribed Date, Source, Tags.
- `--recent` orders by newest first (default).

### `bd send <email_id> --new-only`

Send a published email to all active subscribers who haven't received it yet.

```
bd send <email_id> --new-only [--dry-run]
```

**Flow:**

1. `GET /emails/{id}` — confirm email exists and status is `sent` (published).
2. `GET /emails/{id}/analytics` — retrieve recipient data to determine who already received it.
3. `GET /subscribers?type=regular` — paginate through all active subscribers.
4. Compute diff: active subscribers not in the recipients list.
5. Display count and prompt for confirmation (unless `--dry-run`).
6. For each new subscriber: `POST /subscribers/{id}/emails/{email_id}`.
7. Print progress bar and summary (sent N, failed M).

**`--dry-run`**: Show what would be sent without sending. Lists the email addresses that would receive it.

**Error handling:**
- If the email is not published, exit with error.
- Individual send failures are logged but don't abort the batch.
- Summary at end reports successes and failures.

### `bd send <email_id> --to <email_address>`

Send a specific published email to a specific subscriber.

```
bd send <email_id> --to user@example.com
```

**API:** `POST /subscribers/{email_address}/emails/{email_id}`

**Output:** Success/failure message.

**Validation:** `--new-only` and `--to` are mutually exclusive.

## Project Structure

```
buttondown-cli-python/
├── pyproject.toml
├── src/
│   └── bd/
│       ├── __init__.py
│       ├── cli.py          # Typer app, command definitions
│       ├── client.py        # Buttondown API client (httpx)
│       └── config.py        # Config resolution (flags > env > file)
└── tests/
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `typer` | CLI framework (includes Click + Rich) |
| `httpx` | HTTP client for API calls |

`tomllib` from stdlib (Python 3.11+) handles config file parsing.

## Install

```bash
pip install -e .
```

Entry point defined in `pyproject.toml`:

```toml
[project.scripts]
bd = "bd.cli:app"
```

## Testing

- Unit tests for config resolution (precedence logic).
- Unit tests for the subscriber diff logic (who hasn't received an email).
- Integration tests against the live API are out of scope for v1 — the OpenAPI spec and manual testing are sufficient.

## Out of Scope (v1)

- Creating or editing emails via CLI
- Subscriber management (create, delete, tag)
- Automation management
- Analytics beyond what `bd emails` shows
- Shell completions (Typer supports this but not needed yet)
