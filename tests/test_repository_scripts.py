from pathlib import Path

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
