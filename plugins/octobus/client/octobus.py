import json
import os
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import requests


class OctoBusError(Exception):
    pass


@dataclass(frozen=True)
class OctoBusConfig:
    url: str
    admin_token: str = ""
    capset_token: str = ""
    capset_tokens: dict[str, str] | None = None
    # Deprecated compatibility token. New deployments should use the
    # control-plane and data-plane token fields above.
    token: str = ""
    headers: dict[str, str] | None = None
    timeout_seconds: float = 60

    @classmethod
    def from_env(cls) -> "OctoBusConfig":
        return cls(
            url=os.getenv("OCTOBUS_URL", ""),
            admin_token=os.getenv("OCTOBUS_ADMIN_TOKEN", ""),
            capset_token=os.getenv("OCTOBUS_CAPSET_TOKEN", ""),
            capset_tokens=parse_string_map(
                os.getenv("OCTOBUS_CAPSET_TOKENS_JSON", ""),
                "OCTOBUS_CAPSET_TOKENS_JSON",
            ),
            token=os.getenv("OCTOBUS_TOKEN", ""),
            headers=parse_headers_json(os.getenv("OCTOBUS_HEADERS_JSON", "")),
            timeout_seconds=parse_timeout(os.getenv("OCTOBUS_TIMEOUT_SECONDS", ""), 60),
        )

    @classmethod
    def from_mapping(cls, values: dict[str, Any] | None) -> "OctoBusConfig":
        values = values or {}
        env = cls.from_env()
        return cls(
            url=str(values.get("octobus_url") or env.url),
            admin_token=str(values.get("octobus_admin_token") or env.admin_token),
            capset_token=str(values.get("octobus_capset_token") or env.capset_token),
            capset_tokens=parse_string_map(
                values.get("octobus_capset_tokens_json") or "",
                "octobus_capset_tokens_json",
            )
            or env.capset_tokens,
            token=str(values.get("octobus_token") or env.token),
            headers=parse_headers_json(values.get("octobus_headers_json") or "") or env.headers,
            timeout_seconds=parse_timeout(
                values.get("octobus_timeout_seconds") or "", env.timeout_seconds
            ),
        )

    def normalized_url(self) -> str:
        url = self.url.strip().rstrip("/")
        if not url:
            raise OctoBusError("octobus_url is required")
        return url


@dataclass(frozen=True)
class Capset:
    id: str
    name: str = ""
    description: str = ""
    raw: dict[str, Any] | None = None

    @property
    def label(self) -> str:
        if self.name and self.name != self.id:
            return f"{self.name} ({self.id})"
        return self.id


@dataclass(frozen=True)
class Capability:
    capset_id: str
    tool_name: str
    name: str
    description: str = ""
    service_id: str = ""
    method: str = ""
    protocol: str = ""
    input_schema: dict[str, Any] | None = None
    raw: dict[str, Any] | None = None

    def selection_value(self) -> str:
        return json.dumps(
            {"capset_id": self.capset_id, "tool_name": self.tool_name},
            ensure_ascii=True,
            separators=(",", ":"),
        )

    @property
    def label(self) -> str:
        prefix = f"{self.capset_id}/"
        name = self.tool_name or self.name
        return prefix + name


