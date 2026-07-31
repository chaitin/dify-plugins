# Monorepo Open-Source Migration Plan

## Objective

Transform `chaitin/dify-plugins` from a single legacy plugin repository into
the public, GitHub-native monorepo for Chaitin-maintained Dify plugins. The
repository targets Dify 1.15.0 and later, builds each plugin independently,
and publishes verified `.difypkg` files in GitHub Releases.

## Execution Status

The repository migration described by W0-W4 is complete. All three delegated
worktree branches were reviewed, integrated, and removed. The source
`dynamic-workflow` baseline passed 43 tests before migration; the monorepo now
passes 97 repository/plugin tests and packages all four plugins with the
checksum-verified Dify plugin CLI 0.6.3. W5's repository automation is ready;
creating a public prerelease and installing it in an external clean Dify 1.15.0
deployment remain maintainer-operated release actions.

The first public collection contains:

| Plugin | Dify extension type | Source |
| --- | --- | --- |
| `rivers_ioc` | Tool | Refactored from the repository's legacy `chaitin_ioc` plugin |
| `agent_compose_workflow` | Tool | Renamed migration of `dynamic_workflow_tool` |
| `agent_compose_strategy` | Agent Strategy | Migration from `dynamic-workflow` |
| `octobus` | Tool | Migration from `dynamic-workflow` |

The three plugins imported from `dynamic-workflow` were completed and tested
before migration. Their runtime logic is treated as a verified input: the
migration changes repository layout, names, tasks, documentation, and public
CI integration, but does not redesign their behavior.

## Architectural Decisions

1. Every directory under `plugins/` is a complete, independently packageable
   Dify plugin and owns its manifest, runtime dependencies, tests, docs, and
   `Taskfile.yml`.
2. The root Taskfile aggregates the same `lint`, `test`, `validate`, `build`,
   and `check` contracts exposed by each plugin.
3. `meta.minimum_dify_version` is `1.15.0`; Python plugins use Python 3.12.
4. Release packages are built with the official CLI distributed by
   `langgenius/dify-plugin-daemon`. The baseline CLI is 0.6.3, matching Dify
   1.15.0; a newer pinned CLI may be used as an additional compatibility gate.
5. Plugin versions remain independent. A repository release is a release
   train containing all current plugin packages and `SHA256SUMS`.
6. The repository is Apache-2.0 and copyrighted by Chaitin. Imported assets
   and code must pass a provenance/license review before release.
7. GitLab CI, internal registries, proxies, private hosts, generated packages,
   caches, and source-repository metadata are not migrated.

## Work Breakdown

### W0: Baseline and coordination

Owner: lead. Establish this plan, record the clean source baseline, assign
orthogonal worktree branches, review commits, merge in dependency order, run
the final acceptance suite, and remove all temporary worktrees.

### W1: Repository foundation and public governance

Deliver the root Taskfile and Python development configuration, GitHub Actions
CI and release workflows, CLI resolver/validation scripts, bilingual root
README files, contributor and security policies, Apache-2.0 `LICENSE`,
`NOTICE`, `AGENTS.md`, and repository-wide ignore/security rules.

W1 must not implement plugin runtime behavior. It may define the common task
contract consumed by W2 and W3.

### W2: Rivers IOC modernization

Move and rename the legacy plugin to `plugins/rivers_ioc`, align its manifest
and SDK usage with Dify 1.15.0+, add bounded HTTP behavior and safe error
handling, implement credential and IP validation, return structured results,
and add focused unit tests and bilingual plugin documentation.

This is the only runtime modernization workstream because the source plugin is
legacy and has no meaningful test baseline.

### W3: Dynamic-workflow migration

Copy the three verified source plugin directories into the monorepo, rename
`dynamic_workflow_tool` to `agent_compose_workflow`, adjust identifiers and
import/test paths required by that rename, add per-plugin Taskfiles and place
each plugin's documentation with that plugin. Preserve runtime logic. Remove
internal GitLab, proxy, registry, private IP, cache, binary, and build outputs.

Before migration, `task check` in the source repository must pass. After
migration, the equivalent tests must pass from the new layout.

### W4: Integration and acceptance

Merge W1 first when its common interfaces are required, then W2 and W3. Resolve
only integration-level conflicts. Run repository-wide lint, tests, validation,
and builds; scan for private references and secrets; inspect package contents;
and verify expected artifact names and checksums.

### W5: GitHub release readiness

Validate workflows and release permissions, document required branch
protection settings, confirm the legal name in `NOTICE`, audit OctoBus-related
provenance against its upstream GPL-3.0 license, then create a prerelease and
install all four artifacts into a clean Dify 1.15.0 environment. Publishing an
actual GitHub Release is an explicit maintainer action after these checks.

## Dependency Graph

```text
W0 baseline
 ├── W1 repository foundation ─┐
 ├── W2 Rivers IOC ────────────┼── W4 integration ── W5 release readiness
 └── W3 workflow migration ────┘
```

W1, W2, and W3 are developed in parallel worktrees. W2 and W3 own disjoint
plugin directories. W1 owns root-level and `.github` files. Documentation for
a specific plugin belongs to that plugin's workstream, preventing overlapping
edits.

## Merge and Worktree Protocol

1. Each developer creates a branch and worktree from the agreed baseline.
2. Each branch commits only its assigned paths and reports tests executed.
3. The lead reviews the diff and test evidence before merging without force.
4. After merging, the lead runs integration checks on `main`.
5. The lead removes the completed worktree and deletes the local task branch.
6. Generated `.difypkg`, virtual environments, caches, and downloaded CLI
   binaries are never committed.

## Acceptance Criteria

- Exactly four supported plugin directories are independently packageable.
- Every plugin exposes `task lint`, `task test`, `task validate`, `task build`,
  and `task check`; the root exposes aggregate equivalents.
- All manifests identify `author: chaitin`, target Dify 1.15.0+, and reference
  existing entrypoints and assets.
- The migrated dynamic-workflow suite retains its passing test baseline.
- Rivers IOC has tests for input validation, credentials, success, HTTP errors,
  rate limiting, timeouts, malformed responses, and secret-safe errors.
- Root and plugin documentation is English-first with Chinese navigation.
- No GitLab configuration, internal hostname, private IP example, credential,
  generated package, cache, or nested repository metadata is committed.
- Pull requests run lint, tests, Dify validation, and package builds.
- A release workflow produces four versioned packages and `SHA256SUMS` using a
  pinned, checksum-verified official Dify plugin CLI.
- License, notice, privacy, contribution, security, and AI-agent guidance are
  present and internally consistent.

## Out of Scope

- Redesigning the verified agent-compose or OctoBus plugin runtime behavior.
- Automatically publishing to the upstream `langgenius/dify-plugins`
  marketplace repository.
- Publishing a public GitHub Release before maintainer/legal review and clean
  Dify 1.15.0 installation testing are complete.
