# `bd` CLI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a generic Buttondown newsletter CLI (`bd`) with the core feature of sending published emails to new subscribers who missed them.

**Architecture:** Standalone Python package with Typer CLI, httpx API client, and TOML-based config with three-layer precedence (CLI flags > env vars > config file). Uses the Buttondown REST API v1.

**Tech Stack:** Python 3.11+, Typer, httpx, stdlib tomllib

**Spec:** `docs/design.md`

**OpenAPI reference:** https://github.com/buttondown/openapi (`openapi.json`)

---

## Chunk 1: Project Scaffold & Config

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/bd/__init__.py`
- Create: `src/bd/cli.py`
- Create: `src/bd/client.py`
- Create: `src/bd/config.py`
- Create: `tests/__init__.py`
- Create: `tests/test_config.py`
- Create: `.gitignore`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "buttondown-cli"
version = "0.1.0"
description = "A command-line interface for Buttondown newsletter administration"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.9.0",
    "httpx>=0.24.0",
]

[project.scripts]
bd = "bd.cli:app"

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create `.gitignore`**

```
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.venv/
.env
```

- [ ] **Step 3: Create `src/bd/__init__.py`**

```python
"""Buttondown CLI."""
```

- [ ] **Step 4: Create empty module files**

Create `src/bd/cli.py`, `src/bd/client.py`, `src/bd/config.py`, `tests/__init__.py`, `tests/test_config.py` as empty files.

- [ ] **Step 5: Create venv and install in dev mode**

```bash
cd ~/src/buttondown-cli-python
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" 2>/dev/null || pip install -e .
pip install pytest
```

- [ ] **Step 6: Verify `bd` entry point works**

```bash
bd --help
```

Expected: Typer will fail or show empty help (no app defined yet). That's fine — confirms the entry point is wired.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "Initial project scaffold with pyproject.toml and package structure"
```

### Task 2: Config resolution

**Files:**
- Create: `src/bd/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config resolution**

```python
# tests/test_config.py
import os
import textwrap
from pathlib import Path
from unittest.mock import patch

from bd.config import resolve_config


