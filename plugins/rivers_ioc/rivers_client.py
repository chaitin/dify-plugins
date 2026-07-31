"""HTTP client for the Rivers threat-intelligence API."""

from __future__ import annotations

import ipaddress
from typing import Any

import httpx

API_URL = "https://intelligence.rivers.chaitin.cn/api/v1/ip_info"
DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=5.0, read=15.0, write=5.0, pool=5.0)


class RiversAPIError(RuntimeError):
    """A safe, user-facing Rivers API error."""


def normalize_ip(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RiversAPIError("An IP address is required.")
    try:
        return str(ipaddress.ip_address(value.strip()))
    except ValueError as exc:
        raise RiversAPIError("The supplied value is not a valid IPv4 or IPv6 address.") from exc


class RiversClient:
    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.Client | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise RiversAPIError("A Rivers access token is required.")
        self._api_key = api_key.strip()
        self._client = client
        self._timeout = timeout

    def query_ip(self, ip_address: Any) -> dict[str, Any]:
        normalized_ip = normalize_ip(ip_address)
        headers = {
            "Accept": "application/json",
            "User-Agent": "chaitin-dify-rivers-ioc/0.2.0",
            "X-CA-Token": self._api_key,
        }
        owns_client = self._client is None
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            response = client.get(API_URL, params={"ip": normalized_ip}, headers=headers)
        except httpx.TimeoutException as exc:
            raise RiversAPIError("The Rivers API request timed out. Please try again.") from exc
        except httpx.RequestError as exc:
            raise RiversAPIError("The Rivers API could not be reached. Please try again.") from exc
        finally:
            if owns_client:
                client.close()

        if response.status_code in (401, 403):
            raise RiversAPIError("The Rivers access token is invalid or lacks permission.")
        if response.status_code == 429:
            raise RiversAPIError("The Rivers API rate limit was exceeded. Please try again later.")
        if response.status_code >= 500:
            raise RiversAPIError(
                "The Rivers API is temporarily unavailable. Please try again later."
            )
        if response.is_error:
            raise RiversAPIError(
                f"The Rivers API rejected the request (HTTP {response.status_code})."
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise RiversAPIError("The Rivers API returned an invalid JSON response.") from exc
        if not isinstance(payload, dict):
            raise RiversAPIError("The Rivers API returned an unexpected response format.")
        return payload
