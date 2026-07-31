# agent-compose Strategy

[English](README.md)

这是一个 Dify Agent Strategy 插件，可将 Agent 节点执行委托给 [agent-compose](https://github.com/chaitin/agent-compose)，并支持隔离沙箱生命周期管理及结构化运行信息。

要求 Dify 1.15.0 或更高版本。使用 `keep_running` 时，Strategy 可以按 Dify 会话和 Agent 保存、复用沙箱；一次性任务可选择完成后停止或删除。详见[配置与使用](docs/usage.zh-CN.md)和[完整架构与选型介绍](docs/architecture.zh-CN.md)。本项目采用 Apache-2.0 许可证，以仓库根目录许可证为准。
