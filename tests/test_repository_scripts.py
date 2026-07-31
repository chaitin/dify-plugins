import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml

from scripts.build_release import build_release, validate_version
from scripts.discover_plugins import discover
from scripts.validate_plugins import scan_private_references


def test_discover_returns_sorted_plugins(tmp_path: Path) -> None:
    for name in ("zeta", "alpha"):
        plugin = tmp_path / "plugins" / name
        plugin.mkdir(parents=True)
        (plugin / "manifest.yaml").touch()
    assert [item["name"] for item in discover(tmp_path)] == ["alpha", "zeta"]


def test_private_reference_scan_covers_all_rfc1918_networks(tmp_path: Path) -> None:
    (tmp_path / "addresses.txt").write_text(
        "10.2.3.4 172.16.0.1 172.31.255.254 192.168.1.1 127.0.0.1 203.0.113.2",  # private-reference: allow -- scanner fixture.
        encoding="utf-8",
    )
    assert scan_private_references(tmp_path) == ["private IP found in addresses.txt"]


def test_private_reference_scan_allows_localhost(tmp_path: Path) -> None:
    (tmp_path / "localhost.txt").write_text("127.0.0.1 localhost", encoding="utf-8")
    assert scan_private_references(tmp_path) == []


def test_agent_compose_clients_do_not_drift() -> None:
    root = Path(__file__).resolve().parents[1]
    workflow = root / "plugins/agent_compose_workflow/client/agent_compose.py"
    strategy = root / "plugins/agent_compose_strategy/client/agent_compose.py"
    assert workflow.read_bytes() == strategy.read_bytes()


def test_release_build_uses_version_without_modifying_sources(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    original_manifests = {
        item["name"]: (root / item["path"] / "manifest.yaml").read_bytes()
        for item in discover(root)
    }

    def fake_runner(command: list[str], *, check: bool) -> subprocess.CompletedProcess[bytes]:
        assert check is True
        staging = Path(command[3])
        output = Path(command[5])
        with zipfile.ZipFile(output, "w") as archive:
            archive.write(staging / "manifest.yaml", "manifest.yaml")
        return subprocess.CompletedProcess(command, 0)

    packages = build_release(root, "1.2.3", tmp_path, "dify", runner=fake_runner)

    assert {package.name for package in packages} == {
        f"{name}-1.2.3.difypkg" for name in original_manifests
    }
    for package in packages:
        with zipfile.ZipFile(package) as archive:
            manifest = yaml.safe_load(archive.read("manifest.yaml"))
        assert manifest["version"] == "1.2.3"
        assert manifest["meta"]["version"] == "1.2.3"
    for item in discover(root):
        assert (root / item["path"] / "manifest.yaml").read_bytes() == original_manifests[
            item["name"]
        ]


@pytest.mark.parametrize("version", ["v1.2.3", "1.2", "1.2.3-rc1", "../1.2.3"])
def test_release_version_rejects_non_semver(version: str) -> None:
    with pytest.raises(ValueError, match="SemVer"):
        validate_version(version)
