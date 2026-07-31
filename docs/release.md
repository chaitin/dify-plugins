# Release Process

Repository tags are the release version for every packaged plugin. Source manifests
carry a development baseline, but release packaging uses a temporary staging tree and
sets both `version` and `meta.version` to an unprefixed SemVer tag such as `0.3.0`.
Source manifests are never modified by the release job.

1. Confirm all required checks pass on the tagged main-branch commit.
2. Create an annotated SemVer tag without a `v` prefix.
3. The release workflow runs all quality gates and rebuilds every plugin with Dify
   plugin CLI 0.6.3 using the tag as its embedded version.
5. It creates `SHA256SUMS`, provenance attestations, and a GitHub Release containing
   `<plugin>-<tag>.difypkg` for every plugin.
6. Install and smoke-test every package on a clean Dify 1.15.0 deployment before
   promoting a prerelease.

The workflow never edits another repository or uses a personal access token.
