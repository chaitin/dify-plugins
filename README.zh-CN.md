# 长亭 Dify 插件集合

[English](README.md)

本仓库收录由长亭维护的 Dify 插件。仓库采用 monorepo 组织，每个插件独立版本、独立测试和打包，支持 Dify 1.15.0 及以上版本。

## 插件

| 插件 | 形态 | 简介 | 文档 |
| --- | --- | --- | --- |
| Rivers IOC | 工具 | 查询长亭百川云 Rivers 威胁情报 | [插件文档](plugins/rivers_ioc/README.zh-CN.md) |
| agent-compose Workflow | 工具 | 在 Dify 工作流中调用 agent-compose | [插件文档](plugins/agent_compose_workflow/README.zh-CN.md) |
| agent-compose Strategy | Agent 策略 | 在 Dify Agent 节点中使用 agent-compose | [插件文档](plugins/agent_compose_strategy/README.zh-CN.md) |
| OctoBus | 工具 | 发现并调用 OctoBus 能力 | [插件文档](plugins/octobus/README.zh-CN.md) |

请从 [GitHub Releases](../../releases) 下载 `.difypkg` 和 `SHA256SUMS`，并通过 Dify 插件管理界面安装。

## 开发

安装 [Task](https://taskfile.dev/) 和 [uv](https://docs.astral.sh/uv/) 后执行：

```shell
task setup
task check
task build
```

`plugins/` 下每个目录均可独立测试和打包。更多信息参见[开发指南](docs/development.md)、[贡献指南](CONTRIBUTING.md)和[安全策略](SECURITY.md)。

## 许可证

本项目采用 Apache License 2.0，详见 [LICENSE](LICENSE) 和 [NOTICE](NOTICE)。
