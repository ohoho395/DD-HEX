"""游戏内详情窗口的两页正文，使用 Qt 支持的表格与内联样式。"""
from html import escape

from ..panel import split_augment_samples
from . import buildview

INK = "#d6d6d6"
MUTED = "#adadad"
ACCENT = "#f7f7f7"


def _text(value, color=INK, size=13, bold=False):
    return (f"<span style='font-size:{size}px;color:{color};font-weight:{600 if bold else 400}'>"
            + escape(str(value)) + "</span>")


def _pct(value):
    return "—" if value is None else f"{value*100:.1f}%"


def _header(title, note=""):
    return ("<table width='100%' cellspacing='0' cellpadding='1'><tr>"
            "<td align='left'>" + _text(title, size=15, bold=True) + "</td>"
            "<td align='right'>" + _text(note, MUTED, 11) + "</td></tr></table>")


def _table(rows):
    return "<table width='100%' cellspacing='0' cellpadding='3'>" + "".join(rows) + "</table>"


def _row(left, middle, right=""):
    return (f"<tr><td valign='middle'>{left}</td><td valign='middle'>{middle}</td>"
            f"<td valign='middle' align='right'>{right}</td></tr>")


def _item(icons, item, size=22):
    return buildview.item(icons, {**item, "name": escape(str(item.get("name") or item.get("id") or ""))}, size)


def _loadout(d, icons, show_win):
    builds = d.get("builds") or {}
    parts = []

    def rate(row):
        return _text(_pct(row["win"]), ACCENT, size=14, bold=True) if show_win and row.get("win") is not None else ""

    rows = []
    for i, route in enumerate((builds.get("core") or [])[:3], 1):
        joiner = " → " if route.get("ordered") is True else " + "
        items = joiner.join(_item(icons, it, 26) for it in route.get("items") or [])
        if items:
            rows.append(_row(_text(f"方案 {i}", MUTED), items, rate(route)))
    if rows:
        note = " · ".join(s for s in (d.get("core_band"), "胜率" if show_win else "") if s)
        parts += [_header("核心三件", note), _table(rows)]

    spells = []
    for row in (d.get("summoners") or [])[:3]:
        entries = [{**spell, "name": escape(str(spell.get("name") or ""))} for spell in row.get("spells") or []]
        pair = buildview.spell_pair(icons, {"spells": entries}, 22)
        pick = _text(f"出场 {_pct(row['pick'])}", MUTED) if row.get("pick") is not None else ""
        spells.append(_row(pair, pick, rate(row)))
    if spells:
        source = " · ".join(str(s) for s in (d.get("summoner_source"), d.get("summoner_source_date")) if s)
        parts += [_header("召唤师技能", source), _table(spells)]

    support = []
    skills = d.get("skills") or []
    order = [k for k in (skills[0].get("max") or []) if k in ("Q", "W", "E")] if skills else []
    if order:
        priority = "　".join(f"{role} {key}" for role, key in zip(("主", "副"), order))
        support.append(_row(_text("加点", MUTED), _text(priority, bold=True), rate(skills[0])))
    for label, entries in (("出门装", (builds.get("start") or [])[:1]),
                           ("鞋子", (builds.get("shoes") or [])[:2])):
        for i, row in enumerate(entries):
            items = row.get("items") or ([row["item"]] if row.get("item") else [])
            support.append(_row(_text(label if i == 0 else "", MUTED),
                                " + ".join(_item(icons, item) for item in items), rate(row)))
    common = (d.get("item_stats") or [])[:4]
    if common:
        values = [_item(icons, row["item"], 20) + " " + rate(row) for row in common]
        for i in range(0, len(values), 2):
            support.append(_row(_text("常出装备" if i == 0 else "", MUTED), "　".join(values[i:i+2])))
    if support:
        parts += [_header("装备与加点"), _table(support)]
    return "".join(parts) or _text("暂无出装与加点资料", MUTED)


def _augments(d, reliable_games):
    qualified, low = split_augment_samples(d.get("augments") or [], reliable_games)
    sections = []
    for label, rows in (("推荐海克斯", qualified[:5]), ("小样本参考", low[:2])):
        if not rows:
            continue
        threshold = f"门槛 {reliable_games:,} 局" if label == "推荐海克斯" else f"不足 {reliable_games:,} 局"
        scopes = {r.get("evidence_scope") or "全段位" for r in rows}
        scope = next(iter(scopes)) if len(scopes) == 1 else ""
        header = _row(_text("海克斯", MUTED, 12), _text(scope + "样本", MUTED, 12),
                      _text("较基准（百分点）", MUTED, 12))
        result = [header]
        for row in rows:
            n = row.get("evidence_games") or row.get("games") or 0
            count = f"{n:,} 局" if scope else f"{row.get('evidence_scope') or '全段位'} {n:,} 局"
            result.append(_row(_text(row["name"]), _text(count, MUTED),
                               _text(f"{row['delta']:+.1f}", ACCENT if label == "推荐海克斯" else MUTED)))
        sections += [_header(label, threshold), _table(result)]
    return "".join(sections) or _text("当前英雄暂无可靠海克斯样本", MUTED)


def render_details(d, icons, show_win, reliable_games, view):
    """根据真实英雄资料渲染出装或海克斯正文；不会修改引擎或读取网络。"""
    if not d:
        return _text("选定英雄后可查看详情", MUTED)
    if view == "loadout":
        return _loadout(d, icons, show_win)
    if view == "augments":
        return _augments(d, reliable_games)
    raise ValueError(f"未知详情页：{view!r}")
