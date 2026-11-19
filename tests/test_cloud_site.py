"""Independent release has no inherited service or application update fallback."""
import json

import pytest

from lolhex import BACKUP_SITES, WEBSITE, cloud, distribution, patch, update
from lolhex.config import Settings, app_home
from lolhex.data.public import PublicStore


def test_copied_cloud_cannot_enable_network(monkeypatch, tmp_path):
    monkeypatch.setenv("DDHEX_HOME", str(tmp_path))
    payload = {"site": {"urls": ["https://aramhex.com"]},
               "mirrors": {"update": ["https://aramhex.com/u/{version}"], "data": ["https://aramhex.com/u/data"]},
               "rank": {"enabled": True}, "logs": {"request": ["0123456789abcdef"]},
               "settings": [{"force": {"show_winrate": False}}]}
    (app_home() / "cloud.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(cloud, "_cache", None)
    def no_request(*a, **k):
        pytest.fail("copied cloud made a network request")
    monkeypatch.setattr(cloud.requests, "get", no_request)
    assert cloud.get()["settings"] == []
    assert cloud.refresh()["mirrors"] == {"update": [], "data": [], "official": []}
    assert cloud.refresh(url="https://aramhex.com/config.json") == cloud.get()
    assert cloud.sites() == [] and cloud.site() == "" and not cloud.own("https://aramhex.com/api/logs")
    assert WEBSITE == "" and BACKUP_SITES == ()
    assert patch.sources_for("0.2.0") == []
    assert update.check("0.1.0", strict=True) is None
    assert update.download_page() == ""


def test_default_store_never_syncs_until_user_opts_in(tmp_path, monkeypatch):
    def no_request(*a, **k):
        pytest.fail("statistics accessed before opt-in")
    monkeypatch.setattr(cloud.requests, "get", no_request)
    store = PublicStore(tmp_path, managed_official=True, check_updates=Settings().check_data_updates)
    assert store.check_updates is False
    assert store.sync_data(force=True) is False
    assert store.sync_data(force=True, manual=True) is False
    assert store.base_urls == [distribution.DATA_RAW_URL]
    seen = []
    def unavailable(url, **kw):
        seen.append(url)
        raise cloud.requests.ConnectionError("offline")
    monkeypatch.setattr(cloud.requests, "get", unavailable)
    store.check_updates = True
    store.sync_data(force=True)
    assert seen == [distribution.DATA_RAW_URL + "/latest.json"]


@pytest.mark.parametrize("repo", ["czgreat/aramhex", "CZGREAT/ARAMHEX", "czgreat/aramhex-data", "https://github.com/me/fork", "bad"])
def test_update_repo_rejects_upstream_and_invalid_values(monkeypatch, repo):
    monkeypatch.setattr(distribution, "UPDATE_REPO", repo)
    with pytest.raises(ValueError):
        update.check("0.1.0")
    with pytest.raises(ValueError):
        patch.sources_for("0.2.0")


def test_independent_repo_only(monkeypatch):
    monkeypatch.setattr(distribution, "UPDATE_REPO", "example-owner/ddhex")
    asked = []
    class Resp:
        status_code = 404
    monkeypatch.setattr(cloud.requests, "get", lambda url, **kw: asked.append(url) or Resp())
    assert update.check("0.1.0") is None
    assert asked == ["https://api.github.com/repos/example-owner/ddhex/releases/latest"]
    assert patch.sources_for("0.2.0") == [
        "https://raw.githubusercontent.com/example-owner/ddhex/updates-v0.2.0",
        "https://raw.githubusercontent.com/example-owner/ddhex/updates"]
    assert update.download_page() == "https://github.com/example-owner/ddhex/releases"


@pytest.mark.parametrize("url", ["https://aramhex.com/u/latest.json", "https://aramhex.cn/u/latest.json",
                                   "https://api.github.com/repos/czgreat/aramhex/releases/latest",
                                   "https://raw.githubusercontent.com/czgreat/aramhex-data/main/latest.json"])
def test_explicit_upstream_program_updates_are_refused(url):
    with pytest.raises(ValueError):
        distribution.reject_upstream_update(url)
