# Configuration and usage

Configure the reachable OctoBus daemon URL and, when enabled, admin and capset bearer tokens. The plugin can list capsets, inspect their schemas, search capabilities, and invoke a selected MCP tool. Per-capset tokens and additional headers can be supplied as JSON objects.

## Tools

- `list_capsets` returns the capability sets visible through the Admin API.
- `describe_capset` combines catalog metadata and MCP tool schemas for one capset.
- `search_capabilities` searches names, services, methods, and descriptions, optionally within one capset.
- `call_capability` invokes a selected capability through MCP `tools/call`.

The source also contains diagnostic service and instance clients, while the public provider exposes the progressive discovery tools intended for normal Agent workflows.

## Credentials

`octobus_admin_token` authenticates Admin API discovery. `octobus_capset_token` is the default MCP token. `octobus_capset_tokens_json` maps individual capset IDs to tokens, for example `{"security":"token"}`. `octobus_headers_json` supplies additional headers required by an upstream gateway.

Do not place secrets directly in workflow prompts or tool arguments. Configure them as provider credentials so Dify stores them as secrets.

## Recommended Agent flow

Start with `list_capsets`. Describe a likely capset or search with a short user-derived keyword. Inspect the returned input schema before constructing `arguments_json`, then call the selected capability. Treat tool-level MCP errors as failed capability calls and surface them to the workflow.

For local development, `http://localhost:9000` is a suitable example only when the Dify plugin runtime can reach that address. Container deployments normally require a routable service hostname.
