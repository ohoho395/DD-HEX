"""Local redaction/tail helpers remain; remote requests cannot activate logs."""
import json
import logging

import pytest

from lolhex import cloud, logupload
from lolhex.config import Settings

def test_redact():
    t = logupload.redact(r"目录：C:\Users\zhangsan\AppData\Roaming\AramHex 查分 提莫队长#54321 对面 亚索#ABC12 GitHub #4 版本 #1234567",
                         "提莫队长#54321")
    assert "zhangsan" not in t and "提莫队长" not in t and "亚索" not in t
    assert r"C:\Users\<用户>\AppData" in t and "GitHub #4" in t and "#1234567" in t


def test_redact_case_and_spaces(monkeypatch):
    monkeypatch.setenv("USERNAME", "John Smith")
    monkeypatch.setenv("COMPUTERNAME", "DESKTOP-AB12CD")
    t = logupload.redact(r"C:\Users\john smith\x c:\users\Zhang San\y desktop-ab12cd hide on bush#kr1",
                         "Hide on bush#KR1")
    assert "john" not in t.lower() and "zhang" not in t.lower() and "desktop" not in t.lower() and "hide on" not in t



def test_copied_settings_and_cloud_never_upload_or_enable_remote_debug(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"send_usage": True, "install_id": "0123456789abcdef"}), encoding="utf-8")
    s = Settings.load(path)
    assert s.send_usage is False and s.install_id == ""
    # Even an in-memory caller cannot turn the removed upload feature back on.
    s.send_usage, s.install_id = True, "0123456789abcdef"
    remote = {"logs": {"url": "https://aramhex.com/api/logs", "request": [s.install_id], "verbose": [s.install_id + ":v1"]}}
    monkeypatch.setattr(logupload.requests, "post", lambda *a, **k: pytest.fail("logs uploaded"))
    assert logupload.maybe_upload(s, remote) == []
    monkeypatch.setattr(logging.getLogger(), "level", logging.INFO)
    assert not logupload.apply_verbose(s, remote) and logging.getLogger().level == logging.INFO
    assert "verbose_seen" not in s.extra
    s.debug_mode = True
    assert logupload.apply_verbose(s, {}) and logging.getLogger().level == logging.DEBUG


def test_local_tail_reader_keeps_recent_log_order_and_limit(tmp_path):
    (tmp_path / "ddhex.log").write_text("新文件\n" * 1000, encoding="utf-8")
    (tmp_path / "ddhex.log.1").write_text("上一个文件\n" * 300000, encoding="utf-8")
    body = logupload._read_recent(tmp_path, 2048 * 1024).decode("utf-8").replace("\r\n", "\n")
    assert body.endswith("新文件\n") and body.startswith("上一个文件\n")
    assert 1900 * 1024 < len(body.encode()) <= 2048 * 1024
    assert logupload._limit(cloud._merge({"logs": {"max_kb": 10 ** 9}})) == 4096 * 1024
