#!/usr/bin/env python3
"""Discover self-contained Dify plugins in the monorepo."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def discover(root: Path) -> list[dict[str, str]]:
    plugins_dir = root / "plugins"
    if not plugins_dir.is_dir():
        return []
    return [
        {"name": path.parent.name, "path": path.parent.relative_to(root).as_posix()}
        for path in sorted(plugins_dir.glob("*/manifest.yaml"))
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("json", "names", "paths"), default="json")
    args = parser.parse_args()
    plugins = discover(args.root.resolve())
    if args.format == "json":
        print(json.dumps({"plugin": plugins}, separators=(",", ":")))
    else:
        key = "name" if args.format == "names" else "path"
        print(" ".join(plugin[key] for plugin in plugins))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
