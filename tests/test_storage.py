"""Tests for bundle extraction, manifests, path safety and the cache manager."""

import zipfile
from pathlib import Path

import pytest

from nepher.storage.bundle import BundleManager, iter_bundle_files
from nepher.storage.cache import CacheManager
from nepher.storage.manifest import ManifestParser
from nepher.storage.paths import resolve_within, safe_env_id

MANIFEST = "id: demo-env\ncategory: navigation\nscenes:\n  - scene_id: s1\n    usd: scene.usd\n    omap_meta: omap/map.yaml\n"


def _zip(path: Path, members: dict) -> Path:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return path


@pytest.mark.parametrize("env_id", ["demo-env", "env_1.2", "abc123"])
def test_safe_env_id_accepts(env_id):
    assert safe_env_id(env_id) == env_id


@pytest.mark.parametrize("env_id", ["", "..", "../x", "a/b", "a\\b", ".hidden", "C:x", "a..b"])
def test_safe_env_id_rejects(env_id):
    with pytest.raises(ValueError):
        safe_env_id(env_id)


@pytest.mark.parametrize("rel", ["../x", "/etc/passwd", "C:\\x", "a/../../x"])
def test_resolve_within_rejects(tmp_path, rel):
    with pytest.raises(ValueError):
        resolve_within(tmp_path, rel)


def test_resolve_within_accepts(tmp_path):
    assert resolve_within(tmp_path, "a/b.usd") == (tmp_path / "a" / "b.usd").resolve()


def test_extract_bundle_resolves_asset_paths(tmp_path):
    zip_path = _zip(tmp_path / "b.zip", {"manifest.yaml": MANIFEST, "scene.usd": "x"})
    dest = tmp_path / "cache" / "demo-env"
    env = BundleManager.extract_bundle(zip_path, dest)
    assert env.cache_path == dest.resolve()
    assert env.scenes[0].usd == (dest / "scene.usd").resolve()
    assert env.scenes[0].omap_meta == (dest / "omap" / "map.yaml").resolve()
    assert [p.name for p in dest.parent.iterdir()] == ["demo-env"]


def test_extract_bundle_rejects_zip_slip(tmp_path):
    zip_path = _zip(tmp_path / "b.zip", {"manifest.yaml": MANIFEST, "../../evil.txt": "x"})
    dest = tmp_path / "cache" / "demo-env"
    with pytest.raises(ValueError):
        BundleManager.extract_bundle(zip_path, dest)
    assert not (tmp_path / "evil.txt").exists()
    assert not dest.exists()
    assert list(dest.parent.iterdir()) == []


def test_extract_bundle_without_manifest_leaves_nothing(tmp_path):
    zip_path = _zip(tmp_path / "b.zip", {"scene.usd": "x"})
    dest = tmp_path / "cache" / "demo-env"
    with pytest.raises(ValueError):
        BundleManager.extract_bundle(zip_path, dest)
    assert not dest.exists()


def test_failed_reextract_keeps_existing_cache(tmp_path):
    dest = tmp_path / "cache" / "demo-env"
    BundleManager.extract_bundle(_zip(tmp_path / "good.zip", {"manifest.yaml": MANIFEST}), dest)
    with pytest.raises(ValueError):
        BundleManager.extract_bundle(_zip(tmp_path / "bad.zip", {"x": "y"}), dest)
    assert (dest / "manifest.yaml").is_file()


def test_manifest_rejects_escaping_asset(tmp_path):
    (tmp_path / "manifest.yaml").write_text("scenes:\n  - scene_id: s\n    usd: ../outside.usd\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ManifestParser.parse(tmp_path / "manifest.yaml")


def test_manifest_rejects_empty_file(tmp_path):
    (tmp_path / "manifest.yaml").write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        ManifestParser.parse(tmp_path / "manifest.yaml")


def test_iter_bundle_files_skips_vcs_and_secrets(tmp_path):
    for rel in ["manifest.yaml", "a/scene.usd", ".git/config", ".env", "a/__pycache__/m.pyc", "b.pyc"]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x", encoding="utf-8")
    names = sorted(rel.as_posix() for _, rel in iter_bundle_files(tmp_path))
    assert names == ["a/scene.usd", "manifest.yaml"]


def test_cache_manager_clear_all_only_removes_environments(tmp_path):
    root = tmp_path / "cache"
    (root / "env-a").mkdir(parents=True)
    (root / "env-a" / "manifest.yaml").write_text("id: env-a", encoding="utf-8")
    (root / "unrelated.txt").write_text("keep", encoding="utf-8")
    manager = CacheManager(cache_dir=root)
    assert manager.list_cached() == ["env-a"]
    assert manager.clear_cache() is True
    assert (root / "unrelated.txt").exists()
    assert manager.list_cached() == []


def test_cache_manager_rejects_bad_ids(tmp_path):
    with pytest.raises(ValueError):
        CacheManager(cache_dir=tmp_path).clear_cache("../../x")


def test_migrate_updates_config(tmp_path):
    from nepher.config import get_config

    old, new = tmp_path / "old", tmp_path / "new"
    (old / "env-a").mkdir(parents=True)
    (old / "env-a" / "manifest.yaml").write_text("id: env-a", encoding="utf-8")
    CacheManager(cache_dir=old).migrate_cache(new)
    assert (new / "env-a" / "manifest.yaml").is_file()
    assert get_config().get_cache_dir() == new.resolve()
