"""CLI behaviour tests with a fake API client."""

import io
import zipfile

from click.testing import CliRunner

from nepher.api.client import APIError
from nepher.cli.main import main


class FakeClient:
    def __init__(self, env_error=None, envs=None, bundle=None):
        self.env_error = env_error
        self.envs = envs or []
        self.bundle = bundle
        self.searched = False

    def get_environment(self, env_id):
        if self.env_error:
            raise self.env_error
        return {"id": env_id, "category": "navigation"}

    def list_environments(self, **kwargs):
        self.searched = True
        return self.envs

    def download_environment(self, env_id, dest_path):
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dest_path.write_bytes(self.bundle)
        return dest_path


def _bundle(manifest="id: demo-env\n"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("manifest.yaml", manifest)
    return buf.getvalue()


def _run(monkeypatch, client, *args):
    monkeypatch.setattr("nepher.cli.commands.download.get_client", lambda api_key=None: client)
    return CliRunner().invoke(main, ["download", *args])


def test_download_unauthorized_does_not_fall_back_to_search(monkeypatch, tmp_path):
    client = FakeClient(env_error=APIError("Unauthorized", status_code=401))
    result = _run(monkeypatch, client, "demo-env", "--cache-dir", str(tmp_path))
    assert result.exit_code == 1
    assert "Unauthorized" in result.output
    assert client.searched is False


def test_download_404_uses_exact_name_only(monkeypatch, tmp_path):
    client = FakeClient(
        env_error=APIError("Not found", status_code=404),
        envs=[{"id": "demo-env-v2", "original_name": "demo-env-v2"}],
    )
    cache = tmp_path / "cache"
    result = _run(monkeypatch, client, "demo-env", "--cache-dir", str(cache))
    assert result.exit_code == 1
    assert "not found" in result.output
    assert not cache.exists()


def test_download_extracts_into_cache(monkeypatch, tmp_path):
    cache = tmp_path / "cache"
    result = _run(monkeypatch, FakeClient(bundle=_bundle()), "demo-env", "--cache-dir", str(cache))
    assert result.exit_code == 0, result.output
    assert (cache / "demo-env" / "manifest.yaml").is_file()
    assert sorted(p.name for p in cache.iterdir()) == ["demo-env"]


def test_download_rejects_unsafe_server_id(monkeypatch, tmp_path):
    client = FakeClient(bundle=_bundle())
    client.get_environment = lambda env_id: {"id": "../escape"}
    result = _run(monkeypatch, client, "demo-env", "--cache-dir", str(tmp_path / "cache"))
    assert result.exit_code == 1
    assert not (tmp_path / "escape").exists()


def test_login_rejects_bad_prefix():
    result = CliRunner().invoke(main, ["login", "--api-key", "not-a-key"])
    assert result.exit_code == 1


def test_config_set_api_key_is_refused():
    result = CliRunner().invoke(main, ["config", "set", "api_key", "nepher_x"])
    assert result.exit_code == 1
