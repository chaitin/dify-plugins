# AGENTS.md

This is a monorepo of independently installable Dify plugins maintained by Chaitin.

## Rules

- Prefer the codebase-memory MCP graph for code discovery; use text search for configs.
- Every plugin lives at `plugins/<manifest-name>` and must package without root runtime code.
- Support Dify 1.15.0+, Python 3.12, and the pinned official Dify plugin CLI.
- Run `task check` and `task build`; plugin Taskfiles expose `lint`, `test`, `validate`, `build`, `check`, and `clean`.
- Keep manifests, tests, privacy policy, changelog, and bilingual documentation aligned.
- Do not add private hosts/IPs, secrets, private dependencies, generated packages, caches, or virtual environments.
- Every file must have SPDX metadata. Prefer SPDX headers for substantive source files;
  use `REUSE.toml` annotations for generated, bulk, or non-commentable files.
- Preserve third-party copyright and license metadata; never relabel third-party work.
- Preserve plugin identities and versions unless a migration explicitly requires a breaking rename.

See `docs/architecture.md` and `docs/development.md` before structural changes.
