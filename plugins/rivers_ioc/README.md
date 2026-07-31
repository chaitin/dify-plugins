# Rivers IOC

[中文文档](README.zh-CN.md)

Rivers IOC is a Dify tool plugin for querying IP threat intelligence from
[Chaitin Rivers](https://rivers.chaitin.cn). It supports IPv4 and IPv6 and returns the upstream
response as structured JSON for downstream workflow nodes.

## Requirements

- Dify 1.15.0 or later
- A Rivers access token with threat-intelligence permission

## Install and configure

Install the `.difypkg` from this repository's GitHub Release, add the plugin in Dify, and enter a
token created in the [Rivers console](https://rivers.chaitin.cn/console/space). Credential
validation performs one query for the public address `1.1.1.1`; this may consume one API request.

See [configuration and troubleshooting](docs/configuration.md) for operational details.

## Development

```shell
task setup
task check
task build DIFY_PLUGIN_CLI=/path/to/dify
```
