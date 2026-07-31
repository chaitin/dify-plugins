#!/usr/bin/env python3
"""Validate repository conventions and essential Dify manifest fields."""

from __future__ import annotations

import argparse
import ipaddress
import re
import sys
from pathlib import Path

import yaml

try:
    from .discover_plugins import discover
except ImportError:  # Executed directly as a script.
    from discover_plugins import discover

REQUIRED_FILES = (
    "manifest.yaml",
    "main.py",
    "requirements.txt",
    "PRIVACY.md",
    "Taskfile.yml",
    "README.md",
    "CHANGELOG.md",
)
PRIVATE_HOST = re.compile(
    r"(?:git\.in\.chaitin\.net|portus\.in\.chaitin\.net|proxy\.in\.chaitin\.net)", re.I
)
PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(network)
    for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")  # private-reference: allow
)


def validate_plugin(root: Path, item: dict[str, str]) -> list[str]:
    errors: list[str] = []
    path = root / item["path"]
    for filename in REQUIRED_FILES:
        if not (path / filename).is_file():
            errors.append(f"{item['name']}: missing {filename}")
    try:
        manifest = yaml.safe_load((path / "manifest.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        return errors + [f"{item['name']}: invalid manifest: {exc}"]
    if manifest.get("name") != item["name"]:
        errors.append(f"{item['name']}: manifest name must match directory")
    if manifest.get("author") != "chaitin":
        errors.append(f"{item['name']}: manifest author must be chaitin")
    meta = manifest.get("meta") or {}
    if meta.get("minimum_dify_version") != "1.15.0":
        errors.append(f"{item['name']}: minimum_dify_version must be 1.15.0")
    if str(manifest.get("version", "")) != str(meta.get("version", "")):
        errors.append(f"{item['name']}: version and meta.version must match")
    if not (path / "_assets" / "icon.svg").is_file():
        errors.append(f"{item['name']}: missing _assets/icon.svg")
    return errors


def scan_private_references(root: Path) -> list[str]:
    errors: list[str] = []
    excluded = {".git", ".venv", ".uv-cache", ".dify", "dist"}
    for path in root.rglob("*"):
        if not path.is_file() or excluded.intersection(path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".difypkg"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            if "private-reference: allow" in line:
                continue
            if PRIVATE_HOST.search(line):
                errors.append(f"private hostname found in {path.relative_to(root)}")
            for match in re.finditer(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", line):
                try:
                    address = ipaddress.ip_address(match.group())
                except ValueError:
                    continue
                if any(address in network for network in PRIVATE_NETWORKS):
                    errors.append(f"private IP found in {path.relative_to(root)}")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()
    plugins = discover(root)
    names = {item["name"] for item in plugins}
    errors: list[str] = []
    if not plugins:
        errors.append("at least one plugin must be present")
    if len(names) != len(plugins):
        errors.append("plugin names must be unique")
    for item in plugins:
        errors.extend(validate_plugin(root, item))
    errors.extend(scan_private_references(root))
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"validated {len(plugins)} plugin(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
