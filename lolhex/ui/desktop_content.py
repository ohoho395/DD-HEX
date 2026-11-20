"""桌面资料与选卡页的排版。数据顺序由 panel / recommend 决定。"""
from html import escape

from .. import recommend
from ..data.tencent import RARITY_CN
from . import buildview


INK = "#172d30"
MUTED = "#526768"
ACCENT = "#006d61"


def _text(value, *, size=13, color=INK, bold=False):
    weight = "600" if bold else "400"
    return f"<span style='font-size:{size}px;color:{color};font-weight:{weight}'>{escape(str(value))}</span>"


def _heading(name, scope=""):
    return ("<p style='margin:12px 0 5px'>" + _text(name, size=17, bold=True)
            + ("　" + _text(scope, size=12, color=MUTED) if scope else "") + "</p>")


def _table(rows):
    """QLabel uses QTextDocument's HTML subset; keep tables intrinsically sized."""
    return "<table cellspacing='0' cellpadding='4'>" + "".join(rows) + "</table>"


def _row(name, content, detail=""):
    return (f"<tr><td valign='middle'>{name}</td><td valign='middle'>{content}</td>"
            f"<td valign='middle' align='right'>{detail}</td></tr>")


def _rate(row, show):
    win = row.get("win")
    if not show or win is None:
        return ""
    return _text(f"胜率 {win * 100:.1f}%", color=ACCENT)


def hero_html(d, icons, show_win):
    b = d.get("builds") or {}
    sections = []
    rows = []
    for index, build in enumerate((b.get("core") or [])[:3], 1):
        delimiter = "　→　" if build.get("ordered") else "　+　"
        items = delimiter.join(buildview.item(icons, it, 32) for it in build["items"])
        rows.append(_row(_text(f"方案 {index}", color=MUTED), items, _rate(build, show_win)))
    if rows:
        sections.extend([_heading("核心三件", d.get("core_band") or ""), _table(rows)])

    loadout = []
    starters = b.get("start") or []
    if starters:
        starter = starters[0]
        items = "　+　".join(buildview.item(icons, it, 24) for it in starter["items"])
        loadout.append(_row(_text("出门装", color=MUTED), items, _rate(starter, show_win)))
    for index, shoe in enumerate((b.get("shoes") or [])[:2]):
        loadout.append(_row(_text("鞋子" if index == 0 else "", color=MUTED),
                            buildview.item(icons, shoe["item"], 24), _rate(shoe, show_win)))
    if d.get("item_stats"):
        items = [buildview.item(icons, it["item"], 24) + " " + _rate(it, show_win)
                 for it in d["item_stats"][:6]]
        for index in range(0, len(items), 3):
            loadout.append(_row(_text("常出装备" if index == 0 else "", color=MUTED),
                                "　".join(items[index:index+3])))
    skills = d.get("skills") or []
    keys = [key for key in (skills[0].get("max") or []) if key in ("Q", "W", "E")] if skills else []
    if keys:
        priority = f"主 {keys[0]}" + (f"　副 {keys[1]}" if len(keys) > 1 else "")
        loadout.append(_row(_text("技能加点", color=MUTED), _text(priority, bold=True), _rate(skills[0], show_win)))
    if loadout:
        sections.extend([_heading("装备与加点"), _table(loadout)])

    spell_section = ""
    spells = d.get("summoners") or []
    if spells:
        scope = " · ".join(str(s) for s in (d.get("summoner_source"), d.get("summoner_source_date")) if s)
        cells = []
        for spell in spells:
            pair = buildview.spell_pair(icons, spell, 26)
            pick = spell.get("pick")
            pick_text = _text(f"出场 {pick*100:.1f}%", size=12, color=MUTED) if pick is not None else ""
            cells.append("<td valign='top'>" + pair + "<br>" + _rate(spell, show_win)
                         + ("<br>" if show_win and pick_text else "") + pick_text + "</td>")
        spell_section = (_heading("召唤师技能", scope) + "<table width='100%' cellspacing='0' cellpadding='5'>"
                         + "<tr>" + "".join(cells) + "</tr></table>")

    top = sorted((a for a in d.get("augments", []) if a.get("delta") is not None and a.get("sample") != "low"),
                 key=lambda a: -a["delta"])[:8]
    ranking = ""
    if top:
        rows = []
        for aug in top:
            tier = " · ".join(s for s in (RARITY_CN.get(aug.get("rarity")), aug.get("tier")) if s)
            rows.append(_row(_text(aug["name"], bold=True), _text(tier, size=12, color=MUTED),
                             _text(f"{aug['delta']:+.1f}", color=ACCENT)))
        ranking = _heading("推荐海克斯") + _text("相对英雄基准 · 平滑后百分点", size=12, color=MUTED) + (
            "<table width='100%' cellspacing='0' cellpadding='5'>" + "".join(rows) + "</table>")
    if ranking and sections:
        content = ("<table width='100%' cellspacing='0' cellpadding='5'><tr>"
                "<td width='55%' valign='top'>" + "".join(sections) + "</td>"
                "<td width='45%' valign='top' bgcolor='#f4f7f3'>" + ranking + "</td></tr></table>")
    else:
        content = ranking or "".join(sections)
    return content + spell_section or _text("当前英雄暂无装备或海克斯资料", color=MUTED)


def offer_html(row, show_win):
    verdict = row["verdict"]
    label = {"best": "首选", "ok": "可选", "reroll": "可考虑刷新",
             "nodata": "无数据"}.get(verdict, "未识别")
    if verdict == "best" and row.get("sample_warning"):
        label = "相对较好，仅供参考"
    tone = ACCENT if verdict == "best" and not row.get("sample_warning") else MUTED
    lines = [_text(label, size=12, bold=True, color=tone),
             _text(row.get("name") or "未识别", size=20, bold=True)]
    tier = " · ".join(s for s in (RARITY_CN.get(row.get("rarity")), row.get("tier")) if s)
    if tier:
        lines.append(_text(tier, size=12, color=MUTED))
    if show_win:
        rate = recommend.win_text(row)
        if rate:
            lines.append(_text(rate, size=16, bold=True))
    if row.get("basis") == "hero_win" and row.get("score") is not None:
        lines.append(_text(f"较基准 {row['score']:+.1f}", color=MUTED))
    if row.get("games") is not None:
        lines.append(_text(f"样本 {row['games']:,} 局", color=MUTED))
    if row.get("thin") or row.get("sample_warning"):
        lines.append(_text("样本太少" if row.get("thin") == "too_few" else "样本偏少", color="#856128"))
    if verdict == "nodata":
        note = recommend.NODATA_NOTE if row.get("basis") == "excluded" else recommend.NEW_NOTE
        lines.append(_text(note, color=MUTED))
    elif row.get("basis") == "pbe":
        games = row.get("pbe_games")
        data = f"全英雄 {games} 局" if games else ""
        if show_win and games and row.get("pbe_win") is not None:
            data += f" · 胜率 {row['pbe_win']*100:.1f}%"
        lines.append(_text(f"{recommend.PBE_NOTE}　{data}".strip(), color=MUTED))
    elif row.get("basis") == "tier_only":
        lines.append(_text("按官方评级估计", color=MUTED))
    elif row.get("basis") == "rare":
        lines.append(_text("本英雄样本不足", color=MUTED))
    return "<br>".join(lines)
