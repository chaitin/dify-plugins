from types import SimpleNamespace

import pytest
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

import provider.rivers_ioc as provider_module
import tools.rivers_ioc as tool_module
from rivers_client import RiversAPIError


def test_provider_performs_real_safe_query(monkeypatch):
    calls = []

    class FakeClient:
        def __init__(self, token):
            calls.append(("token", token))

        def query_ip(self, ip):
            calls.append(("ip", ip))

    monkeypatch.setattr(provider_module, "RiversClient", FakeClient)
    provider_module.RiversIOCProvider._validate_credentials(object(), {"api_key": "secret"})
    assert calls == [("token", "secret"), ("ip", "1.1.1.1")]


def test_provider_wraps_only_safe_client_error(monkeypatch):
    class FakeClient:
        def __init__(self, token):
            pass

        def query_ip(self, ip):
            raise RiversAPIError("safe authorization error")

    monkeypatch.setattr(provider_module, "RiversClient", FakeClient)
    with pytest.raises(ToolProviderCredentialValidationError, match="safe authorization error"):
        provider_module.RiversIOCProvider._validate_credentials(object(), {"api_key": "secret"})


def test_tool_emits_structured_json(monkeypatch):
    class FakeClient:
        def __init__(self, token):
            assert token == "secret"

        def query_ip(self, ip):
            assert ip == "8.8.8.8"
            return {"risk": "low"}

    class FakeTool:
        runtime = SimpleNamespace(credentials={"api_key": "secret"})

        def create_json_message(self, value):
            return ("json", value)

        def create_text_message(self, value):
            return ("text", value)

    monkeypatch.setattr(tool_module, "RiversClient", FakeClient)
    messages = list(tool_module.RiversIOCTool._invoke(FakeTool(), {"ip_address": "8.8.8.8"}))
    assert messages == [("json", {"risk": "low"})]


def test_tool_emits_safe_error(monkeypatch):
    class FakeClient:
        def __init__(self, token):
            pass

        def query_ip(self, ip):
            raise RiversAPIError("request timed out")

    class FakeTool:
        runtime = SimpleNamespace(credentials={"api_key": "secret"})

        def create_text_message(self, value):
            return value

    monkeypatch.setattr(tool_module, "RiversClient", FakeClient)
    messages = list(tool_module.RiversIOCTool._invoke(FakeTool(), {"ip_address": "8.8.8.8"}))
    assert messages == ["Rivers IOC query failed: request timed out"]
