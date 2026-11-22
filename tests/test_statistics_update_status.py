"""Remote-check outcomes must never be inferred from the bool activation API."""
from types import SimpleNamespace

import pytest

from conftest import make_dataset
from test_public import _publish, server  # loopback fixture
from lolhex import distribution, update
from lolhex.data import public
from lolhex.data.public import PublicStore
from lolhex.ui.data_status import data_status_html, statistics_check_message, statistics_settings_text
from lolhex.ui.mainwindow import MainWindow


def manual(store, enabled=True):
    window = SimpleNamespace(engine=SimpleNamespace(store=store, settings=SimpleNamespace(check_data_updates=enabled)))
    return MainWindow._sync_data_now(window)


def test_disabled_deferred_and_busy_do_not_claim_latest_or_touch_remote(tmp_path, monkeypatch):
    def unexpected(*a, **kw):
        pytest.fail("No remote request is allowed in an unchecked state")
    monkeypatch.setattr(public.requests, "get", unexpected)
    store = PublicStore(tmp_path / "data", managed_official=True, check_updates=False)
    assert not store.sync_data(force=True, manual=True)
    assert store.sync_state == "disabled" and "关闭" in manual(store, enabled=False)
    store.check_updates = True
    store.hold = lambda: True
    assert "推迟" in manual(store) and store.sync_state == "deferred"
    assert store.last_successful_check_at is None
    store.hold = lambda: False
    store._sync_lock.acquire()
    try:
        assert "正在进行" in manual(store) and store.sync_state == "checking"
    finally:
        store._sync_lock.release()
    assert "尚未成功检查" in statistics_settings_text(store.status(), enabled=True)


def test_remote_unchanged_updated_failed_and_persisted_check_time(tmp_path, server, monkeypatch):
    remote, base = server
    bundled = tmp_path / "bundled"
    day = "2026-11-01T12:00:00+08:00"
    make_dataset(bundled, snapshot_at=day)
    _publish(remote, day)
    store = PublicStore(tmp_path / "data", bundled=bundled, base_url=base, managed_official=True)
    assert not store.sync_data(force=True, manual=True)
    assert store.sync_state == "unchanged" and store.last_successful_check_at > 0
    first_check = store.last_successful_check_at
    text = statistics_settings_text(store.status(), enabled=True)
    assert "当前统计无需更新" in text and "样本截至 11-01" in text and "北京时间" in text
    assert "内置快照" in text and "未配置独立发布源" in text
    restarted = PublicStore(tmp_path / "data", bundled=bundled, base_url=base, managed_official=True)
    assert restarted.last_successful_check_at == first_check
    assert restarted.sync_state == "never_checked"  # a persisted timestamp is not a fresh check
    _publish(remote, "2026-11-02T12:00:00+08:00")
    assert store.sync_data(force=True, manual=True)
    assert store.sync_state == "updated" and store.dataset.snapshot_at.startswith("2026-11-02")
    successful = store.last_successful_check_at
    def unavailable(*a, **kw):
        raise public.requests.ConnectionError("simulated offline")
    monkeypatch.setattr(public.requests, "get", unavailable)
    assert not store.sync_data(force=True, manual=True)
    assert store.sync_state == "failed" and store.last_successful_check_at == successful
    assert "检查失败" in manual(store) and "最新" not in manual(store)


def test_download_staged_during_game_is_not_reported_as_unchanged(tmp_path, server, monkeypatch):
    remote, base = server
    bundled = tmp_path / "bundled"
    make_dataset(bundled, snapshot_at="2026-11-01T12:00:00+08:00")
    _publish(remote, "2026-11-02T12:00:00+08:00")
    store = PublicStore(tmp_path / "data", bundled=bundled, base_url=base, managed_official=True)
    original = public.download
    def enter_game(*a, **kw):
        original(*a, **kw)
        store.hold = lambda: True
    monkeypatch.setattr(public, "download", enter_game)
    assert not store.sync_data(force=True, manual=True)
    assert store.sync_state == "staged" and store.last_successful_check_at is not None
    assert "等待对局结束后启用" in manual(store)
    assert store.dataset.snapshot_at.startswith("2026-11-01")
    store.hold = lambda: False
    assert store.sync_data()  # applies the downloaded snapshot without pretending to check again
    assert store.sync_state == "updated" and store.dataset.snapshot_at.startswith("2026-11-02")


def test_independent_404_and_invalid_release_cannot_confirm_latest(monkeypatch):
    monkeypatch.setattr(distribution, "UPDATE_REPO", "independent-owner/ddhex")
    monkeypatch.setattr(update.requests, "get", lambda *a, **kw: SimpleNamespace(status_code=404))
    assert update.check("0.1.3") is None
    with pytest.raises(ValueError, match="未完成版本核对"):
        update.check("0.1.3", strict=True)
    class InvalidRelease:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"tag_name": ""}
    monkeypatch.setattr(update.requests, "get", lambda *a, **kw: InvalidRelease())
    with pytest.raises(ValueError, match="有效的版本号"):
        update.check("0.1.3", strict=True)


def test_versions_are_neutral_and_stale_timestamp_is_not_sample_freshness():
    status = {"dataset": True, "patch": "16.22", "dataset_patch": "16.23",
              "dataset_snapshot": "2026-11-01T12:00:00+08:00", "data_last_checked_at": 1700000000,
              "data_check_state": "failed", "dataset_origin": "downloaded"}
    text = data_status_html(status)
    assert "16.23" in text and "官方资料 16.22" in text
    assert "游戏已更新" not in text and "还没更新" not in text
    detailed = statistics_settings_text(status, enabled=True, update_source="https://github.com/independent/ddhex/releases")
    assert "检查失败" in detailed and "样本截至 11-01" in detailed and "上次成功检查：2023" in detailed
    assert "已下载快照" in detailed and "软件更新源：https://github.com/independent/ddhex/releases" in detailed
    assert "尚未完成" in statistics_check_message({})
