# Release Process

Plugins version independently in their manifests and changelogs. Repository tags use
a release-train version such as `v2026.08.0`; they do not replace plugin versions.

1. Confirm all required checks pass on the tagged main-branch commit.
2. Confirm each changed plugin's version and changelog were updated.
3. Create an annotated `v*` tag.
4. The release workflow rebuilds all plugins with Dify plugin CLI 0.6.3.
5. It creates `SHA256SUMS`, provenance attestations, and a GitHub Release containing
   `<plugin>-<version>.difypkg` for every plugin.
6. Install and smoke-test every package on a clean Dify 1.15.0 deployment before
   promoting a prerelease.

The workflow never edits another repository or uses a personal access token.
