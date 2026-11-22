"""桌面资料与选卡页的排版。数据顺序由 panel / recommend 决定。"""
from html import escape

from .. import recommend
from ..panel import split_augment_samples
from ..data.tencent import RARITY_CN


INK = "#253630"
MUTED = "#57695f"
ACCENT = "#256951"


def _text(value, *, size=14, color=INK, bold=False):
    weight = "600" if bold else "400"
    return f"<span style='font-size:{size}px;color:{color};font-weight:{weight}'>{escape(str(value))}</span>"


def _pct(value):
    return "—" if value is None else f"{value * 100:.1f}%"


def _heading(name, scope=""):
    return ("<table width='100%' cellspacing='0' cellpadding='0'><tr>"
            "<td style='padding:14px 0 8px'>" + _text(name, size=19, bold=True) + "</td>"
            "<td align='right' valign='middle' style='padding:14px 0 8px'>"
            + _text(scope, size=12, color=MUTED) + "</td></tr></table>")


def _table(headings, rows, numeric=(), *, compact=False):
    pad = 4 if compact else 7

    def row(cells, header=False):
        out = []
        for i, cell in enumerate(cells):
            fill = " bgcolor='#eef0ea'" if header else ""
            align = "right" if i in numeric else "left"
            content = _text(cell, size=12, color=MUTED, bold=True) if header else cell
            out.append(f"<td valign='middle' align='{align}'{fill} "
                       f"style='border-bottom:1px solid #d9ded7'>{content}</td>")
        return "<tr>" + "".join(out) + "</tr>"

    return (f"<table width='100%' cellspacing='0' cellpadding='{pad}' style='border-collapse:collapse'>"
            + row(headings, header=True) + "".join(row(cells) for cells in rows) + "</table>")


def _icon(icons, asset, kind, size):
    path = icons.local(kind, asset.get("id"), asset.get("icon")) if icons and asset.get("id") else None
    return f'<img src="{escape(str(path), quote=True)}" width="{size}" height="{size}" align="middle">' if path else ""


def _named_item(icons, item, size):
    icon = _icon(icons, item, "item", size)
    return (icon + " " if icon else "") + _text(item.get("name") or item.get("id") or "—", size=14)


def _core_routes(d, icons, show_win, compact):
    builds = (d.get("builds") or {}).get("core") or []
    if not builds:
        return ""
    builds = builds[:3]
    ordered = all(b.get("ordered") is True for b in builds)
    columns = ["路线", *(["第一件", "第二件", "第三件"] if ordered else ["装备一", "装备二", "装备三"]), "出场率"]
    if show_win:
        columns.append("胜率")
    rows = []
    for i, b in enumerate(builds, 1):
        note = "（无固定顺序）" if not ordered and b.get("ordered") is not True else ""
        cells = [_text(f"方案 {i}{note}", color=MUTED, size=13)]
        entries = b.get("items") or []
        cells.extend(_named_item(icons, entries[j], 22 if compact else 28) if j < len(entries) else _text("—")
                     for j in range(3))
        cells.append(_text(_pct(b.get("pick"))))
        if show_win:
            cells.append(_text(_pct(b.get("win")), color=ACCENT, bold=True))
        rows.append(cells)
    rates = [b.get("win") for b in builds]
    sort_note = "按胜率降序" if show_win and all(v is not None for v in rates) and rates == sorted(rates, reverse=True) else ""
    sub = " · ".join(s for s in (d.get("core_band"), sort_note) if s)
    return _heading("核心三件", sub) + _table(columns, rows, numeric=(4, 5), compact=compact)


