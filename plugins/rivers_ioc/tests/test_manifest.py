from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_manifest_identity_and_compatibility():
    manifest = yaml.safe_load((ROOT / "manifest.yaml").read_text())
    assert manifest["name"] == "rivers_ioc"
    assert manifest["author"] == "chaitin"
    assert manifest["version"] == manifest["meta"]["version"]
    assert manifest["meta"]["minimum_dify_version"] == "1.15.0"
    assert manifest["meta"]["runner"]["version"] == "3.12"


def test_all_declared_sources_exist():
    provider = yaml.safe_load((ROOT / "provider/rivers_ioc.yaml").read_text())
    tool = yaml.safe_load((ROOT / "tools/rivers_ioc.yaml").read_text())
    assert (ROOT / provider["extra"]["python"]["source"]).is_file()
    assert (ROOT / tool["extra"]["python"]["source"]).is_file()
    assert (ROOT / "_assets/icon.svg").is_file()
    assert (ROOT / "PRIVACY.md").is_file()
