import importlib.util
import json
import sys
from pathlib import Path

import pytest
import requests
import responses

OCTOBUS_CLIENT_PATH = Path(__file__).resolve().parents[1] / "client" / "octobus.py"
spec = importlib.util.spec_from_file_location("octobus_client_under_test", OCTOBUS_CLIENT_PATH)
assert spec is not None
octobus_client = importlib.util.module_from_spec(spec)
sys.modules["octobus_client_under_test"] = octobus_client
assert spec.loader is not None
spec.loader.exec_module(octobus_client)

OctoBusClient = octobus_client.OctoBusClient
OctoBusConfig = octobus_client.OctoBusConfig
OctoBusError = octobus_client.OctoBusError
parse_arguments_json = octobus_client.parse_arguments_json
parse_capability_selection = octobus_client.parse_capability_selection


BASE_URL = "http://octobus.local"


def config() -> OctoBusConfig:
    return OctoBusConfig(
        url=BASE_URL,
        admin_token="admin-token",
        capset_token="default-capset-token",
        capset_tokens={"security": "security-token"},
        headers={"X-Test": "yes"},
    )


def test_config_parses_separate_admin_and_capset_tokens():
    parsed = OctoBusConfig.from_mapping(
        {
            "octobus_url": BASE_URL,
            "octobus_admin_token": "admin",
            "octobus_capset_token": "default",
            "octobus_capset_tokens_json": '{"security":"security-secret"}',
        }
    )

    assert parsed.admin_token == "admin"
    assert parsed.capset_token == "default"
    assert parsed.capset_tokens == {"security": "security-secret"}


@pytest.mark.parametrize(
    "url",
    ["octobus.local", "ftp://octobus.local", "http://user:secret@octobus.local", "https://x?q=1"],
)
def test_config_rejects_unsafe_urls(url):
    with pytest.raises(OctoBusError):
        OctoBusConfig(url=url).normalized_url()


def test_config_rejects_excessive_timeout():
    with pytest.raises(OctoBusError, match="between 1 and"):
        octobus_client.parse_timeout("3601", 60)


@responses.activate
def test_status_uses_configured_url_and_auth_headers():
    responses.add(responses.GET, f"{BASE_URL}/admin/v1/status", json={"ok": True})

    assert OctoBusClient(config()).status() == {"ok": True}

    request = responses.calls[0].request
    assert request.headers["Authorization"] == "Bearer admin-token"
    assert request.headers["X-Test"] == "yes"


@responses.activate
def test_list_capsets_accepts_wrapped_response():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/capsets",
        json={
            "capsets": [
                {"id": "security", "name": "Security", "description": "Security ops"},
                {"capset_id": "ops"},
            ]
        },
    )

    capsets = OctoBusClient(config()).list_capsets()

    assert [capset.id for capset in capsets] == ["security", "ops"]
    assert capsets[0].label == "Security (security)"


@responses.activate
def test_list_capsets_accepts_go_style_fields():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/capsets",
        json={
            "capsets": [
                {"ID": "internal-tools", "Name": "Internal Tools", "Description": "Debug tools"}
            ]
        },
    )

    capsets = OctoBusClient(config()).list_capsets()

    assert capsets[0].id == "internal-tools"
    assert capsets[0].name == "Internal Tools"
    assert capsets[0].description == "Debug tools"


@responses.activate
def test_list_capsets_accepts_null_when_no_capsets_exist():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/capsets",
        json={"capsets": None},
    )

    assert OctoBusClient(config()).list_capsets() == []


@responses.activate
def test_list_capsets_does_not_fall_back_to_agent_compose():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/capsets",
        json={"err": "Unknown", "msg": "Not Found, code=404, message=Not Found"},
        status=404,
    )
    with pytest.raises(OctoBusError, match="HTTP 404"):
        OctoBusClient(config()).list_capsets()

    assert len(responses.calls) == 1


@responses.activate
def test_http_error_does_not_reflect_remote_body():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/capsets",
        body="secret upstream diagnostic",
        status=500,
    )
    with pytest.raises(OctoBusError, match="HTTP 500") as caught:
        OctoBusClient(config()).list_capsets()
    assert "secret upstream diagnostic" not in str(caught.value)


@responses.activate
def test_timeout_is_wrapped_as_safe_octobus_error():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/status",
        body=requests.exceptions.ConnectTimeout("secret URL detail"),
    )
    with pytest.raises(OctoBusError, match="timed out") as caught:
        OctoBusClient(config()).status()
    assert "secret URL detail" not in str(caught.value)


@responses.activate
def test_list_services_accepts_wrapped_response():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/services",
        json={"services": [{"id": "jira", "name": "Jira"}, {"id": "devboard"}]},
    )

    services = OctoBusClient(config()).list_services()

    assert [service["id"] for service in services] == ["jira", "devboard"]


@responses.activate
def test_list_services_accepts_null_when_no_services_exist():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/services",
        json={"services": None},
    )

    assert OctoBusClient(config()).list_services() == []


@responses.activate
def test_list_instances_accepts_wrapped_response():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/instances",
        json={
            "instances": [
                {"id": "jira", "service_id": "jira", "status": "running"},
                {"id": "devboard", "service_id": "devboard", "status": "running"},
            ]
        },
    )

    instances = OctoBusClient(config()).list_instances()

    assert [instance["id"] for instance in instances] == ["jira", "devboard"]


