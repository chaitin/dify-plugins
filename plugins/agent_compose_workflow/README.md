# agent-compose Workflow

[中文文档](README.zh-CN.md)

A Dify Tool plugin that discovers and runs [agent-compose](https://github.com/chaitin/agent-compose) agents from Workflow Tool nodes. Each run is executed in an isolated sandbox managed by agent-compose.

## When to use it

Use this plugin when a Dify workflow needs one step backed by a coding agent, a reproducible workspace, MCP capabilities, or a long-running sandbox. Dify remains responsible for application input, orchestration, knowledge retrieval, and output; agent-compose handles the complex Agent execution.

## Requirements and setup

- Dify 1.15.0 or later.
- A reachable agent-compose HTTP/Connect endpoint.
- An optional bearer token when the service enables authentication.

Install the versioned `.difypkg`, configure the provider, then add **Run agent-compose Agent** to a workflow. The agent selector is populated dynamically from agent-compose projects.

## Inputs and outputs

The tool accepts an agent, query, optional instruction, cleanup policy, optional output schema, and idempotent client request ID. It returns the text result plus `run_id`, `sandbox_id`, status, errors, and warnings as structured values.

Choose `stop_on_completion` for ordinary one-shot work, `keep_running` when a later request should reuse the sandbox, or `remove_on_completion` when the workspace must be discarded.

See [configuration and usage](docs/usage.md) and the [architecture introduction](docs/architecture.zh-CN.md). This project is licensed under Apache-2.0; see the repository-level license.
