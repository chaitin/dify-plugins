# Architecture

The repository is a release-oriented monorepo. `plugins/<name>` is the unit of
ownership, testing, versioning, and packaging. A plugin may not import runtime code
from the repository root or another plugin. Root tooling discovers plugins from
`plugins/*/manifest.yaml` and delegates work to each plugin's Taskfile.

The root layer owns policy, CI, release assembly, documentation, and pinned build
tools. Plugin layers own Dify manifests, provider/tool/strategy declarations,
implementation, dependencies, tests, privacy terms, and user documentation.

The initial public catalog contains `rivers_ioc`, `agent_compose_workflow`,
`agent_compose_strategy`, and `octobus`. Plugin versions are independent. A dated
repository release train bundles the current validated version of every plugin.