def _augment_ranking(d, reliable_games, compact):
    qualified, low = split_augment_samples(d.get("augments", []), reliable_games)
    groups = []
    for label, rows in (("推荐海克斯", qualified[:8]), ("小样本参考", low[:3])):
        if not rows:
            continue
        scopes = {row.get("evidence_scope") or "全段位" for row in rows}
        scope = next(iter(scopes)) if len(scopes) == 1 else ""
        columns = ["海克斯", "稀有度", f"{scope}样本数", "较基准（百分点）"]
        data = []
        for a in rows:
            games = a.get("evidence_games") or a.get("games") or 0
            amount = f"{games:,} 局" if scope else f"{a.get('evidence_scope') or '全段位'} {games:,} 局"
            rarity = " · ".join(s for s in (RARITY_CN.get(a.get("rarity")), a.get("tier")) if s)
            data.append([_text(a["name"]), _text(rarity, size=13, color=MUTED), _text(amount),
                         _text(f"{a['delta']:+.1f}", color=ACCENT, bold=True)])
        limit = ("首选样本门槛" if label == "推荐海克斯" else "不足首选门槛") + f" {reliable_games:,} 局"
        groups.append(_heading(label, limit) + _table(columns, data, numeric=(2, 3), compact=compact))
    return "".join(groups)


def _spells_and_skills(d, icons, show_win, compact):
    out = []
    spells = d.get("summoners") or []
    if spells:
        scope = " · ".join(str(s) for s in (d.get("summoner_source"), d.get("summoner_source_date")) if s)
        columns = ["技能组合", "出场率"] + (["胜率"] if show_win else [])
        rows = []
        for row in spells:
            pair = row.get("spells") or []
            images = " ".join(_icon(icons, spell, "spell", 22) for spell in pair).strip()
            names = " + ".join(s.get("name") or str(s.get("id") or "") for s in pair)
            cells = [(images + "　" if images else "") + _text(names), _text(_pct(row.get("pick")))]
            if show_win:
                cells.append(_text(_pct(row.get("win")), color=ACCENT))
            rows.append(cells)
        out += [_heading("召唤师技能", scope), _table(columns, rows, numeric=(1, 2), compact=compact)]
    skills = d.get("skills") or []
    keys = [k for k in (skills[0].get("max") or []) if k in ("Q", "W", "E")] if skills else []
    if keys:
        words = "　".join(_text(role, color=MUTED) + " " + _text(key, bold=True)
                          for role, key in zip(("主升", "副升"), keys))
        win = skills[0].get("win")
        if show_win and win is not None:
            words += "　" + _text(f"胜率 {_pct(win)}", size=13, color=MUTED)
        out += [_heading("加点顺序"), words]
    return "".join(out)


def _other_items(d, icons, show_win, compact):
    builds = d.get("builds") or {}
    rows = []
    for title, entries in (("出门装", (builds.get("start") or [])[:1]),
                           ("鞋子", (builds.get("shoes") or [])[:2]),
                           ("常出装备", (d.get("item_stats") or [])[:6])):
        for i, entry in enumerate(entries):
            items = entry.get("items") or [entry["item"]]
            cells = [_text(title if i == 0 else "", color=MUTED),
                     " + ".join(_named_item(icons, it, 22) for it in items)]
            if show_win:
                cells.append(_text(_pct(entry.get("win")), color=ACCENT))
            rows.append(cells)
    if not rows:
        return ""
    return _heading("其他装备") + _table(["类型", "装备"] + (["胜率"] if show_win else []),
                                         rows, numeric=(2,), compact=compact)


def hero_html(d, icons, show_win, reliable_games=recommend.RELIABLE_GAMES, *, compact=False):
    core = _core_routes(d, icons, show_win, compact)
    ranking = _augment_ranking(d, reliable_games, compact)
    detail = _spells_and_skills(d, icons, show_win, compact) + _other_items(d, icons, show_win, compact)
    if not compact and ranking and detail:
        lower = ("<table width='100%' cellspacing='0' cellpadding='0'><tr>"
                 f"<td width='52%' valign='top'>{ranking}</td><td width='3%'></td>"
                 f"<td width='45%' valign='top'>{detail}</td></tr></table>")
    else:
        lower = ranking + detail
    return core + lower or _text("当前英雄暂无装备或海克斯资料", color=MUTED)


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
        lines.append(_text("样本太少" if row.get("thin") == "too_few" else "样本偏少", color="#835b24"))
    if verdict == "nodata":
        note = {"excluded": recommend.NODATA_NOTE, "new": recommend.NEW_NOTE,
                "rare": "本英雄暂无可靠样本", "tier_only": "仅有官方评级，暂无胜率样本"}.get(
                    row.get("basis"), "暂无可靠样本")
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