@responses.activate
def test_list_instances_accepts_null_when_no_instances_exist():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/instances",
        json={"instances": None},
    )

    assert OctoBusClient(config()).list_instances() == []


@responses.activate
def test_catalog_parses_normalized_methods():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/catalog/security",
        json={
            "capset_id": "security",
            "mcp": [
                {
                    "service_id": "das",
                    "method_full_name": "DAS.BlockIP",
                    "tool_name": "das_block_ip",
                }
            ],
        },
    )
    responses.add(
        responses.POST,
        f"{BASE_URL}/capsets/security/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "response-id",
            "result": {
                "tools": [
                    {
                        "name": "das_block_ip",
                        "description": "Block an IP address",
                        "inputSchema": {"type": "object"},
                    }
                ]
            },
        },
    )

    capabilities = OctoBusClient(config()).list_capabilities("security")

    assert len(capabilities) == 1
    assert capabilities[0].tool_name == "das_block_ip"
    assert capabilities[0].method == "DAS.BlockIP"
    assert capabilities[0].description == "Block an IP address"
    assert capabilities[0].input_schema == {"type": "object"}
    assert responses.calls[0].request.url.endswith("/admin/v1/catalog/security?mcp=true")
    assert responses.calls[0].request.headers["Authorization"] == "Bearer admin-token"
    assert responses.calls[1].request.headers["Authorization"] == "Bearer security-token"
    assert json.loads(capabilities[0].selection_value()) == {
        "capset_id": "security",
        "tool_name": "das_block_ip",
    }


@responses.activate
def test_list_mcp_tools_uses_default_capset_token():
    responses.add(
        responses.POST,
        f"{BASE_URL}/capsets/ops/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "response-id",
            "result": {"tools": [{"name": "restart"}]},
        },
    )

    capabilities = OctoBusClient(config()).list_mcp_tools("ops")

    assert capabilities[0].tool_name == "restart"
    assert responses.calls[0].request.headers["Authorization"] == "Bearer default-capset-token"


@responses.activate
def test_search_capabilities_searches_all_capsets():
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/capsets",
        json={"capsets": [{"id": "security"}, {"id": "ops"}]},
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/catalog/security",
        json={"mcp": [{"tool_name": "block_ip", "service_id": "security"}]},
    )
    responses.add(
        responses.POST,
        f"{BASE_URL}/capsets/security/mcp",
        json={"result": {"tools": [{"name": "block_ip", "description": "Block IP"}]}},
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/admin/v1/catalog/ops",
        json={"mcp": [{"tool_name": "restart", "service_id": "ops"}]},
    )
    responses.add(
        responses.POST,
        f"{BASE_URL}/capsets/ops/mcp",
        json={"result": {"tools": [{"name": "restart", "description": "Restart"}]}},
    )

    capabilities = OctoBusClient(config()).search_capabilities("block")

    assert [capability.tool_name for capability in capabilities] == ["block_ip"]


@responses.activate
def test_call_capability_posts_mcp_tools_call():
    responses.add(
        responses.POST,
        f"{BASE_URL}/capsets/security/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "dify-octobus-call",
            "result": {"structuredContent": {"ok": True}},
        },
    )

    result = OctoBusClient(config()).call_capability(
        capset_id="security",
        tool_name="block_ip",
        arguments={"ip": "1.2.3.4"},
    )

    assert result == {"structuredContent": {"ok": True}}
    request_body = json.loads(responses.calls[0].request.body)
    assert request_body["jsonrpc"] == "2.0"
    assert request_body["id"].startswith("dify-octobus-")
    assert request_body["method"] == "tools/call"
    assert request_body["params"] == {
        "name": "block_ip",
        "arguments": {"ip": "1.2.3.4"},
    }
    assert responses.calls[0].request.headers["Authorization"] == "Bearer security-token"


@responses.activate
def test_call_capability_raises_mcp_error():
    responses.add(
        responses.POST,
        f"{BASE_URL}/capsets/security/mcp",
        json={"jsonrpc": "2.0", "id": "dify-octobus-call", "error": {"message": "denied"}},
    )

    with pytest.raises(OctoBusError, match="denied"):
        OctoBusClient(config()).call_capability(
            capset_id="security",
            tool_name="block_ip",
            arguments={},
        )


@responses.activate
def test_call_capability_raises_tool_level_mcp_error():
    responses.add(
        responses.POST,
        f"{BASE_URL}/capsets/security/mcp",
        json={
            "result": {
                "isError": True,
                "content": [{"type": "text", "text": "upstream denied"}],
            }
        },
    )

    with pytest.raises(OctoBusError, match="upstream denied"):
        OctoBusClient(config()).call_capability(
            capset_id="security",
            tool_name="block_ip",
            arguments={},
        )


def test_parse_arguments_json_accepts_object_only():
    assert parse_arguments_json('{"ip":"1.2.3.4"}') == {"ip": "1.2.3.4"}

    with pytest.raises(OctoBusError, match="JSON object"):
        parse_arguments_json("[1, 2]")


def test_parse_capability_selection_accepts_json_and_path():
    assert parse_capability_selection('{"capset_id":"security","tool_name":"block_ip"}') == (
        "security",
        "block_ip",
    )
    assert parse_capability_selection("security/block_ip") == ("security", "block_ip")
    assert parse_capability_selection("block_ip") == ("", "block_ip")
