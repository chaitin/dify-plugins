# Contributing a Plugin

Create `plugins/<name>` where `<name>` exactly matches manifest `name`. The manifest
must use author `chaitin`, minimum Dify version `1.15.0`, Python 3.12, matching top-level
and metadata versions, and the least privileges needed. Follow Dify's official plugin
manifest and Marketplace requirements.

A plugin includes `manifest.yaml`, `main.py`, `requirements.txt`, `PRIVACY.md`,
`Taskfile.yml`, `_assets/icon.svg`, tests, English `README.md`, Chinese
`README.zh-CN.md`, and a changelog. Its Taskfile exposes `lint`, `test`, `validate`,
`build`, `check`, and `clean`. Packaging must not include tests, docs, caches, or
development tools.

Document credentials, data sent to external services, configuration, examples,
permissions, and troubleshooting. Add the plugin to both root README tables. Run
`task check` and `task build`, then install the resulting package in Dify 1.15.0.
