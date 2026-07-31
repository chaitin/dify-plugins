from pathlib import Path

import pytest

from scripts.build_plugin import read_identity


def write_manifest(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def test_read_identity_derives_package_metadata(tmp_path):
    manifest = write_manifest(
        tmp_path / "manifest.yaml",
        "name: rivers_ioc\nversion: 1.2.3\nmeta:\n  version: 1.2.3\n",
    )
    assert read_identity(manifest) == ("rivers_ioc", "1.2.3")


def test_read_identity_rejects_version_mismatch(tmp_path):
    manifest = write_manifest(
        tmp_path / "manifest.yaml",
        "name: rivers_ioc\nversion: 1.2.3\nmeta:\n  version: 1.2.4\n",
    )
    with pytest.raises(ValueError, match="must match"):
        read_identity(manifest)


@pytest.mark.parametrize(
    "content",
    ["version: 1.2.3\nmeta:\n  version: 1.2.3\n", "name: rivers_ioc\nmeta: {}\n"],
)
def test_read_identity_requires_name_and_version(tmp_path, content):
    manifest = write_manifest(tmp_path / "manifest.yaml", content)
    with pytest.raises(ValueError):
        read_identity(manifest)
