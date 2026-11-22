from lolhex.ui.desktop_content import hero_html


class LocalIcons:
    def local(self, kind, asset_id, url):
        return f"/tmp/{kind}/{asset_id}.png"


def test_route_table_pairs_icons_with_full_names_and_correct_metrics():
    names = ["残疫", "兰德里的折磨", "灭世者的死亡之帽"]
    data = {"builds": {"core": [{"ordered": True, "win": .5397, "pick": .0315,
                                 "items": [{"id": str(i), "name": name} for i, name in enumerate(names)]}]}}
    for compact in (False, True):
        html = hero_html(data, LocalIcons(), True, compact=compact)
        for col in ("路线", "第一件", "第二件", "第三件", "出场率", "胜率"):
            assert col in html
        assert all(name in html for name in names) and html.count("<img") == 3
        assert "54.0%" in html and "3.1%" in html
        hidden = hero_html(data, LocalIcons(), False, compact=compact)
        assert "54.0%" not in hidden and "胜率" not in hidden and "3.1%" in hidden


def test_unordered_or_missing_rows_do_not_imply_order_or_zero_rates():
    row = {"ordered": False, "win": None, "pick": None,
           "items": [{"name": "A"}, {"name": "B"}, {"name": "C"}]}
    html = hero_html({"builds": {"core": [row]}}, None, True)
    assert "无固定顺序" in html and "第一件" not in html
    assert "0.0%" not in html and "按胜率降序" not in html
