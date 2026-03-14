"""Tests for ButtondownClient, focused on pagination logic."""

import pytest
from pytest_httpx import HTTPXMock

from bd.client import BASE_URL, ButtondownClient


@pytest.fixture()
def client():
    with ButtondownClient(api_key="test-key") as c:
        yield c


class TestPagination:
    """Pagination follows next URLs and respects limits."""

    def test_single_page(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE_URL}/emails",
            json={"results": [{"id": "1"}, {"id": "2"}], "next": None, "count": 2},
        )
        results = client._paginate("/emails")
        assert results == [{"id": "1"}, {"id": "2"}]

    def test_multi_page(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE_URL}/emails",
            json={
                "results": [{"id": "1"}],
                "next": f"{BASE_URL}/emails?page=2",
                "count": 2,
            },
        )
        httpx_mock.add_response(
            url=f"{BASE_URL}/emails?page=2",
            json={"results": [{"id": "2"}], "next": None, "count": 2},
        )
        results = client._paginate("/emails")
        assert results == [{"id": "1"}, {"id": "2"}]

    def test_limit_stops_pagination_early(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE_URL}/emails",
            json={
                "results": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
                "next": f"{BASE_URL}/emails?page=2",
                "count": 6,
            },
        )
        results = client._paginate("/emails", limit=2)
        assert len(results) == 2
        assert results == [{"id": "1"}, {"id": "2"}]

    def test_empty_results(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE_URL}/emails",
            json={"results": [], "next": None, "count": 0},
        )
        results = client._paginate("/emails")
        assert results == []

    def test_next_url_without_page_param_warns_and_stops(
        self, client, httpx_mock: HTTPXMock, capsys
    ):
        httpx_mock.add_response(
            url=f"{BASE_URL}/emails",
            json={
                "results": [{"id": "1"}],
                "next": f"{BASE_URL}/emails?cursor=abc",
                "count": 2,
            },
        )
        results = client._paginate("/emails")
        assert results == [{"id": "1"}]
        assert "Could not parse next page URL" in capsys.readouterr().err


class TestHeaders:
    """Client sets correct auth and newsletter headers."""

    def test_auth_header(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE_URL}/emails/test-id", json={"id": "test-id"})
        with ButtondownClient(api_key="my-secret") as c:
            c.get_email("test-id")
        request = httpx_mock.get_request()
        assert request.headers["authorization"] == "Token my-secret"

    def test_newsletter_header_when_set(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE_URL}/emails/test-id", json={"id": "test-id"})
        with ButtondownClient(api_key="key", newsletter="nl-123") as c:
            c.get_email("test-id")
        request = httpx_mock.get_request()
        assert request.headers["x-buttondown-newsletter"] == "nl-123"

    def test_no_newsletter_header_when_not_set(self, httpx_mock: HTTPXMock):
        httpx_mock.add_response(url=f"{BASE_URL}/emails/test-id", json={"id": "test-id"})
        with ButtondownClient(api_key="key") as c:
            c.get_email("test-id")
        request = httpx_mock.get_request()
        assert "x-buttondown-newsletter" not in request.headers


class TestPostResponse:
    """POST handles empty and non-empty responses."""

    def test_empty_response_returns_empty_dict(self, client, httpx_mock: HTTPXMock):
        httpx_mock.add_response(
            url=f"{BASE_URL}/subscribers/sub-1/emails/em-1",
            content=b"",
            status_code=200,
        )
        result = client.send_email_to_subscriber("sub-1", "em-1")
        assert result == {}
