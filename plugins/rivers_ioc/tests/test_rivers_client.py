from __future__ import annotations

import httpx
import pytest

from rivers_client import RiversAPIError, RiversClient, normalize_ip


def client(handler, token: str = "top-secret-token") -> RiversClient:
    return RiversClient(
        token, client=httpx.Client(transport=httpx.MockTransport(handler))
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [("8.8.8.8", "8.8.8.8"), ("2001:0db8::1", "2001:db8::1")],
)
def test_normalize_ip(value, expected):
    assert normalize_ip(value) == expected


@pytest.mark.parametrize("value", [None, "", "example.com", "999.1.1.1"])
def test_rejects_invalid_ip(value):
    with pytest.raises(RiversAPIError, match="valid|required"):
        normalize_ip(value)


def test_success_returns_structured_payload_and_sends_token():
    def handler(request: httpx.Request):
        assert request.url.params["ip"] == "8.8.8.8"
        assert request.headers["X-CA-Token"] == "top-secret-token"
        return httpx.Response(200, json={"data": {"risk": "low"}})

    assert client(handler).query_ip("8.8.8.8") == {"data": {"risk": "low"}}


@pytest.mark.parametrize(
    ("status", "message"),
    [
        (401, "invalid"),
        (403, "invalid"),
        (429, "rate limit"),
        (500, "unavailable"),
        (400, "HTTP 400"),
    ],
)
def test_http_errors_are_classified_and_do_not_leak_token(status, message):
    api = client(
        lambda request: httpx.Response(status, text="top-secret-token upstream detail")
    )
    with pytest.raises(RiversAPIError, match=message) as caught:
        api.query_ip("8.8.8.8")
    assert "top-secret-token" not in str(caught.value)
    assert "upstream detail" not in str(caught.value)


def test_timeout_is_safe():
    def handler(request):
        raise httpx.ReadTimeout("top-secret-token", request=request)

    with pytest.raises(RiversAPIError, match="timed out") as caught:
        client(handler).query_ip("8.8.8.8")
    assert "top-secret-token" not in str(caught.value)


def test_bad_json_is_safe():
    api = client(lambda request: httpx.Response(200, text="not-json top-secret-token"))
    with pytest.raises(RiversAPIError, match="invalid JSON") as caught:
        api.query_ip("8.8.8.8")
    assert "top-secret-token" not in str(caught.value)


def test_unexpected_json_shape_is_rejected():
    api = client(lambda request: httpx.Response(200, json=["unexpected"]))
    with pytest.raises(RiversAPIError, match="unexpected"):
        api.query_ip("8.8.8.8")


def test_empty_token_is_rejected():
    with pytest.raises(RiversAPIError, match="token"):
        RiversClient(" ")
