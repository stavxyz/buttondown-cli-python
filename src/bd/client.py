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
