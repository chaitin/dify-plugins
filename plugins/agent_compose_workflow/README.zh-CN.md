# agent-compose Workflow

要求使用 agent-compose `v2609.1.0` 或更高版本；插件通过 run label 关联会话以实现多轮对话连续性。

[English](README.md)

这是一个 Dify Tool 插件，可在 Workflow 的 Tool 节点中发现并运行 [agent-compose](https://github.com/chaitin/agent-compose) 智能体。每次运行均由 agent-compose 在隔离沙箱中执行。

要求 Dify 1.15.0 或更高版本。配置 agent-compose 基础地址和可选 Bearer Token 后，在工作流中加入 **运行动态工作流** 工具即可。

详见[配置与使用](docs/usage.zh-CN.md)和[完整架构与选型介绍](docs/architecture.zh-CN.md)。插件支持动态选择 Agent、沙箱清理策略、结构化输出和幂等请求 ID，并返回文本及结构化运行信息。本项目采用 Apache-2.0 许可证，以仓库根目录许可证为准。

对于可复用的清理策略，插件会使用 Dify `conversation_id` label 查询 agent-compose 最近一次运行并找回 sandbox，不依赖 Dify session storage。当前 Dify 工作流运行时可能不提供 `message_id`；若运行时提供，插件仍会把它记录为 run label。
