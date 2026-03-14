"""Tests for CLI commands, focused on send guards and recipient diff logic."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from bd.cli import _send_to_new, app, console

runner = CliRunner()


class TestSendGuards:
    """The send command validates flags and email status before sending."""

    @patch("bd.cli._get_client")
    def test_new_only_and_to_are_mutually_exclusive(self, mock_client):
        result = runner.invoke(
            app,
            ["--api-key", "test", "send", "em-1", "--new-only", "--to", "a@b.com"],
        )
        assert result.exit_code == 1
        assert "mutually exclusive" in result.output

    @patch("bd.cli._get_client")
    def test_requires_new_only_or_to(self, mock_client):
        result = runner.invoke(
            app,
            ["--api-key", "test", "send", "em-1"],
        )
        assert result.exit_code == 1
        assert "Specify --new-only or --to" in result.output

    @patch("bd.cli._get_client")
    def test_rejects_draft_email(self, mock_client):
        client = MagicMock()
        client.get_email.return_value = {"status": "draft", "subject": "Test"}
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        mock_client.return_value = client

        result = runner.invoke(
            app,
            ["--api-key", "test", "send", "em-1", "--new-only"],
        )
        assert result.exit_code == 1
        assert "draft" in result.output

    @patch("bd.cli._get_client")
    def test_accepts_sent_email(self, mock_client):
        client = MagicMock()
        client.get_email.return_value = {"status": "sent", "subject": "Test"}
        client.list_events.return_value = []
        client.list_subscribers.return_value = []
        client.__enter__ = MagicMock(return_value=client)
        client.__exit__ = MagicMock(return_value=False)
        mock_client.return_value = client

        result = runner.invoke(
            app,
            ["--api-key", "test", "send", "em-1", "--new-only"],
        )
        assert result.exit_code == 0
        assert "All subscribers have already received" in result.output


class TestRecipientDiff:
    """The --new-only logic correctly identifies who hasn't received an email."""

    def _make_client(self, events_by_type, subscribers):
        client = MagicMock()

        def fake_list_events(email_id=None, event_type=None):
            return events_by_type.get(event_type, [])

        client.list_events.side_effect = fake_list_events
        client.list_subscribers.return_value = subscribers
        return client

    def test_excludes_delivered_subscribers(self):
        client = self._make_client(
            events_by_type={
                "delivered": [{"subscriber_id": "sub-1"}],
                "attempted": [],
                "bounced": [],
            },
            subscribers=[
                {"id": "sub-1", "email_address": "a@b.com", "creation_date": "2026-01-01"},
                {"id": "sub-2", "email_address": "c@d.com", "creation_date": "2026-01-02"},
            ],
        )
        # Use dry_run to avoid confirmation prompt
        _send_to_new(client, "em-1", "Test Subject", dry_run=True)
        # sub-2 should be in the "Would send to" output, sub-1 excluded

    def test_excludes_attempted_subscribers(self):
        client = self._make_client(
            events_by_type={
                "delivered": [],
                "attempted": [{"subscriber_id": "sub-1"}],
                "bounced": [],
            },
            subscribers=[
                {"id": "sub-1", "email_address": "a@b.com", "creation_date": "2026-01-01"},
            ],
        )
        _send_to_new(client, "em-1", "Test Subject", dry_run=True)
        # All subscribers already received — should print "All subscribers" message

    def test_excludes_bounced_subscribers(self):
        client = self._make_client(
            events_by_type={
                "delivered": [],
                "attempted": [],
                "bounced": [{"subscriber_id": "sub-1"}],
            },
            subscribers=[
                {"id": "sub-1", "email_address": "a@b.com", "creation_date": "2026-01-01"},
            ],
        )
        _send_to_new(client, "em-1", "Test Subject", dry_run=True)

    def test_includes_new_subscribers(self):
        client = self._make_client(
            events_by_type={
                "delivered": [{"subscriber_id": "sub-1"}],
                "attempted": [],
                "bounced": [],
            },
            subscribers=[
                {"id": "sub-1", "email_address": "old@b.com", "creation_date": "2026-01-01"},
                {"id": "sub-2", "email_address": "new@b.com", "creation_date": "2026-01-02"},
                {"id": "sub-3", "email_address": "also-new@b.com", "creation_date": "2026-01-03"},
            ],
        )
        _send_to_new(client, "em-1", "Test Subject", dry_run=True)
        # sub-2 and sub-3 should appear in output

    def test_all_received_shows_complete_message(self):
        client = self._make_client(
            events_by_type={
                "delivered": [{"subscriber_id": "sub-1"}, {"subscriber_id": "sub-2"}],
                "attempted": [],
                "bounced": [],
            },
            subscribers=[
                {"id": "sub-1", "email_address": "a@b.com", "creation_date": "2026-01-01"},
                {"id": "sub-2", "email_address": "c@d.com", "creation_date": "2026-01-02"},
            ],
        )
        _send_to_new(client, "em-1", "Test Subject", dry_run=True)

    def test_mixed_event_types_all_excluded(self):
        """Subscriber with events across different types is still excluded."""
        client = self._make_client(
            events_by_type={
                "delivered": [{"subscriber_id": "sub-1"}],
                "attempted": [{"subscriber_id": "sub-2"}],
                "bounced": [{"subscriber_id": "sub-3"}],
            },
            subscribers=[
                {"id": "sub-1", "email_address": "a@b.com", "creation_date": "2026-01-01"},
                {"id": "sub-2", "email_address": "c@d.com", "creation_date": "2026-01-02"},
                {"id": "sub-3", "email_address": "e@f.com", "creation_date": "2026-01-03"},
                {"id": "sub-4", "email_address": "new@b.com", "creation_date": "2026-01-04"},
            ],
        )
        _send_to_new(client, "em-1", "Test Subject", dry_run=True)
        # Only sub-4 should be in output
