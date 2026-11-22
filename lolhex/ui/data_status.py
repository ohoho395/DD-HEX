"""数据来源一行字（主窗口和浮窗共用），文字都已转义。"""
from datetime import datetime, timedelta, timezone
from html import escape


def _bjt(value, fmt="%m-%d"):
    try:
        stamp = datetime.fromisoformat(str(value))
        if stamp.tzinfo is not None:
            return stamp.astimezone(timezone(timedelta(hours=8))).strftime(fmt)
    except (TypeError, ValueError):
        pass
    return ""


def data_status_html(d):
    if not d.get("dataset"):
        parts = ["没有统计数据"]
    else:
        parts = ([d["dataset_mode_label"]] if d.get("dataset_mode_label") else []) + [f"{d.get('dataset_patch')} 版本"]
        matches = d.get("dataset_matches")
        if isinstance(matches, int):
            parts.append(f"{matches / 10000:.0f} 万局")
        day = _bjt(d.get("dataset_snapshot"))
        if day:
            parts.append(f"截至 {day}")
        if d.get("patch") and d.get("dataset_patch") and d["patch"] != d["dataset_patch"]:
            parts.append(f"官方资料 {d['patch']} 版本")
    if d.get("event_fallback") and d.get("event_label"):
        parts.append(f"{d['event_label']}的数据还没出，先用常规")
    if d.get("error"):
        parts.append("官方资料获取失败")
    return escape(" · ".join(parts))


_CHECK_MESSAGES = {
    "disabled": "统计更新已关闭，正在使用本地快照",
    "never_checked": "尚未完成远程统计检查",
    "deferred": "对局中，统计检查已推迟到对局结束",
    "checking": "统计检查正在进行，请稍候",
    "staged": "新统计已下载，等待对局结束后启用",
    "updated": "统计数据已更新",
    "unchanged": "已核对远端，当前统计无需更新",
    "failed": "统计检查失败，继续使用本地快照，可稍后重试",
    "offer": "有统计更新等待确认",
}


def statistics_check_message(d):
    state = d.get("data_check_state") or "never_checked"
    text = _CHECK_MESSAGES.get(state, _CHECK_MESSAGES["never_checked"])
    if d.get("dataset_patch"):
        day = _bjt(d.get("dataset_snapshot"))
        text += f"（{d['dataset_patch']} 版本" + (f"，样本截至 {day}" if day else "") + "）"
    return text + "。"


def statistics_settings_text(d, *, enabled, update_source=""):
    """Visible audit trail distinguishes sample freshness from remote checks."""
    current = dict(d)
    if not enabled:
        current["data_check_state"] = "disabled"
    origin = {"bundled": "内置快照", "downloaded": "已下载快照"}.get(d.get("dataset_origin"), "本地快照")
    stamp = d.get("data_last_checked_at")
    try:
        checked = datetime.fromtimestamp(stamp, timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S（北京时间）") if stamp else "尚未成功检查"
    except (TypeError, ValueError, OverflowError, OSError):
        checked = "尚未成功检查"
    return (statistics_check_message(current) + f"\n统计来源：{origin} · GitHub 公开统计"
            + f"\n上次成功检查：{checked}"
            + (f"\n软件更新源：{update_source}" if update_source else "\n软件更新：未配置独立发布源"))
