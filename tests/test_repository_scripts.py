from pathlib import Path

from scripts.discover_plugins import discover


def test_discover_returns_sorted_plugins(tmp_path: Path) -> None:
    for name in ("zeta", "alpha"):
        plugin = tmp_path / "plugins" / name
        plugin.mkdir(parents=True)
        (plugin / "manifest.yaml").touch()
    assert [item["name"] for item in discover(tmp_path)] == ["alpha", "zeta"]
