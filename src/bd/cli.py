from __future__ import annotations

import functools
import sys
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from bd.client import ButtondownClient
from bd.config import Config, ConfigError, resolve_config

app = typer.Typer(
    name="bd",
    help="Buttondown newsletter CLI.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()


# --- Error handling ---


def _format_http_error(e: httpx.HTTPStatusError) -> str:
    """Extract a user-friendly message from an HTTP error response."""
    try:
        body = e.response.json()
        detail = body.get("detail", e.response.text)
    except Exception:
        detail = e.response.text
    return f"{e.response.status_code}: {detail}"


def handle_api_errors(func):
    """Decorator that catches HTTP and config errors, prints user-friendly messages."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConfigError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status == 401:
                console.print("[red]Error:[/red] Authentication failed. Check your API key (--api-key or BD_API_KEY).")
            elif status == 404:
                console.print("[red]Error:[/red] Resource not found. Check the ID you provided.")
            elif status == 429:
                console.print("[red]Error:[/red] Rate limited by Buttondown API. Wait and try again.")
            else:
                console.print(f"[red]Error:[/red] API returned {_format_http_error(e)}")
            raise typer.Exit(1)
        except httpx.ConnectError:
            console.print("[red]Error:[/red] Could not connect to api.buttondown.com. Check your network.")
            raise typer.Exit(1)
        except httpx.TimeoutException:
            console.print("[red]Error:[/red] Request to Buttondown API timed out. Try again.")
            raise typer.Exit(1)
    return wrapper


# --- Config & client helpers ---


def _get_config(ctx: typer.Context) -> Config:
    return resolve_config(
        api_key=ctx.obj.get("api_key"),
        newsletter=ctx.obj.get("newsletter"),
        profile=ctx.obj.get("profile", "default"),
    )


def _get_client(ctx: typer.Context) -> ButtondownClient:
    cfg = _get_config(ctx)
    return ButtondownClient(api_key=cfg.api_key, newsletter=cfg.newsletter)


# --- Commands ---


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
@handle_api_errors
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
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Subject", style="bold")
    table.add_column("Date")
    table.add_column("Status")
    table.add_column("Deliveries", justify="right")

    for email in results:
        analytics = email.get("analytics") or {}
        table.add_row(
            email["id"],
            email.get("subject", "(no subject)"),
            (email.get("publish_date") or email.get("creation_date", ""))[:10],
            email.get("status", ""),
            str(analytics.get("deliveries", "")),
        )

    console.print(table)


@app.command()
@handle_api_errors
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
        tags = ", ".join(
            t.get("id", str(t)) if isinstance(t, dict) else str(t)
            for t in sub.get("tags", [])
        )
        table.add_row(
            sub["email_address"],
            sub.get("creation_date", "")[:10],
            sub.get("source", ""),
            tags,
        )

    console.print(table)


@app.command()
@handle_api_errors
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
    except httpx.HTTPStatusError as e:
        console.print(f"[red]Failed[/red] to send to {to}: {_format_http_error(e)}")
        raise typer.Exit(1)


def _send_to_new(
    client: ButtondownClient, email_id: str, subject: str, dry_run: bool
):
    """Send a published email to subscribers who haven't received it."""
    console.print(f"Checking recipients for '{subject}'...")

    # Get subscribers who already had a send attempted for this email.
    # Check delivered, attempted, and bounced to match Buttondown's
    # EMAIL_ALREADY_SENT guard which prevents re-sending after any attempt.
    already_received: set[str] = set()
    for event_type in ("delivered", "attempted", "bounced"):
        events = client.list_events(email_id=email_id, event_type=event_type)
        already_received.update(e["subscriber_id"] for e in events)

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
    with console.status("Sending...") as spinner:
        for s in new_subscribers:
            try:
                client.send_email_to_subscriber(s["id"], email_id)
                sent += 1
                spinner.update(f"Sending... ({sent}/{len(new_subscribers)})")
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (401, 403):
                    console.print(f"\n[red]Authentication error ({e.response.status_code}). Aborting.[/red]")
                    break
                if e.response.status_code == 429:
                    console.print(f"\n[red]Rate limited. Sent {sent} so far. Try again later.[/red]")
                    break
                failed += 1
                console.print(f"  [red]Failed[/red] {s['email_address']}: {_format_http_error(e)}")

    console.print(f"\n[bold]Done.[/bold] Sent: {sent}, Failed: {failed}")
