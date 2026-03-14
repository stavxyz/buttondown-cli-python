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