class TestConfigResolution:
    """Config precedence: CLI flags > env vars > config file."""

    def test_cli_flags_take_precedence_over_everything(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [default]
            api_key = "from-file"
        """))
        with patch.dict(os.environ, {"BD_API_KEY": "from-env"}):
            cfg = resolve_config(
                api_key="from-cli",
                newsletter=None,
                profile="default",
                config_path=config_file,
            )
        assert cfg.api_key == "from-cli"

    def test_env_vars_take_precedence_over_config_file(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [default]
            api_key = "from-file"
        """))
        with patch.dict(os.environ, {"BD_API_KEY": "from-env"}):
            cfg = resolve_config(
                api_key=None,
                newsletter=None,
                profile="default",
                config_path=config_file,
            )
        assert cfg.api_key == "from-env"

    def test_config_file_used_when_no_flag_or_env(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [default]
            api_key = "from-file"
            newsletter = "nl-123"
        """))
        with patch.dict(os.environ, {}, clear=True):
            env_keys = ["BD_API_KEY", "BD_NEWSLETTER"]
            cleaned = {k: v for k, v in os.environ.items() if k not in env_keys}
            with patch.dict(os.environ, cleaned, clear=True):
                cfg = resolve_config(
                    api_key=None,
                    newsletter=None,
                    profile="default",
                    config_path=config_file,
                )
        assert cfg.api_key == "from-file"
        assert cfg.newsletter == "nl-123"

    def test_named_profile(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [default]
            api_key = "default-key"

            [nbbw]
            api_key = "nbbw-key"
            newsletter = "nbbw-newsletter"
        """))
        with patch.dict(os.environ, {}, clear=True):
            env_keys = ["BD_API_KEY", "BD_NEWSLETTER"]
            cleaned = {k: v for k, v in os.environ.items() if k not in env_keys}
            with patch.dict(os.environ, cleaned, clear=True):
                cfg = resolve_config(
                    api_key=None,
                    newsletter=None,
                    profile="nbbw",
                    config_path=config_file,
                )
        assert cfg.api_key == "nbbw-key"
        assert cfg.newsletter == "nbbw-newsletter"

    def test_missing_api_key_raises_error(self, tmp_path):
        config_file = tmp_path / "nonexistent.toml"
        import pytest
        with patch.dict(os.environ, {}, clear=True):
            env_keys = ["BD_API_KEY", "BD_NEWSLETTER"]
            cleaned = {k: v for k, v in os.environ.items() if k not in env_keys}
            with patch.dict(os.environ, cleaned, clear=True):
                with pytest.raises(SystemExit):
                    resolve_config(
                        api_key=None,
                        newsletter=None,
                        profile="default",
                        config_path=config_file,
                    )

    def test_newsletter_is_optional(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text(textwrap.dedent("""\
            [default]
            api_key = "key-only"
        """))
        with patch.dict(os.environ, {}, clear=True):
            env_keys = ["BD_API_KEY", "BD_NEWSLETTER"]
            cleaned = {k: v for k, v in os.environ.items() if k not in env_keys}
            with patch.dict(os.environ, cleaned, clear=True):
                cfg = resolve_config(
                    api_key=None,
                    newsletter=None,
                    profile="default",
                    config_path=config_file,
                )
        assert cfg.api_key == "key-only"
        assert cfg.newsletter is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd ~/src/buttondown-cli-python
.venv/bin/pytest tests/test_config.py -v
```

Expected: ImportError or AttributeError — `resolve_config` doesn't exist yet.

- [ ] **Step 3: Implement config resolution**

```python
# src/bd/config.py
from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "bd" / "config.toml"


@dataclass
class Config:
    api_key: str
    newsletter: Optional[str] = None


def _load_profile(config_path: Path, profile: str) -> dict:
    """Load a named profile from the TOML config file."""
    if not config_path.exists():
        return {}
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    return data.get(profile, {})


def resolve_config(
    *,
    api_key: Optional[str],
    newsletter: Optional[str],
    profile: str = "default",
    config_path: Optional[Path] = None,
) -> Config:
    """Resolve config with precedence: CLI flags > env vars > config file."""
    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    file_config = _load_profile(config_path, profile)

    resolved_api_key = (
        api_key
        or os.environ.get("BD_API_KEY")
        or file_config.get("api_key")
    )
    resolved_newsletter = (
        newsletter
        or os.environ.get("BD_NEWSLETTER")
        or file_config.get("newsletter")
    )

    if not resolved_api_key:
        print(
            "Error: No API key found. Provide --api-key, set BD_API_KEY, "
            f"or add api_key to [{profile}] in {config_path}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return Config(api_key=resolved_api_key, newsletter=resolved_newsletter)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd ~/src/buttondown-cli-python
.venv/bin/pytest tests/test_config.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/bd/config.py tests/test_config.py
git commit -m "Add config resolution with three-layer precedence"
```

---

## Chunk 2: API Client

### Task 3: Buttondown API client

**Files:**
- Create: `src/bd/client.py`

- [ ] **Step 1: Implement the API client**

```python
# src/bd/client.py
from __future__ import annotations

from typing import Any, Optional

import httpx

BASE_URL = "https://api.buttondown.com/v1"


class ButtondownClient:
    """HTTP client for the Buttondown API."""

    def __init__(self, api_key: str, newsletter: Optional[str] = None):
        headers = {"Authorization": f"Token {api_key}"}
        if newsletter:
            headers["X-Buttondown-Newsletter"] = newsletter
        self._client = httpx.Client(
            base_url=BASE_URL,
            headers=headers,
            timeout=30.0,
        )

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        resp = self._client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: Optional[dict] = None) -> dict:
        resp = self._client.post(path, json=json)
        resp.raise_for_status()
        return resp.json()

    def _paginate(self, path: str, params: Optional[dict] = None) -> list[dict]:
        """Fetch all pages of a paginated endpoint."""
        results = []
        params = dict(params or {})
        while True:
            data = self._get(path, params=params)
            results.extend(data.get("results", []))
            next_url = data.get("next")
            if not next_url:
                break
            # next_url is absolute — parse page param from it
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(next_url)
            page_values = parse_qs(parsed.query).get("page", [])
            if page_values:
                params["page"] = page_values[0]
            else:
                break
        return results

    # --- Emails ---

    def list_emails(
        self, status: Optional[list[str]] = None, limit: Optional[int] = None
    ) -> list[dict]:
        params: dict[str, Any] = {}
        if status:
            params["status"] = status
        if limit:
            # Buttondown doesn't have a limit param — we paginate and slice
            all_emails = self._paginate("/emails", params)
            return all_emails[:limit]
        return self._paginate("/emails", params)

    def get_email(self, email_id: str) -> dict:
        return self._get(f"/emails/{email_id}")

    def get_email_analytics(self, email_id: str) -> dict:
        return self._get(f"/emails/{email_id}/analytics")

    # --- Subscribers ---

    def list_subscribers(
        self,
        subscriber_type: Optional[list[str]] = None,
        ordering: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict]:
        params: dict[str, Any] = {}
        if subscriber_type:
            params["type"] = subscriber_type
        if ordering:
            params["ordering"] = ordering
        if limit:
            all_subs = self._paginate("/subscribers", params)
            return all_subs[:limit]
        return self._paginate("/subscribers", params)

    # --- Events ---

    def list_events(
        self,
        email_id: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> list[dict]:
        params: dict[str, Any] = {}
        if email_id:
            params["email_id"] = email_id
        if event_type:
            params["event_type"] = event_type
        return self._paginate("/events", params)

    # --- Send ---

    def send_email_to_subscriber(
        self, subscriber_id_or_email: str, email_id: str
    ) -> dict:
        return self._post(
            f"/subscribers/{subscriber_id_or_email}/emails/{email_id}"
        )
```

- [ ] **Step 2: Verify import works**

```bash
cd ~/src/buttondown-cli-python
.venv/bin/python -c "from bd.client import ButtondownClient; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/bd/client.py
git commit -m "Add Buttondown API client with pagination support"
```

---

## Chunk 3: CLI Commands

### Task 4: CLI app with `emails` and `subscribers` commands

**Files:**
- Create: `src/bd/cli.py`

- [ ] **Step 1: Implement CLI app with global options and list commands**

```python
# src/bd/cli.py
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from bd.client import ButtondownClient
from bd.config import Config, resolve_config

app = typer.Typer(
    name="bd",
    help="Buttondown newsletter CLI.",
    no_args_is_help=True,
)
console = Console()


def _get_config(ctx: typer.Context) -> Config:
    return resolve_config(
        api_key=ctx.obj.get("api_key"),
        newsletter=ctx.obj.get("newsletter"),
        profile=ctx.obj.get("profile", "default"),
    )


def _get_client(ctx: typer.Context) -> ButtondownClient:
    cfg = _get_config(ctx)
    return ButtondownClient(api_key=cfg.api_key, newsletter=cfg.newsletter)


@app.callback()
def main(
    ctx: typer.Context,
    api_key: Optional[str] = typer.Option(
        None, "--api-key", envvar="BD_API_KEY", help="Buttondown API key."
    ),
    newsletter: Optional[str] = typer.Option(
        None, "--newsletter", help="Newsletter ID for multi-newsletter accounts."
    ),
    profile: str = typer.Option(
        "default", "--profile", help="Config profile name."
    ),
):
    """Buttondown newsletter CLI."""
    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key
    ctx.obj["newsletter"] = newsletter
    ctx.obj["profile"] = profile


@app.command()
def emails(
    ctx: typer.Context,
    status: Optional[str] = typer.Option(
        None, "--status", help="Filter by status (draft, sent, scheduled)."
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", "-n", help="Max emails to show."
    ),
):
    """List emails."""
    with _get_client(ctx) as client:
        status_filter = [status] if status else None
        results = client.list_emails(status=status_filter, limit=limit)

    table = Table(title="Emails")
    table.add_column("ID", style="dim", max_width=12)
    table.add_column("Subject", style="bold")
    table.add_column("Date")
    table.add_column("Status")
    table.add_column("Deliveries", justify="right")

    for email in results:
        analytics = email.get("analytics") or {}
        table.add_row(
            email["id"][:12],
            email.get("subject", "(no subject)"),
            (email.get("publish_date") or email.get("creation_date", ""))[:10],
            email.get("status", ""),
            str(analytics.get("deliveries", "")),
        )

    console.print(table)


@app.command()
def subscribers(
    ctx: typer.Context,
    limit: Optional[int] = typer.Option(
        None, "--limit", "-n", help="Max subscribers to show."
    ),
    recent: bool = typer.Option(
        True, "--recent/--oldest", help="Order by newest first."
    ),
):
    """List subscribers."""
    ordering = "-creation_date" if recent else "creation_date"
    with _get_client(ctx) as client:
        results = client.list_subscribers(
            subscriber_type=["regular"],
            ordering=ordering,
            limit=limit,
        )

    console.print(f"\n[bold]{len(results)}[/bold] active subscribers\n")

    table = Table()
    table.add_column("Email", style="bold")
    table.add_column("Subscribed")
    table.add_column("Source")
    table.add_column("Tags")

    for sub in results:
        tags = ", ".join(t.get("id", str(t)) if isinstance(t, dict) else str(t) for t in sub.get("tags", []))
        table.add_row(
            sub["email_address"],
            sub.get("creation_date", "")[:10],
            sub.get("source", ""),
            tags,
        )

    console.print(table)
```

- [ ] **Step 2: Verify help output**

```bash
cd ~/src/buttondown-cli-python
.venv/bin/bd --help
.venv/bin/bd emails --help
.venv/bin/bd subscribers --help
```

Expected: Clean help text for all three.

- [ ] **Step 3: Commit**

```bash
git add src/bd/cli.py
git commit -m "Add emails and subscribers list commands"
```

### Task 5: `send` command

**Files:**
- Modify: `src/bd/cli.py`

- [ ] **Step 1: Add the `send` command to `cli.py`**

Append to `src/bd/cli.py`:

```python
@app.command()
def send(
    ctx: typer.Context,
    email_id: str = typer.Argument(help="ID of the email to send."),
    new_only: bool = typer.Option(
        False, "--new-only", help="Send only to subscribers who haven't received it."
    ),
    to: Optional[str] = typer.Option(
        None, "--to", help="Send to a specific subscriber email address."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be sent without sending."
    ),
):
    """Send a published email to subscribers."""
    if new_only and to:
        console.print("[red]Error:[/red] --new-only and --to are mutually exclusive.")
        raise typer.Exit(1)

    if not new_only and not to:
        console.print("[red]Error:[/red] Specify --new-only or --to <email>.")
        raise typer.Exit(1)

    with _get_client(ctx) as client:
        # Verify email exists and is published
        email = client.get_email(email_id)
        if email.get("status") != "sent":
            console.print(
                f"[red]Error:[/red] Email status is '{email.get('status')}', "
                "expected 'sent' (published)."
            )
            raise typer.Exit(1)

        subject = email.get("subject", "(no subject)")

        if to:
            _send_to_one(client, email_id, subject, to, dry_run)
        else:
            _send_to_new(client, email_id, subject, dry_run)


def _send_to_one(
    client: ButtondownClient, email_id: str, subject: str, to: str, dry_run: bool
):
    """Send a specific email to a specific subscriber."""
    if dry_run:
        console.print(f"[yellow]Dry run:[/yellow] Would send '{subject}' to {to}")
        return

    try:
        client.send_email_to_subscriber(to, email_id)
        console.print(f"[green]Sent[/green] '{subject}' to {to}")
    except Exception as e:
        console.print(f"[red]Failed[/red] to send to {to}: {e}")
        raise typer.Exit(1)


def _send_to_new(
    client: ButtondownClient, email_id: str, subject: str, dry_run: bool
):
    """Send a published email to subscribers who haven't received it."""
    console.print(f"Checking recipients for '{subject}'...")

    # Get subscribers who already received this email
    events = client.list_events(email_id=email_id, event_type="delivered")
    already_received = {e["subscriber_id"] for e in events}

    # Get all active subscribers
    all_subscribers = client.list_subscribers(subscriber_type=["regular"])
    new_subscribers = [
        s for s in all_subscribers if s["id"] not in already_received
    ]

    if not new_subscribers:
        console.print("[green]All subscribers have already received this email.[/green]")
        return

    console.print(
        f"\n[bold]{len(new_subscribers)}[/bold] subscribers haven't received this email "
        f"(out of {len(all_subscribers)} total).\n"
    )

    if dry_run:
        table = Table(title="Would send to")
        table.add_column("Email")
        table.add_column("Subscribed")
        for s in new_subscribers:
            table.add_row(s["email_address"], s.get("creation_date", "")[:10])
        console.print(table)
        return

    if not typer.confirm(f"Send '{subject}' to {len(new_subscribers)} subscribers?"):
        console.print("Aborted.")
        raise typer.Exit(0)

    sent = 0
    failed = 0
    with console.status("Sending...") as status:
        for s in new_subscribers:
            try:
                client.send_email_to_subscriber(s["id"], email_id)
                sent += 1
                status.update(f"Sending... ({sent}/{len(new_subscribers)})")
            except Exception as e:
                failed += 1
                console.print(
                    f"  [red]Failed[/red] {s['email_address']}: {e}"
                )

    console.print(f"\n[bold]Done.[/bold] Sent: {sent}, Failed: {failed}")
```

- [ ] **Step 2: Verify help output**

```bash
cd ~/src/buttondown-cli-python
.venv/bin/bd send --help
```

Expected: Shows email_id argument and --new-only, --to, --dry-run options.

- [ ] **Step 3: Commit**

```bash
git add src/bd/cli.py
git commit -m "Add send command with --new-only and --to options"
```

---

## Chunk 4: Polish & Ship

### Task 6: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write README**

```markdown
# bd — Buttondown CLI

A command-line interface for [Buttondown](https://buttondown.com) newsletter administration.

## Install

```bash
pip install -e .
```

## Configuration

`bd` resolves credentials with precedence: CLI flags > environment variables > config file.

### Environment variables

```bash
export BD_API_KEY="your-api-key"
export BD_NEWSLETTER="optional-newsletter-id"  # for multi-newsletter accounts
```

### Config file

`~/.config/bd/config.toml`:

```toml
[default]
api_key = "your-api-key"

[myproject]
api_key = "different-key"
newsletter = "newsletter-id"
```

Select a profile with `--profile`:

```bash
bd --profile myproject emails
```

## Commands

### List emails

```bash
bd emails
bd emails --status sent
bd emails --limit 5
```

### List subscribers

```bash
bd subscribers
bd subscribers --limit 10
bd subscribers --oldest
```

### Send to new subscribers

Send a previously published email to subscribers who haven't received it:

```bash
bd send <email_id> --new-only --dry-run  # preview first
bd send <email_id> --new-only            # send with confirmation
```

### Send to a specific subscriber

```bash
bd send <email_id> --to user@example.com
```
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "Add README with install, config, and usage docs"
```

### Task 7: Final verification & push

- [ ] **Step 1: Run full test suite**

```bash
cd ~/src/buttondown-cli-python
.venv/bin/pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 2: Verify CLI end-to-end (with real API key if available)**

```bash
bd --help
bd emails --help
bd subscribers --help
bd send --help
```

- [ ] **Step 3: Push to GitHub**

```bash
cd ~/src/buttondown-cli-python
git push origin main
```
