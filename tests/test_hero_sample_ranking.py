"""首选门槛和跨分段样本应与实际选卡一致。"""
from lolhex import recommend
from lolhex.panel import hero_panel, split_augment_samples
from lolhex.ui.desktop_content import hero_html, offer_html


def test_low_sample_rows_stay_separate_when_threshold_changes():
    rows = [
        {"name": "厄运", "rarity": "gold", "delta": 6.1, "games": 278, "evidence_games": 278},
        {"name": "有始有终", "rarity": "gold", "delta": 2.0, "games": 5000, "evidence_games": 5000},
        {"name": "无数据", "delta": None, "evidence_games": 0},
    ]
    data = {"augments": rows}
    main, reference = split_augment_samples(rows, 1000)
    assert [x["name"] for x in main] == ["有始有终"]
    assert [x["name"] for x in reference] == ["厄运"]
    html = hero_html(data, None, True, 1000)
    assert html.index("有始有终") < html.index("小样本参考") < html.index("厄运")
    assert "278 局" in html and "全段位" in html
    assert "小样本参考" not in hero_html(data, None, True, 250)


def test_band_rank_uses_same_game_count_as_offer(store):
    store.set_band("high")
    _, band = store.dataset.table("high")
    band["17"]["2128"] = {"games": 80, "wins": 76, "win_rate": .95}
    row = next(a for a in hero_panel(store, "17")["augments"] if a["id"] == "2128")
    slot = recommend.evaluate(store, "17", ["2128", "1029", None])["slots"][0]
    assert row["games"] == 80 and row["evidence_games"] == slot["games_all"]
    assert row["evidence_games"] >= 1000 and row["evidence_scope"] == "全段位"
    assert split_augment_samples([row], 1000)[0] == [row]


def test_missing_sample_cards_explain_actual_basis():
    for basis, why in [("rare", "本英雄暂无可靠样本"), ("tier_only", "仅有官方评级，暂无胜率样本")]:
        row = {"verdict": "nodata", "basis": basis, "name": "卡名"}
        assert why in offer_html(row, True)
        assert recommend.NEW_NOTE not in offer_html(row, True)
