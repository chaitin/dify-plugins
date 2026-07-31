# Chaitin Dify Plugins

[中文文档](README.zh-CN.md)

Officially maintained Dify plugins from Chaitin. This monorepo publishes independently
versioned, self-contained plugin packages for Dify 1.15.0 and later.

## Plugins

| Plugin | Form | Description | Documentation |
| --- | --- | --- | --- |
| Rivers IOC | Tool | Query threat intelligence from Chaitin Rivers | [Plugin README](plugins/rivers_ioc/README.md) |
| agent-compose Workflow | Tool | Invoke agent-compose from a Dify workflow | [Plugin README](plugins/agent_compose_workflow/README.md) |
| agent-compose Strategy | Agent strategy | Use agent-compose in Dify Agent nodes | [Plugin README](plugins/agent_compose_strategy/README.md) |
| OctoBus | Tool | Discover and invoke OctoBus capabilities | [Plugin README](plugins/octobus/README.md) |

Download attested build artifacts and `SHA256SUMS` from [GitHub Releases](../../releases).
Install a `.difypkg` through Dify's plugin management interface.

## Development

Install [Task](https://taskfile.dev/) and [uv](https://docs.astral.sh/uv/), then run:

```shell
task setup
task check
task build
```

Each directory under `plugins/` is independently testable and packageable. See the
[development guide](docs/development.md), [contribution guide](CONTRIBUTING.md), and
[security policy](SECURITY.md).

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
