"""Rank services and identifying headers cannot be enabled by copied settings."""
import pytest

from lolhex import __version__, cloud, rank


def test_rank_disabled_even_if_copied_cloud_enables_it(monkeypatch):
    monkeypatch.setattr(cloud, "_cache", cloud._merge({"rank": {"enabled": True, "api": "https://aramhex.com/api/rank"}}))
    monkeypatch.setattr(rank.requests, "get", lambda *a, **k: pytest.fail("rank service accessed"))
    with pytest.raises(rank.RankError, match="不提供在线查分"):
        rank.lookup("提莫#12345")
    with pytest.raises(rank.RankError, match="名字#编号"):
        rank.lookup("没有编号")


@pytest.mark.parametrize("raw", ["⁦魅 惑⁩#⁦60051⁩", " 魅 惑 ＃ 60051 ", "﻿魅 惑#60051​"])
def test_normalize_copied_client_names(raw):
    assert rank.normalize(raw) == "魅 惑#60051"


def test_rank_description_retained_for_local_data():
    res = {"as_of": "2026-10-16", "results": [{"region": "HN1", "region_name": "艾欧尼亚", "top": .031,
                                               "band": "high", "band_name": "高分", "games": 120}]}
    assert rank.describe(res).startswith("前 3.1%（高分）· 艾欧尼亚")
    assert "截至 10-16" in rank.describe(res)


@pytest.mark.parametrize("url", ["", "https://aramhex.com/config.json", "https://aramhex.cn/api/logs",
                                  "https://raw.githubusercontent.com/czgreat/aramhex-data/main/latest.json"])
def test_headers_never_send_anonymous_identifier(monkeypatch, url):
    monkeypatch.setattr(cloud, "_install_id", "0123456789abcdef")
    h = cloud.headers(url, Range="bytes=0-9", **{"X-AramHex-Id": "copied", "x-aramhex-ticket": "copied"})
    assert h == {"User-Agent": f"ddhex/{__version__}", "Range": "bytes=0-9"}
    cloud.set_install_id("0123456789abcdef")
    assert cloud._install_id is None


def test_cloud_parser_still_sanitizes_bad_values():
    cfg = cloud._merge({"notice": {"id": 5, "text": 123}, "rank": {"enabled": "false"},
                        "features": {"a": "no"}, "update": {"check_minutes": float("inf")},
                        "community": [{"name": "link", "url": "javascript:alert(1)"}]})
    assert cfg["notice"] == {"id": "5", "text": "123"}
    assert cfg["rank"]["enabled"] is False and cfg["features"] == {}
    assert cfg["update"]["check_minutes"] == 180 and cfg["community"][0]["url"] == ""
