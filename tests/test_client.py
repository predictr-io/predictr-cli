"""Tests for the HTTP client: auth headers, retry behaviour, error mapping."""

from __future__ import annotations

import httpx
import pytest
import respx

from pebbles.client import APIError, Client
from pebbles.config import Config


def _config(**overrides) -> Config:
    """Build a Config with sensible defaults for tests."""
    base = dict(
        api_url="https://api.example",
        org_name="acme",
        api_key="secret",
        bearer_token=None,
        output_format="json",
        verbose=False,
        quiet=True,
        max_retries=2,
        no_retry=False,
    )
    base.update(overrides)
    return Config(**base)


@respx.mock
def test_get_sends_api_key_header_and_returns_json():
    route = respx.get("https://api.example/meta").mock(
        return_value=httpx.Response(200, json={"version": "1.2.3"})
    )
    with Client(_config()) as client:
        result = client.get("/meta")
    assert result == {"version": "1.2.3"}
    assert route.calls.last.request.headers["x-api-key"] == "secret"


@respx.mock
def test_bearer_token_takes_precedence():
    route = respx.get("https://api.example/meta").mock(
        return_value=httpx.Response(200, json={})
    )
    with Client(_config(bearer_token="jwt", api_key="ignored")) as client:
        client.get("/meta")
    headers = route.calls.last.request.headers
    assert headers["authorization"] == "Bearer jwt"
    assert "x-api-key" not in headers


@respx.mock
def test_4xx_raises_apierror_without_retry():
    route = respx.get("https://api.example/meta").mock(
        return_value=httpx.Response(400, json={"message": "bad input"})
    )
    with Client(_config()) as client:
        with pytest.raises(APIError) as info:
            client.get("/meta")
    assert info.value.status_code == 400
    assert "bad input" in str(info.value)
    assert route.call_count == 1  # not retried


@respx.mock
def test_5xx_retries_then_succeeds():
    responses = [
        httpx.Response(500, text="boom"),
        httpx.Response(500, text="boom"),
        httpx.Response(200, json={"ok": True}),
    ]
    route = respx.get("https://api.example/meta").mock(side_effect=responses)
    with Client(_config(max_retries=2)) as client:
        result = client.get("/meta")
    assert result == {"ok": True}
    assert route.call_count == 3


@respx.mock
def test_5xx_retries_exhausted_raises_apierror():
    route = respx.get("https://api.example/meta").mock(
        return_value=httpx.Response(503, text="overloaded")
    )
    with Client(_config(max_retries=1)) as client:
        with pytest.raises(APIError) as info:
            client.get("/meta")
    assert info.value.status_code == 0  # network/retry layer error
    assert "retries exhausted" in str(info.value)
    assert route.call_count == 2  # initial + 1 retry


@respx.mock
def test_no_retry_flag_disables_retries():
    route = respx.get("https://api.example/meta").mock(
        return_value=httpx.Response(503, text="overloaded")
    )
    with Client(_config(no_retry=True)) as client:
        with pytest.raises(APIError):
            client.get("/meta")
    assert route.call_count == 1


@respx.mock
def test_204_returns_none():
    respx.delete("https://api.example/acme/connections/abc").mock(
        return_value=httpx.Response(204)
    )
    with Client(_config()) as client:
        result = client.delete("/acme/connections/abc")
    assert result is None


@respx.mock
def test_post_sends_json_body():
    route = respx.post("https://api.example/acme/connections").mock(
        return_value=httpx.Response(200, json={"id": "new"})
    )
    with Client(_config()) as client:
        result = client.post("/acme/connections", json={"name": "my-conn"})
    assert result == {"id": "new"}
    import json
    sent = json.loads(route.calls.last.request.content.decode())
    assert sent == {"name": "my-conn"}


@respx.mock
def test_query_params_passed_through():
    route = respx.get("https://api.example/acme/connections/abc/columns").mock(
        return_value=httpx.Response(200, json=[])
    )
    with Client(_config()) as client:
        client.get("/acme/connections/abc/columns", params={"table": "orders"})
    assert route.calls.last.request.url.params["table"] == "orders"


@respx.mock
def test_paginate_follows_next_page_token():
    """paginate() should chain pages until x-next-page is absent."""
    responses = [
        httpx.Response(200, json=[{"id": 1}, {"id": 2}], headers={"x-next-page": "p2"}),
        httpx.Response(200, json=[{"id": 3}], headers={"x-next-page": "p3"}),
        httpx.Response(200, json=[{"id": 4}]),  # no header → terminate
    ]
    route = respx.get("https://api.example/acme/datasets").mock(side_effect=responses)
    with Client(_config()) as client:
        items = list(client.paginate("/acme/datasets"))
    assert items == [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}]
    assert route.call_count == 3
    # Page-token header sent on follow-up requests but not the first.
    assert "x-page-token" not in route.calls[0].request.headers
    assert route.calls[1].request.headers["x-page-token"] == "p2"
    assert route.calls[2].request.headers["x-page-token"] == "p3"


@respx.mock
def test_get_page_returns_body_and_token():
    respx.get("https://api.example/acme/datasets").mock(
        return_value=httpx.Response(
            200, json=[{"id": 1}], headers={"x-next-page": "abc"}
        )
    )
    with Client(_config()) as client:
        body, token = client.get_page("/acme/datasets")
    assert body == [{"id": 1}]
    assert token == "abc"


@respx.mock
def test_get_page_passes_page_token_header():
    route = respx.get("https://api.example/acme/datasets").mock(
        return_value=httpx.Response(200, json=[])
    )
    with Client(_config()) as client:
        client.get_page("/acme/datasets", page_token="abc")
    assert route.calls.last.request.headers["x-page-token"] == "abc"