class OctoBusClient:
    def __init__(self, config: OctoBusConfig | None = None) -> None:
        self.config = config or OctoBusConfig.from_env()

    def status(self) -> dict[str, Any]:
        body = self._get_json("/admin/v1/status", headers=self._admin_headers())
        if isinstance(body, dict) and not is_not_found_body(body):
            return body
        raise OctoBusError("OctoBus returned invalid status response")

    def list_capsets(self) -> list[Capset]:
        body = self._get_json("/admin/v1/capsets", headers=self._admin_headers())
        items = extract_list(body, "capsets", allow_empty_object=True)
        return [parse_capset(item) for item in items]

    def list_services(self) -> list[dict[str, Any]]:
        body = self._get_json("/admin/v1/services", headers=self._admin_headers())
        items = extract_list(body, "services", allow_empty_object=True)
        return [item for item in items if isinstance(item, dict)]

    def list_instances(self) -> list[dict[str, Any]]:
        body = self._get_json("/admin/v1/instances", headers=self._admin_headers())
        items = extract_list(body, "instances", allow_empty_object=True)
        return [item for item in items if isinstance(item, dict)]

    def catalog(self, capset_id: str) -> dict[str, Any]:
        capset_id = capset_id.strip()
        if not capset_id:
            raise OctoBusError("capset_id is required")
        body = self._get_json(
            f"/admin/v1/catalog/{quote(capset_id, safe='')}?mcp=true",
            headers=self._admin_headers(),
        )
        if isinstance(body, dict) and not is_not_found_body(body):
            return body
        raise OctoBusError("OctoBus returned invalid catalog response")

    def list_capabilities(
        self,
        capset_id: str,
        *,
        catalog: dict[str, Any] | None = None,
    ) -> list[Capability]:
        catalog = catalog or self.catalog(capset_id)
        catalog_capabilities = {
            item.tool_name: item
            for item in parse_capabilities(capset_id, catalog)
            if item.tool_name
        }
        capabilities: list[Capability] = []
        for tool in self.list_mcp_tools(capset_id):
            catalog_item = catalog_capabilities.get(tool.tool_name)
            capabilities.append(merge_capability(tool, catalog_item))
        return capabilities

    def list_mcp_tools(self, capset_id: str) -> list[Capability]:
        result = self._mcp_request(capset_id, "tools/list", {})
        tools = result.get("tools")
        if not isinstance(tools, list):
            raise OctoBusError("OctoBus MCP tools/list response is missing tools")
        return [parse_capability(capset_id, item) for item in tools if isinstance(item, dict)]

    def list_all_capabilities(self) -> list[Capability]:
        capabilities: list[Capability] = []
        for capset in self.list_capsets():
            capabilities.extend(self.list_capabilities(capset.id))
        return capabilities

    def search_capabilities(self, query: str, capset_id: str = "") -> list[Capability]:
        query_tokens = tokenize(query)
        capabilities = (
            self.list_capabilities(capset_id) if capset_id.strip() else self.list_all_capabilities()
        )
        if not query_tokens:
            return capabilities
        return [
            capability
            for capability in capabilities
            if all(token in capability_search_text(capability) for token in query_tokens)
        ]

    def call_capability(
        self,
        *,
        capset_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        capset_id = capset_id.strip()
        tool_name = tool_name.strip()
        if not capset_id:
            raise OctoBusError("capset_id is required")
        if not tool_name:
            raise OctoBusError("tool_name is required")
        return self._mcp_request(
            capset_id,
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

    def mcp_endpoint(self, capset_id: str) -> str:
        capset_id = capset_id.strip()
        if not capset_id:
            raise OctoBusError("capset_id is required")
        return f"{self.config.normalized_url()}/capsets/{quote(capset_id, safe='')}/mcp"

    def _headers(self, token: str = "") -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.config.headers:
            headers.update(self.config.headers)
        if token.strip():
            headers["Authorization"] = f"Bearer {token.strip()}"
        return headers

    def _admin_headers(self) -> dict[str, str]:
        return self._headers(self.config.admin_token or self.config.token)

    def _capset_headers(self, capset_id: str) -> dict[str, str]:
        capset_tokens = self.config.capset_tokens or {}
        token = capset_tokens.get(capset_id) or self.config.capset_token or self.config.token
        return self._headers(token)

    def _get_json(self, path: str, *, headers: dict[str, str] | None = None) -> Any:
        response = requests.get(
            self.config.normalized_url() + path,
            headers=headers or self._headers(),
            timeout=self.config.timeout_seconds,
        )
        return parse_response(response)

    def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        headers: dict[str, str] | None = None,
    ) -> Any:
        response = requests.post(
            self.config.normalized_url() + path,
            headers={**(headers or self._headers()), "Content-Type": "application/json"},
            json=payload,
            timeout=self.config.timeout_seconds,
        )
        return parse_response(response)

    def _mcp_request(
        self,
        capset_id: str,
        method: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        capset_id = capset_id.strip()
        if not capset_id:
            raise OctoBusError("capset_id is required")
        payload = {
            "jsonrpc": "2.0",
            "id": f"dify-octobus-{uuid.uuid4()}",
            "method": method,
            "params": params,
        }
        body = self._post_json(
            f"/capsets/{quote(capset_id, safe='')}/mcp",
            payload,
            headers=self._capset_headers(capset_id),
        )
        if not isinstance(body, dict):
            raise OctoBusError("OctoBus returned invalid MCP response")
        error = body.get("error")
        if error:
            if isinstance(error, dict):
                raise OctoBusError(str(error.get("message") or error))
            raise OctoBusError(str(error))
        result = body.get("result")
        if not isinstance(result, dict):
            raise OctoBusError("OctoBus MCP response did not contain a result")
        if result.get("isError") is True:
            raise OctoBusError(mcp_error_message(result))
        return result


def parse_response(response: requests.Response) -> Any:
    if response.status_code < 200 or response.status_code >= 300:
        raise OctoBusError(f"OctoBus returned HTTP {response.status_code}: {response.text}")
    try:
        return response.json()
    except ValueError as exc:
        raise OctoBusError("OctoBus returned a non-JSON response") from exc


def parse_timeout(value: Any, default: float) -> float:
    if value is None or value == "":
        return default
    try:
        timeout = float(value)
    except (TypeError, ValueError) as exc:
        raise OctoBusError("timeout must be a number") from exc
    if timeout <= 0:
        raise OctoBusError("timeout must be positive")
    return timeout


def parse_headers_json(value: Any) -> dict[str, str] | None:
    return parse_string_map(value, "octobus_headers_json")


def parse_string_map(value: Any, field_name: str) -> dict[str, str] | None:
    if not value:
        return None
    if isinstance(value, dict):
        return {str(key): str(val) for key, val in value.items()}
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise OctoBusError(f"{field_name} must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise OctoBusError(f"{field_name} must be a JSON object")
    return {str(key): str(val) for key, val in parsed.items()}


def parse_arguments_json(value: Any) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise OctoBusError("arguments_json must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise OctoBusError("arguments_json must be a JSON object")
    return parsed


def parse_capability_selection(value: Any) -> tuple[str, str]:
    text = str(value or "").strip()
    if not text:
        return "", ""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        if "/" in text:
            capset_id, tool_name = text.split("/", 1)
            return capset_id.strip(), tool_name.strip()
        return "", text
    if not isinstance(parsed, dict):
        raise OctoBusError("capability must be a JSON object or tool name")
    return str(parsed.get("capset_id") or "").strip(), str(parsed.get("tool_name") or "").strip()


def is_not_found_body(body: Any) -> bool:
    if not isinstance(body, dict):
        return False
    status = str(body.get("status") or body.get("code") or body.get("err") or "").lower()
    message = str(body.get("message") or body.get("msg") or body.get("error") or "").lower()
    return status in {"404", "not_found", "notfound", "unknown"} and "not found" in message


def extract_list(body: Any, key: str, *, allow_empty_object: bool = False) -> list[Any]:
    if isinstance(body, list):
        return body
    if not isinstance(body, dict):
        raise OctoBusError(f"OctoBus returned invalid {key} response")
    value = body.get(key)
    if isinstance(value, list):
        return value
    if allow_empty_object and key in body and value is None:
        return []
    data = body.get("data")
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return data[key]
    if isinstance(data, list):
        return data
    if allow_empty_object and body == {}:
        return []
    keys = ", ".join(sorted(str(key) for key in body)) or "<empty>"
    raise OctoBusError(f"OctoBus returned invalid {key} response; response keys: {keys}")


def parse_capset(item: Any) -> Capset:
    if not isinstance(item, dict):
        raise OctoBusError("OctoBus returned invalid capset item")
    capset_id = first_string(item, "id", "ID", "capset_id", "capsetId", "CapsetID")
    if not capset_id:
        raise OctoBusError("OctoBus capset item is missing id")
    return Capset(
        id=capset_id,
        name=first_string(item, "name", "Name", "label", "Label"),
        description=first_string(item, "description", "Description", "desc", "Desc"),
        raw=item,
    )


def parse_capabilities(capset_id: str, catalog: dict[str, Any]) -> list[Capability]:
    capabilities: list[Capability] = []
    for item in catalog_items(catalog):
        capabilities.append(parse_capability(capset_id, item))
    return capabilities


def catalog_items(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    methods = catalog.get("methods") or catalog.get("Methods")
    if isinstance(methods, list):
        return [item for item in methods if isinstance(item, dict)]

    items: list[dict[str, Any]] = []
    for key, protocol in (("mcp", "mcp"), ("MCP", "mcp"), ("grpc", "grpc"), ("GRPC", "grpc")):
        value = catalog.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    items.append({**item, "_protocol": protocol})
    return items


def parse_capability(capset_id: str, item: dict[str, Any]) -> Capability:
    endpoints = item.get("endpoints")
    endpoint = first_endpoint(endpoints)
    tool_name = (
        first_string(item, "tool_name", "toolName", "mcp_tool_name", "mcpToolName")
        or first_string(endpoint, "tool_name", "toolName")
        or first_string(item, "name")
        or first_string(item, "method_full_name", "methodFullName", "full_name", "fullName")
    )
    name = first_string(item, "name") or tool_name
    return Capability(
        capset_id=capset_id,
        tool_name=tool_name,
        name=name,
        description=first_string(item, "description", "desc"),
        service_id=first_string(item, "service_id", "serviceId"),
        method=first_string(item, "method_full_name", "methodFullName", "full_name", "fullName"),
        protocol=first_string(endpoint, "protocol") or first_string(item, "_protocol", "protocol"),
        input_schema=first_dict(item, "input_schema", "inputSchema", "schema"),
        raw=item,
    )


def merge_capability(primary: Capability, metadata: Capability | None) -> Capability:
    if metadata is None:
        return primary
    return Capability(
        capset_id=primary.capset_id,
        tool_name=primary.tool_name,
        name=primary.name or metadata.name,
        description=primary.description or metadata.description,
        service_id=metadata.service_id or primary.service_id,
        method=metadata.method or primary.method,
        protocol="mcp",
        input_schema=primary.input_schema,
        raw={"mcp_tool": primary.raw, "catalog": metadata.raw},
    )


def mcp_error_message(result: dict[str, Any]) -> str:
    content = result.get("content")
    if isinstance(content, list):
        messages = [
            str(item.get("text")) for item in content if isinstance(item, dict) and item.get("text")
        ]
        if messages:
            return "; ".join(messages)
    return "OctoBus MCP tool returned an error"


def first_endpoint(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                return item
    return {}


def first_string(item: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = item.get(key)
        if value not in {"", None}:
            return str(value)
    return ""


def first_dict(item: dict[str, Any], *keys: str) -> dict[str, Any] | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, dict):
            return value
    return None


def tokenize(query: str) -> list[str]:
    return [token for token in query.lower().split() if token]


def capability_search_text(capability: Capability) -> str:
    return (
        f"{capability.capset_id} {capability.tool_name} {capability.name} "
        f"{capability.description} {capability.service_id} {capability.method} "
        f"{capability.protocol}"
    ).lower()
