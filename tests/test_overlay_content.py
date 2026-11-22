from lolhex.ui.overlay_content import render_details


class Icons:
    def local(self, kind, asset_id, url):
        return f"/cache/{kind}-{asset_id}.png"


def test_loadout_table_uses_real_items_order_and_display_setting():
    data = {"builds": {"core": [{"ordered": True, "items": [{"id": "123", "name": "甲"},
                                                            {"id": "234", "name": "乙"}], "win": .567}],
                       "shoes": [{"item": {"id": "1", "name": "鞋"}}]},
            "summoners": [{"spells": [{"id": "4", "name": "闪现"}], "pick": .451, "win": .511}],
            "skills": [{"max": ["Q", "W"]}],
            "item_stats": [{"item": {"id": "432", "name": "装备"}, "win": .60}]}
    html = render_details(data, Icons(), True, 1000, "loadout")
    assert all(s in html for s in ("方案 1", "item-123.png", " → ", "56.7%", "45.1%",
                                   "spell-4.png", "主 Q", "副 W", "item-432.png", "鞋子"))
    hidden = render_details(data, None, False, 1000, "loadout")
    assert "56.7%" not in hidden and "51.1%" not in hidden
    assert "45.1%" in hidden and "甲 → 乙" in hidden and "常出装备" in hidden


def test_augment_page_keeps_low_sample_and_scope_separate():
    data = {"augments": [{"name": "低样本", "delta": 8.4, "games": 20, "evidence_games": 278,
                          "evidence_scope": "全段位"},
                         {"name": "已达标", "delta": 3.2, "games": 25, "evidence_games": 2300,
                          "evidence_scope": "全段位"},
                         {"name": "不参与评分", "delta": None, "games": 3000}]}
    html = render_details(data, None, True, 1000, "augments")
    assert html.index("已达标") < html.index("小样本参考") < html.index("低样本")
    assert all(s in html for s in ("全段位样本", "2,300 局", "278 局", "+3.2", "+8.4"))
    assert "不参与评分" not in html and "胜率" not in html
    assert "推荐海克斯" not in render_details(data, None, True, 9999, "augments")
    assert "暂无可靠" in render_details({"augments": []}, None, True, 1000, "augments")
