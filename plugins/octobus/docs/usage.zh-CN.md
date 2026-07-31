# 配置与使用

配置 Dify 可访问的 OctoBus daemon 地址；开启鉴权时填写 Admin 和 capset Bearer Token。插件支持列出 capset、查看 Schema、搜索能力以及调用所选 MCP 工具。可通过 JSON 对象提供各 capset Token 和附加请求头。

## 工具

- `list_capsets`：通过 Admin API 列出可见能力集。
- `describe_capset`：合并指定 capset 的目录元数据和 MCP 工具 Schema。
- `search_capabilities`：按名称、服务、方法或描述搜索能力，也可限定 capset。
- `call_capability`：通过 MCP `tools/call` 调用选定能力。

源码还包含服务和实例诊断客户端；公开 Provider 默认暴露适合 Agent 工作流的渐进式发现工具。

## 凭证

`octobus_admin_token` 用于 Admin API；`octobus_capset_token` 是默认 MCP Token；`octobus_capset_tokens_json` 可按 capset ID 配置独立 Token，例如 `{"security":"token"}`；`octobus_headers_json` 用于上游网关要求的附加请求头。

不要在工作流提示词或工具参数中直接填写密钥，应通过 Provider Credential 配置，让 Dify 按 Secret 保存。

## 推荐调用流程

先调用 `list_capsets`，再描述可能相关的 capset，或使用从用户问题提取的短关键词搜索。根据返回的输入 Schema 构造 `arguments_json`，最后调用目标能力。MCP 工具级错误应作为能力调用失败处理并反馈给工作流。

本地开发可使用 `http://localhost:9000` 作为示例，但前提是 Dify 插件运行环境能访问该地址；容器部署通常应使用可路由的服务名。
