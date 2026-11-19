"""Local diagnostic redaction helpers; remote logs and remote debug are disabled."""

from __future__ import annotations

import logging
import os
import re

import requests

from . import cloud

log = logging.getLogger(__name__)
MAX_BYTES = 512 * 1024
# 只保留本程序固定诊断事件中的计数/单位，不把任意文本里的数字当作性能数据。
_DIAGNOSTIC_EVENT = re.compile(
    r"^(?:推荐状态发布|扫描诊断|这局认字|运行资源|OCR(?:整块|标题)耗时|运行环境)：")
_LOG_HEADER = re.compile(
    r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} "
    r"(?:DEBUG|INFO|WARNING|ERROR|CRITICAL) lolhex(?:\.[a-z_]+)*: ")
_DIAGNOSTIC_NUMBER = re.compile(
    r"(?:\b(?:scan|observation|capture|work|after|total|frame_age)|文本行|输入|逻辑核|"
    r"可用/总内存|标题间隔|启动扫描间隔|已运行|本程序内存|系统可用/总内存|总计|等待锁|检测|认字)="
    r"\d+(?:\.\d+)?(?:/\d+)?(?:x\d+)?(?:ms|MB|毫秒|秒|小时)?(?=\s|[；;）)\r\n]|$)"
    r"|(?:标题条|整块扫描|标题OCR|平均) \d+(?:\.\d+)?(?=\s*(?:次|毫秒))"
    r"|(?<=CPU )\d+(?=）)"
    r"|(?<=峰值)\d+(?=MB)"
    r"|(?<=私有)\d+(?=MB)")


def _redact_names(text: str, patterns: list[re.Pattern]) -> str:
    for pattern in patterns:
        text = pattern.sub("<已去掉>", text)
    return text


def _redact_line(line: str, patterns: list[re.Pattern]) -> str:
    header = _LOG_HEADER.match(line)
    prefix = header.group() if header else ""
    message = line[len(prefix):]
    event = _DIAGNOSTIC_EVENT.match(message)
    if not event:
        return prefix + _redact_names(message, patterns)
    # 数字原样拷贝，其余仍脱敏；不用可与用户名字相撞的临时占位符。
    parts, end = [prefix, event.group()], event.end()
    for match in _DIAGNOSTIC_NUMBER.finditer(message, end):
        parts.extend((_redact_names(message[end:match.start()], patterns), match.group()))
        end = match.end()
    parts.append(_redact_names(message[end:], patterns))
    return "".join(parts)


def apply_verbose(settings, cfg: dict, now: float | None = None) -> bool:
    """Only local debug_mode controls detailed logging."""
    # Only an explicit local debug switch may enable detailed logging.
    verbose = bool(getattr(settings, "debug_mode", False))
    logging.getLogger().setLevel(logging.DEBUG if verbose else logging.INFO)
    return verbose


def redact(text: str, riot_id: str = "") -> str:
    """去掉日志里能认出人的东西：游戏账号名、Windows 用户名（含路径里的）、计算机名。"""
    names = []
    rid = (riot_id or "").strip()
    if rid:
        names += [rid, rid.rpartition("#")[0]]
    for var in ("USERNAME", "USER", "COMPUTERNAME", "USERDOMAIN"):
        v = os.environ.get(var) or ""
        if len(v) >= 2:
            names.append(v)
    # 用户文件夹名可以带空格：一直到下一个 \ / 引号 或行尾
    text = re.sub(r"(?i)([A-Z]:[\\/]+(?:Users|Documents and Settings)[\\/]+)[^\\/\"'\r\n：]+", r"\1<用户>", text)
    text = re.sub(r"(/(?:home|Users)/)[^/\"'\r\n]+", r"\1<用户>", text)
    if "#" in rid:
        text = re.sub(re.escape(rid), "<游戏账号>", text, flags=re.I)
    # 名字#编号 这种写法（别人的游戏账号也可能出现在日志里）
    text = re.sub(r"[^\s#：:，,（()）\[\]\"'<>]{1,16}#[0-9A-Za-z]{3,5}(?![0-9A-Za-z])", "<游戏账号>", text)
    patterns = []
    for name in sorted({n for n in names if n and len(n) >= 2}, key=len, reverse=True):
        # ASCII 名称只匹配完整标识，Win/78 不应破坏 Windows/178ms；中文周围常没有空格。
        pattern = re.escape(name)
        if name.isascii():
            pattern = r"(?<![A-Za-z0-9_])" + pattern + r"(?![A-Za-z0-9_])"
        patterns.append(re.compile(pattern, re.I))
    return "".join(_redact_line(line, patterns) for line in text.splitlines(keepends=True))


def _read_recent(folder, limit: int) -> bytes:
    """最近 limit 字节日志：先取 ddhex.log 结尾，不够再从 ddhex.log.1 结尾补在前面。"""
    data = _read_tail(folder / "ddhex.log", limit)
    rest = limit - len(data)
    older = folder / "ddhex.log.1"
    if rest > 4096 and older.is_file():
        try:
            data = _read_tail(older, rest) + data
        except OSError:
            pass
    return data


def _limit(cfg: dict) -> int:
    kb = ((cfg or {}).get("logs") or {}).get("max_kb")
    if isinstance(kb, bool) or not isinstance(kb, (int, float)):
        return MAX_BYTES
    return int(max(64, min(4096, kb))) * 1024


def _read_tail(path, limit: int) -> bytes:
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        size = f.tell()
        f.seek(max(0, size - limit))
        data = f.read()
    if size > limit:  # 从中间截的：丢掉半行
        data = data.split(b"\n", 1)[-1]
    return data


def maybe_upload(settings, cfg: dict, timeout: float = 30) -> list[str]:
    """云控点名了本机就上传日志；返回这次传成功的单号。不在主线程调用。"""
    # No setting or copied cloud request can re-enable log uploading.
    return []
