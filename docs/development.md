# Development

Install Python 3.12, [uv](https://docs.astral.sh/uv/), and
[Task](https://taskfile.dev/). Run `task setup`, then use `task check` for the same
quality gates as CI and `task build` to create all packages under `dist/`.

To work on one plugin, enter its directory and use its Taskfile:

```shell
cd plugins/rivers_ioc
task check
task build
```

The root environment is for repository tooling. A plugin declares and locks its own
runtime/test dependencies. The official CLI resolver downloads Dify plugin CLI 0.6.3
for the current OS and architecture and verifies a pinned SHA-256 digest. Set
`DIFY_PLUGIN_CLI` to use a preinstalled, independently verified binary.

Before submitting, verify there are no internal hosts, private addresses, secrets,
generated packages, or caches in the change.
