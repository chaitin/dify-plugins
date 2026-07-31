# Rivers IOC

[English](README.md)

Rivers IOC 是用于查询[长亭百川云](https://rivers.chaitin.cn) IP 威胁情报的 Dify 工具插件，
支持 IPv4 和 IPv6，并以结构化 JSON 返回结果，便于工作流后续节点处理。

## 环境要求

- Dify 1.15.0 或更高版本
- 具有威胁情报权限的百川云访问令牌

## 安装和配置

从本仓库的 GitHub Release 下载 `.difypkg` 并安装，然后填写在
[百川云控制台](https://rivers.chaitin.cn/console/space)创建的令牌。凭证校验会使用公网地址
`1.1.1.1` 发起一次查询，因此可能消耗一次 API 调用额度。

运行细节见[配置与故障排查](docs/configuration.zh-CN.md)。
