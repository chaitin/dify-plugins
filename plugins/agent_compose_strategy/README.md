# agent-compose Strategy

[中文文档](README.zh-CN.md)

A Dify Agent Strategy plugin that delegates Agent node execution to [agent-compose](https://github.com/chaitin/agent-compose), including isolated sandbox lifecycle management and structured run metadata.

## When to use it

Choose this form when the Dify Agent node itself should be implemented by an agent-compose agent. It fits multi-turn or complex tasks that benefit from code-defined agents, isolated workspaces, skills, MCP services, and explicit sandbox lifecycle management.

## Requirements and setup

- Dify 1.15.0 or later.
- A reachable agent-compose HTTP/Connect endpoint.
- An agent reference in `project/agent` form, or a unique agent name.

Install the versioned `.difypkg`, select **agent-compose Strategy** in an Agent node, then configure its connection, query, optional instruction, timeout, cleanup policy, and optional structured-output schema.

## Conversation state

With `keep_running`, the strategy remembers an agent-scoped sandbox for the Dify conversation and can reuse it on later turns. Stop and remove policies avoid retaining sandbox state. Every invocation emits text, JSON, and separate structured run variables.

See [configuration and usage](docs/usage.md) and the [architecture introduction](docs/architecture.zh-CN.md). This project is licensed under Apache-2.0; see the repository-level license.
