# OctoBus

[中文文档](README.zh-CN.md)

A Dify Tool plugin for progressively discovering and invoking capabilities exposed by [OctoBus](https://github.com/chaitin/OctoBus) capsets through MCP.

## Progressive discovery

The plugin keeps large, changing capability catalogs out of a static Dify tool definition. An Agent can list capsets, describe one capset and its schemas, search capabilities, then call only the selected MCP tool.

## Requirements and setup

- Dify 1.15.0 or later.
- A reachable OctoBus daemon URL shared by Admin API and MCP endpoints.
- Optional Admin, default capset, or per-capset bearer tokens.

Install the versioned `.difypkg` and configure the provider. Use `list_capsets` first, `describe_capset` or `search_capabilities` to inspect available tools, and `call_capability` with JSON arguments to invoke one.

## Authentication

Admin API discovery uses the Admin token. MCP calls prefer a token mapped to the selected capset and fall back to the default capset token. Extra headers can be supplied as a JSON object for deployments using gateway-specific authentication.

See [configuration and usage](docs/usage.md). This project is licensed under Apache-2.0; see the repository-level license.
