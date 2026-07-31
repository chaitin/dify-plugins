import argparse
import os
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def package_identity() -> tuple[str, str]:
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text(encoding="utf-8"))
    name = manifest.get("name")
    version = manifest.get("version")
    meta_version = manifest.get("meta", {}).get("version")
    if not isinstance(name, str) or not SAFE_COMPONENT.fullmatch(name):
        raise SystemExit("manifest name is missing or unsafe")
    if not isinstance(version, str) or not SAFE_COMPONENT.fullmatch(version):
        raise SystemExit("manifest version is missing or unsafe")
    if version != meta_version:
        raise SystemExit(
            f"manifest version {version!r} does not match meta.version {meta_version!r}"
        )
    return name, version


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    name, version = package_identity()
    if args.validate_only:
        return
    output_dir = Path(os.environ.get("DIST_DIR", "dist")).expanduser()
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir.resolve() / f"{name}-{version}.difypkg"
    cli = os.environ.get("DIFY_PLUGIN_CLI", "dify")
    subprocess.run([cli, "plugin", "package", str(ROOT), "--output_path", str(output)], check=True)
    print(output)


if __name__ == "__main__":
    main()
