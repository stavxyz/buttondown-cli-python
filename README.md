# bd — Buttondown CLI

A command-line interface for [Buttondown](https://buttondown.com) newsletter administration.

The core feature: send a previously published email to new subscribers who missed it, without duplicating to existing recipients.

## Requirements

- Python 3.11+
- A [Buttondown](https://buttondown.com) account with an API key ([find yours here](https://buttondown.com/requests))

## Install

```bash
git clone https://github.com/stavxyz/buttondown-cli-python.git
cd buttondown-cli-python
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify it works:

```bash
bd -h
```

## Configuration

`bd` resolves credentials with strict precedence: **CLI flags > environment variables > config file**.

### Option 1: Environment variables

The simplest way to get started:

```bash
export BD_API_KEY="your-api-key"
```

For multi-newsletter accounts:

```bash
export BD_NEWSLETTER="newsletter-id"
```

### Option 2: Config file

For managing multiple accounts or newsletters, create `~/.config/bd/config.toml`:

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

### Option 3: CLI flags

Override anything on the command line:

```bash
bd --api-key "your-key" --newsletter "nl-id" emails
```

## Commands

### `bd emails` — List emails

```bash
bd emails                  # list all emails
bd emails --status sent    # only published emails
bd emails --status draft   # only drafts
bd emails --limit 5        # limit results
```

Output includes the full email ID, which you'll need for the `send` command.

### `bd subscribers` — List subscribers

```bash
bd subscribers             # all active subscribers, newest first
bd subscribers --limit 10  # limit results
bd subscribers --oldest    # oldest first
```

### `bd send` — Send emails to subscribers

**Send to new subscribers only** (the killer feature):

```bash
# Preview who would receive it
bd send <email_id> --new-only --dry-run

# Send with confirmation prompt
bd send <email_id> --new-only
```

This works by diffing the current subscriber list against Buttondown's delivery events (delivered, attempted, and bounced) to find subscribers who haven't received the email yet. Buttondown's own `EMAIL_ALREADY_SENT` guard provides an additional safety net against duplicates.

**Send to a specific subscriber:**

```bash
bd send <email_id> --to user@example.com
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--new-only` | Send only to subscribers who haven't received the email |
| `--to EMAIL` | Send to a specific subscriber (mutually exclusive with `--new-only`) |
| `--dry-run` | Preview what would be sent without actually sending |

## How `--new-only` works

1. Fetches the email and confirms it's published (status: `sent`)
2. Queries Buttondown's events API for all `delivered`, `attempted`, and `bounced` events for that email
3. Fetches all active subscribers
4. Computes the diff: active subscribers not in any event list
5. Prompts for confirmation, then sends to each new subscriber
6. Reports results (sent count, failed count)

## API

`bd` uses the [Buttondown REST API v1](https://docs.buttondown.com/api-introduction). The [OpenAPI spec](https://github.com/buttondown/openapi) is available for reference.

## License

MIT
