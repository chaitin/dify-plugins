# Contributing

Thank you for contributing. Development requires Python 3.12, uv, Task, and Git.
Run `task setup` once, then `task check` and `task build` before opening a pull request.

Each plugin belongs in `plugins/<manifest-name>/`, is independently packageable, and
owns its tests, Taskfile, English and Chinese README, privacy policy, and changelog.
New plugins must follow [the plugin contribution guide](docs/contributing-plugin.md)
and Dify's current plugin specification. Never commit credentials, private hosts,
generated `.difypkg` files, virtual environments, or internal dependencies.

Commits should be focused and pull requests should explain user impact, testing, and
documentation changes. All contributions are licensed under Apache-2.0.
