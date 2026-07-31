"""Build a plugin package whose filename is derived from its manifest."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import yaml


def read_identity(manifest_path: Path) -> tuple[str, str]:
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise TypeError("manifest must be a mapping")
    name = manifest.get("name")
    version = manifest.get("version")
    meta = manifest.get("meta")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("manifest name must be a non-empty string")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("manifest version must be a non-empty string")
    if not isinstance(meta, dict) or meta.get("version") != version:
        raise ValueError("manifest version and meta.version must match")
    return name, version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", required=True)
    parser.add_argument("--dist-dir", default="dist")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    name, version = read_identity(root / "manifest.yaml")
    dist_dir = Path(args.dist_dir)
    if not dist_dir.is_absolute():
        dist_dir = root / dist_dir
    dist_dir.mkdir(parents=True, exist_ok=True)
    output = dist_dir / f"{name}-{version}.difypkg"
    subprocess.run(
        [args.cli, "plugin", "package", str(root), "-o", str(output)],
        check=True,
    )
    print(output)


if __name__ == "__main__":
    main()
