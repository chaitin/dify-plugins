#!/usr/bin/env python3
"""Build every plugin with a version derived from the repository release tag."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
import zipfile
from collections.abc import Callable, Sequence
from datetime import date, datetime
from pathlib import Path

import yaml

try:
    from .discover_plugins import discover
except ImportError:  # Executed directly as a script.
    from discover_plugins import discover

SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")
IGNORED_NAMES = {
    ".cache",
    ".coverage",
    ".pytest_cache",
    ".ruff_cache",
    ".task",
    ".venv",
    "__pycache__",
    "dist",
}
Runner = Callable[..., subprocess.CompletedProcess[bytes] | subprocess.CompletedProcess[str]]


def validate_version(version: str) -> str:
    if not SEMVER.fullmatch(version):
        raise ValueError(f"release version must be SemVer without a prefix: {version!r}")
    return version


def write_release_manifest(source: Path, destination: Path, version: str) -> str:
    manifest = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("name"), str):
        raise TypeError(f"invalid plugin manifest: {source}")
    meta = manifest.get("meta")
    if not isinstance(meta, dict):
        raise TypeError(f"manifest meta must be a mapping: {source}")
    manifest["version"] = version
    meta["version"] = version
    if isinstance(manifest.get("created_at"), (date, datetime)):
        manifest["created_at"] = manifest["created_at"].isoformat()
    destination.write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return manifest["name"]


def verify_package(package: Path, expected_name: str, expected_version: str) -> None:
    if not package.is_file():
        raise RuntimeError(f"Dify CLI did not create {package}")
    with zipfile.ZipFile(package) as archive:
        manifest = yaml.safe_load(archive.read("manifest.yaml"))
    if not isinstance(manifest, dict):
        raise TypeError(f"packaged manifest is invalid: {package}")
    actual = (
        manifest.get("name"),
        manifest.get("version"),
        (manifest.get("meta") or {}).get("version"),
    )
    expected = (expected_name, expected_version, expected_version)
    if actual != expected:
        raise RuntimeError(f"packaged identity {actual!r} does not match {expected!r}")


def build_release(
    root: Path,
    version: str,
    dist_dir: Path,
    cli: str,
    *,
    runner: Runner = subprocess.run,
) -> list[Path]:
    version = validate_version(version)
    root = root.resolve()
    dist_dir = dist_dir.resolve()
    dist_dir.mkdir(parents=True, exist_ok=True)
    packages: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="dify-plugins-release-") as temporary:
        staging_root = Path(temporary)
        for plugin in discover(root):
            source = root / plugin["path"]
            staging = staging_root / plugin["name"]
            shutil.copytree(
                source,
                staging,
                ignore=lambda _path, names: IGNORED_NAMES.intersection(names),
            )
            name = write_release_manifest(
                source / "manifest.yaml", staging / "manifest.yaml", version
            )
            if name != plugin["name"]:
                raise ValueError(f"manifest name does not match plugin directory: {source}")
            output = dist_dir / f"{name}-{version}.difypkg"
            runner(
                [cli, "plugin", "package", str(staging), "--output_path", str(output)],
                check=True,
            )
            verify_package(output, name, version)
            packages.append(output)
    return packages


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--cli", required=True)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    packages = build_release(args.root, args.version, args.dist_dir, args.cli)
    for package in packages:
        print(package)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
